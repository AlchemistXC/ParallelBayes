"""Explicit operational continuation of an already bound Mac technical batch.

Scientific sources, actual input arrays, task order and all numerical controls
remain pinned to the original protocol. This separate driver retains observed
interruptions without reexecution and journals its own additional source and
timing scope. It neither starts formal inference nor retries failed tasks.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
from batch_contract import BatchPlan
from batch_progress import advance
from formal_runtime import atomic_json,file_hash,host_lease
from measured_coordinator import MeasuredCoordinator

ROOT=Path(__file__).resolve().parents[2]


def run(protocol,inputs,output,rscript,r_library,host_lock,batch=0):
    protocol,inputs,output,rscript,r_library,host_lock=map(lambda p:Path(p).resolve(),
        (protocol,inputs,output,rscript,r_library,host_lock))
    p=json.loads(protocol.read_text());plan=BatchPlan(p)
    if sys.platform!='darwin' or p['required_platform']!='darwin' or p['scope_kind']!='technical_batch_validation':
        raise ValueError('Only an existing Mac technical batch is supported; formal/Windows gates remain open')
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Frozen source differs: '+name)
    for name,row in p['inputs'].items():
        if file_hash(inputs/name)!=row['sha256']:raise ValueError('Actual input file differs: '+name)
    for name,version in p['required_versions'].items():
        if importlib.metadata.version(name)!=version:raise ValueError('Frozen dependency differs: '+name)
    expected=dict(protocol_sha256=plan.protocol_sha256,inputs=str(inputs),rscript=str(rscript),
                  r_library=str(r_library),host_lock=str(host_lock))
    if not output.exists() or json.loads((output/'binding.json').read_text())!=expected:
        raise ValueError('Continuation requires the original established batch binding')
    tasks=list(plan.tasks(batch))
    if not tasks:raise ValueError('No declared tasks in this batch')
    extra={f'scripts/completion/{n}.py':file_hash(ROOT/f'scripts/completion/{n}.py') for n in ('batch_progress','continue_batch')}
    for name,h in extra.items():
        import hashlib
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit operational source before execution: '+name)
    with host_lease(output/'continuation-driver.lock','continue original technical batch'):
        invocation=output/'continuations'/str(time.time_ns());invocation.mkdir(parents=True,exist_ok=False)
        start=dict(protocol_sha256=plan.protocol_sha256,batch=batch,tasks=[t['id'] for t in tasks],
            driver_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            additional_operational_sources=extra,original_scientific_source_commit=p['source_commit'],
            scientific_parameters_changed=False,automatic_retries=False,
            cost_scope='Driver loop including per-task history observation, retention decisions and journaling. Excludes initial source/input/dependency checks and own final report write. Original worker and invocation ledgers keep their distinct scopes.',
            started_ns=time.time_ns(),formal_inference_complete=False)
        atomic_json(invocation/'started.json',start)
        measured=MeasuredCoordinator(host_lock,output/'call-costs');rows=[];began=time.perf_counter()
        try:
            for index,task in enumerate(tasks):
                capsule,digest=plan.capsule(task['id'])
                job=dict(task=dict(task,protocol_sha256=plan.protocol_sha256),
                    request=dict(capsule=capsule,capsule_sha256=digest,inputs=str(inputs),rscript=str(rscript),r_library=str(r_library)),
                    worker=ROOT/'scripts/completion/batch_worker.py',output=output/'tasks'/task['id'],
                    required_disk_bytes=p['required_disk_bytes_per_task'],max_tree_rss_bytes=p['process_tree_rss_limit_bytes'])
                print(json.dumps(dict(index=index+1,total=len(tasks),task=task)),flush=True)
                result=advance(measured,job);rows.append(result)
                atomic_json(invocation/f'task-{index:04d}.json',result)
                print(json.dumps({k:result[k] for k in ('status','operation','newly_executed','retry_available')}),flush=True)
        except BaseException as exc:
            atomic_json(invocation/'driver-failure.json',dict(error=type(exc).__name__+': '+str(exc),
                traceback=traceback.format_exc(),journaled_tasks=len(rows),driver_loop_seconds=time.perf_counter()-began,
                remaining_tasks=len(tasks)-len(rows),failure_is_not_a_numerical_task_result=True))
            raise
        report=dict(protocol_sha256=plan.protocol_sha256,batch=batch,planned=len(tasks),
            completed=sum(r['status']=='completed' for r in rows),failed=sum(r['status']=='failed' for r in rows),
            interrupted=sum(r['status']=='interrupted' for r in rows),pending=0,
            newly_executed=sum(r['newly_executed'] for r in rows),
            retained_without_reexecution=sum(r['operation']=='retain_without_reexecution' for r in rows),
            complete_invocation_seconds_available=sum(r['costs']['complete_invocation_seconds'] is not None for r in rows),
            driver_loop_seconds=time.perf_counter()-began,cost_scope=start['cost_scope'],
            task_rows=[f'task-{i:04d}.json' for i in range(len(rows))],
            formal_scientific_repetitions=0,formal_inference_complete=False)
        atomic_json(invocation/'summary.json',report)
        return dict(report,invocation=str(invocation))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','inputs','output','rscript','r-library','host-lock'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--batch',type=int,default=0)
    print(json.dumps(run(**vars(p.parse_args())),indent=2),flush=True)
