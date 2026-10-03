"""Batch sampling interface with honest numerical guarantees and cost accounting."""
import hashlib
import json
import os
import platform
import time
from dataclasses import dataclass
import numpy as np
import jax
import jax.numpy as jnp
from .models import make_model, Model
from .executors import program
from .kernels import numpy_reference
from .output import constrain_checked

DEFAULTS = dict(kernel="mala", executor="sequential", draws=256, chains=1, seed=2026,
                solver_seed=7103, step_size=0.05, window=64, max_iter=256,
                atol=1e-10, rtol=1e-10, jacobian_clip=1., platform=os.environ.get("PB_TEST_PLATFORM", "cpu"),
                on_failure="error", audit=False, warmup=256, max_tree_depth=8,
                memory_limit_mb=2048, initial=None, timing_repeats=1)


def settings(config):
    unknown = set(config or {})-set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown settings: {sorted(unknown)}")
    c = dict(DEFAULTS, **(config or {}))
    for k in ("draws", "chains", "window", "max_iter", "warmup", "max_tree_depth", "memory_limit_mb", "timing_repeats"):
        if not float(c[k]).is_integer() or c[k] < 1:
            raise ValueError(f"{k} must be a positive integer")
        c[k] = int(c[k])
    for k in ("seed", "solver_seed"):
        if not float(c[k]).is_integer() or c[k] < 0:
            raise ValueError(f"{k} must be a nonnegative integer")
        c[k] = int(c[k])
    for k in ("step_size", "atol", "rtol", "jacobian_clip"):
        if not np.isfinite(c[k]) or c[k] <= 0:
            raise ValueError(f"{k} must be finite and positive")
    if c["kernel"] not in ("mala", "rwm", "nuts") or c["executor"] not in (
            "sequential", "quasi_deer", "online_picard"):
        raise ValueError("unsupported kernel or executor")
    if c["executor"] == "online_picard" and c["kernel"] != "rwm":
        raise ValueError("Online Picard currently supports only RWM increments")
    if c["executor"] == "quasi_deer" and c["kernel"] != "mala":
        raise ValueError("quasi-DEER currently supports only MALA")
    if c["on_failure"] not in ("error", "sequential") or c["platform"] not in ("cpu", "gpu"):
        raise ValueError("invalid failure policy or platform")
    return c


def capabilities(spec=None):
    stan = spec is not None and spec.get("kind") == "stan"
    return dict(provider="bridgestan_cpu" if stan else "native_jax",
                kernels=["rwm", "mala"] if stan else ["rwm", "mala", "nuts"],
                executors=["sequential"] if stan else ["sequential", "online_picard", "quasi_deer"],
                combinations=[["rwm", "sequential"], ["mala", "sequential"]] + ([] if stan else [
                    ["rwm", "online_picard"], ["mala", "quasi_deer"], ["nuts", "sequential"]]),
                dtype="float64", available_devices=[str(d) for d in jax.devices()],
                gpu_runtime_verified=False, arbitrary_stan_to_jax=False, independent_trajectory_audit=not stan)


def random_tape(c, d):
    shape = (c["chains"], c["draws"], d)
    rng = np.random.Generator(np.random.Philox(np.random.SeedSequence([c["seed"], 101])))
    solver = np.random.Generator(np.random.Philox(np.random.SeedSequence([c["solver_seed"], 102])))
    z = rng.standard_normal(shape)
    logu = np.log(np.maximum(rng.random(shape[:2]), np.finfo(float).tiny))
    v = (2*solver.integers(0, 2, size=shape)-1).astype(float)
    return dict(noise=z, log_uniform=logu, directions=v)


