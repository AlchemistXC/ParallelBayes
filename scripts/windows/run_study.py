"""Pilot, freeze and resume the new Windows study without touching CPU archives."""
import argparse
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path
import numpy as np
from parallelbayes import sample,make_model
from parallelbayes.torch_backend.sampling import settings,random_tape,tape_hash
from evidence import (ROOT,configure,write_json,save_result,source_files,git,runtime,
                      fingerprint,sha,verify_checksums)

PAIRS=[('mala','sequential'),('mala','quasi_deer'),('rwm','sequential'),('rwm','online_picard')]
PROTOCOL=ROOT/'benchmark/protocols/windows-native-v1.json'
RUN=ROOT/'execution/windows-native/windows-native-v1'


def models():
    # Shared data/spec only: no reuse of the old protocol's execution identity.
    return json.loads((ROOT/'benchmark/protocols/protocol-v1.json').read_text())['models']


def step_size(name,kernel):
    old=json.loads((ROOT/'benchmark/protocols/protocol-v1.json').read_text())
    return next(t['config']['step_size'] for t in old['tasks'] if t['model']==name and t['config']['kernel']==kernel)


def task(name,kernel,executor,device,draws,chains,window,rep):
    return dict(model=name,replicate=rep,discard=draws//4,config=settings(dict(
        device=device,kernel=kernel,executor=executor,draws=draws,chains=chains,window=window,
        seed=841000+sorted(models()).index(name)*100+rep,solver_seed=951000+rep,
        step_size=step_size(name,kernel),max_iter=1024,audit=True)))


def execute_task(t,spec,tape,folder,repeats):
    start=time.perf_counter();folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    write_json(folder/'task.json',t)
    c=t['config']
    result=dict(status='failed',task=t)
    try:
        begin=time.perf_counter();model=make_model(spec,backend='torch',device=c['device'])
        model_seconds=time.perf_counter()-begin
        result=sample(model,c,tape)
        result['model_seconds']=model_seconds
        # Direct ordinary inference measurement from a newly constructed target.
        begin=time.perf_counter()
        normal=sample(spec,dict(c,audit=False),tape,backend='torch')
        if normal['status']=='completed':
            normal['moments']=[normal['draws'].mean((0,1)),normal['draws'].var((0,1))]
        normal_wall=time.perf_counter()-begin
        checks,output_seconds=save_result(folder/'normal',normal)
        result['normal']=dict(status=normal['status'],wall_seconds=normal_wall,
            timing=normal['timing'],checksums=checks,ordinary_output_seconds=output_seconds,
            scope='Python model construction, inputs, eager sampling, transform, basic moments; modern R diagnostics separate')
        same=normal['status']==result['status']
        if same and result['status']=='completed':
            same=np.array_equal(normal['unconstrained'],result['unconstrained']) and np.array_equal(normal['accept'],result['accept'])
        result['normal_replay_identical']=bool(same)
        warmed=[]
        for _ in range(repeats):
            replay=sample(model,dict(c,audit=False),tape)
            warmed.append(dict(status=replay['status'],timing=replay['timing'],diagnostics=replay['diagnostics']))
            if result['status']=='completed' and (replay['status']!='completed' or not np.array_equal(replay['unconstrained'],result['unconstrained'])):
                same=False
        result['warmed_eager_replays']=warmed
        if not same:
            result['failed_trajectory']=result.get('unconstrained',result.get('failed_trajectory'))
            result['draws']=result['unconstrained']=None
            result['status']='failed';result['replay_error']='normal/warmed replay differs from audited path'
    except Exception as exc:
        result=dict(status='failed',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc(),task=t)
    checks,output_seconds=save_result(folder,result,tape)
    checks['task.json']=sha(folder/'task.json')
    state=dict(task=t,status=result['status'],checksums=checks,elapsed_including_output=time.perf_counter()-start,
               output_seconds=output_seconds,tape_sha256=tape_hash(tape))
    write_json(folder/'state.json',state)
    return state


