"""Explicit Mac recovery alongside immutable v1 attempt evidence.

This profile requires workers and descendants to remain in the fresh process
group established by formal_runtime. It never kills a process and never uses
elapsed time or a stale PID file as proof that a task has stopped. A Windows
process-cohort adapter and formal coordinator integration remain separate.
"""
import json
import os
from pathlib import Path
import sys
import time

import psutil

import formal_runtime
from formal_runtime import atomic_json, execute_task, file_hash, fingerprint, host_lease


class RecoveryConflict(RuntimeError):
    pass


class LiveAttempt(RecoveryConflict):
    pass


def _snapshot(directory):
    paths=sorted(directory.rglob('*'))
    if any(p.is_symlink() for p in paths):raise RecoveryConflict('Symlink evidence cannot be recovered')
    return {p.relative_to(directory).as_posix():file_hash(p) for p in paths if p.is_file()}


def _binding(original,host_lock):
    if sys.platform!='darwin':raise RecoveryConflict('Only the native Mac recovery profile is validated')
    binding=json.loads((original/'binding.json').read_text())
    if formal_runtime.task_artifact_kind(binding['task'])=='cache_measurement':
        raise RecoveryConflict('Cache measurement retries are not authorized; preserve the incomplete measurement')
    expected=dict(python=sys.version,executable=str(Path(sys.executable).resolve()),platform=sys.platform,
                  psutil=psutil.__version__,host_lock=str(Path(host_lock).resolve()),
                  runtime_helper_sha256=file_hash(Path(formal_runtime.__file__)))
    if any(binding.get(k)!=v for k,v in expected.items()):
        raise RecoveryConflict('Original execution environment or runtime changed')
    path=original/'attempt-0001/process.json'
    if not path.is_file():raise RecoveryConflict('No owned process receipt; automatic recovery cannot prove absence')
    process=json.loads(path.read_text());worker=Path(process['worker'])
    if process['command_role']!='owned_task_worker' or not isinstance(process['pid'],int) or process['pid']<=1:
        raise RecoveryConflict('Invalid owned process identity')
    if Path(process['request']).resolve()!=original/'attempt-0001/request.json':
        raise RecoveryConflict('Owned request path differs')
    if file_hash(worker)!=binding['worker_sha256']:
        raise RecoveryConflict('Worker source changed')
    if json.loads((original/'attempt-0001/request.json').read_text())!=binding['request']:
        raise RecoveryConflict('Actual request changed')
    return binding,process


def _assert_group_absent(pid):
    try:os.killpg(pid,0)
    except ProcessLookupError:return dict(process_group=pid,observed='absent',checked_ns=time.time_ns())
    except PermissionError as exc:raise RecoveryConflict('Cannot observe the original process group') from exc
    raise LiveAttempt('Original process group is still live; no recovery or retry is permitted')


def _reject_reported_worker_failure(original):
    path=original/'attempt-0001/worker-result.json'
    if path.exists():
        result=json.loads(path.read_text())
        if result.get('status')=='failed':
            raise RecoveryConflict('The worker already reported failed output; missing supervisor finalization does not authorize a retry')
        if result.get('status')!='completed' or result.get('samples_eligible') is not True:
            raise RecoveryConflict('Worker output classification is ambiguous; no automatic retry')


def _read_recovery(original,host_lock):
    directory=original.with_name(original.name+'.recovery')
    record=json.loads((directory/'recovery.json').read_text())
    unsigned=dict(record);digest=unsigned.pop('recovery_sha256')
    if fingerprint(unsigned)!=digest:raise RecoveryConflict('Recovery record changed')
    if record['original']!=str(original) or record['host_lock']!=str(Path(host_lock).resolve()):
        raise RecoveryConflict('Recovery path/lock identity changed')
    binding,process=_binding(original,host_lock)
    if fingerprint(binding)!=record['binding_sha256'] or _snapshot(original)!=record['original_assets']:
        raise RecoveryConflict('Original attempt evidence changed after recovery')
    _assert_group_absent(process['pid'])
    _reject_reported_worker_failure(original)
    return record,binding,process


