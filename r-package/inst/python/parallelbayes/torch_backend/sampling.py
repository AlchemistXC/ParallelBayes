"""Batch torch entry point: explicit resources, fixed tapes, failure quarantine."""
import hashlib
import time
import numpy as np
import torch
from ..reference import Model, numpy_reference
from ..output import constrain_checked
from .models import make_model
from .kernels import transition
from .executors import execute

DEFAULTS = dict(kernel="mala",executor="sequential",device="cpu",draws=64,chains=1,
    seed=2026,solver_seed=7103,step_size=.05,window=16,max_iter=256,atol=1e-10,rtol=1e-10,
    jacobian_clip=1.,memory_limit_mb=2048,initial=None,on_failure="error",audit=True)


def settings(config=None):
    if set(config or {})-set(DEFAULTS):
        raise ValueError("unknown torch settings")
    c = dict(DEFAULTS,**(config or {}))
    for k in ("draws","chains","window","max_iter","memory_limit_mb","seed","solver_seed"):
        if isinstance(c[k],bool) or not np.isfinite(c[k]) or int(c[k])!=c[k] or c[k]<(0 if k.endswith("seed") else 1):
            raise ValueError("invalid "+k)
        c[k] = int(c[k])
    for k in ("step_size","atol","rtol","jacobian_clip"):
        if not np.isfinite(c[k]) or c[k]<=0:
            raise ValueError("invalid "+k)
    if (c["kernel"],c["executor"]) not in (("mala","sequential"),("rwm","sequential"),
            ("mala","quasi_deer"),("rwm","online_picard")):
        raise ValueError("unsupported torch kernel/executor combination")
    if c["device"] not in ("cpu","cuda","cuda:0") or c["on_failure"] not in ("error","sequential"):
        raise ValueError("unsupported device/failure policy")
    if not isinstance(c["audit"],bool):
        raise ValueError("audit must be boolean")
    return c


def random_tape(c,d):
    shape = (c["chains"],c["draws"],d)
    rng = np.random.Generator(np.random.Philox(np.random.SeedSequence([c["seed"],101])))
    solver = np.random.Generator(np.random.Philox(np.random.SeedSequence([c["solver_seed"],102])))
    return dict(noise=rng.standard_normal(shape),
        log_uniform=np.log(np.maximum(rng.random(shape[:2]),np.finfo(float).tiny)),
        directions=(2*solver.integers(0,2,size=shape)-1).astype(float))


