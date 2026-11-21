"""Compare development Gaussian fixed-tape paths with an analytic serial oracle."""
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
sys.path.insert(0,str(ROOT/"scripts/prospective_torch"))
from gaussian_cost import build
from parallelbayes.torch_backend.sampling import sample


def clean(x):
    if isinstance(x,dict): return {k:clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    if isinstance(x,np.generic): return clean(x.item())
    if isinstance(x,float) and not math.isfinite(x): return str(x)
    return x


def digest(path):
    h=sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda:file.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main(source,output,device):
    if device=="cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable; no substitution")
    receipt=json.loads((source/'receipt.json').read_text())
    if receipt.get('passed') is not True:
        raise ValueError('development static validation did not pass')
    output.mkdir()
    torch.set_num_threads(1)
    rows=[]
    for d,m in ((8,256),(128,65536)):
        identity=next((r for r in receipt['rows'] if (r['dimension'],r['rows'])==(d,m)),None)
        if identity is None or not identity['passed']:
            raise ValueError('missing target static check')
        input_file=source/identity['actual_input']
        if digest(input_file)!=identity['actual_input_sha256']:
            raise ValueError('development input hash mismatch')
        model,(x,y,diag,linear)=build(d,m,device)
        with np.load(input_file,allow_pickle=False) as saved:
            if any(not np.array_equal(saved[k],v) for k,v in
                   [('design',x),('response',y),('diagonal',diag),('linear',linear)]):
                raise ValueError('actual dense arrays differ from static validation')
        rng=np.random.default_rng(762341+d)
        # Development-only stress draw selected to cover rejection on both cost extremes.
        noise=rng.normal(size=(4,3,d));noise[:,1,1]=1000.
        log_uniform=np.full((4,3),np.log(.5));log_uniform[:,1]=-1e-12
        tape={'noise':noise,'log_uniform':log_uniform,
              'directions':np.where(rng.integers(0,2,size=(4,3,d)),1.,-1.)}
        tape_path=output/f'd{d}-m{m}-tape.npz'
        with tape_path.open('xb') as file: np.savez(file,**tape,initial=np.zeros((4,d)))
        reference={}
        for kernel,executor,scale in (('rwm','sequential',.001),('rwm','online_picard',.001),
                                      ('mala','sequential',1e-6),('mala','quasi_deer',1e-6)):
            config={'device':device,'draws':3,'chains':4,'window':2,'max_iter':30,'initial':np.zeros((4,d)),
                    'step_size':scale,'kernel':kernel,'executor':executor,'audit':True,'on_failure':'error'}
            started=time.monotonic()
            try: result=sample(model,config,tape=tape)
            except (RuntimeError,MemoryError,FloatingPointError,ValueError) as error:
                row={'dimension':d,'rows':m,'kernel':kernel,'executor':executor,'status':'exception','passed':False,
                     'error_type':type(error).__name__,'error':str(error),'seconds':time.monotonic()-started}
                rows.append(row);print(json.dumps(row),flush=True);continue
            path=result['unconstrained'] if result['status']=='completed' else result['failed_trajectory']
            name=f'd{d}-m{m}-{kernel}-{executor}.npz'
            with (output/name).open('xb') as file:np.savez(file,path=path,accept=result['accept'])
            if executor=='sequential':reference[kernel]=result
            delta=matching=None
            if executor!='sequential' and result['status']=='completed' and kernel in reference and reference[kernel]['status']=='completed':
                delta=float(np.max(np.abs(path-reference[kernel]['unconstrained'])))
                matching=bool(np.array_equal(result['accept'],reference[kernel]['accept']))
            passed=result['status']=='completed' and result['audit'] is not None and result['audit']['passed']
            if executor!='sequential':passed=passed and matching and delta<=2e-8
            row={'dimension':d,'rows':m,'kernel':kernel,'executor':executor,'status':result['status'],
                 'passed':bool(passed),'accept':result['accept'].tolist(),'path_delta':delta,'events_match':matching,
                 'audit':result['audit'],'diagnostics':result['diagnostics'],'timing':result['timing'],
                 'static_input_sha256':identity['actual_input_sha256'],'tape_file':tape_path.name,
                 'tape_file_sha256':digest(tape_path),'path_file':name,'path_sha256':digest(output/name)}
            rows.append(row);print(json.dumps(clean(row),allow_nan=False),flush=True)
    report={'scope':'development cost extremes only; synthetic four-chain three-step paths',
            'device':device,'torch':torch.__version__,'rows':rows,'passed':len(rows)==8 and all(x['passed'] for x in rows)}
    with (output/'receipt.json').open('x') as f:json.dump(clean(report),f,indent=2,allow_nan=False);f.write('\n')
    if not report['passed']:raise SystemExit('Gaussian fixed-tape path audit failed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--device',choices=('cpu','cuda'),default='cpu')
    args=parser.parse_args();main(args.source,args.output,args.device)
