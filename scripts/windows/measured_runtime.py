"""External actual invocation ledger for the new Windows coordinator.

Uses the verified portable measured_coordinator reader/cost policy, without
using its Mac coordinator or process-group observations.
"""
from pathlib import Path
import time
from formal_runtime import atomic_json,file_hash,fingerprint,host_lease
from measured_coordinator import read_calls


def invoke(coordinator,kwargs,ledger,*,resume=False,retry=False):
    directory=Path(ledger);directory.parent.mkdir(parents=True,exist_ok=True)
    identity=dict(schema=1,original=str(Path(kwargs['output']).resolve()),task=kwargs['task'],
        host_lock=str(coordinator.lock),recorder_source_sha256=file_hash(__file__),
        native_schema='windows-owned-runtime-v1',cost_scope='Complete native coordinator invocation; external ledger writes and between-call waiting excluded')
    with host_lease(directory.with_suffix('.lock'),'Windows invocation ledger'):
        if directory.exists():
            previous,calls=read_calls(directory)
            if previous!=identity:raise ValueError('Invocation identity differs')
        else:
            directory.mkdir();atomic_json(directory/'identity.json',identity);calls=[]
        folder=directory/f'call-{len(calls):06d}';folder.mkdir()
        atomic_json(folder/'started.json',dict(index=len(calls),action='retry' if retry else 'run',
            identity_sha256=fingerprint(identity),recorded_ns=time.time_ns(),timestamp_is_not_elapsed_time=True))
        result=None;error=None;start=time.perf_counter()
        try:
            result=coordinator.run(**kwargs,resume=resume,retry=retry)
            return result
        except BaseException as exc:
            error=type(exc).__name__+': '+str(exc);raise
        finally:
            seconds=time.perf_counter()-start
            value=dict(seconds=seconds,started_sha256=file_hash(folder/'started.json'),error=error,
                result=None if result is None else dict(task=kwargs['task'],outcome=result['outcome'],
                    newly_executed=result['newly_executed'],attempt_id=result['attempt_id']))
            value['receipt_sha256']=fingerprint(value);atomic_json(folder/'finished.json',value)