def recover_task(original, *, host_lock, reason):
    """Seal a stopped interrupted attempt in a deterministic sibling directory.

    Completed/numerically failed/resource-failed terminals are never retried.
    Unsealed worker output is retained but not promoted to normal samples.
    """
    original=Path(original).resolve()
    if not isinstance(reason,str) or not reason.strip():raise ValueError('Explicit recovery reason required')
    with host_lease(host_lock,'classify interruption '+str(original)):
        directory=original.with_name(original.name+'.recovery')
        if directory.exists():return _read_recovery(original,host_lock)[0]
        binding,process=_binding(original,host_lock)
        observed=_assert_group_absent(process['pid'])
        _reject_reported_worker_failure(original)
        cost=None;status='unsealed';statefile=original/'state.json';completion=original/'completion.json'
        if statefile.exists():
            state=json.loads(statefile.read_text());status=state['status']
            if state['binding_sha256']!=fingerprint(binding):raise RecoveryConflict('Terminal binding changed')
            if status in ('completed','failed'):
                raise RecoveryConflict('A '+status+' terminal is immutable and must not be retried')
            if status!='interrupted':raise RecoveryConflict('Unknown original terminal classification')
            for name,h in state['assets'].items():
                path=original/name
                if not path.resolve().is_relative_to(original) or file_hash(path)!=h:
                    raise RecoveryConflict('Original terminal asset changed')
            if completion.exists():
                receipt=json.loads(completion.read_text())
                if receipt['state_sha256']!=file_hash(statefile):raise RecoveryConflict('Completion checksum changed')
                cost=receipt['inclusive_preflight_through_terminal_seconds']
        elif completion.exists():raise RecoveryConflict('Completion exists without terminal state')
        record=dict(schema=1,original=str(original),host_lock=str(Path(host_lock).resolve()),
            retry_output=str(original.with_name(original.name+'.retry')),
            original_assets=_snapshot(original),binding_sha256=fingerprint(binding),
            original_status=status,outcome='infrastructure_interruption',samples_eligible=False,
            cost_seconds=cost,cost_scope='v1 inclusive preflight through terminal when recorded; missing after an abrupt supervisor loss is unknown, never zero',
            worker_group_observation=observed,reason=reason.strip(),
            recovery_source_sha256=file_hash(Path(__file__)),
            process_policy='Native Mac fresh process group, no escaping/daemonizing descendants; no terminating signals sent',
            retry_policy='Explicit single deterministic retry destination, unchanged task/request/worker/environment; all prior evidence preserved')
        record['recovery_sha256']=fingerprint(record)
        directory.mkdir(exist_ok=False)
        atomic_json(directory/'recovery.json',record)
        return record


def retry_task(original, *, host_lock):
    """Execute/resume the one reserved retry; never replace original evidence."""
    original=Path(original).resolve()
    with host_lease(host_lock,'reserve explicit retry '+str(original)):
        record,binding,process=_read_recovery(original,host_lock)
        destination=Path(record['retry_output'])
        if destination!=original.with_name(original.name+'.retry'):
            raise RecoveryConflict('Retry destination changed')
        claim=dict(recovery_sha256=record['recovery_sha256'],binding_sha256=record['binding_sha256'],
                   retry_output=str(destination),original=str(original))
        claimfile=original.with_name(original.name+'.recovery')/'retry-claim.json'
        if claimfile.exists():
            if json.loads(claimfile.read_text())!=claim:raise RecoveryConflict('Retry reservation changed')
        else:atomic_json(claimfile,claim)
    # execute_task reacquires the same host lease. Concurrent invocations use
    # the same destination: the second can only validate/resume its terminal.
    result=execute_task(binding['task'],binding['request'],process['worker'],destination,host_lock,
                        binding['required_disk_bytes'],binding['max_tree_rss_bytes'],resume=True)
    return dict(result,recovery_sha256=record['recovery_sha256'],
                original_interruption_cost_seconds=record['cost_seconds'],
                original_interruption_remains_in_history=True)
