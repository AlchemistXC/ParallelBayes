"""F3 CPU-only Pyro baseline using documented Model/MCMC interfaces.

Chains run serially. Explicit starts and RNG snapshots are retained. Adaptation
is discarded warmup; MH fixed-tape equivalence and CUDA NUTS are not claimed.
The original frozen baseline is not modified by this companion implementation.
"""
import random
import time
import traceback
import numpy as np
import torch
import pyro
from pyro.infer.mcmc import MCMC,NUTS
from parallelbayes.reference import Model
from parallelbayes.output import constrain_checked


def sample_nuts(model,initial,chain_seeds,draws=256,warmup=256,max_tree_depth=8,
                target_accept_prob=.8,full_mass=False,memory_limit_mb=2048):
    if not isinstance(model,Model) or model.backend!='torch' or model.device.type!='cpu':
        raise ValueError('An explicit CPU torch Model is required')
    for name,value,lower in [('draws',draws,4),('warmup',warmup,1),('max_tree_depth',max_tree_depth,1),('memory_limit_mb',memory_limit_mb,1)]:
        if isinstance(value,bool) or not np.isfinite(value) or int(value)!=value or value<lower:
            raise ValueError('Invalid '+name)
    if not isinstance(full_mass,bool) or not 0<target_accept_prob<1:
        raise ValueError('Invalid adaptation settings')
    seeds=list(chain_seeds)
    if not seeds or len(set(seeds))!=len(seeds) or any(isinstance(s,bool) or not isinstance(s,(int,np.integer)) or not 0<=s<2**32 for s in seeds):
        raise ValueError('Distinct uint32 chain seeds are required')
    start=np.asarray(initial,float)
    if start.shape!=(len(seeds),model.dimension) or not np.isfinite(start).all():
        raise ValueError('Explicit finite chain-by-dimension initial values required')
    estimate=len(seeds)*(draws+warmup)*model.dimension*8*10
    if estimate>memory_limit_mb*1024**2:raise MemoryError('Stored-array estimate exceeds limit; not a strict allocator bound')
    began=time.perf_counter()
    result=dict(status='started',initial=start.copy(),chain_seeds=seeds,draws=None,unconstrained=None,
        warmup_states=None,chain_records=[],partial_chains=[],target_id=model.target_id,
        base_target_id=model.spec.get('base_target_id',model.target_id),names=model.names,
        fixed_mh_tape_comparison=False,provider='pyro_cpu_nuts',pyro_version=pyro.__version__,
        torch_version=torch.__version__,mass_matrix_adaptation=True,full_mass=full_mass,
        target_accept_prob=target_accept_prob,max_tree_depth=max_tree_depth,
        warmup_per_chain=warmup,draws_per_chain=draws,chains_serialized=True,
        tree_depth_hit_count=None,tree_depth_note='Not exposed by documented Pyro diagnostics; no inferred zero',
        stored_array_estimate_bytes=estimate,
        timing=dict(warmup=0.,sample=0.,finalization_diagnostics=0.,transform=0.),
        cost_scope='Inclusive CPU MCMC workflow. Warmup boundary is last warmup hook; sample boundary is last retained hook. Hook logging overhead included, no exclusive kernel timing claim.',
        guarantee='finite-output and transform check only; convergence and posterior accuracy require separate evaluation')
    paths=[];warm_paths=[];saved_rng=[];end_rng=[]
    saved_python=random.getstate();saved_numpy=np.random.get_state()
    try:
        with torch.random.fork_rng(devices=[]):
            for chain,seed in enumerate(seeds):
                pyro.set_rng_seed(seed);saved_rng.append(torch.get_rng_state().numpy().copy())
                trace=dict(chain=chain,warmup=[],sample=[],warmup_step_size=[],sample_step_size=[])
                result['partial_chains'].append(trace)
                chain_start=time.perf_counter();boundary=[None,None];final_geometry={}
                def hook(kernel,params,stage,index):
                    label='warmup' if stage.startswith('Warmup') else 'sample'
                    state=params['q'].detach().numpy().copy()
                    trace[label].append(state)
                    trace[label+'_step_size'].append(float(kernel.step_size))
                    if not np.isfinite(state).all():raise FloatingPointError('Nonfinite NUTS state')
                    if label=='warmup' and index==warmup-1:boundary[0]=time.perf_counter()
                    if label=='sample' and index==draws-1:
                        final_geometry.update(step_size=float(kernel.step_size),
                            inverse_mass_matrix={','.join(k):v.detach().numpy().copy() for k,v in kernel.inverse_mass_matrix.items()})
                        boundary[1]=time.perf_counter()
                kernel=NUTS(potential_fn=lambda state:-model.log_density(state['q']),
                    target_accept_prob=target_accept_prob,full_mass=full_mass,
                    adapt_step_size=True,adapt_mass_matrix=True,max_tree_depth=max_tree_depth,jit_compile=False)
                mcmc=MCMC(kernel,num_samples=draws,warmup_steps=warmup,num_chains=1,
                    initial_params={'q':torch.tensor(start[chain],dtype=torch.float64)},
                    hook_fn=hook,disable_progbar=True)
                mcmc.run()
                path=mcmc.get_samples()['q'].detach().numpy().copy()
                if len(trace['warmup'])!=warmup or len(trace['sample'])!=draws or not np.array_equal(path,np.asarray(trace['sample'])):
                    raise RuntimeError('MCMC hook/output mismatch')
                diag=mcmc.diagnostics()
                finish=time.perf_counter()
                result['timing']['warmup']+=boundary[0]-chain_start
                result['timing']['sample']+=boundary[1]-boundary[0]
                result['timing']['finalization_diagnostics']+=finish-boundary[1]
                paths.append(path);warm_paths.append(np.asarray(trace['warmup']))
                end_rng.append(torch.get_rng_state().numpy().copy())
                result['chain_records'].append(dict(chain=chain,seed=seed,diagnostics=diag,
                    diagnostic_note='Pyro diagnostics retained; modern multichain posterior diagnostics computed separately',
                    adapted_geometry=final_geometry,seconds=finish-chain_start))
            path=np.stack(paths);warm_path=np.stack(warm_paths)
            now=time.perf_counter();theta,error=constrain_checked(model,path)
            device_theta=model.constrain_device(torch.tensor(path,dtype=torch.float64)).detach().numpy()
            if error or not np.isfinite(path).all() or not np.isfinite(device_theta).all() or not np.allclose(theta,device_theta,rtol=1e-10,atol=1e-12):
                raise FloatingPointError('NUTS output/transform check failed: '+str(error))
            result['timing']['transform']=time.perf_counter()-now
            result.update(status='completed',draws=theta,unconstrained=path,warmup_states=warm_path)
    except Exception as exc:
        result.update(status='failed',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),
            draws=None,unconstrained=None,warmup_states=None)
    finally:
        random.setstate(saved_python);np.random.set_state(saved_numpy)
    result['initial_torch_rng_states']=np.asarray(saved_rng)
    result['final_torch_rng_states']=np.asarray(end_rng)
    result['timing']['total']=time.perf_counter()-began
    return result