def tape_hash(tape):
    h = hashlib.sha256()
    for k in sorted(tape):
        a = np.ascontiguousarray(tape[k],dtype="<f8")
        h.update(k.encode());h.update(str(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()


def sync(device):
    if device.type=="cuda":
        torch.cuda.synchronize(device)


def audit_path(model,c,q0,tape,path,accept):
    errors,branches,constrained = [],[],[]
    try:
        for i in range(c["chains"]):
            ref,acc = numpy_reference(model,c["kernel"],q0[i],tape["noise"][i],tape["log_uniform"][i],c["step_size"])
            errors.append(float(np.max(np.abs(ref-path[i]))))
            branches.append(int(np.sum(acc!=accept[i])))
            with np.errstate(over="raise",invalid="raise"):
                constrained.append(float(np.max(np.abs(model.constrain(ref)-model.constrain(path[i])))))
        limits = [100*(c["atol"]+c["rtol"]*max(1.,float(np.max(np.abs(p))))) for p in path]
        passed = all(e<=limit for e,limit in zip(errors,limits)) and not any(branches)
        return dict(passed=passed,max_abs_path_error=errors,acceptance_mismatches=branches,
                    max_abs_constrained_error=constrained,oracle="independent_numpy_float64")
    except (ValueError,RuntimeError,FloatingPointError,OverflowError) as exc:
        return dict(passed=False,error=f"{type(exc).__name__}: {exc}",failed_chain=i,
                    max_abs_path_error=errors,acceptance_mismatches=branches)


def sample(spec,config=None,tape=None):
    started = time.perf_counter()
    c = settings(config)
    model = spec if isinstance(spec,Model) else make_model(spec,c["device"])
    if model.backend!="torch":
        raise ValueError("torch sampling requires an explicit torch target")
    requested = torch.device(c["device"])
    if model.device.type!=requested.type or (requested.index is not None and model.device.index not in (None,requested.index)):
        raise ValueError("model and requested device differ")
    d = model.dimension
    estimated = c["chains"]*(c["draws"]+c["window"])*d*8*40
    if estimated>c["memory_limit_mb"]*1024**2:
        raise MemoryError("array-workspace estimate exceeds configured limit; not a strict allocator bound")
    t = time.perf_counter()
    tape = random_tape(c,d) if tape is None else tape
    shape = (c["chains"],c["draws"],d)
    for k,expected in (("noise",shape),("directions",shape),("log_uniform",shape[:2])):
        if k not in tape or np.asarray(tape[k]).shape!=expected or not np.isfinite(tape[k]).all():
            raise ValueError("invalid actual random array: "+k)
    if (np.asarray(tape["log_uniform"])>0).any() or not np.isin(tape["directions"],[-1.,1.]).all():
        raise ValueError("invalid log uniforms or Rademacher directions")
    q0 = np.zeros((c["chains"],d)) if c["initial"] is None else np.asarray(c["initial"],float)
    if q0.shape==(d,):
        q0 = np.broadcast_to(q0,(c["chains"],d)).copy()
    if q0.shape!=(c["chains"],d) or not np.isfinite(q0).all():
        raise ValueError("invalid initial coordinates")
    args = tuple(torch.tensor(a,dtype=torch.float64,device=model.device) for a in
                 (q0,tape["noise"],tape["log_uniform"],tape["directions"]))
    sync(model.device)
    inputs = time.perf_counter()-t
    if model.device.type=="cuda":
        torch.cuda.reset_peak_memory_stats(model.device)
    step = transition(model.log_density,c["kernel"])
    timing = dict(input=inputs,compile=0.,warmup=0.,sample=0.,transfer=0.,audit=0.,fallback=0.,transform=0.)
    def run(cc):
        sync(model.device); begin = time.perf_counter()
        path,accept,stats = execute(step,*args,cc)
        sync(model.device); duration = time.perf_counter()-begin
        begin = time.perf_counter()
        pn,an = path.detach().cpu().numpy(),accept.detach().cpu().numpy()
        timing["transfer"] += time.perf_counter()-begin
        return path,pn,an,stats,duration
    path,pn,an,stats,timing["sample"] = run(c)
    primary = stats.copy();primary_accept = an.copy();primary_path = None
    audit = None
    valid = stats["status"]==0 and np.isfinite(pn).all()
    if c["audit"] and valid:
        t=time.perf_counter();audit=audit_path(model,c,q0,tape,pn,an);timing["audit"]+=time.perf_counter()-t
        valid = audit["passed"]
    primary_audit = audit
    fallback = bool(not valid and c["on_failure"]=="sequential" and c["executor"]!="sequential")
    if fallback:
        primary_path = pn.copy()
        path,pn,an,stats,timing["fallback"] = run(dict(c,executor="sequential"))
        valid = stats["status"]==0 and np.isfinite(pn).all()
        if c["audit"] and valid:
            t=time.perf_counter();audit=audit_path(model,c,q0,tape,pn,an);timing["audit"]+=time.perf_counter()-t
            valid = audit["passed"]
    t=time.perf_counter()
    theta,error = constrain_checked(model,pn) if valid else (None,None)
    if valid and error is None:
        device_theta = model.constrain_device(path).detach().cpu().numpy()
        if not np.isfinite(device_theta).all() or not np.allclose(device_theta,theta,rtol=1e-10,atol=1e-12):
            error="device constraint output differs from independent NumPy transform"
    timing["transform"] = time.perf_counter()-t
    valid = bool(valid and error is None)
    memory = dict(estimated_array_workspace_bytes=estimated)
    if model.device.type=="cuda":
        memory.update(peak_allocated_bytes=torch.cuda.max_memory_allocated(model.device),
                      peak_reserved_bytes=torch.cuda.max_memory_reserved(model.device))
    timing["total"] = time.perf_counter()-started
    return dict(status="completed" if valid else "failed",draws=theta if valid else None,
        unconstrained=pn if valid else None,failed_trajectory=None if valid else pn,
        primary_failed_trajectory=primary_path,accept=an,primary_accept=primary_accept,
        diagnostics=stats,primary_diagnostics=primary,audit=audit,primary_audit=primary_audit,
        transform_error=error,fallback=fallback,config=c,names=model.names,target_id=model.target_id,
        coordinate_id=model.spec["coordinate_id"],tape_sha256=tape_hash(tape),timing=timing,memory=memory,
        guarantee="independently_audited_fixed_tape" if valid and c["audit"] else "executor_output_standard_only",
        stopping_reason="output_standard_met" if valid else ("transform_failed" if error else "solver_or_audit_failed"),
        state_repairs=0,implementation="torch eager; Python round control; no compiled device-loop claim")


def capabilities(spec=None):
    # Runtime availability is distinct from checked-in validation evidence.
    if spec is not None:
        make_reference_spec = make_model(spec,"cpu")
        del make_reference_spec
    return dict(provider="native_torch",dtype="float64",continuous_latents_only=True,
        combinations=[["mala","sequential"],["rwm","sequential"],["mala","quasi_deer"],["rwm","online_picard"]],
        available_devices=["cpu"]+(["cuda:0"] if torch.cuda.is_available() else []),
        verification_scope="See execution/windows-native validation receipts; availability is not target certification",
        validation_evidence=dict(version="0.2.0.dev1",torch="2.13.0+cu130",os="Windows 11",
            devices=["AMD CPU", "RTX 5080 sm_120"],target_kinds=["gaussian","logistic","lognormal",
                "funnel","funnel_noncentered","mixture","normal_mean"],
            note="Finite tested specs and tapes; other data/custom models require validation"),
        arbitrary_stan_translation=False,nuts=False,compiled_device_control=False)


def environment():
    import platform
    import sys
    import psutil
    return dict(provider="native_torch",python=sys.version,python_executable=sys.executable,
        os=platform.platform(),torch=torch.__version__,cuda_build=torch.version.cuda,
        cuda_available=torch.cuda.is_available(),gpu_name=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        ram_bytes=psutil.virtual_memory().total,cpu_threads=torch.get_num_threads(),dtype="float64")
