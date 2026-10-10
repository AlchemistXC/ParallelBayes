"""Three-prespecified-batch driver with explicit boundary pause and verify-only.

Historical formal_batch is never called. Cooperative pause does not interrupt
the current Job; SIGINT only requests the same boundary action. Real native
end evidence remains required, not a state file or an observation timeout.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time
import traceback
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'scripts/windows')]
from compact_freeze import verify
from compact_execution import CompactDispatch
from compact_control import request_pause,pause_pending,acknowledge_pause
from formal_runtime import atomic_json,file_hash,host_lease,ResourceWait
from formal_execution import ENDED
from formal_batch import verify_phase_closure
from task_journal import TaskJournal


def resource_guard(available_ram,minimum_ram,disk_free,required_disk):
    if available_ram<minimum_ram:raise ResourceWait('Available RAM below compact task boundary reserve')
    if disk_free<required_disk:raise ResourceWait('Disk below compact task start reserve')


def execute_slots(dispatch,batch,phase,*,coordinator,phase_root,invocation,make_request,limits,
                  resume=False,verify_only=False,retry_task=None,pause_check=lambda:None,resource_check=lambda:None):
    """Native runtime calls isolated from scope preflight for genuine fixture tests."""
    from formal_measured_runtime import invoke
    phase_root=Path(phase_root);invocation=Path(invocation)
    registered=set(coordinator.task_keys(dispatch.plan.protocol_sha256,batch))
    slots=list(dispatch.slots(batch,phase))
    if verify_only and any(TaskJournal.key(s['task']) not in registered for s in slots):
        raise ValueError('Verify-only cannot register or start an unvisited compact task')
    rows=[];new=0
    visits=phase_root/'visits'/invocation.name;visits.mkdir(parents=True,exist_ok=False)
    for index,slot in enumerate(slots,1):
        pending=None if verify_only else pause_check()
        if pending:
            receipt=dict(status='paused_at_task_boundary',pending=pending,visited=len(rows),newly_executed=new,
                last_task=rows[-1]['task']['id'] if rows else None,remaining=len(slots)-len(rows),
                protocol_sha256=dispatch.plan.protocol_sha256,rows=rows,phase_closed=False,
                pause_receipt_is_not_alone_native_job_end_proof=True)
            atomic_json(invocation/'paused.json',receipt);return receipt
        resource_check()
        task=slot['task'];key=TaskJournal.key(task)
        kwargs=dict(task=task,request=make_request(slot),worker=ROOT/'scripts/windows/compact_worker.py',
            output=phase_root/'tasks'/task['id'],limits=limits)
        print(json.dumps(dict(index=index,total=len(slots),task=task)),flush=True)
        result=invoke(coordinator,kwargs,phase_root/'call-costs'/task['id'],
            resume=(resume or verify_only) and key in registered,retry=retry_task==task['id'])
        if verify_only and result['newly_executed']:raise ValueError('Unexpected execution during verify-only')
        registered.add(key)
        history=visits/(task['id']+'.history.json');coordinator.export_task(task,history)
        row=dict(task=task,scheduled_index=index,outcome=result['outcome'],newly_executed=result['newly_executed'],
            samples_eligible=result['samples_eligible'],measurement_available=result['measurement_available'],
            history_export=history.name,history_export_sha256=file_hash(history))
        if row['outcome'] not in ENDED:raise ValueError('Nonterminal compact runtime outcome')
        atomic_json(visits/(task['id']+'.json'),row);rows.append(row);new+=int(row['newly_executed'])
        atomic_json(phase_root/'progress.json',dict(invocation=invocation.name,visited=len(rows),newly_executed=new,
            last_task=task['id'],remaining=len(slots)-len(rows),phase_closed=False))
        print(json.dumps(dict(task=task['id'],outcome=row['outcome'],newly_executed=row['newly_executed'])),flush=True)
    summary=dispatch.summarize_phase(batch,phase,rows)
    if not summary['closed']:raise ValueError('Incomplete compact phase cannot close')
    closure=dict(summary=summary,rows={r['task']['id']+'.json':file_hash(visits/(r['task']['id']+'.json')) for r in rows},
        phase_closure_does_not_imply_convergence=True)
    atomic_json(visits/'closed.json',closure)
    atomic_json(phase_root/'latest-closed.json',dict(summary=(visits/'closed.json').relative_to(phase_root).as_posix(),sha256=file_hash(visits/'closed.json')))
    return dict(summary,status='closed',newly_executed=new,verify_only=verify_only)


def task_assets(root):
    root=Path(root)
    return {p.relative_to(root).as_posix():file_hash(p) for p in root.rglob('*') if p.is_file()}


def storage_observation(bundle,protocol):
    bundle=Path(bundle);size=sum(p.stat().st_size for p in bundle.rglob('*') if p.is_file())
    observation=dict(bundle_bytes=size,disk=shutil.disk_usage(bundle)._asdict(),
        volume=str(bundle.anchor),maximum_bundle_bytes=protocol['storage_policy']['maximum_bundle_bytes'],
        polling_peak_is_not_hard_cap=True,checked_at_phase_boundary=True)
    if size>observation['maximum_bundle_bytes']:raise ResourceWait('Compact bundle allocation exceeded; preserve assets and await resources')
    resource_guard(2**63,0,observation['disk']['free'],protocol['required_disk_bytes_per_task'])
    return observation


def run(bundle,batch,phase,*,native_acceptance=None,resume=False,verify_only=False,retry_task=None,retry_reason=None):
    if sys.platform!='win32':raise ValueError('Actual native Windows required')
    if bool(retry_task)!=bool(retry_reason) or (retry_task and (not resume or phase!='main' or verify_only)):
        raise ValueError('One named main infrastructure retry needs explicit resume/reason')
    bundle=Path(bundle).resolve()
    with host_lease(bundle/'compact-driver.lock','compact phase driver'):
        invocation=bundle/'driver-invocations'/uuid.uuid4().hex;invocation.mkdir(parents=True,exist_ok=False)
        from job_objects import identity
        atomic_json(invocation/'started.json',dict(batch=batch,phase=phase,resume=resume,verify_only=verify_only,
            retry_task=retry_task,retry_reason=retry_reason,pid_identity=identity(os.getpid()),source_sha256=file_hash(__file__),
            started_ns=time.time_ns(),timestamp_is_not_duration=True))
        began=time.perf_counter();previous_handler=None
        try:
            marker,p,plan,binding=verify(bundle)
            from compact_prepare import gather_environment
            current,probe,resources,_,_=gather_environment(Path(binding['environment']['rscript']),Path(binding['environment']['r_library']))
            atomic_json(invocation/'probe.json',probe);atomic_json(invocation/'resources.json',resources)
            if current!=binding['environment']:raise ValueError('Frozen full compact environment changed')
            for name,digest in p['source_files'].items():
                if file_hash(ROOT/name)!=digest:raise ValueError('Frozen compact source changed: '+name)
            if not plan['technical']:
                from compact_acceptance import verify_acceptance
                verify_acceptance(native_acceptance,p,ROOT,environment=current)
            dispatch=CompactDispatch(p,plan,ROOT)
            atomic_json(invocation/'storage-before.json',storage_observation(bundle,p))
            for b,prior in dispatch.predecessors(batch,phase):
                verify_phase_closure(bundle/'formal-runs'/f'batch-{b:02d}'/prior,dispatch,b,prior)
            identifiers={t['id'] for t in dispatch.tasks(batch,phase)}
            if retry_task and retry_task not in identifiers:raise ValueError('Retry task outside compact main phase')
            from formal_owned_runtime import Coordinator
            coordinator=Coordinator(Path(binding['shared_host_lock']))
            phase_root=bundle/'formal-runs'/f'batch-{batch:02d}'/phase;phase_root.mkdir(parents=True,exist_ok=True)
            before=task_assets(phase_root/'tasks') if verify_only else None
            def make_request(slot):
                return dispatch.request(slot,bundle=bundle,source_root=ROOT,rscript=current['rscript'],
                    r_library=current['r_library'],sealed_marker=bundle/'FROZEN.json',native_acceptance=native_acceptance)
            import psutil
            def guard():resource_guard(psutil.virtual_memory().available,p['minimum_available_ram_bytes'],
                shutil.disk_usage(bundle).free,p['required_disk_bytes_per_task'])
            if not verify_only:
                previous_handler=signal.signal(signal.SIGINT,lambda *_:request_pause(bundle,p['protocol_sha256'],'SIGINT received: cooperative boundary pause'))
            result=execute_slots(dispatch,batch,phase,coordinator=coordinator,phase_root=phase_root,invocation=invocation,
                make_request=make_request,limits=p['windows_limits'],resume=resume,verify_only=verify_only,retry_task=retry_task,
                pause_check=lambda:pause_pending(bundle,p['protocol_sha256']),resource_check=guard)
            if verify_only:
                after=task_assets(phase_root/'tasks')
                if before!=after:raise ValueError('Original task assets changed during zero-execution verification')
                result.update(task_assets_unchanged=True,task_asset_count=len(before),
                    task_assets_sha256=__import__('formal_runtime').fingerprint(before))
            atomic_json(invocation/'storage-after.json',storage_observation(bundle,p))
            result.update(controller_seconds=time.perf_counter()-began,invocation=str(invocation),formal_inference_complete=False)
            atomic_json(invocation/'finished.json',result);return result
        except BaseException as exc:
            atomic_json(invocation/'failed.json',dict(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),
                controller_seconds=time.perf_counter()-began,unvisited_tasks_are_not_failures=True,automatic_retries=False));raise
        finally:
            if previous_handler is not None:signal.signal(signal.SIGINT,previous_handler)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('run');p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--batch',type=int,choices=range(3),required=True);p.add_argument('--phase',choices=['main','cache'],required=True)
    p.add_argument('--native-acceptance',type=Path);p.add_argument('--resume',action='store_true');p.add_argument('--verify-only',action='store_true')
    p.add_argument('--retry-task');p.add_argument('--retry-reason')
    for name in ('pause','clear-pause'):
        p=sub.add_parser(name);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--reason',required=True)
    args=vars(parser.parse_args());cmd=args.pop('command')
    if cmd=='run':result=run(**args)
    else:
        marker=json.loads((args['bundle']/'FROZEN.json').read_text())
        if marker['schema']!='compact-study-freeze-v1':raise ValueError('Compact-only control')
        if cmd=='clear-pause':
            # The driver lease proves no cooperating phase writer; registry
            # reconciliation under the actual shared lock confirms Job ends.
            with host_lease(args['bundle']/'compact-driver.lock','acknowledge ended compact phase'):
                from formal_owned_runtime import Coordinator
                binding=json.loads((args['bundle']/'archive.json').read_text())['binding']
                Coordinator(binding['shared_host_lock']).task_keys(marker['protocol_sha256'])
                result=acknowledge_pause(args['bundle'],marker['protocol_sha256'],args['reason'])
        else:result=request_pause(args['bundle'],marker['protocol_sha256'],args['reason'])
    print(json.dumps(result,indent=2),flush=True)
