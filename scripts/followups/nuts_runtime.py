"""Owned execution and verify-only recovery for finite technical calls.

No time cutoff. A registered interrupted call is closed with its observed
partial evidence and is never retried under the same identity.
"""
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import uuid
import psutil
from nuts_events import atomic_json,sha
from nuts_instrumented_worker import require_windows
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_runtime import host_lease
GIB=1024**3
WORK_CAP=6*GIB
RESERVE=128*1024**2

class ResourceStop(RuntimeError):
    """Preserve this registered attempt and stop launching additional calls."""



def tree_bytes(root):return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())


def preflight(root):
    if psutil.virtual_memory().available<12*GIB:raise MemoryError('At least 12 GiB available RAM is required at launch')
    used=tree_bytes(root)
    if used>WORK_CAP-RESERVE:raise OSError('Technical study working file allocation reached')
    if shutil.disk_usage(root).free<max(0,2*(WORK_CAP-used))+4*GIB:
        raise OSError('Insufficient free disk for remaining working files, one archive and 4 GiB reserve')


def seal(root,summary):
    atomic_json(root/'finished.json',summary)
    hashes={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'checksums.json'}
    atomic_json(root/'checksums.json',hashes)
    return dict(**summary,checksums_sha256=sha(root/'checksums.json'))


def verify(root,outcome):
    if sha(root/'checksums.json')!=outcome['checksums_sha256']:raise ValueError('Call integrity manifest differs')
    values=json.loads((root/'checksums.json').read_text())
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p!=root/'checksums.json'}
    if actual!=set(values):raise ValueError('Call asset set differs')
    for relative,digest in values.items():
        p=root/relative
        if not p.resolve().is_relative_to(root.resolve()) or sha(p)!=digest:raise ValueError('Call asset differs: '+relative)
    if json.loads((root/'finished.json').read_text())!={k:v for k,v in outcome.items() if k!='checksums_sha256'}:
        raise ValueError('Call outcome differs from the registry')
    return len(values)


def recover(root,record,registry):
    """Invoked while the host lease is held. Never restarts work."""
    require_windows()
    if record['outcome'] is not None:return verify(root,record['outcome'])
    from job_objects import observe_named_job
    root.mkdir(parents=True,exist_ok=True)
    if not (root/'request.json').exists():atomic_json(root/'request.json',record['request'])
    intent=root/'job-intent.json'
    if intent.exists():
        job=observe_named_job(json.loads(intent.read_text())['name'])
        if job['state']=='present' and job['active_processes']!=0:
            raise RuntimeError('Registered Job still has active processes; observe it again, never relaunch')
        proof=dict(kind='kernel_job_observation',value=job)
    else:
        # Job intent is durably written before Job creation/launch. This is
        # proof of a never-attempted spawn in this runner, not inference from PID.
        proof=dict(kind='never_launched_by_runner',reason='No launch intent; journal is ordered before CreateProcess')
    if (root/'finished.json').exists():
        existing=json.loads((root/'finished.json').read_text())
        if not (root/'checksums.json').exists():
            hashes={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
            atomic_json(root/'checksums.json',hashes)
        result=dict(**existing,checksums_sha256=sha(root/'checksums.json'))
        verify(root,result);registry.finish(record['id'],result);return len(json.loads((root/'checksums.json').read_text()))
    result=seal(root,dict(status='interrupted',kernel_terminal_verified=True,managed_active_processes=0,
        termination_proof=proof,posterior_samples_eligible=False,new_execution_on_recovery=0))
    registry.finish(record['id'],result);return verify(root,result)


def execute(root,study_root,request,registry):
    require_windows()
    if not registry.register(request):
        record=next(x for x in registry.records() if x['id']==request['id'])
        return recover(root,record,registry)
    root.mkdir(parents=True,exist_ok=False)
    atomic_json(root/'request.json',request)
    start=time.perf_counter();primary=None;final=None;code=None;error=None;spawned=False
    termination=None;job=None
    try:
        preflight(study_root)
        from nuts_job import ObservedJob
        name='Local\\ParallelBayes-nuts-localization-'+uuid.uuid4().hex
        atomic_json(root/'job-intent.json',dict(name=name,kill_on_last_noninherited_handle_close=True))
        environment=dict(os.environ);environment.pop('PYTHONPATH',None)
        environment.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONUTF8='1',
            PYTHONIOENCODING='utf-8',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
            R_LIBS_USER=request['r_library'])
        with ObservedJob(name,12*GIB) as job:
            with (root/'stdout.log').open('xb') as stdout,(root/'stderr.log').open('xb') as stderr,(root/'ownership.ndjson').open('x',encoding='utf-8',newline='\n') as log:
                try:
                    primary=job.launch_suspended([sys.executable,str(ROOT/'scripts/followups/nuts_child.py'),str(root/'request.json')],ROOT,stdout,stderr,environment)
                    spawned=True;atomic_json(root/'primary.json',primary);job.resume()
                    while True:
                        state=job.observe();state.update(utc_ns=time.time_ns(),monotonic_ns=time.perf_counter_ns())
                        # Scan disk every observation: small bounded study, no
                        # unbounded allocator or duration assumptions.
                        state['study_bytes']=tree_bytes(study_root);state['disk_free_bytes']=shutil.disk_usage(study_root).free
                        log.write(json.dumps(state,allow_nan=False)+'\n');log.flush()
                        if any(m['message'] in (9,10) for m in state['completion_messages']):
                            raise MemoryError('Owned Job reported a memory limit event')
                        if state['sampled_rss_bytes']>8*GIB:raise MemoryError('Owned process RSS guard exceeded')
                        if state['study_bytes']>WORK_CAP-RESERVE or state['disk_free_bytes']<4*GIB:
                            raise OSError('Working file or free disk guard reached')
                        if job.poll() is not None and state['active_processes']==0:break
                        time.sleep(.2)
                    final=job.observe();code=job.poll();termination='observed_zero_owned_processes'
                except BaseException:
                    job.terminate()
                    while True:
                        final=job.observe();log.write(json.dumps(final,allow_nan=False)+'\n');log.flush()
                        if final['active_processes']==0:break
                        time.sleep(.2)
                    code=job.poll() if spawned else None;termination='owned_termination_observed_zero';raise
    except BaseException as exc:
        error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
        if termination is None:
            if not spawned:termination='never_launched'
            else:
                # An observation error after spawn is unresolved. Do not write
                # a terminal outcome; the next explicit resume queries the Job.
                atomic_json(root/'runner-observation-error.json',error);raise
    child=json.loads((root/'child-result.json').read_text()) if (root/'child-result.json').exists() else None
    completed=error is None and code==0 and child is not None and child['status']=='completed'
    result=seal(root,dict(status='completed' if completed else 'failed',exit_code=code,error=error,
        kernel_terminal_verified=True,managed_active_processes=0,termination_proof=termination,
        final_job=final,primary=primary,seconds=time.perf_counter()-start,posterior_samples_eligible=False))
    registry.finish(request['id'],result)
    print(json.dumps(dict(call=request['id'],status=result['status'],seconds=result['seconds'])),flush=True)
    if error is not None:
        raise ResourceStop('Call saved; further launches stopped after runner/resource error: '+error['type']+': '+error['message'])
    return result