def tape_hash(tape):
    h = hashlib.sha256()
    for k in sorted(tape):
        a = np.ascontiguousarray(tape[k], dtype=np.float64)
        h.update(k.encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def environment():
    import importlib.metadata as md
    import psutil
    packages = {}
    for p in ("jax", "jaxlib", "blackjax", "numpy", "scipy", "bridgestan", "parallelbayes"):
        try:
            packages[p] = md.version(p)
        except md.PackageNotFoundError:
            packages[p] = None
    return dict(system=platform.system(), machine=platform.machine(), python=platform.python_version(),
                host=platform.node(), os_release=platform.release(),
                processor=platform.processor(), logical_cpus=psutil.cpu_count(),
                memory_bytes=psutil.virtual_memory().total, packages=packages,
                devices=[dict(platform=d.platform, kind=d.device_kind, id=d.id) for d in jax.devices()],
                x64=jax.config.x64_enabled)


@dataclass
class Prepared:
    model: Model
    config: dict
    compiled: object
    args: tuple
    compile_seconds: float
    input_seconds: float
    tape: dict
    q0: np.ndarray

    def run(self):
        t = time.perf_counter()
        path, stats = self.compiled(*self.args)
        jax.block_until_ready((path, stats))
        elapsed = time.perf_counter()-t
        t = time.perf_counter()
        paths = np.asarray(path)
        details = {k: np.asarray(v) for k, v in stats.items()}
        return paths, details, elapsed, time.perf_counter()-t


def prepare(model, c, tape=None):
    estimated = c["chains"]*(c["draws"]+c["window"])*model.dimension*8*40
    if estimated > c["memory_limit_mb"]*1024**2:
        raise MemoryError("conservative array-workspace estimate exceeds configured limit")
    t = time.perf_counter()
    tape = random_tape(c, model.dimension) if tape is None else tape
    shape = (c["chains"], c["draws"], model.dimension)
    for k, expected in (("noise", shape), ("directions", shape), ("log_uniform", shape[:2])):
        if k not in tape or np.asarray(tape[k]).shape != expected or not np.isfinite(tape[k]).all():
            raise ValueError(f"invalid {k} shape or nonfinite tape")
    if (np.asarray(tape["log_uniform"])>0).any():
        raise ValueError("log_uniform must be <= 0")
    q0 = np.zeros((c["chains"], model.dimension)) if c["initial"] is None else np.asarray(c["initial"], float)
    if q0.shape == (model.dimension,):
        q0 = np.broadcast_to(q0, (c["chains"], model.dimension)).copy()
    if q0.shape != (c["chains"], model.dimension) or not np.isfinite(q0).all():
        raise ValueError("invalid initial state")
    device = jax.devices(c["platform"])[0]
    with jax.default_device(device):
        args = tuple(jax.device_put(jnp.asarray(a, dtype=jnp.float64), device) for a in (
            q0, tape["noise"], tape["log_uniform"], tape["directions"], c["step_size"]))
        jax.block_until_ready(args)
        input_seconds = time.perf_counter()-t
        t = time.perf_counter()
        fn = program(model, c["kernel"], c["executor"], min(c["window"], c["draws"]),
                     c["max_iter"], c["atol"], c["rtol"], c["jacobian_clip"])
        compiled = fn.lower(*args).compile()
        compile_seconds = time.perf_counter()-t
    return Prepared(model, c, compiled, args, compile_seconds, input_seconds, tape, q0)


def sample(spec, config=None, tape=None):
    started = time.perf_counter()
    c = settings(config)
    model = spec if isinstance(spec, Model) else make_model(spec)
    if model.backend == "bridgestan":
        from .stan import sample_stan
        return sample_stan(model, c, tape)
    if c["kernel"] == "nuts":
        if tape is not None:
            raise ValueError("NUTS uses its own keyed random stream, not the fixed MH tape")
        from .nuts import sample_nuts
        return sample_nuts(model, c)
    prepared = prepare(model, c, tape)
    draws, diagnostics, execution, transfer = prepared.run()
    cached_times=[]
    replay_started=time.perf_counter()
    for _ in range(c["timing_repeats"]-1):
        replay, _, seconds, _ = prepared.run()
        if not np.array_equal(replay,draws,equal_nan=True):
            raise RuntimeError("Repeated compiled execution changed the fixed-tape output")
        cached_times.append(seconds)
    timing_replay_cost=time.perf_counter()-replay_started
    primary = {k: v.copy() for k, v in diagnostics.items()}
    primary_failed_trajectory = None
    fallback = 0.
    fell_back = bool(np.any(diagnostics["status"])) and c["on_failure"] == "sequential"
    if fell_back:
        primary_failed_trajectory=draws.copy()
        t = time.perf_counter()
        sequential = prepare(model, dict(c, executor="sequential", on_failure="error"), prepared.tape)
        draws, diagnostics, _, _ = sequential.run()
        fallback = time.perf_counter()-t
    valid = not np.any(diagnostics["status"]) and bool(np.isfinite(draws).all())
    audit = None
    t = time.perf_counter()
    if c["audit"] and valid:
        errors, branches = [], []
        try:
            for i in range(c["chains"]):
                reference, accept = numpy_reference(model, c["kernel"], prepared.q0[i],
                    prepared.tape["noise"][i], prepared.tape["log_uniform"][i], c["step_size"])
                errors.append(float(np.max(np.abs(reference-draws[i]))))
                branches.append(int(np.sum(accept != diagnostics["accept"][i])))
            audit = dict(max_abs_path_error=errors, acceptance_mismatches=branches,
                         comparison="independent_numpy_float64", exact_bitwise_claim=False)
            valid &= all(x==0 for x in branches) and all(
                errors[i] <= 100*(c["atol"]+c["rtol"]*max(1.,float(np.max(np.abs(draws[i])))))
                for i in range(c["chains"]))
        except (RuntimeError, ValueError, FloatingPointError, OverflowError) as exc:
            valid=False
            audit=dict(error=f'{type(exc).__name__}: {exc}', failed_chain=i,
                       max_abs_path_error=errors, acceptance_mismatches=branches)
    audit_seconds = time.perf_counter()-t
    guarantee = "sequential_kernel" if c["executor"] == "sequential" or fell_back else (
        "increment_prefix_consistency_float64" if c["executor"] == "online_picard" else
        "numerical_recurrence_residual_only")
    transform_started=time.perf_counter()
    constrained, transform_error=constrain_checked(model,draws) if valid else (None,None)
    transform_seconds=time.perf_counter()-transform_started
    valid &= transform_error is None
    return dict(status="completed" if valid else "failed", draws=constrained if valid else None,
                unconstrained=draws if valid else None, failed_trajectory=draws if not valid else None,
                primary_failed_trajectory=primary_failed_trajectory, transform_error=transform_error,
                diagnostics=diagnostics, primary_diagnostics=primary, audit=audit,
                guarantee=guarantee, fallback=fell_back, target_id=model.target_id,
                stopping_reason=("output_standard_met" if valid else ("transform_failed" if transform_error else ("audit_mismatch" if audit is not None else "solver_status_failed"))),
                state_repairs=0, cached_execution_seconds=cached_times,
                timing_replay_overhead=timing_replay_cost,
                coordinate_id=model.spec["coordinate_id"], names=model.names, config=c,
                tape_sha256=tape_hash(prepared.tape),
                timing=dict(input=prepared.input_seconds, compile=prepared.compile_seconds,
                            sample=execution, transfer=transfer, audit=audit_seconds,
                            fallback=fallback, transform=transform_seconds,total=time.perf_counter()-started-timing_replay_cost))


def validate_model(spec, points=None):
    model = spec if isinstance(spec, Model) else make_model(spec)
    d = model.dimension
    if model.backend != "jax":
        return dict(passed=False, reference="independent reference required",
                    note="Use stan.cross_validate with explicit common-coordinate points")
    if points is None:
        points = np.vstack((np.zeros(d), np.ones(d), -np.ones(d), np.ones(d)*5))
    points = np.asarray(points, float)
    if points.ndim != 2 or points.shape[1] != d:
        raise ValueError("validation points must have shape (points, dimension)")
    grad = jax.grad(model.log_density) if model.backend == "jax" else model.gradient_reference
    offset = float(model.log_density(points[0]))-model.reference(points[0])
    density, gradients = [], []
    for q in points:
        density.append(abs(float(model.log_density(q))-model.reference(q)-offset))
        gradients.append(float(np.max(np.abs(np.asarray(grad(q))-model.gradient_reference(q)))))
    return dict(target_id=model.target_id, max_relative_log_density_error=max(density),
                max_gradient_error=max(gradients),
                passed=max(density)<1e-8 and max(gradients)<1e-7,
                reference="independent_numpy" if model.backend=="jax" else "same_Stan_provider_not_independent")
