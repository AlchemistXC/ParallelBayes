"""Finite mechanism pilot; preserve core samplers and all original protocols."""
import hashlib
import json
from pathlib import Path
import os
import platform
import sys
import time
import traceback
import argparse
import subprocess
import importlib.metadata
from contextlib import contextmanager
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'r-package/inst/python'))
sys.path.insert(0,str(ROOT/'scripts/completion'))


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def design(profile):
    old=json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())
    groups=[]
    def add(name,kernel,rep,chains,draws,windows,step,role):
        g=dict(model=name,kernel=kernel,replicate=rep,chains=chains,draws=draws,
               windows=windows,step_size=step,role=role)
        g['id']=identity(g)[:20];groups.append(g)
    if profile=='windows':
        for name in ['G1','G2','L1']:
            for kernel in ['mala','rwm']:
                step=next(t['config']['step_size'] for t in old['tasks'] if t['model']==name and t['config']['kernel']==kernel)
                for rep in range(2):
                    for chains in [1,4]:add(name,kernel,rep,chains,128,[4,16],step,'window_chain_grid')
        for rep in range(2):
            for chains in [1,4]:add('G2','rwm',rep,chains,128,[4,16],.25,'prespecified_step_contrast')
            for name,step in [('G2',.25),('L1',.1)]:
                add(name,'rwm',rep,1,512,[16],step,'equal_512_output_chain_allocation')
                add(name,'rwm',rep,16,32,[],step,'equal_512_output_chain_allocation')
        platform='win32';devices=['cpu','cuda'];reps=2;threads=4
    elif profile=='smoke':
        add('G1','mala',0,2,24,[4,8],.1,'Mac_runner_validation')
        add('G1','rwm',0,2,24,[4,8],.5,'Mac_runner_validation')
        add('G2','mala',0,1,16,[4,8],.1,'Mac_runner_validation')
        platform='darwin';devices=['cpu'];reps=1;threads=1
    else:raise ValueError('Unknown experiment profile')
    names=sorted(set(g['model'] for g in groups))
    return dict(identity='mechanism-'+profile+'-pilot-v1',profile=profile,required_platform=platform,
        devices=devices,models={n:old['models'][n] for n in names},groups=groups,
        independent_tapes_per_model=reps,torch_cpu_threads=threads,technical_replays=3,
        inference_claim=False,
        scope='Finite mechanism pilot; technical repetitions are not independent inference experiments',
        master_tape_shape_policy='16 chains x 512 transitions x dimension; all configurations use exact prefixes',
        master_seed_base=4761000,solver_seed_base=4762000,order_seed=4763000,
        tolerance=dict(atol=1e-10,rtol=1e-10,paired_atol=1e-7,acceptance_mismatches_allowed=0),
        max_iter=2048,memory_limit_mb=2048,
        interpretation='Window comparisons preserve a kernel and actual tape. Different chain allocations have different paths, same 512 total outputs and same machine; this is throughput, not equivalent inference.',
        step_contrast='G2 RWM .25 versus historical 1.0 is a prespecified mechanism perturbation, not an optimized or inference-validated setting.',
        measurements='Audited first call, 3 interleaved warmed calls, separate operation probes and one post-probe replay; synchronized wall time/process CPU time/actual arrays/solver work/host reads/memory/failures. Probe calls 3 blocks x 5 repetitions, not independent sampling replicates. No summed GPU/host component fiction.')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(value):
    if isinstance(value,np.ndarray):return plain(value.tolist())
    if isinstance(value,np.generic):return plain(value.item())
    if isinstance(value,dict):return {k:plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    if isinstance(value,float) and not np.isfinite(value):return None
    return value


def write(path,value):
    path.write_text(json.dumps(plain(value),indent=2,allow_nan=False)+'\n')


def actual_hash(tape):
    h=hashlib.sha256()
    for k in sorted(tape):
        a=np.ascontiguousarray(tape[k],dtype='<f8')
        h.update(k.encode());h.update(str(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()


def source_files():
    old=json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())
    names=list(old['source_files'])+['scripts/completion/mechanism_runner.py','scripts/completion/mechanism_probes.py']
    return {n:sha(ROOT/n) for n in sorted(names)}


@contextmanager
def experiment_lease(folder):
    """An OS lock is authoritative; the persistent metadata is informative only."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    stream=(folder/'runner.lock').open('a+b')
    if stream.seek(0,2)==0:stream.write(b'0');stream.flush()
    stream.seek(0)
    acquired=False
    try:
        try:
            if sys.platform=='win32':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            acquired=True
        except OSError as exc:raise RuntimeError('An active runner holds the operating-system lease') from exc
        write(folder/'lease.json',dict(pid=os.getpid(),host=platform.node(),state='held',
             note='Metadata is not proof of liveness; the OS lock enforces ownership'))
        yield
    finally:
        if acquired:
            write(folder/'lease.json',dict(pid=os.getpid(),host=platform.node(),state='released'))
            stream.seek(0)
            if sys.platform=='win32':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        stream.close()


def run_group(spec,group,tape,folder,device,technical_replays=3,resume=False):
    """Audited complete workflows, counterbalanced replays, immutable checkpoints."""
    import torch
    import psutil
    from parallelbayes.torch_backend.models import make_model
    from parallelbayes.torch_backend.sampling import sample,settings,sync
    folder=Path(folder)
    fingerprint=identity(dict(spec=spec,group=group,tape=actual_hash(tape),device=device,
        technical_replays=technical_replays,sources=source_files(),torch=torch.__version__,
        threads=torch.get_num_threads(),python=platform.python_version()))
    statefile=folder/'state.json'
    if folder.exists():
        if not resume:raise FileExistsError('Use explicit resume for an existing group')
        if statefile.exists():
            saved=json.loads(statefile.read_text())
            if saved['identity']!=fingerprint:raise ValueError('Group identity changed')
            for name,digest in saved['assets'].items():
                if sha(folder/name)!=digest:raise ValueError('Group checksum mismatch: '+name)
            return saved  # Both terminal success and terminal failure are retained.
    else:folder.mkdir(parents=True)
    attempt=folder/('attempt-'+str(time.time_ns()));attempt.mkdir()
    write(attempt/'started.json',dict(identity=fingerprint,group=group,tape_sha256=actual_hash(tape)))
    np.savez_compressed(attempt/'inputs.npz',**tape)
    group_start=time.perf_counter()
    begin=time.perf_counter()
    try:
        model=make_model(spec,device);sync(model.device)
    except Exception as exc:
        write(attempt/'setup-failure.json',dict(status='failed',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc()))
        state=dict(identity=fingerprint,status='failed',attempt=attempt.name,group=group,device=device,
            assets={str(p.relative_to(folder)):sha(p) for p in attempt.iterdir() if p.is_file()},
            audited_workflows=0,paired_acceptance_mismatches=None,replays_identical=False,records=[],
            probes=[],failure_scope='model setup; no workflow sampled')
        temporary=folder/'state.new.json';write(temporary,state);os.replace(temporary,statefile)
        return state
    setup_seconds=time.perf_counter()-begin
    defaults=dict(kernel=group['kernel'],device=device,draws=group['draws'],chains=group['chains'],
        initial=np.zeros((group['chains'],model.dimension)).tolist(),step_size=group['step_size'],
        max_iter=2048,memory_limit_mb=2048,on_failure='error',audit=True)
    executor='quasi_deer' if group['kernel']=='mala' else 'online_picard'
    configs={'sequential':settings(dict(defaults,executor='sequential',window=1))}
    configs.update({f'{executor}-w{w}':settings(dict(defaults,executor=executor,window=w)) for w in group['windows']})
    names=list(configs);order=list(names)
    rng=np.random.Generator(np.random.Philox(int(identity(group)[:12],16)))
    rng.shuffle(order)
    baseline={};records=[];identical=True
    array_keys=['draws','unconstrained','accept','primary_accept','failed_trajectory','primary_failed_trajectory']
    process=psutil.Process()
    probe_reports=[]
    for phase in range(technical_replays+2):
        if phase==technical_replays+1:
            first=baseline['sequential']
            if first['status']=='completed':
                from mechanism_probes import probe_fixed_batch
                path=first['unconstrained']
                previous=np.concatenate((np.zeros((group['chains'],1,model.dimension)),path[:,:-1,:]),axis=1)
                for width in (group['windows'] or [1]):
                    width=min(width,group['draws'])
                    tensors=[torch.tensor(x,dtype=torch.float64,device=model.device) for x in
                        [previous[:,:width],tape['noise'][:,:width],tape['log_uniform'][:,:width],tape['directions'][:,:width]]]
                    probe=probe_fixed_batch(model,*tensors,group['step_size'],group['kernel'],attempt/f'probe-w{width}')
                    probe_reports.append(dict(width=width,status=probe['status']))
            else:probe_reports.append(dict(status='not_run_invalid_reference'))
        labels=order[phase%len(order):]+order[:phase%len(order)]
        for label in labels:
            config=dict(configs[label],audit=phase==0)
            before_rss=process.memory_info().rss
            cpu0=time.process_time();wall0=time.perf_counter()
            try:
                result=sample(model,config,tape)
                match=True
                if phase==0:baseline[label]=result
                else:
                    first=baseline[label]
                    match=first['status']==result['status']=='completed' and all(np.array_equal(first[k],result[k]) for k in ['unconstrained','accept'])
                    identical=identical and match
                    if not match:
                        result['failed_trajectory']=result.get('unconstrained',result.get('failed_trajectory'))
                        result['draws']=result['unconstrained']=None
                        result['status']='failed';result['replay_error']='Actual path/events differ from audited first call or first call failed'
            except Exception as exc:
                result=dict(status='failed',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
                match=False;identical=False
                if phase==0:baseline[label]=result
            wall=time.perf_counter()-wall0;cpu=time.process_time()-cpu0
            name=f'phase-{phase}-{label}'
            arrays={k:result[k] for k in array_keys if result.get(k) is not None}
            archive_start=time.perf_counter()
            np.savez_compressed(attempt/(name+'.npz'),**arrays)
            small={k:v for k,v in result.items() if k not in array_keys}
            small['measurement']=dict(phase='audited_first_call' if phase==0 else ('post_probe_replay' if phase==technical_replays+1 else 'warmed_replay'),
                replay_index=phase,wall_seconds=wall,process_cpu_seconds=cpu,
                process_cpu_percent=100*cpu/wall if wall else None,rss_before=before_rss,
                rss_after=process.memory_info().rss,process_threads=process.num_threads(),
                scope='Process CPU utilization can exceed 100%; RSS endpoints are not peak CPU memory; CUDA work synchronized by sampler')
            write(attempt/(name+'.json'),small)
            records.append(dict(label=label,phase=phase,status=result['status'],raw=name+'.npz',record=name+'.json',
                                replay_identical=match if phase else None,archive_seconds=time.perf_counter()-archive_start))
    pairs=[];sequential=baseline['sequential']
    for label in names[1:]:
        other=baseline[label]
        if sequential['status']==other['status']=='completed':
            error=float(np.max(np.abs(sequential['unconstrained']-other['unconstrained'])))
            branches=int(np.sum(sequential['accept']!=other['accept']))
            pairs.append(dict(label=label,max_path_error=error,acceptance_mismatches=branches,passed=error<=1e-7 and branches==0))
        else:pairs.append(dict(label=label,passed=False,reason='At least one audited workflow failed'))
    write(attempt/'comparison.json',dict(pairs=pairs,model_setup_seconds=setup_seconds,
         order=order,records=records,scope='One actual tape; replay phases do not increase independent replication'))
    passed=all(x['status']=='completed' for x in records) and all(x['passed'] for x in pairs) and identical and all(x['status']=='passed' for x in probe_reports)
    assets={str(p.relative_to(folder)):sha(p) for p in sorted(attempt.rglob('*')) if p.is_file()}
    state=dict(identity=fingerprint,status='completed' if passed else 'failed',attempt=attempt.name,
        group=group,device=device,assets=assets,audited_workflows=len(configs),
        paired_acceptance_mismatches=sum(p['acceptance_mismatches'] for p in pairs) if all('acceptance_mismatches' in p for p in pairs) else None,
        replays_identical=identical,records=records,model_setup_seconds=setup_seconds,probes=probe_reports,
        group_seconds_before_final_state_write=time.perf_counter()-group_start)
    temporary=folder/'state.new.json';write(temporary,state);os.replace(temporary,statefile)
    return state


def master_tape(plan,name,rep):
    d=plan['models'][name]['dimension'];index=sorted(plan['models']).index(name)
    seed=plan['master_seed_base']+100*index+rep
    solver=plan['solver_seed_base']+100*index+rep
    rng=np.random.Generator(np.random.Philox(np.random.SeedSequence([seed,101])))
    srng=np.random.Generator(np.random.Philox(np.random.SeedSequence([solver,102])))
    shape=(16,512,d)
    return dict(noise=rng.standard_normal(shape),log_uniform=np.log(np.maximum(rng.random(shape[:2]),np.finfo(float).tiny)),
                directions=(2*srng.integers(0,2,size=shape)-1).astype(float))


def freeze(profile,folder):
    if folder.exists():raise FileExistsError('Preserve frozen experiment identity')
    plan=design(profile);sources=source_files()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for name,digest in sources.items():
        if hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)).hexdigest()!=digest:
            raise ValueError('Commit source before freezing: '+name)
    folder.mkdir(parents=True);inputs=folder/'inputs';inputs.mkdir()
    hashes={}
    for name in sorted(plan['models']):
        for rep in range(plan['independent_tapes_per_model']):
            key=f'{name}-r{rep}';tape=master_tape(plan,name,rep)
            np.savez_compressed(inputs/(key+'.npz'),**tape)
            hashes[key]=dict(actual_sha256=actual_hash(tape),file_sha256=sha(inputs/(key+'.npz')))
    plan.update(source_commit=commit,source_files=sources,inputs=hashes)
    plan['protocol_sha256']=identity(plan)
    write(folder/'protocol.json',plan)
    print(json.dumps(dict(protocol_sha256=plan['protocol_sha256'],groups=len(plan['groups']),
                         workflow_configurations=sum(1+len(g['windows']) for g in plan['groups'])*len(plan['devices']))))


def read_plan(path):
    plan=json.loads(path.read_text());unsigned=dict(plan);digest=unsigned.pop('protocol_sha256')
    if identity(unsigned)!=digest:raise ValueError('Protocol checksum mismatch')
    if plan['source_files']!=source_files():raise ValueError('Frozen scientific source changed')
    return plan


def prepare_inputs(plan,folder):
    folder.mkdir(parents=True,exist_ok=True)
    for name in sorted(plan['models']):
        for rep in range(plan['independent_tapes_per_model']):
            key=f'{name}-r{rep}';path=folder/(key+'.npz');expected=plan['inputs'][key]
            if not path.exists():
                tape=master_tape(plan,name,rep)
                if actual_hash(tape)!=expected['actual_sha256']:raise ValueError('Regenerated actual arrays differ')
                np.savez_compressed(path,**tape)
            if sha(path)!=expected['file_sha256']:raise ValueError('Input file checksum mismatch: '+key)
    return dict(status='inputs_verified',files=len(plan['inputs']),protocol_sha256=plan['protocol_sha256'])


def _run_experiment(plan,inputs,output,device,resume=False):
    if sys.platform!=plan['required_platform']:
        raise RuntimeError('Actual platform does not match protocol; no WSL/Linux or Mac substitution for Windows')
    if device not in plan['devices']:raise ValueError('Device not in frozen protocol')
    if output==inputs or inputs in output.parents:raise ValueError('Keep output outside frozen inputs')
    prepare_inputs(plan,inputs)
    import torch
    import scipy
    import psutil
    from parallelbayes.torch_backend.sampling import environment
    torch.set_num_threads(plan['torch_cpu_threads'])
    env=environment();env.update(numpy=np.__version__,scipy=scipy.__version__,psutil=psutil.__version__,
                                physical_cpus=psutil.cpu_count(logical=False),logical_cpus=psutil.cpu_count(),
                                cuda_capability=list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None)
    env['installed_packages']={d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name']}
    if env['cuda_available']:
        try:
            probe=subprocess.run(['nvidia-smi','--query-gpu=driver_version,name,memory.total','--format=csv,noheader'],capture_output=True,text=True)
            env['nvidia_smi_driver_query']=dict(exit_code=probe.returncode,stdout=probe.stdout.strip(),stderr=probe.stderr.strip())
        except OSError as exc:env['nvidia_smi_driver_query']=dict(error=str(exc))
    if device=='cuda' and (not env['cuda_available'] or '5080' not in str(env['gpu_name'])):
        raise RuntimeError('Protocol requires the actual RTX5080 CUDA device')
    manifest=dict(protocol_sha256=plan['protocol_sha256'],source_commit=plan['source_commit'],device=device,runtime=env)
    if (output/'run.json').exists():
        if not resume:raise FileExistsError('Use --resume for an existing run')
        if json.loads((output/'run.json').read_text())!=manifest:raise ValueError('Resume protocol/runtime identity differs')
    else:
        write(output/'run.json',manifest)
    groups=list(plan['groups'])
    np.random.Generator(np.random.Philox(plan['order_seed'])).shuffle(groups)
    states=[]
    for i,g in enumerate(groups):
        key=f"{g['model']}-r{g['replicate']}"
        with np.load(inputs/(key+'.npz'),allow_pickle=False) as data:
            master={k:data[k].copy() for k in data.files}
        if actual_hash(master)!=plan['inputs'][key]['actual_sha256']:raise ValueError('Actual tape checksum mismatch')
        tape={k:a[:g['chains'],:g['draws']].copy() for k,a in master.items()}
        state=run_group(plan['models'][g['model']],g,tape,output/'groups'/g['id'],device,
                        technical_replays=plan['technical_replays'],resume=resume)
        states.append(state)
        print(i+1,len(groups),g['model'],g['kernel'],g['chains'],g['draws'],state['status'],flush=True)
    summary=dict(status='terminal',protocol_sha256=plan['protocol_sha256'],device=device,
        planned_groups=len(groups),completed_groups=sum(s['status']=='completed' for s in states),
        failed_groups=sum(s['status']=='failed' for s in states),
        audited_workflows=sum(s['audited_workflows'] for s in states),
        all_group_identities={s['group']['id']:s['identity'] for s in states},
        independent_tapes_per_model=plan['independent_tapes_per_model'],inference_claim=False)
    write(output/'summary.json',summary)
    print(json.dumps(summary,indent=2))
    return summary


def run_experiment(plan,inputs,output,device,resume=False):
    if sys.platform!=plan['required_platform']:
        raise RuntimeError('Actual platform does not match protocol; no substitute execution')
    if output==inputs or inputs in output.parents:raise ValueError('Preserve input directory')
    if output.exists():
        if not resume:raise FileExistsError('Existing run requires --resume')
        if not (output/'run.json').exists():raise ValueError('No valid run manifest; preserve this attempt and choose a new output')
    with experiment_lease(output):
        try:return _run_experiment(plan,inputs,output,device,resume)
        except Exception as exc:
            write(output/('run-error-'+str(time.time_ns())+'.json'),dict(error=type(exc).__name__+': '+str(exc),
                protocol_sha256=plan['protocol_sha256'],traceback=traceback.format_exc()))
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');f.add_argument('--profile',choices=['windows','smoke'],required=True);f.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('prepare');p.add_argument('--plan',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    r=sub.add_parser('run');r.add_argument('--plan',type=Path,required=True);r.add_argument('--inputs',type=Path,required=True)
    r.add_argument('--output',type=Path,required=True);r.add_argument('--device',choices=['cpu','cuda'],required=True);r.add_argument('--resume',action='store_true')
    a=parser.parse_args()
    if a.action=='freeze':freeze(a.profile,a.output.resolve())
    elif a.action=='prepare':print(json.dumps(prepare_inputs(read_plan(a.plan),a.inputs.resolve()),indent=2))
    else:run_experiment(read_plan(a.plan),a.inputs.resolve(),a.output.resolve(),a.device,a.resume)
