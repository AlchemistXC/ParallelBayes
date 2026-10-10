"""Owned child work for the new Windows-only NUTS localization protocol."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import numpy as np
from nuts_events import atomic_json,sha,snapshot_memory
from nuts_instrumented_worker import require_windows,initialize_worker,execute_chain
ROOT=Path(__file__).resolve().parents[2]


def event(root,name,**extra):
    with (root/'parent-events.ndjson').open('a',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(dict(event=name,utc_ns=time.time_ns(),monotonic_ns=time.perf_counter_ns(),
            **snapshot_memory(),**extra),allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())


def save_array(path,array):
    with path.open('xb') as f:np.save(f,array,allow_pickle=False);f.flush();os.fsync(f.fileno())
    return dict(name=path.name,sha256=sha(path),shape=list(array.shape),dtype=str(array.dtype))


def legacy_chain(payload):
    import torch
    from pyro.ops.stats import effective_sample_size
    root=Path(payload['directory']);root.mkdir(parents=True,exist_ok=True)
    event(root,'legacy_ess_worker_enter',chain=payload['chain'])
    # Independently saved old array; this does not reconstruct the old MCMC
    # object's private state or its entire diagnostics() implementation.
    with np.load(payload['input'],allow_pickle=False) as z:q=z['unconstrained'][payload['chain']].copy()
    event(root,'legacy_ess_enter',shape=list(q.shape))
    try:
        ess=effective_sample_size(torch.tensor(q[None,...],dtype=torch.float64),chain_dim=0,sample_dim=1)
        record=save_array(root/'legacy-ess.npy',ess.detach().numpy())
        event(root,'legacy_ess_exit',finite=bool(np.isfinite(ess.detach().numpy()).all()))
        return dict(chain=payload['chain'],status='returned',result=record)
    except BaseException as exc:
        event(root,'legacy_ess_exception',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc());raise


def run_pool(request,root,diagnostic=False):
    event(root,'pool_create_enter',workers=request['workers'])
    errors={};received={};workers=root/'workers';workers.mkdir()
    with ProcessPoolExecutor(max_workers=request['workers'],mp_context=multiprocessing.get_context('spawn'),
        initializer=initialize_worker,initargs=(str(workers),)) as pool:
        futures={}
        for chain in range(4):
            directory=root/f'chain-{chain}';payload=dict(chain=chain,directory=str(directory))
            if diagnostic:
                payload['input']=request['diagnostic_input'];function=legacy_chain
            else:
                case=request['case'];states=json.loads(Path(request['rng_file']).read_text())
                if sha(request['rng_file'])!=request['rng_sha256']:raise ValueError('Actual RNG input differs')
                payload.update(spec=case['target_spec'],target_id=case['target_id'],initial=case['initial'][chain],
                    seed=case['chain_seeds'][chain],initial_rng_state=states['states'][chain],
                    config=request['config'],diagnostics_enabled=request['diagnostics_enabled'])
                function=execute_chain
            futures[pool.submit(function,payload)]=chain
        event(root,'pool_submitted',chains=4)
        for future in as_completed(futures):
            chain=futures[future]
            try:
                value=future.result()
                event(root,'future_received',chain=chain)
                if diagnostic:received[chain]=value
                else:
                    result=value.pop('result');status=result['status'];arrays={}
                    if status=='completed':
                        for key in ('draws','unconstrained','warmup_states','initial_torch_rng_states','final_torch_rng_states'):
                            arrays[key]=save_array(root/f'chain-{chain}-{key}.npy',result[key])
                    received[chain]=dict(**value,status=status,arrays=arrays,error=result.get('error'))
                atomic_json(root/f'chain-{chain}-received.json',received[chain])
            except BaseException as exc:
                errors[str(chain)]=dict(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
                event(root,'future_exception',chain=chain,**errors[str(chain)])
        event(root,'pool_shutdown_enter')
    event(root,'pool_shutdown_returned')
    valid='returned' if diagnostic else 'completed'
    complete=not errors and len(received)==4 and all(x['status']==valid for x in received.values())
    return dict(status='completed' if complete else 'failed',received=received,errors=errors,
        posterior_samples_eligible=False,scope='New technical localization call; no historical task is replaced')


def modern(request,root):
    with np.load(request['diagnostic_input'],allow_pickle=False) as z:a=z['draws'].transpose(1,0,2).astype('<f8')
    transport=root/'draws.bin'
    with transport.open('xb') as f:f.write(a.tobytes(order='F'));f.flush();os.fsync(f.fileno())
    atomic_json(root/'transport.json',dict(scope='Saved old four-chain diagnostics, no new fitting',
        independent_unit='Original input label; the four chains are not four datasets',
        fits=[dict(id=request['model'],input='draws.bin',shape=list(a.shape),names=request['names'])]))
    event(root,'modern_R_enter')
    command=[request['rscript'],'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(root)]
    with (root/'R-stdout.log').open('xb') as out,(root/'R-stderr.log').open('xb') as err:
        result=subprocess.run(command,stdout=out,stderr=err,check=False)
    event(root,'modern_R_exit',exit_code=result.returncode)
    if result.returncode:raise RuntimeError('Joint R posterior diagnostics failed')
    if sha(transport)!=sha(root/'draws.bin.roundtrip'):raise ValueError('R binary roundtrip differs')
    return dict(status='completed',posterior_samples_eligible=False,posterior_sha256=sha(root/'posterior.json'))


def main(request_path):
    require_windows();request=json.loads(request_path.read_text());root=request_path.parent
    if (root/'child-result.json').exists():raise FileExistsError('A child result already exists')
    event(root,'child_enter',call=request['id'])
    if request['phase']=='diagnostic' and sha(request['diagnostic_input'])!=request['diagnostic_input_sha256']:
        raise ValueError('Saved diagnostic input changed')
    try:
        if request['phase']=='diagnostic' and request['diagnostic_kind']=='modern':result=modern(request,root)
        else:result=run_pool(request,root,diagnostic=request['phase']=='diagnostic')
    except BaseException as exc:
        event(root,'child_exception',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
        result=dict(status='failed',error=type(exc).__name__+': '+str(exc),posterior_samples_eligible=False)
    atomic_json(root/'child-result.json',result);event(root,'child_exit_ready',status=result['status'])
    return 0 if result['status']=='completed' else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('request',type=Path)
    sys.exit(main(parser.parse_args().request.resolve()))
