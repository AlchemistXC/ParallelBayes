"""CPU chain-level parallel baseline with explicit spawn and process costs.

Only serialized built-in/explicit wells/fixed-affine Model contracts are
reconstructed. No arbitrary closure pickling, CUDA, or Stan translation.
"""
from concurrent.futures import ProcessPoolExecutor,as_completed
import multiprocessing
import os
from pathlib import Path
import sys
import time
import traceback
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'r-package/inst/python'))
sys.path.insert(0,str(ROOT/'examples'))
sys.path.insert(0,str(ROOT/'scripts/completion'))


def restore_model(spec):
    from parallelbayes import make_model
    if spec['kind']=='fixed_affine':
        from affine_target import affine_model
        base=restore_model(spec['base_spec'])
        if base.target_id!=spec['base_target_id']:raise ValueError('Base target identity changed')
        return affine_model(base,spec['center'],spec['factor'])
    if spec['kind']=='external_wells_distance':
        from external_wells import make_wells
        return make_wells(dict(N=spec['N'],dist=spec['dist'],switched=spec['switched']),'torch','cpu')
    return make_model(spec,backend='torch',device='cpu')


def initialize_worker(threads):
    import torch
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)


def run_chain(payload):
    import torch
    from inference_nuts import sample_nuts
    begin=time.perf_counter()
    model=restore_model(payload['spec'])
    if model.target_id!=payload['target_id']:raise ValueError('Reconstructed target identity changed')
    setup=time.perf_counter()-begin
    result=sample_nuts(model,[payload['initial']],[payload['seed']],**payload['config'])
    # Diagnostics can contain torch tensors even though sampled states are
    # NumPy. Send owned host values through standard process IPC: no tensor
    # storage handles or torch shared-memory manager are part of this API.
    def transport(value):
        if isinstance(value,torch.Tensor):return value.detach().cpu().numpy().copy()
        if isinstance(value,dict):return {k:transport(v) for k,v in value.items()}
        if isinstance(value,list):return [transport(v) for v in value]
        if isinstance(value,tuple):return tuple(transport(v) for v in value)
        return value
    result=transport(result)
    return dict(chain=payload['chain'],worker_pid=os.getpid(),threads=torch.get_num_threads(),
        interop_threads=torch.get_num_interop_threads(),target_setup_seconds=setup,
        worker_wall=time.perf_counter()-begin,transport='owned NumPy and plain values; no torch storage handles',result=result)


def sample_parallel_nuts(spec,target_id,initial,chain_seeds,workers=4,threads_per_worker=1,**config):
    began=time.perf_counter();seeds=list(chain_seeds);start=np.asarray(initial,float)
    if not seeds or start.ndim!=2 or start.shape!=(len(seeds),spec['dimension']) or not np.isfinite(start).all():
        raise ValueError('Explicit finite chain starts required')
    for name,value in [('workers',workers),('threads_per_worker',threads_per_worker)]:
        if isinstance(value,bool) or not isinstance(value,int) or value<1:raise ValueError('Invalid '+name)
    if len(set(seeds))!=len(seeds):raise ValueError('Distinct chain seeds required')
    allowed={'draws','warmup','max_tree_depth','target_accept_prob','full_mass','memory_limit_mb'}
    if set(config)-allowed:raise ValueError('Unsupported NUTS configuration')
    expected=len(seeds)*(config.get('draws',256)+config.get('warmup',256))*spec['dimension']*8*10
    if expected>config.get('memory_limit_mb',2048)*1024**2:raise MemoryError('Aggregate stored-array estimate exceeds limit')
    actual_workers=min(workers,len(seeds));received={};errors={}
    pool_start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=actual_workers,mp_context=multiprocessing.get_context('spawn'),
                             initializer=initialize_worker,initargs=(threads_per_worker,)) as pool:
        futures={pool.submit(run_chain,dict(spec=spec,target_id=target_id,initial=start[i].tolist(),
                    seed=seed,chain=i,config=config)):i for i,seed in enumerate(seeds)}
        for future in as_completed(futures):
            index=futures[future]
            try:received[index]=future.result()
            except Exception as exc:errors[index]=dict(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
    pool_wall=time.perf_counter()-pool_start
    records=[received[i] for i in sorted(received)]
    success=not errors and len(records)==len(seeds) and all(r['result']['status']=='completed' for r in records)
    result=dict(status='completed' if success else 'failed',draws=None,unconstrained=None,
        initial=start.copy(),chain_seeds=seeds,target_id=target_id,provider='pyro_cpu_spawn_chains',
        workers_requested=workers,workers_allocated=actual_workers,threads_per_worker=threads_per_worker,
        observed_worker_pids=sorted(set(r['worker_pid'] for r in records)),
        process_start_method='spawn',components_are_additive=False,worker_records=records,
        worker_errors=errors,fixed_mh_tape_comparison=False,stored_array_estimate_bytes=expected,
        resource_note='Requested process/thread configuration is recorded; not exclusive physical-core allocation',
        timing=dict(pool_wall=pool_wall),
        cost_scope='Parent pool wall includes process startup/imports, target reconstruction, warmup, sampling, IPC and shutdown; concurrent child durations cannot be summed as wall time',
        guarantee='Numerical workflow output only; modern multichain diagnostics and accuracy evaluation remain separate')
    if success:
        for key in ['draws','unconstrained','warmup_states','initial_torch_rng_states','final_torch_rng_states']:
            result[key]=np.concatenate([r['result'][key] for r in records],axis=0)
        result['names']=records[0]['result']['names']
    result['timing']['total']=time.perf_counter()-began
    return result
