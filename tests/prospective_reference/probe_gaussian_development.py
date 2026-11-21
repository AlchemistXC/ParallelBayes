"""Exercise 64-step probes on a synthetic development target; not a first-use run."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/prospective_torch'))
from gaussian_cost import build
from parallelbayes.torch_backend.sampling import sample, settings, audit_path, tape_hash


def safe(value):
    if isinstance(value,dict):return {k:safe(v) for k,v in value.items()}
    if isinstance(value,list):return [safe(v) for v in value]
    if isinstance(value,np.generic):return safe(value.item())
    if isinstance(value,float) and not math.isfinite(value):return str(value)
    return value


def stream(seed, steps, dimension):
    rng=np.random.default_rng(seed)
    return {'noise':rng.normal(size=(4,steps,dimension)),
            'log_uniform':np.log(np.maximum(rng.random((4,steps)),np.finfo(float).tiny)),
            'directions':np.where(rng.integers(0,2,size=(4,steps,dimension)),1.,-1.)}


def main(output, device, kernel):
    if device=='cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no CPU substitution')
    output.mkdir()
    torch.set_num_threads(1)
    start=time.perf_counter()
    model,(design,response,diagonal,linear)=build(8,256,device)
    seeds=np.random.SeedSequence(810431).spawn(2)
    probe=stream(seeds[0],64,8);reserved=stream(seeds[1],256,8)
    if np.array_equal(probe['noise'],reserved['noise'][:,:64]):
        raise ValueError('probe and reserved noise arrays unexpectedly match')
    q0=np.zeros((4,8))
    arrays={**{'probe_'+k:v for k,v in probe.items()},**{'reserved_'+k:v for k,v in reserved.items()},
            'initial':q0,'design':design,'response':response,'diagonal':diagonal,'linear':linear}
    with (output/'actual-inputs.npz').open('xb') as file:np.savez(file,**arrays)
    probe_hash,reserved_hash=tape_hash(probe),tape_hash(reserved)
    runs=[];raw=[]
    executor='online_picard' if kernel=='rwm' else 'quasi_deer'
    scale=.01 if kernel=='rwm' else .001
    for window in (None,4,8,16,32,64):
        config={'device':device,'kernel':kernel,'executor':'sequential' if window is None else executor,
                'draws':64,'chains':4,'window':window or 4,'initial':q0,'step_size':scale,
                'max_iter':512,'audit':False,'on_failure':'error'}
        try:
            result=sample(model,config,tape=probe)
            path=result['unconstrained'] if result['status']=='completed' else result['failed_trajectory']
            filename='sequential.npz' if window is None else f'w{window}.npz'
            with (output/filename).open('xb') as file:np.savez(file,path=path,accept=result['accept'])
            stats=result['diagnostics'];rounds=stats['iterations']
            row={'window':window,'status':result['status'],'path_file':filename,
                 'path_sha256':sha256((output/filename).read_bytes()).hexdigest(),
                 'tape_sha256':result['tape_sha256'],'sample_seconds':result['timing']['sample'],
                 'reported_total_seconds':result['timing']['total'],'rounds':rounds,
                 'progress_per_round':stats['confirmed']/(4*rounds) if rounds else None,
                 'seconds_per_round':result['timing']['sample']/rounds if rounds else None,
                 'diagnostics':stats}
            raw.append((result,config))
        except (RuntimeError,MemoryError,ValueError,FloatingPointError) as error:
            row={'window':window,'status':'exception','error_type':type(error).__name__,'error':str(error)}
            raw.append((None,config))
        runs.append(row)
    probe_seconds=time.perf_counter()-start
    audit_start=time.perf_counter()
    serial=raw[0][0]
    for row,(result,config) in zip(runs,raw,strict=True):
        if result is None or result['status']!='completed':row['independent_audit']=None;row['passed']=False;continue
        audit=audit_path(model,settings(config),q0,probe,result['unconstrained'],result['accept'])
        row['independent_audit']=audit
        row['passed']=bool(audit['passed'])
        if row['window'] is not None:
            if serial is None or serial['status']!='completed':row['passed']=False
            else:
                row['same_events_as_sequential']=bool(np.array_equal(result['accept'],serial['accept']))
                row['max_path_difference']=float(np.max(np.abs(result['unconstrained']-serial['unconstrained'])))
                row['passed'] &= row['same_events_as_sequential'] and row['max_path_difference']<=2e-8
    report={'scope':'development probe demonstration only; not a calibrated or formal first-use strategy',
            'device':device,'kernel':kernel,'chains':4,'probe_steps':64,'reserved_steps':256,
            'seed_construction':'two children of a SeedSequence; distinct saved actual arrays',
            'actual_inputs_sha256':sha256((output/'actual-inputs.npz').read_bytes()).hexdigest(),
            'probe_tape_sha256':probe_hash,'reserved_tape_sha256':reserved_hash,
            'probe_wall_seconds':probe_seconds,'offline_audit_seconds':time.perf_counter()-audit_start,
            'timing_scope':'initialized process; target setup, probe and dummy reserved input generation, six full eager executions and local path writes; excludes offline audit',
            'blindness':'synthetic reserved arrays coexist in the same file; not suitable for formal input sealing',
            'rows':runs,'passed':all(row['passed'] for row in runs)}
    with (output/'receipt.json').open('x') as file:json.dump(safe(report),file,indent=2,allow_nan=False);file.write('\n')
    if not report['passed']:raise SystemExit('one or more probe path audits failed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path);parser.add_argument('--device',choices=('cpu','cuda'),default='cpu')
    parser.add_argument('--kernel',choices=('rwm','mala'),required=True)
    args=parser.parse_args();main(args.output,args.device,args.kernel)
