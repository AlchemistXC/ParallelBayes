"""Append-only, predeclared batch overhead; never silently amortize it per fit.

A missing finish is unknown time, not evidence of process death. The caller
owns operation/resource safety; this module only serializes cooperating work
with a native host lease and preserves the measurement and result envelope.
"""
import copy
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from formal_runtime import atomic_json,file_hash,fingerprint,host_lease

STAGES={'input_preparation','archive','transfer','verification'}
SCOPE='Wall time around one declared operation. Includes that operation and any subprocess waiting it performs; excludes ledger writes, report/reopen/duplicate checks, inter-operation gaps, and external unregistered activity. No per-fit allocation.'


def _spec(value):
    spec=copy.deepcopy(value)
    if set(spec)!={'study_identity','design_sha256','operations'} or not isinstance(spec['study_identity'],str) or not spec['study_identity']:
        raise ValueError('Explicit batch design identity required')
    if not isinstance(spec['design_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',spec['design_sha256']):
        raise ValueError('Batch design checksum required before input generation')
    if not isinstance(spec['operations'],list) or not spec['operations']:raise ValueError('Declared operations required')
    seen=set()
    for op in spec['operations']:
        if (set(op)!={'id','stage'} or not isinstance(op['id'],str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,95}',op['id'])
            or op['id'] in seen or op['stage'] not in STAGES):raise ValueError('Invalid or duplicate batch operation')
        seen.add(op['id'])
    return spec


def read_batch_costs(directory):
    """Read verified receipts after relocation; never sample, retry, or observe PIDs."""
    directory=Path(directory)
    identity=json.loads((directory/'identity.json').read_text());spec=_spec(identity['spec'])
    if identity['schema']!=1 or identity['scope']!=SCOPE:raise ValueError('Batch cost schema/scope differs')
    expected={op['id'] for op in spec['operations']}
    actual={p.name[3:] for p in directory.glob('op-*')}
    if not actual<=expected:raise ValueError('Undeclared batch operation on disk')
    rows=[]
    for op in spec['operations']:
        path=directory/('op-'+op['id'])
        row=dict(**op,outcome='not_run',seconds=None,result=None,error=None)
        if path.exists():
            if path.is_symlink():raise ValueError('Operation path must not be a symlink')
            start=json.loads((path/'started.json').read_text())
            if start['identity_sha256']!=fingerprint(identity) or start['operation']!=op:
                raise ValueError('Batch operation identity differs')
            row['outcome']='unfinished'
            if (path/'finished.json').exists():
                end=json.loads((path/'finished.json').read_text());unsigned=dict(end);digest=unsigned.pop('receipt_sha256')
                if fingerprint(unsigned)!=digest or end['started_sha256']!=file_hash(path/'started.json'):
                    raise ValueError('Batch cost receipt checksum differs')
                if type(end['seconds']) not in (float,int) or not math.isfinite(end['seconds']) or end['seconds']<0:
                    raise ValueError('Invalid batch cost time')
                if end['outcome'] not in ('completed','failed') or (end['outcome']=='failed')!=(end['error'] is not None):
                    raise ValueError('Batch operation outcome differs')
                row.update({key:end[key] for key in ('outcome','seconds','result','error')})
        rows.append(row)
    known=sum(r['seconds'] for r in rows if r['seconds'] is not None)
    missing=sum(r['seconds'] is None for r in rows)
    bystage={}
    for stage in sorted({r['stage'] for r in rows}):
        subset=[r for r in rows if r['stage']==stage]
        partial=sum(r['seconds'] for r in subset if r['seconds'] is not None)
        bystage[stage]=dict(planned=len(subset),known_seconds=partial,
            complete_seconds=partial if all(r['seconds'] is not None for r in subset) else None,
            completed=sum(r['outcome']=='completed' for r in subset),failed=sum(r['outcome']=='failed' for r in subset),
            unfinished=sum(r['outcome']=='unfinished' for r in subset),not_run=sum(r['outcome']=='not_run' for r in subset))
    return dict(identity=identity,operations=rows,planned_operations=len(rows),finished_operations=len(rows)-missing,
        unrecorded_operations=sum(r['outcome']=='not_run' for r in rows),
        unfinished_operations=sum(r['outcome']=='unfinished' for r in rows),
        known_seconds=known,complete_seconds=None if missing else known,by_stage=bystage,
        per_fit_cost_allocation=None,statistical_repetitions_added=0,proves_process_termination=False)


class BatchCostLedger:
    def __init__(self,directory,spec,host_lock):
        self.directory=Path(directory).resolve();self.host_lock=Path(host_lock).resolve()
        spec=_spec(spec)
        identity=dict(schema=1,spec=spec,host_lock=str(self.host_lock),scope=SCOPE,
            python=sys.version,executable=str(Path(sys.executable).resolve()),recorder_source_sha256=file_hash(__file__))
        with host_lease(self.host_lock,'bind batch overhead '+spec['study_identity']):
            if self.directory.exists():
                if read_batch_costs(self.directory)['identity']!=identity:raise ValueError('Batch cost identity differs')
            else:
                self.directory.mkdir(parents=True,exist_ok=False);atomic_json(self.directory/'identity.json',identity)
        self.identity=identity;self.operations={op['id']:op for op in spec['operations']}

    def run(self,operation_id,operation):
        """Measure once. A refused duplicate cannot silently rerun or erase evidence.

Return JSON-compatible artifact identifiers/hashes, never large arrays. A
failed operation is recorded and re-raised. For a later explicit attempt use
a separately declared operation; this recorder does not authorize retries.
"""
        if operation_id not in self.operations:raise ValueError('Undeclared batch operation')
        with host_lease(self.host_lock,'batch overhead '+operation_id):
            if read_batch_costs(self.directory)['identity']!=self.identity:raise ValueError('Batch cost identity differs')
            path=self.directory/('op-'+operation_id)
            if path.exists():raise ValueError('Operation already recorded; no automatic rerun')
            path.mkdir()
            atomic_json(path/'started.json',dict(identity_sha256=fingerprint(self.identity),
                operation=self.operations[operation_id],recorded_ns=time.time_ns(),owner_pid=os.getpid(),
                timestamp_is_not_elapsed_time=True))
            result=None;error=None;start=time.perf_counter()
            try:
                result=operation()
                # Ensure the result can be archived before declaring success.
                fingerprint(result)
            except BaseException as exc:
                error=dict(type=type(exc).__name__,message=str(exc));raise
            finally:
                elapsed=time.perf_counter()-start
                receipt=dict(started_sha256=file_hash(path/'started.json'),seconds=elapsed,
                    outcome='completed' if error is None else 'failed',result=result if error is None else None,error=error)
                receipt['receipt_sha256']=fingerprint(receipt);atomic_json(path/'finished.json',receipt)
            return receipt