def pilot(out):
    if out.exists():raise FileExistsError('pilot attempt exists; select a new output')
    out.mkdir(parents=True);specs=models();tasks=[]
    for name in ['G1','G2','L1']:
        for chains in [1,4]:
            for window in [8,16]:
                for device in ['cpu','cuda']:
                    for kernel,executor in PAIRS:
                        tasks.append(task(name,kernel,executor,device,64,chains,window,90))
    write_json(out/'design.json',dict(scope='development pilot; not formal evidence',models=specs,tasks=tasks,
        source_commit=git('rev-parse','HEAD'),source_files=source_files(),runtime=runtime()))
    statuses=[]
    for i,t in enumerate(tasks):
        tape=random_tape(t['config'],specs[t['model']]['dimension'])
        s=execute_task(t,specs[t['model']],tape,out/f'{i:03d}',2);statuses.append(s['status'])
        print('pilot',i+1,len(tasks),s['status'],flush=True)
    write_json(out/'summary.json',dict(planned=len(tasks),completed=statuses.count('completed'),failed=statuses.count('failed')))


def freeze(pilot_path):
    if git('status','--porcelain'):raise RuntimeError('Commit source before protocol freeze')
    if PROTOCOL.exists() or RUN.exists():raise FileExistsError('frozen identity already exists')
    marker=Path(sys.prefix)/'PARALLELBAYES-FROZEN.json'
    if marker.exists():raise FileExistsError('venv already frozen')
    summary=json.loads((pilot_path/'summary.json').read_text())
    if summary['completed']+summary['failed']!=summary['planned']:raise ValueError('pilot incomplete')
    specs=models();tasks=[]
    for name in sorted(specs):
        for draws in [128,512]:
            for rep in range(4):
                for device in ['cpu','cuda']:
                    for kernel,executor in PAIRS:
                        tasks.append(task(name,kernel,executor,device,draws,4,16,rep))
    np.random.Generator(np.random.Philox(731045)).shuffle(tasks)
    RUN.mkdir(parents=True);inputs=RUN/'inputs';inputs.mkdir()
    for t in tasks:
        tape=random_tape(t['config'],specs[t['model']]['dimension'])
        digest=tape_hash(tape);target=inputs/(digest+'.npz')
        if not target.exists():np.savez_compressed(target,**tape)
        t['tape_sha256']=digest;t['tape_file_sha256']=sha(target)
    lock=ROOT/'environment/locks/windows-native-v1-pip-freeze.txt'
    lock.write_bytes(subprocess.check_output([sys.executable,'-m','pip','freeze','--all']))
    rlock=ROOT/'environment/locks/windows-native-v1-r-packages.csv'
    rlock.write_bytes((ROOT/'execution/windows-native/r-packages.csv').read_bytes())
    payload=dict(version='windows-native-v1',frozen_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        source_commit=git('rev-parse','HEAD'),source_files=source_files(),runtime=runtime(),
        dependency_lock=str(lock.relative_to(ROOT)).replace('\\','/'),dependency_lock_sha256=sha(lock),
        r_dependency_lock=str(rlock.relative_to(ROOT)).replace('\\','/'),r_dependency_lock_sha256=sha(rlock),
        r_executable='D:/Tools/R-4.6.1/bin/Rscript.exe',r_executable_sha256=sha('D:/Tools/R-4.6.1/bin/Rscript.exe'),
        pilot_summary_sha256=sha(pilot_path/'summary.json'),models=specs,tasks=tasks,
        purpose='Bounded native Windows eager execution comparison and finite-budget error; no universal GPU acceleration claim',
        primary_comparison='Same torch, target, float64, MH tape, kernel; sequential vs time executor separately on cpu and cuda',
        independent_replicates=4,technical_replays=2,initial='zero in each unconstrained coordinate',
        coordinate_policy='JSON specs, ordered q[1..d], log-positive exp; H2 maps z to x=exp(v/2)z',
        random_policy='Actual saved Philox arrays; same arrays across resource/executor within each model/rep/budget; budgets are not nested',
        audit_policy='zero acceptance mismatches; path error <=100*(atol+rtol*max(1,max(abs(path)))); finite and constraint gates',
        failure_policy='all terminal failures retained; no automatic fallback or replacement; interrupted attempts retained; checksum/identity-gated resume',
        memory_policy='2048 MiB array-workspace estimate, not a strict allocator bound; actual CUDA allocator peak separately recorded',
        iteration_policy='1024 per quasi-DEER block; 1024 total Picard rounds; no elapsed-time cutoff',
        reference_policy='Analytic functions for Gaussian/H1/H2/M1. Logistic finite reference unresolved: no reference error or accuracy pass claim. Historical L2 indeterminacy preserved.',
        functions={'gaussian':['standardized q1','standardized q1 squared','standardized q1 > 1'],
            'funnel':['v/3','tanh(v/3)','x1>0','cos(x1*exp(-v/2))'],
            'funnel_noncentered':['v/3','tanh(v/3)','x1>0','cos(x1*exp(-v/2))'],
            'mixture':['q1/sqrt(1+separation^2)','q1>0','q2','q2^2'],
            'logistic':['q1','q2','sigmoid(q1)','q1>0']},
        uncertainty='Paired replicate bootstrap (2000 fixed resamples) for median execution ratio and mean squared error; n=4 limited, pointwise descriptive intervals, no precise time-to-accuracy',
        timing_policy='synchronize CUDA before/after; compile=0 eager; actual first audit execution, ordinary inference and warmed eager execution separate; transfer, audit, output and R diagnostics separate; technical replays not independent draws',
        background_policy='Shared Windows desktop/WDDM; not exclusive GPU; no deletion based on load',
        nuts_scope='Pyro CPU baseline separately checked; not included in fixed-MH-tape formal comparison; GPU NUTS unverified',
        selector='deferred')
    payload['protocol_sha256']=fingerprint(payload)
    write_json(PROTOCOL,payload);write_json(RUN/'protocol.json',payload)
    write_json(marker,dict(protocol='windows-native-v1',protocol_sha256=payload['protocol_sha256'],
        source_commit=payload['source_commit'],dependency_lock_sha256=payload['dependency_lock_sha256']))
    print('frozen',len(tasks),'tasks',payload['protocol_sha256'])


