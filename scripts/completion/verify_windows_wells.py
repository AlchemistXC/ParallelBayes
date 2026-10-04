"""Check the native-Windows wells return against one independent NumPy tape."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'r-package/inst/python'))
sys.path.insert(0,str(ROOT/'examples'))
sys.path.insert(0,str(ROOT/'scripts/completion'))
from external_wells import load_wells,make_wells
from parallelbayes.reference import numpy_reference
from windows_wells import inspect,DIRECTORY,INPUT,sha
from validate_wells import verify_protocol


def verify(source,cpu,cuda,r_return,output):
    if output.exists():raise FileExistsError('Preserve previous verification')
    report=dict(status='failed',scope='Native Windows external-target and R transport checks, not convergence/performance',
                source_script_sha256=sha(Path(__file__)))
    try:
        inspect(DIRECTORY)
        protocols={d:verify_protocol(DIRECTORY/(d+'.json')) for d in ['cpu','cuda']}
        p=protocols['cpu'];config=p['base_config'];model=make_wells(load_wells(source))
        with np.load(INPUT,allow_pickle=False) as z:tape={k:z[k].copy() for k in z.files}
        oracle={}
        for workflow in p['workflows']:
            if workflow['executor']!='sequential':continue
            paths=[];events=[]
            for i in range(config['chains']):
                a,b=numpy_reference(model,workflow['kernel'],np.array(config['initial'][i]),
                    tape['noise'][i],tape['log_uniform'][i],workflow['step_size'])
                paths.append(a);events.append(b)
            oracle[workflow['kernel']]=(np.stack(paths),np.stack(events))
        saved={};rows=[];runtimes={}
        for label,folder,device in [('CPU',cpu,'cpu'),('CUDA',cuda,'cuda'),('R-CUDA',r_return/'python','cuda')]:
            checks=json.loads((folder/'checksums.json').read_text())
            for name,digest in checks.items():
                if sha(folder/name)!=digest:raise ValueError('Run checksum mismatch: '+label+'/'+name)
            meta=json.loads((folder/'result.json').read_text())
            if meta['status']!='passed' or not meta['platform'].startswith('Windows'):
                raise ValueError('Actual native Windows passed receipt is required: '+label)
            if meta['protocol_sha256']!=protocols[device]['protocol_sha256'] or meta['target_id']!=model.target_id or meta['tape_sha256']!=p['tape_sha256']:
                raise ValueError('Protocol/target/tape identity mismatch: '+label)
            if not meta['validation']['passed']:raise ValueError('Target derivative validation failed')
            if device=='cuda' and '5080' not in str(meta['environment']['gpu_name']):
                raise ValueError('Actual RTX5080 required for CUDA receipt')
            runtimes[label]=meta['environment']
            for workflow in p['workflows']:
                name=workflow['kernel']+'-'+workflow['executor']
                record=json.loads((folder/(name+'.json')).read_text())
                expected_config=dict(protocols[device]['base_config'],**workflow)
                if record['status']!='completed' or record['config']!=expected_config or not record['audit']['passed']:
                    raise ValueError('Invalid or changed workflow: '+label+'/'+name)
                if not record['diagnostics']['tensor_device'].startswith(device) or record['diagnostics']['tensor_dtype']!='torch.float64':
                    raise ValueError('Actual tensor device/dtype differs')
                with np.load(folder/(name+'.npz'),allow_pickle=False) as z:
                    path=z['unconstrained'].copy();accept=z['accept'].copy()
                    if not np.array_equal(path,z['draws']):raise ValueError('Identity transform differs')
                expected,events=oracle[workflow['kernel']]
                error=float(np.max(np.abs(path-expected)));mismatch=int(np.sum(accept!=events))
                if not np.isfinite(path).all() or error>p['paired_atol'] or mismatch:
                    raise ValueError('Independent trajectory/acceptance mismatch')
                saved[label,name]=(path,accept)
                rows.append(dict(run=label,workflow=name,max_path_error=error,acceptance_mismatches=mismatch))
        for workflow in p['workflows']:
            name=workflow['kernel']+'-'+workflow['executor']
            a,aa=saved['CPU',name];b,bb=saved['CUDA',name]
            if np.max(np.abs(a-b))>p['paired_atol'] or not np.array_equal(aa,bb):
                raise ValueError('CPU/CUDA actual trajectory mismatch')
            if not all(np.array_equal(x,y) for x,y in zip(saved['CUDA',name],saved['R-CUDA',name])):
                raise ValueError('R CUDA replay differs from Python CUDA')
        expected=np.transpose(saved['R-CUDA','rwm-online_picard'][0],(1,0,2)).astype('<f8').ravel(order='F').tobytes()
        if (r_return/'draws-f64le.bin').read_bytes()!=expected:raise ValueError('R binary array values/order mismatch')
        report.update(status='passed',verified_workflows=12,independent_oracle_chains=8,independent_random_tapes=1,
            R_CUDA_replay_identical=True,R_binary_transport_identical=True,rows=rows,runtimes=runtimes,
            torch_imported='torch' in sys.modules,jax_imported='jax' in sys.modules)
    except Exception as exc:report['error']=type(exc).__name__+': '+str(exc)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','cpu','cuda','r-return','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=verify(a.source.resolve(),a.cpu.resolve(),a.cuda.resolve(),a.r_return.resolve(),a.output.resolve())
    sys.exit(0 if result['status']=='passed' else 1)
