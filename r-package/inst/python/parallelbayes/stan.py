"""BridgeStan CPU provider. C++ density/AD, serial Python orchestration.

One model instance is owned by this process; no shared pointer or nested threads.
Every call requests the Jacobian in Stan's unconstrained coordinates.
"""
import hashlib
import os
import platform
from pathlib import Path
import time
import numpy as np
from .models import Model
from .kernels import numpy_reference, ReferenceFailure
from .output import constrain_checked


def stan_model(spec):
    import bridgestan as bs
    source = Path(spec['stan_file']).expanduser().resolve()
    if not source.is_file() or source.suffix != '.stan':
        raise ValueError('stan_file must name an existing .stan source')
    root = os.environ.get('BRIDGESTAN')
    if not root:
        candidate = Path.cwd()/'environment/bridgestan-2.7.0'
        if candidate.is_dir(): root = str(candidate)
    if not root:
        raise RuntimeError('Set BRIDGESTAN to the extracted, pinned source distribution')
    bs.set_bridgestan_path(root)
    started = time.perf_counter()
    build_args=['STAN_THREADS=', 'O=1']
    if platform.system()=='Darwin' and platform.machine()=='arm64':
        build_args.append('arch=arm64')  # avoid sandbox sysctl misdetecting TBB as ia32
    library = bs.compile_model(source, make_args=build_args)
    model = bs.StanModel(library, data=spec.get('data', {}), seed=1234, warn=False)
    compile_seconds = time.perf_counter()-started
    d = model.param_unc_num()
    spec = dict(spec, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                dimension=d, coordinate_id=spec.get('coordinate_id', 'stan-default-unconstrained'),
                threads=False, propto=True, jacobian=True)
    logp = lambda q: model.log_density(np.ascontiguousarray(q, dtype=np.float64), jacobian=True)
    gradient = lambda q: model.log_density_gradient(np.ascontiguousarray(q, dtype=np.float64), jacobian=True)[1]
    def constrain(q):
        a = np.asarray(q)
        flat = np.asarray([model.param_constrain(np.ascontiguousarray(row)) for row in a.reshape(-1,d)])
        return flat.reshape(a.shape[:-1]+(model.param_num(),))
    result = Model(spec,d,logp,logp,gradient,constrain,model.param_names(),backend='bridgestan')
    result.stan = model
    result.compile_seconds = compile_seconds
    return result


def sample_stan(model,c,tape=None):
    from .sampling import random_tape,tape_hash
    if c['executor']!='sequential' or c['kernel']=='nuts' or c['platform']!='cpu':
        raise ValueError('BridgeStan provider supports CPU sequential RWM/MALA only')
    if c['audit']:raise ValueError('Independent trajectory audit is unavailable for arbitrary Stan models; use explicit cross-provider validation')
    if c['chains']*c['draws']*model.dimension*8*40 > c['memory_limit_mb']*1024**2:
        raise MemoryError('workspace estimate exceeds limit')
    started=time.perf_counter()
    tape=random_tape(c,model.dimension) if tape is None else tape
    expected=(c['chains'],c['draws'],model.dimension)
    for key,shape in [('noise',expected),('log_uniform',expected[:2]),('directions',expected)]:
        if np.asarray(tape[key]).shape!=shape or not np.isfinite(tape[key]).all():
            raise ValueError('invalid random tape')
    if (np.asarray(tape['log_uniform'])>0).any(): raise ValueError('invalid log_uniform')
    q0=np.zeros((c['chains'],model.dimension)) if c['initial'] is None else np.asarray(c['initial'],float)
    if q0.shape==(model.dimension,): q0=np.broadcast_to(q0,(c['chains'],model.dimension))
    if q0.shape!=(c['chains'],model.dimension) or not np.isfinite(q0).all(): raise ValueError('invalid initial state')
    paths=np.full(expected,np.nan); accepted=np.zeros(expected[:2],dtype=bool); error=None
    completed_steps=np.zeros(c["chains"],dtype=int); failed_chain=None
    t=time.perf_counter()
    try:
        for i in range(c['chains']):
            path,acc=numpy_reference(model,c['kernel'],q0[i],tape['noise'][i],tape['log_uniform'][i],c['step_size'],strict=True)
            paths[i]=path; accepted[i]=acc; completed_steps[i]=len(path)
    except (RuntimeError,ValueError,FloatingPointError) as exc:
        error=str(exc); failed_chain=i
        if isinstance(exc,ReferenceFailure):
            completed_steps[i]=len(exc.draws)
            paths[i,:len(exc.draws)]=exc.draws; accepted[i,:len(exc.accepts)]=exc.accepts
    execution=time.perf_counter()-t
    paths=np.asarray(paths)
    valid=error is None and np.isfinite(paths).all()
    t=time.perf_counter()
    draws,transform_error=constrain_checked(model,paths) if valid else (None,None)
    valid &= transform_error is None
    transform_seconds=time.perf_counter()-t
    return dict(status='completed' if valid else 'failed',draws=draws,
                unconstrained=paths if valid else None,failed_trajectory=paths if not valid else None,
                config=c,names=model.names,target_id=model.target_id,coordinate_id=model.spec['coordinate_id'],
                guarantee='sequential_kernel',fallback=False,tape_sha256=tape_hash(tape),
                diagnostics=dict(accept=accepted,error=error,completed_steps=completed_steps,failed_chain=failed_chain),
                transform_error=transform_error,
                audit=dict(note='Use cross-provider validation for an independent check'),
                timing=dict(compile=model.compile_seconds,sample=execution,transfer=0.,transform=transform_seconds,
                            total=time.perf_counter()-started+model.compile_seconds))


def cross_validate(stan,native,points):
    density=[]; gradients=[]; transforms=[]
    q0=np.asarray(points[0],float)
    offset=stan.log_density(q0)-native.reference(q0)
    for point in points:
        q=np.asarray(point,float)
        density.append(abs(stan.log_density(q)-native.reference(q)-offset))
        gradients.append(float(np.max(np.abs(stan.gradient_reference(q)-native.gradient_reference(q)))))
        transforms.append(float(np.max(np.abs(stan.constrain(q)-native.constrain(q)))))
    return dict(density_error=max(density),gradient_error=max(gradients),transform_error=max(transforms),
                constant_offset=float(offset),passed=max(density)<1e-8 and max(gradients)<1e-7 and max(transforms)<1e-8,
                reference='Stan vs independent NumPy with common coordinates and Jacobian')
