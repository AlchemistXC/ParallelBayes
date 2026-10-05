"""External per-call cost ledger around the unchanged task coordinator.

One logical task owns a small append-only call directory. This preserves
initial execution, explicit recovery/retry, refusals and verification costs.
Missing completion records remain unknown even if the sampler later succeeds.
Ledger writing, reporting and between-call waiting are outside the timed call.
"""
import json
import math
from pathlib import Path
import sys
import time

from formal_coordinator import TaskCoordinator
from formal_runtime import atomic_json,file_hash,fingerprint,host_lease

SCOPE='Coordinator run/retry invocation only, including its registration/recovery/sealing/history; excludes measurement-ledger writes, report calls and between-call waiting'


def read_calls(directory):
    """Read declared call artifacts; no process observation or mutation."""
    directory=Path(directory);identity=json.loads((directory/'identity.json').read_text())
    if identity['schema']!=1:raise ValueError('Unsupported measurement ledger')
    rows=[]
    for index,path in enumerate(sorted(directory.glob('call-*'))):
        if path.name!=f'call-{index:06d}' or path.is_symlink():raise ValueError('Call order/path differs')
        start=json.loads((path/'started.json').read_text())
        if start['index']!=index or start['identity_sha256']!=fingerprint(identity):raise ValueError('Call identity differs')
        row=dict(index=index,action=start['action'],seconds=None,result=None,error=None,finished=False)
        if (path/'finished.json').exists():
            end=json.loads((path/'finished.json').read_text());unsigned=dict(end);digest=unsigned.pop('receipt_sha256')
            if fingerprint(unsigned)!=digest or end['started_sha256']!=file_hash(path/'started.json'):
                raise ValueError('Finished call checksum differs')
            seconds=end['seconds']
            if not math.isfinite(seconds) or seconds<0:raise ValueError('Invalid invocation time')
            row.update(seconds=seconds,result=end['result'],error=end['error'],finished=True)
        rows.append(row)
    return identity,rows


def summarize_calls(history,identity,calls):
    """Keep every call; a successful retry never supplies a lost prior time."""
    if history['original']!=identity['original'] or history['task']!=identity['task']:
        raise ValueError('History and measurement identity differ')
    measured_attempts=[];verification=0;by_action={};known=0.
    for call in calls:
        action=call['action']
        if action not in ('run','retry'):raise ValueError('Unsupported measured action')
        row=by_action.setdefault(action,dict(calls=0,known_seconds=0.,unfinished_calls=0));row['calls']+=1
        if call['seconds'] is None:row['unfinished_calls']+=1
        else:known+=call['seconds'];row['known_seconds']+=call['seconds']
        result=call['result']
        if result is not None:
            if result['task']!=history['task']:raise ValueError('Measured return belongs to another task')
            if result['newly_executed']:measured_attempts.append(result['attempt_id'])
            else:verification+=1
    actual={a['attempt_id'] for a in history['attempts']}
    if len(set(measured_attempts))!=len(measured_attempts) or not set(measured_attempts)<=actual:
        raise ValueError('Measured attempt identity is duplicated or absent from history')
    missing=len(actual-set(measured_attempts));unfinished=sum(not c['finished'] for c in calls)
    return dict(outcome=history['summary']['outcome'],history=history,actual_attempts=len(actual),
        recorded_invocations=len(calls),verification_only_invocations=verification,
        unfinished_invocations=unfinished,attempts_missing_outer_measurement=missing,
        known_invocation_seconds=known,complete_invocation_seconds=None if missing or unfinished else known,
        by_action=by_action,calls=calls,attempts_are_statistical_replicates=False,
        unknown_time_imputed=False,cost_scope=SCOPE,
        note='Verification/refusal costs are retained separately; arbitrary extra resume calls are not a standardized time-to-inference estimator')


class MeasuredCoordinator:
    def __init__(self,host_lock,ledger_root):
        self.coordinator=TaskCoordinator(host_lock)
        self.ledger_root=Path(ledger_root).resolve();self.ledger_root.mkdir(parents=True,exist_ok=True)

    def _directory(self,original):
        return self.ledger_root/fingerprint(str(Path(original).resolve()))

    def _call(self,original,task,action,operation):
        original=Path(original).resolve();directory=self._directory(original)
        identity=dict(schema=1,original=str(original),task=task,host_lock=str(self.coordinator.host_lock),
            python=sys.version,executable=str(Path(sys.executable).resolve()),
            recorder_source_sha256=file_hash(Path(__file__)),cost_scope=SCOPE)
        with host_lease(directory.with_suffix('.lock'),'measure '+action+' '+str(original)):
            if directory.exists():
                old,calls=read_calls(directory)
                if old!=identity:raise ValueError('Measurement task/environment/source identity differs')
            else:
                directory.mkdir();atomic_json(directory/'identity.json',identity);calls=[]
            call=directory/f'call-{len(calls):06d}';call.mkdir()
            atomic_json(call/'started.json',dict(index=len(calls),action=action,identity_sha256=fingerprint(identity),
                recorded_ns=time.time_ns(),owner_pid=__import__('os').getpid(),
                timestamp_is_not_elapsed_time=True))
            result=None;error=None;started=time.perf_counter()
            try:
                result=operation();return result
            except BaseException as exc:
                error=dict(type=type(exc).__name__,message=str(exc));raise
            finally:
                seconds=time.perf_counter()-started
                record=None
                if result is not None:
                    history=result['history'];last=history['attempts'][-1] if history['attempts'] else None
                    record=dict(task=result['task'],status=result['status'],newly_executed=result['newly_executed'],
                        attempt_id=last['attempt_id'] if last else None,history_sha256=fingerprint(history))
                receipt=dict(started_sha256=file_hash(call/'started.json'),seconds=seconds,result=record,error=error)
                receipt['receipt_sha256']=fingerprint(receipt);atomic_json(call/'finished.json',receipt)

    def run(self,**job):
        return self._call(job['output'],job['task'],'run',lambda:self.coordinator.run(**job))

    def retry(self,original,*,reason):
        task=json.loads((Path(original)/'binding.json').read_text())['task']
        return self._call(original,task,'retry',lambda:self.coordinator.retry(original,reason=reason))

    def report(self,original):
        directory=self._directory(original)
        with host_lease(directory.with_suffix('.lock'),'read measured task costs'):
            identity,calls=read_calls(directory)
            history=self.coordinator.history(original)
            return dict(summarize_calls(history,identity,calls),ledger_directory=str(directory),
                ledger_sha256=fingerprint({p.relative_to(directory).as_posix():file_hash(p) for p in sorted(directory.rglob('*')) if p.is_file()}))
