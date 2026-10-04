"""Finite, source-frozen MH tuning development; separate from formal inference."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'r-package/inst/python'))
sys.path.insert(0,str(ROOT/'examples'))
sys.path.insert(0,str(ROOT/'scripts/completion'))
from mechanism_runner import identity,sha,plain,write,actual_hash,experiment_lease
from inference_readiness import build_target,save_result,sources as readiness_sources
from inference_tuning_stats import score_path,select_candidate


class EvidenceMismatch(ValueError):
    """An identity failure must abort, never become a numerical candidate failure."""


def source_files():
    files=readiness_sources()
    for n in ['scripts/completion/inference_tuning.py','scripts/completion/inference_tuning_stats.py']:
        files[n]=sha(ROOT/n)
    return dict(sorted(files.items()))


def input_payload(p,item,rep):
    from parallelbayes.torch_backend.sampling import random_tape,settings
    index=p['targets'].index(item);offset=10*index+rep
    c=settings(dict(chains=p['chains'],draws=p['warmup']+p['retained'],
        seed=p['tape_seed_base']+offset,solver_seed=p['solver_seed_base']+offset))
    tape=random_tape(c,item['dimension'])
    rng=np.random.Generator(np.random.Philox(p['initial_seed_base']+offset))
    initial=2*rng.standard_normal((p['chains'],item['dimension']))
    if item['name']=='M1':initial[:,0]=[-5.,5.,-5.,5.]
    return dict(tape,initial=initial)


def freeze(protocol,inputs):
    protocol=Path(protocol);inputs=Path(inputs)
    if protocol.exists() or inputs.exists():raise FileExistsError('Use fresh protocol and inputs')
    files=source_files()
    import hashlib
    for n,h in files.items():
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+n],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit scientific sources first: '+n)
    readiness=json.loads((ROOT/'benchmark/protocols/inference-readiness-mac-v2.json').read_text())
    p=dict(identity='inference-tuning-mac-v1',required_platform='darwin',device='cpu',torch_threads=1,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_files=files,
        targets=[dict(name=t['name'],dimension=t['dimension'],geometry=t['geometry']) for t in readiness['targets']],
        chains=4,warmup=512,retained=1024,replicates=[0,1],
        multiplier_grid=dict(rwm=[.5,1.,1.5,2.4,3.5,5.],mala=[.1,.3,.6,1.,1.6,2.4]),
        step_rule=dict(rwm='multiplier / sqrt(d)',mala='multiplier / d**(1/3)'),
        initial_seed_base=6251000,tape_seed_base=6252000,solver_seed_base=6253000,
        max_iter=2048,memory_limit_mb=2048,window=8,
        statistical_unit='One independent four-chain developmental run; two per candidate. Candidates share actual input arrays within replicate; chains/time steps are not independent experiments.',
        selection='Within each target/kernel, maximize mean ESJD/d over both valid development replicates after 512 discarded steps; all rejection self-transitions count. Exact ties choose smaller step. Any failed/missing replicate makes candidate ineligible; all retained. No positive score yields no selection.',
        scope='MH step development, not formal posterior accuracy, convergence, acceleration or optimal tuning evidence',
        timing='Every candidate, setup, independent audit and selection cost retained; score is not divided by measured time. Hardware contention cannot choose a faster-scoring candidate.',
        failure='Retain all failures/partial outputs; no fallback, no resampling, no grid expansion under this identity',
        future='Budget pilot and formal evaluation must use independent seed namespaces; selected steps require diagnostics and error evaluation. This is not an automatic method selector.',
        master_inputs={},cases=[])
    inputs.mkdir(parents=True)
    for item in p['targets']:
        for rep in p['replicates']:
            name=f'{item["name"]}-rep{rep}.npz';payload=input_payload(p,item,rep)
            np.savez_compressed(inputs/name,**payload)
            p['master_inputs'][name]=dict(sha256=sha(inputs/name),actual_sha256=actual_hash(payload))
        for kernel in ['rwm','mala']:
            denominator=np.sqrt(item['dimension']) if kernel=='rwm' else item['dimension']**(1/3)
            for multiplier in p['multiplier_grid'][kernel]:
                for rep in p['replicates']:
                    case=dict(model=item['name'],kernel=kernel,step=float(multiplier/denominator),
                        multiplier=multiplier,replicate=rep,input=f'{item["name"]}-rep{rep}.npz')
                    case['id']=identity(case)[:20];p['cases'].append(case)
    p['protocol_sha256']=identity(p);protocol.parent.mkdir(parents=True,exist_ok=True);write(protocol,p)
    return dict(protocol_sha256=p['protocol_sha256'],cases=len(p['cases']),inputs=len(p['master_inputs']),source_commit=p['source_commit'])


def check_protocol(protocol,inputs):
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);expected=unsigned.pop('protocol_sha256')
    if identity(unsigned)!=expected:raise ValueError('Protocol checksum differs')
    if sys.platform!=p['required_platform']:raise ValueError('Separate platform identity required')
    for name,digest in p['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Source changed: '+name)
    for name,r in p['master_inputs'].items():
        if sha(Path(inputs)/name)!=r['sha256']:raise ValueError('Master input changed: '+name)
        with np.load(Path(inputs)/name,allow_pickle=False) as z:
            if actual_hash(dict(z))!=r['actual_sha256']:raise ValueError('Actual input identity differs')
    return p


def run(protocol,inputs,source,output,resume=False):
    import torch
    from parallelbayes import sample
    from inference_setup import prepare_geometry
    from affine_target import affine_model
    p=check_protocol(protocol,inputs);inputs=Path(inputs);out=Path(output)
    torch.set_num_threads(p['torch_threads'])
    runtime=dict(protocol_sha256=p['protocol_sha256'],python=platform.python_version(),platform=platform.platform(),
        machine=platform.machine(),torch_threads=torch.get_num_threads(),
        packages=dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())))
    if out.exists():
        if not resume:raise FileExistsError('Use explicit resume')
        if json.loads((out/'runtime.json').read_text())!=runtime:raise ValueError('Resume runtime differs')
    else:out.mkdir(parents=True);write(out/'runtime.json',runtime)
    states=[];invocation=time.perf_counter();invocation_id=str(time.time_ns());new_cases=0
    with experiment_lease(out):
        for item in p['targets']:
            model_name=item['name'];model_dir=out/model_name;model_dir.mkdir(exist_ok=True)
            setup_file=model_dir/'setup.json';setup=None
            try:
                start=time.perf_counter();base=build_target(model_name,source)
                if setup_file.exists():
                    setup=json.loads(setup_file.read_text())
                    unsigned=dict(setup);saved_digest=unsigned.pop('setup_sha256')
                    if identity(unsigned)!=saved_digest:raise EvidenceMismatch('Saved geometry checksum differs')
                    if setup['base_target_id']!=base.target_id or setup['protocol_sha256']!=p['protocol_sha256']:
                        raise EvidenceMismatch('Saved target setup identity differs')
                    geometry=setup['geometry']
                else:
                    geometry=prepare_geometry(base,item['geometry'])
                    setup=dict(base_target_id=base.target_id,geometry=geometry,protocol_sha256=p['protocol_sha256'],
                               initial_setup_seconds=time.perf_counter()-start)
                    setup['setup_sha256']=identity(setup)
                    write(setup_file,setup)
                model=affine_model(base,geometry['center'],geometry['factor'])
            except EvidenceMismatch:
                raise
            except Exception as exc:
                # Explicit terminal setup failure keeps all planned candidates failed.
                failure=dict(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
                model=None
            for case in [c for c in p['cases'] if c['model']==model_name]:
                folder=model_dir/case['id'];statefile=folder/'state.json'
                if statefile.exists():
                    state=json.loads(statefile.read_text())
                    if state['case']!=case or state['protocol_sha256']!=p['protocol_sha256']:
                        raise ValueError('Case identity differs')
                    for name,digest in state['assets'].items():
                        if sha(folder/name)!=digest:raise ValueError('Terminal asset checksum differs: '+name)
                    if state['status']=='completed':
                        if model is None:raise ValueError('Cannot resume completed outputs with failed setup')
                        if state['setup_sha256']!=setup['setup_sha256'] or state['target_id']!=model.target_id:
                            raise ValueError('Case geometry identity differs')
                        scored=json.loads((folder/state['attempt']/'score.json').read_text())
                        if state['score']!=scored['mean_squared_jump_per_dimension']:raise ValueError('Saved score differs')
                    states.append(state);continue
                folder.mkdir(exist_ok=True);attempt=folder/('attempt-'+str(time.time_ns()));attempt.mkdir()
                start=time.perf_counter()
                state=dict(case=case,protocol_sha256=p['protocol_sha256'],status='started',attempt=attempt.name,
                    master_input=p['master_inputs'][case['input']],score=None,
                    setup_sha256=None if setup is None else setup['setup_sha256'])
                write(attempt/'started.json',state)
                try:
                    if model is None:raise RuntimeError('Target setup failed: '+failure['error'])
                    with np.load(inputs/case['input'],allow_pickle=False) as z:payload={k:z[k].copy() for k in z.files}
                    initial=payload.pop('initial')
                    config=dict(kernel=case['kernel'],executor='sequential',device='cpu',chains=p['chains'],
                        draws=p['warmup']+p['retained'],initial=initial.tolist(),step_size=case['step'],
                        window=p['window'],max_iter=p['max_iter'],memory_limit_mb=p['memory_limit_mb'],audit=True,on_failure='error')
                    result=sample(model,config,payload,backend='torch');save_result(attempt,'fit',result)
                    state.update(status=result['status'],target_id=model.target_id,base_target_id=base.target_id,
                        actual_tape_sha256=result['tape_sha256'])
                    if result['status']=='completed':
                        score=score_path(result['unconstrained'],initial,result['accept'],p['warmup'])
                        write(attempt/'score.json',score);state['score']=score['mean_squared_jump_per_dimension']
                        state['acceptance_rate']=score['acceptance_rate']
                except Exception as exc:
                    state.update(status='failed',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
                state['wall_seconds_including_archive']=time.perf_counter()-start
                state['assets']={str(f.relative_to(folder)):sha(f) for f in sorted(attempt.iterdir()) if f.is_file()}
                write(folder/'state.tmp',state);(folder/'state.tmp').replace(statefile)
                states.append(state)
                new_cases+=1
                print(json.dumps(dict(done=len(states),total=len(p['cases']),model=model_name,kernel=case['kernel'],
                    multiplier=case['multiplier'],replicate=case['replicate'],status=state['status'])),flush=True)
        selections=[]
        for item in p['targets']:
            for kernel in ['rwm','mala']:
                rows=[dict(step=s['case']['step'],replicate=s['case']['replicate'],status=s['status'],score=s['score'])
                      for s in states if s['case']['model']==item['name'] and s['case']['kernel']==kernel]
                steps=sorted(set(c['step'] for c in p['cases'] if c['model']==item['name'] and c['kernel']==kernel))
                selected=select_candidate(rows,steps,p['replicates']);selected.update(model=item['name'],kernel=kernel)
                selections.append(selected)
        summary=dict(protocol_sha256=p['protocol_sha256'],cases=len(states),
            completed=sum(s['status']=='completed' for s in states),failed=sum(s['status']=='failed' for s in states),
            selections=selections,all_case_wall_seconds=sum(s['wall_seconds_including_archive'] for s in states),
            invocation_wall_seconds=time.perf_counter()-invocation,scope=p['scope'],formal_inference_complete=False)
        invocations=out/'invocations';invocations.mkdir(exist_ok=True)
        write(invocations/(invocation_id+'.json'),dict(protocol_sha256=p['protocol_sha256'],resume=resume,
            newly_executed_cases=new_cases,seconds_inside_run_after_input_runtime_checks=summary['invocation_wall_seconds'],
            note='Not a fresh-process cold-start measurement; original invocation record is retained after resume'))
        write(out/'summary.json',summary)
    return {k:v for k,v in summary.items() if k!='selections'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');f.add_argument('--protocol',type=Path,required=True);f.add_argument('--inputs',type=Path,required=True)
    r=sub.add_parser('run');r.add_argument('--protocol',type=Path,required=True);r.add_argument('--inputs',type=Path,required=True)
    r.add_argument('--source',type=Path,required=True);r.add_argument('--output',type=Path,required=True);r.add_argument('--resume',action='store_true')
    a=p.parse_args();result=freeze(a.protocol,a.inputs) if a.action=='freeze' else run(a.protocol,a.inputs,a.source,a.output,a.resume)
    print(json.dumps(result,indent=2))