def verify_protocol(p):
    unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if fingerprint(unsigned)!=digest:raise ValueError('protocol changed after freeze')
    if source_files()!=p['source_files']:raise ValueError('source changed after freeze')
    if runtime()!=p['runtime']:raise ValueError('runtime changed after freeze')
    if sha(ROOT/p['dependency_lock'])!=p['dependency_lock_sha256']:raise ValueError('dependency lock changed')
    marker=json.loads((Path(sys.prefix)/'PARALLELBAYES-FROZEN.json').read_text())
    if marker['protocol_sha256']!=digest:raise ValueError('frozen environment belongs to another protocol')


def formal():
    p=json.loads(PROTOCOL.read_text(encoding='utf-8'));verify_protocol(p)
    write_json(RUN/'sessions'/f'{time.time_ns()}.json',dict(source_commit=git('rev-parse','HEAD'),runtime=runtime(),protocol_sha256=p['protocol_sha256']))
    for i,t in enumerate(p['tasks']):
        folder=RUN/'tasks'/fingerprint(t)[:20];statefile=folder/'state.json'
        if statefile.exists():
            state=json.loads(statefile.read_text())
            if state['task']!=t or state.get('protocol_sha256')!=p['protocol_sha256']:
                raise ValueError('task/protocol identity changed')
            verify_checksums(folder/state['attempt'],state['checksums'])
            result=json.loads((folder/state['attempt']/'result.json').read_text())
            if result['status']!=state['status']:raise ValueError('result and state status differ')
            if result.get('normal'):verify_checksums(folder/state['attempt']/'normal',result['normal']['checksums'])
            if state['status'] in ['completed','failed']:continue
        tape_path=RUN/'inputs'/(t['tape_sha256']+'.npz')
        if sha(tape_path)!=t['tape_file_sha256']:raise ValueError('input array checksum changed')
        with np.load(tape_path) as f:tape={k:f[k] for k in f.files}
        if tape_hash(tape)!=t['tape_sha256']:raise ValueError('random tape changed')
        attempt='attempt-'+str(time.time_ns());dest=folder/attempt
        write_json(dest/'started.json',dict(task=t,protocol_sha256=p['protocol_sha256'],status='running'))
        state=execute_task(t,p['models'][t['model']],tape,dest,p['technical_replays'])
        state.update(attempt=attempt,protocol_sha256=p['protocol_sha256']);write_json(statefile,state)
        print('formal',i+1,len(p['tasks']),t['model'],t['config']['device'],t['config']['executor'],state['status'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['pilot','freeze','formal'])
    parser.add_argument('--output',type=Path,default=ROOT/'execution/windows-native/pilot-01')
    a=parser.parse_args();configure()
    if a.mode=='pilot':pilot(a.output)
    elif a.mode=='freeze':freeze(a.output)
    else:formal()
