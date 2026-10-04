"""Native CPU NUTS serial/spawn readiness; no GPU or convergence claim.

Frozen actual starts and per-chain RNG seeds are paired between executions.
All warmup, retained states, RNG endpoints and child diagnostics are preserved.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'r-package/inst/python'),str(ROOT/'examples'),str(ROOT/'scripts/completion')]
from mechanism_runner import identity,sha,actual_hash,write,experiment_lease
from inference_budget_pilot import source_files as budget_sources,save_parallel
from inference_readiness import build_target,save_result


def source_files():
    files=budget_sources()
    for name in ['scripts/completion/nuts_readiness_run.py','scripts/completion/posterior_diagnostics.R','benchmark/protocols/inference-budget-pilot-mac-v1.json']:
        files[name]=sha(ROOT/name)
    return dict(sorted(files.items()))


def freeze(profile,protocol,inputs):
    protocol,inputs=Path(protocol),Path(inputs)
    if protocol.exists() or inputs.exists():raise FileExistsError('New protocol and input paths required')
    if profile not in ('windows-v1','mac-companion-v1'):raise ValueError('Unknown profile')
    files=source_files()
    for name,h in files.items():
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit source first: '+name)
    old=json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    targets=[{k:item[k] for k in ['name','dimension','base_target_id','geometry']} for item in old['targets']]
    windows=profile=='windows-v1'
    p=dict(identity='nuts-native-readiness-'+profile,required_platform='win32' if windows else 'darwin',
        required_versions={'torch':'2.13.0+cu130' if windows else '2.13.0','numpy':'2.2.6','scipy':'1.15.3','pyro-ppl':'1.9.2'},
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_files=files,
        targets=targets,chains=4,draws=64,warmup=128,max_tree_depth=8,target_accept_prob=.8,full_mass=False,
        memory_limit_mb=2048,workers=4,threads_per_worker=1,torch_threads=1,inputs={},
        initial_seed_base=7381000,chain_seed_base=7384000,
        geometry_source_protocol_sha256=old['protocol_sha256'],
        scope='Within-host CPU baseline implementation/resource readiness on nine declared targets. Not inference accuracy, calibration, convergence or performance comparison.',
        execution='One serial four-chain fit and one four-worker spawn fit per target. Parent/children one intraop thread; child interop one. CPU tensors only even for a CUDA-enabled torch wheel.',
        pairing='Exact same actual initial arrays and explicit chain seeds; initial/final actual torch RNG bytes, warmup and retained arrays must agree between serial/spawn on this host. No cross-host bitwise or MH-path claim.',
        initial_rule='Philox N(0,4I) in fixed coordinates; M1 first coordinate -5,+5,-5,+5. Same fixture arrays for Mac companion and Windows validation, not independent repetitions.',
        resource='Record actual child PID/thread counts and inclusive pool/serial costs. No exclusive physical-core or acceleration claim.',
        failure='Retain serial/parallel outputs and partial children; comparisons fail closed; no fallback/redraw or deletion. Existing terminal attempts skipped only with matching identities and checksums.',
        stopping='Finite 9-target checklist and numerical/memory guards; no total wallclock cutoff.',
        statistical_repetitions=1,technical_replay_adds_replicates=False,formal_inference_complete=False)
    inputs.mkdir(parents=True)
    for i,item in enumerate(targets):
        initial=2*np.random.Generator(np.random.Philox(p['initial_seed_base']+i)).standard_normal((p['chains'],item['dimension']))
        if item['name']=='M1':initial[:,0]=[-5.,5.,-5.,5.]
        payload=dict(initial=initial,chain_seeds=np.asarray([p['chain_seed_base']+10*i+ch for ch in range(p['chains'])],dtype=np.int64))
        item['input']=item['name']+'.npz';np.savez_compressed(inputs/item['input'],**payload)
        p['inputs'][item['input']]=dict(sha256=sha(inputs/item['input']),actual_sha256=actual_hash(payload))
    p['protocol_sha256']=identity(p);protocol.parent.mkdir(parents=True,exist_ok=True);write(protocol,p)
    return dict(protocol_sha256=p['protocol_sha256'],targets=len(targets),source_commit=p['source_commit'],required_platform=p['required_platform'])


def validate(protocol,inputs):
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if identity(unsigned)!=digest:raise ValueError('Protocol checksum differs')
    if sys.platform!=p['required_platform']:raise ValueError('Native platform mismatch; use a separate protocol identity')
    for package,version in p['required_versions'].items():
        if importlib.metadata.version(package)!=version:raise ValueError('Dependency differs: '+package)
    for name,h in p['source_files'].items():
        if sha(ROOT/name)!=h:raise ValueError('Frozen source checksum differs: '+name)
    if len({t['name'] for t in p['targets']})!=len(p['targets']):raise ValueError('Duplicate target')
    for item in p['targets']:
        name=item['input'];entry=p['inputs'][name]
        if sha(Path(inputs)/name)!=entry['sha256']:raise ValueError('Input file checksum differs')
        with np.load(Path(inputs)/name,allow_pickle=False) as z:payload=dict(z)
        if actual_hash(payload)!=entry['actual_sha256']:raise ValueError('Actual inputs differ')
    return p


def compare(serial,parallel):
    arrays={};keys=['draws','unconstrained','warmup_states','initial_torch_rng_states','final_torch_rng_states','initial']
    complete=serial['status']==parallel['status']=='completed'
    if complete:
        for key in keys:
            a,b=np.asarray(serial[key]),np.asarray(parallel[key])
            arrays[key]=dict(equal=a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes(),
                serial_shape=list(a.shape),parallel_shape=list(b.shape),
                max_abs_difference=float(np.max(abs(a.astype(float)-b.astype(float)))) if a.shape==b.shape else None)
    return dict(passed=complete and bool(arrays) and all(a['equal'] for a in arrays.values()),arrays=arrays,
        scope='Within-host serial/spawn CPU NUTS replay, not MH path equivalence or statistical accuracy')


def run(protocol,inputs,source,output,resume=False):
    import torch,psutil
    from affine_target import affine_model
    from inference_nuts import sample_nuts
    from inference_parallel_nuts import sample_parallel_nuts
    p=validate(protocol,inputs);inputs=Path(inputs);out=Path(output);torch.set_num_threads(p['torch_threads'])
    runtime=dict(protocol_sha256=p['protocol_sha256'],python=sys.version,platform=platform.platform(),machine=platform.machine(),
        cpu_physical=psutil.cpu_count(logical=False),cpu_logical=psutil.cpu_count(),ram_bytes=psutil.virtual_memory().total,
        torch_threads=torch.get_num_threads(),torch_interop_threads=torch.get_num_interop_threads(),
        thread_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']},
        packages=dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())))
    if out.exists():
        if not resume:raise FileExistsError('Explicit resume required')
        if json.loads((out/'runtime.json').read_text())!=runtime:raise ValueError('Resume environment differs')
    else:out.mkdir(parents=True);write(out/'runtime.json',runtime)
    states=[];new=0;began=time.perf_counter();invocation=str(time.time_ns())
    with experiment_lease(out):
        for item in p['targets']:
            folder=out/item['name'];statefile=folder/'state.json'
            if statefile.exists():
                state=json.loads(statefile.read_text())
                if state['target']!=item or state['protocol_sha256']!=p['protocol_sha256'] or state['status'] not in ['completed','failed']:
                    raise ValueError('Terminal identity differs')
                for name,h in state['assets'].items():
                    if sha(folder/name)!=h:raise ValueError('Terminal asset checksum differs')
                states.append(state);continue
            folder.mkdir(parents=True,exist_ok=True);attempt=folder/('attempt-'+str(time.time_ns()));attempt.mkdir()
            state=dict(target=item,protocol_sha256=p['protocol_sha256'],attempt=attempt.name,status='started')
            write(attempt/'started.json',state);start=time.perf_counter()
            print(json.dumps(dict(starting=item['name'],total=len(p['targets']))),flush=True)
            try:
                base=build_target(item['name'],source)
                if base.target_id!=item['base_target_id']:raise ValueError('Base target differs')
                g=item['geometry'];model=affine_model(base,g['center'],g['factor']);state['target_id']=model.target_id
                with np.load(inputs/item['input'],allow_pickle=False) as z:initial=z['initial'].copy();seeds=z['chain_seeds'].tolist()
                config={k:p[k] for k in ['draws','warmup','max_tree_depth','target_accept_prob','full_mass','memory_limit_mb']}
                serial=sample_nuts(model,initial,seeds,**config)
                (attempt/'serial').mkdir();save_result(attempt/'serial','fit',serial)
                parallel=sample_parallel_nuts(model.spec,model.target_id,initial,seeds,workers=p['workers'],threads_per_worker=p['threads_per_worker'],**config)
                (attempt/'parallel').mkdir();save_parallel(attempt/'parallel',parallel)
                state.update(comparison=compare(serial,parallel),serial_status=serial['status'],parallel_status=parallel['status'],
                    serial_timing=serial['timing'],parallel_timing=parallel['timing'],
                    observed_worker_pids=parallel['observed_worker_pids'],worker_count=len(parallel['observed_worker_pids']),
                    serial_device=str(model.device),child_resources=[dict(pid=r['worker_pid'],threads=r['threads'],interop_threads=r['interop_threads']) for r in parallel['worker_records']])
                state['status']='completed' if state['comparison']['passed'] else 'failed'
                if state['status']=='failed':state['samples_eligible_for_inference']=False
            except Exception as exc:
                state.update(status='failed',samples_eligible_for_inference=False,error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
                write(attempt/'failure.json',dict(error=state['error'],traceback=state['traceback']))
            state['whole_task_seconds']=time.perf_counter()-start
            state['assets']={f.relative_to(folder).as_posix():sha(f) for f in sorted(attempt.rglob('*')) if f.is_file()}
            write(folder/'state.tmp',state);(folder/'state.tmp').replace(statefile);states.append(state);new+=1
            print(json.dumps(dict(done=item['name'],status=state['status'])),flush=True)
        summary=dict(protocol_sha256=p['protocol_sha256'],planned=len(p['targets']),completed=sum(s['status']=='completed' for s in states),
            failed=sum(s['status']=='failed' for s in states),newly_executed_targets=new,invocation_seconds=time.perf_counter()-began,
            scope=p['scope'],formal_inference_complete=False)
        history=out/'invocations';history.mkdir(exist_ok=True);write(history/(invocation+'.json'),dict(summary,resume=resume));write(out/'summary.json',summary)
    return summary


def collect(protocol,run,output):
    from inference_estimands import evaluate
    run,output=Path(run).resolve(),Path(output).resolve()
    if output.exists() or run in output.parents:raise ValueError('Fresh separate diagnostic directory required')
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if identity(unsigned)!=digest:raise ValueError('Protocol checksum differs')
    for name,h in p['source_files'].items():
        if sha(ROOT/name)!=h:raise ValueError('Source checksum differs')
    summary=json.loads((run/'summary.json').read_text())
    if summary['protocol_sha256']!=digest or summary['completed']+summary['failed']!=len(p['targets']):
        raise ValueError('Complete matching run required')
    old=json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text());states=[]
    for item in p['targets']:
        folder=run/item['name'];state=json.loads((folder/'state.json').read_text())
        if state['target']!=item or state['protocol_sha256']!=digest:raise ValueError('Target identity differs')
        for name,h in state['assets'].items():
            if sha(folder/name)!=h:raise ValueError('Raw asset checksum differs')
        states.append((item,folder,state))
    output.mkdir(parents=True);fits=[];failures=[]
    for item,folder,state in states:
        if state['status']!='completed':failures.append(dict(model=item['name'],status=state['status']));continue
        if not state['comparison']['passed']:raise ValueError('Completed target has failed comparison')
        spec=dict(kind='external_wells_distance') if item['name']=='W1' else old['models'][item['name']]
        for execution in ['serial','parallel']:
            raw=folder/state['attempt']/execution/'fit.npz'
            meta=json.loads(raw.with_suffix('.json').read_text())
            if meta['status']!='completed' or meta['target_id']!=state['target_id']:raise ValueError('Fit identity differs')
            with np.load(raw,allow_pickle=False) as z:draws=z['draws'].copy()
            if draws.shape!=(p['chains'],p['draws'],item['dimension']):raise ValueError('Retained shape differs')
            value=evaluate(spec,draws);array=value['values'].transpose(1,0,2)
            fit_id=item['name']+'-'+execution;name=fit_id+'.bin'
            np.asarray(array,dtype='<f8').ravel(order='F').tofile(output/name)
            fits.append(dict(id=fit_id,input=name,shape=list(array.shape),names=value['names'],input_sha256=sha(output/name),source_raw_sha256=sha(raw)))
    write(output/'transport.json',dict(fits=fits,
        scope='Native CPU NUTS readiness; serial/spawn repeats are paired technical executions, not independent inference experiments.',
        independent_unit='One four-chain validation fixture per target; diagnostic results do not establish convergence or formal accuracy.'))
    result=dict(protocol_sha256=digest,diagnostic_fits=len(fits),failed_targets=len(failures),failures=failures,
        source_run_summary_sha256=sha(run/'summary.json'),analysis_source_sha256=sha(Path(__file__)),numpy=np.__version__)
    write(output/'collect-summary.json',result);return result


def verify_diagnostics(output):
    output=Path(output);transport=json.loads((output/'transport.json').read_text())
    result=json.loads((output/'posterior.json').read_text())
    if set(result['results'])!={fit['id'] for fit in transport['fits']}:raise ValueError('Diagnostic fit set differs')
    if result['posterior']!='1.7.0':raise ValueError('Unexpected posterior version; preserve separate identity')
    rows=[]
    for fit in transport['fits']:
        name=fit['input']
        if Path(name).name!=name:raise ValueError('Invalid binary path')
        if sha(output/name)!=fit['input_sha256'] or sha(output/(name+'.roundtrip'))!=fit['input_sha256']:
            raise ValueError('Binary roundtrip checksum differs')
        stats=result['results'][fit['id']]
        if [s['variable'] for s in stats]!=fit['names']:raise ValueError('Function order differs')
        finite=[s['rhat'] for s in stats if s.get('rhat') is not None]
        rows.append(dict(id=fit['id'],some_finite_rhat_gt_1_01=any(x>1.01 for x in finite),
            undefined_rhat=sum(s.get('rhat') is None for s in stats),max_finite_rhat=max(finite,default=None)))
    receipt=dict(binary_roundtrips=len(rows),fits=rows,R=result['R'],posterior=result['posterior'],
        scope='Byte-level diagnostic input verification and descriptive modern diagnostics; no calibration/convergence certification')
    dest=output/'verification.json'
    if dest.exists():raise FileExistsError('Do not overwrite diagnostic receipt')
    write(dest,receipt);return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);subs=parser.add_subparsers(dest='action',required=True)
    f=subs.add_parser('freeze');f.add_argument('--profile',choices=['windows-v1','mac-companion-v1'],required=True)
    for name in ['protocol','inputs']:f.add_argument('--'+name,type=Path,required=True)
    r=subs.add_parser('run')
    for name in ['protocol','inputs','source','output']:r.add_argument('--'+name,type=Path,required=True)
    r.add_argument('--resume',action='store_true')
    c=subs.add_parser('collect')
    for name in ['protocol','run','output']:c.add_argument('--'+name,type=Path,required=True)
    v=subs.add_parser('verify-diagnostics');v.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    if a.action=='freeze':result=freeze(a.profile,a.protocol,a.inputs)
    elif a.action=='run':result=run(a.protocol,a.inputs,a.source,a.output,a.resume)
    elif a.action=='collect':result=collect(a.protocol,a.run,a.output)
    else:result=verify_diagnostics(a.output)
    print(json.dumps(result,indent=2))
