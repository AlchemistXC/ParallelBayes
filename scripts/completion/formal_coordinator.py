"""Cooperating native-Mac task registry around immutable runtime-v1 evidence.

All callers must use the same absolute host-lock path. A separate coordinator
lease serializes registration, OS group observations and delegated execution.
It does not exclude direct runtime-v1 callers or unrelated programs. Workers
and descendants must remain in runtime-v1's fresh process group. Missing
process receipts fail closed; Windows needs its own validated cohort profile.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

import psutil

import formal_runtime
from formal_runtime import atomic_json, execute_task, file_hash, fingerprint, host_lease, HostBusy, ResourceWait
from formal_outcomes import read_attempt, summarize_attempts
from formal_recovery import recover_task, retry_task


class CoordinatorConflict(RuntimeError):
    pass


class CoordinatorBusy(CoordinatorConflict):
    pass


class TaskCoordinator:
    """Register once, run/resume fixed identities, inspect verified histories.

The registry is a durable SQLite journal next to the shared numerical lock.
Only pending records are inspected before a new launch; the complete history
of a requested task is verified on access. Thus old raw arrays are not reread
for every unrelated new task. Checksums detect accidental changes, not an
adversary able to rewrite both data and checksums.
"""
    def __init__(self,host_lock):
        if sys.platform!='darwin':raise CoordinatorConflict('Only the native Mac coordinator profile is validated')
        self.host_lock=Path(host_lock).resolve()
        self.registry_path=self.host_lock.with_name(self.host_lock.name+'.coordinator')
        self.lease_path=self.host_lock.with_name(self.host_lock.name+'.coordinator.lock')

    @contextmanager
    def _registry(self):
        with host_lease(self.lease_path,'formal task coordinator'):
            identity=dict(schema=2,host_lock=str(self.host_lock),platform=sys.platform,
                          profile='native-Mac-fresh-process-group-v1')
            root=self.registry_path;new=not root.exists()
            if root.is_symlink():raise CoordinatorConflict('Registry may not be a symlink')
            if new:root.mkdir()
            database=root/'registry.sqlite3';descriptor=root/'identity.json'
            if not new:
                if not database.is_file() or not descriptor.is_file():
                    raise CoordinatorConflict('Incomplete registry; do not replace missing history')
                if database.is_symlink() or descriptor.is_symlink() or json.loads(descriptor.read_text())!=identity:
                    raise CoordinatorConflict('Registry identity differs')
            db=sqlite3.connect(database)
            try:
                db.execute('PRAGMA synchronous=FULL')
                db.execute('PRAGMA journal_mode=DELETE')
                if new:
                    db.execute('CREATE TABLE tasks (key TEXT PRIMARY KEY, original TEXT UNIQUE NOT NULL, record TEXT NOT NULL, checksum TEXT NOT NULL, active INTEGER NOT NULL)')
                    db.execute('CREATE TABLE events (key TEXT NOT NULL, ordinal INTEGER NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL, PRIMARY KEY(key,ordinal))')
                    db.execute('CREATE INDEX active_tasks ON tasks(active)')
                    db.commit();atomic_json(descriptor,identity)
                yield db
            finally:db.close()

    def _load(self,db,key):
        row=db.execute('SELECT original,record,checksum,active FROM tasks WHERE key=?',(key,)).fetchone()
        if row is None:return None
        record=json.loads(row[1])
        if fingerprint(record)!=row[2] or record['original']!=row[0] or self._task_key(record['binding']['task'])!=key:
            raise CoordinatorConflict('Registry task identity/checksum differs')
        previous=None;last=None
        for number,payload,digest in db.execute('SELECT ordinal,payload,checksum FROM events WHERE key=? ORDER BY ordinal',(key,)):
            event=json.loads(payload)
            if number!=(0 if last is None else last['ordinal']+1) or event['ordinal']!=number or event['previous_sha256']!=previous or fingerprint(event)!=digest:
                raise CoordinatorConflict('Registry event history differs')
            previous=digest;last=event
        if last is None or last['record']!=record or bool(row[3])!=any(a['lifecycle']=='registered' for a in record['attempts']):
            raise CoordinatorConflict('Registry record conflicts with event history')
        return record

    def _store(self,db,key,record,kind):
        last=db.execute('SELECT ordinal,checksum FROM events WHERE key=? ORDER BY ordinal DESC LIMIT 1',(key,)).fetchone()
        event=dict(ordinal=last[0]+1 if last else 0,previous_sha256=last[1] if last else None,
                   kind=kind,recorded_ns=time.time_ns(),record=record,
                   coordinator_source_sha256=file_hash(Path(__file__)))
        encoded=json.dumps(record,sort_keys=True,allow_nan=False)
        with db:
            db.execute('INSERT INTO events VALUES (?,?,?,?)',(key,event['ordinal'],json.dumps(event,sort_keys=True,allow_nan=False),fingerprint(event)))
            db.execute('INSERT INTO tasks VALUES (?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET record=excluded.record,checksum=excluded.checksum,active=excluded.active',
                       (key,record['original'],encoded,fingerprint(record),int(any(a['lifecycle']=='registered' for a in record['attempts']))))

    def _binding(self,task,request,worker,disk,rss):
        if not isinstance(task,dict) or any(not isinstance(task.get(k),str) or not task[k] for k in ('id','protocol_sha256')):
            raise ValueError('Task ID and protocol identity required')
        formal_runtime.task_artifact_kind(task)
        if isinstance(disk,bool) or not isinstance(disk,int) or disk<0:raise ValueError('Nonnegative disk budget required')
        if isinstance(rss,bool) or not isinstance(rss,int) or rss<=0:raise ValueError('Positive memory guard required')
        return dict(task=task,request=request,worker_sha256=file_hash(worker),
                    runtime_helper_sha256=file_hash(Path(formal_runtime.__file__)),python=sys.version,
                    executable=str(Path(sys.executable).resolve()),platform=sys.platform,
                    host_lock=str(self.host_lock),psutil=psutil.__version__,
                    required_disk_bytes=disk,max_tree_rss_bytes=rss)

    @staticmethod
    def _task_key(task):
        return fingerprint({k:task[k] for k in ('id','protocol_sha256')})

    def _observe(self,record,attempt):
        out=Path(attempt['output']);receipt=out/'attempt-0001/process.json'
        if not receipt.is_file():raise CoordinatorConflict('No process receipt for registered task; group absence is unknown')
        process=json.loads(receipt.read_text());pid=process.get('pid')
        if type(pid) is not int or pid<=1 or process.get('command_role')!='owned_task_worker':
            raise CoordinatorConflict('Invalid owned process receipt')
        if process['worker']!=record['worker'] or Path(process['request']).resolve()!=out/'attempt-0001/request.json':
            raise CoordinatorConflict('Process receipt path differs')
        if json.loads((out/'binding.json').read_text())!=record['binding'] or json.loads((out/'attempt-0001/request.json').read_text())!=record['binding']['request']:
            raise CoordinatorConflict('Actual task binding differs')
        try:os.killpg(pid,0)
        except ProcessLookupError:return dict(process_group=pid,observed='absent',checked_ns=time.time_ns())
        except PermissionError as exc:raise CoordinatorConflict('Cannot observe registered process group') from exc
        raise CoordinatorBusy('Registered task process group is still live: '+str(out))

    @staticmethod
    def _snapshot(out):
        paths=sorted(out.rglob('*'))
        if any(p.is_symlink() for p in paths):raise CoordinatorConflict('Task evidence may not contain symlinks')
        return {p.relative_to(out).as_posix():file_hash(p) for p in paths if p.is_file()}

    def _settle(self,db,key,record):
        for attempt in record['attempts']:
            if attempt['lifecycle']!='registered':continue
            observed=self._observe(record,attempt)
            out=Path(attempt['output'])
            if (out/'state.json').is_file() and (out/'completion.json').is_file():
                row=read_attempt(out)
                if row['binding_sha256']!=fingerprint(record['binding']):raise CoordinatorConflict('Terminal binding differs')
                attempt.update(lifecycle='sealed',outcome=row['outcome'],evidence_sha256=row['evidence_sha256'],
                               completion_sha256=file_hash(out/'completion.json'))
            else:
                attempt.update(lifecycle='stopped_unsealed',snapshot=self._snapshot(out))
            attempt['group_observation']=observed
            self._store(db,key,record,'owned_group_observed_absent')

    def _reconcile(self,db):
        for (key,) in db.execute('SELECT key FROM tasks WHERE active=1 ORDER BY key').fetchall():
            self._settle(db,key,self._load(db,key))

    def _history(self,record):
        rows=[]
        for a in record['attempts']:
            out=Path(a['output'])
            if a['lifecycle']=='not_started':
                if out.exists():raise CoordinatorConflict('Output appeared after a recorded non-launch')
                continue
            if a['lifecycle']=='registered':raise CoordinatorConflict('Task has not been observed stopped')
            if a['lifecycle']=='recovered':
                recovery=out.with_name(out.name+'.recovery')/'recovery.json'
                if file_hash(recovery)!=a['recovery_file_sha256']:
                    raise CoordinatorConflict('Registered recovery evidence changed')
                row=read_attempt(out)
            elif a['lifecycle']=='sealed':
                row=read_attempt(out)
                if row['evidence_sha256']!=a['evidence_sha256'] or file_hash(out/'completion.json')!=a['completion_sha256']:
                    raise CoordinatorConflict('Sealed task evidence changed')
            else:
                if self._snapshot(out)!=a['snapshot']:raise CoordinatorConflict('Unsealed task evidence changed')
                resultfile=out/'attempt-0001/worker-result.json'
                result=json.loads(resultfile.read_text()) if resultfile.exists() else {}
                outcome='output_failure_unclassified' if result.get('status')=='failed' else 'infrastructure_interruption'
                row=dict(attempt_id=str(out),binding_sha256=fingerprint(record['binding']),
                    outcome=outcome,seconds=None,evidence_sha256=fingerprint(a['snapshot']),
                    cost_scope='runtime_v1_preflight_through_terminal',fixed_task=record['binding']['task'],
                    artifact_kind=formal_runtime.task_artifact_kind(record['binding']['task']),unknown_time_imputed=False)
            if row['binding_sha256']!=fingerprint(record['binding']):raise CoordinatorConflict('History binding differs')
            rows.append(row)
        return dict(original=record['original'],task=record['binding']['task'],attempts=rows,
                    lifecycle=record['attempts'][-1]['lifecycle'],summary=summarize_attempts(rows),
                    attempts_are_statistical_replicates=False,
                    cost_scope='Runtime-v1 attempts only; coordinator, recovery and between-call time are not included')

    def _invoke(self,db,key,record,call):
        """Only documented pre-spawn refusals certify a non-launch."""
        last=record['attempts'][-1]
        if last['lifecycle']=='not_started':
            last['lifecycle']='registered'
            self._store(db,key,record,'previous_nonlaunch_registered_again')
        try:return call()
        except (ResourceWait,HostBusy) as exc:
            if last['lifecycle']=='registered' and not Path(last['output']).exists():
                last.update(lifecycle='not_started',prelaunch_refusal=type(exc).__name__)
                self._store(db,key,record,'runtime_refused_before_launch')
            raise

    def history(self,original):
        original=str(Path(original).resolve())
        with self._registry() as db:
            self._reconcile(db)
            row=db.execute('SELECT key FROM tasks WHERE original=?',(original,)).fetchone()
            if row is None:raise CoordinatorConflict('Original task is not registered')
            return self._history(self._load(db,row[0]))

    def run(self,task,request,worker,output,required_disk_bytes,max_tree_rss_bytes,*,resume=False):
        worker=Path(worker).resolve();output=Path(output).resolve()
        binding=self._binding(task,request,worker,required_disk_bytes,max_tree_rss_bytes)
        key=self._task_key(task)
        with self._registry() as db:
            self._reconcile(db)
            record=self._load(db,key)
            if record is None:
                if output.exists():raise CoordinatorConflict('Unregistered output already exists')
                record=dict(original=str(output),worker=str(worker),binding=binding,
                            attempts=[dict(output=str(output),lifecycle='registered')])
                self._store(db,key,record,'initial_launch_registered')
            else:
                if record['original']!=str(output) or record['worker']!=str(worker) or record['binding']!=binding:
                    raise CoordinatorConflict('Registered task identity or destination changed')
                if not resume:raise CoordinatorConflict('Registered task requires explicit resume')
                self._history(record)
            destination=Path(record['attempts'][-1]['output'])
            result=self._invoke(db,key,record,lambda:execute_task(task,request,worker,destination,self.host_lock,required_disk_bytes,max_tree_rss_bytes,resume=resume))
            self._settle(db,key,record)
            return dict(result,history=self._history(record),registry=str(self.registry_path))

    def retry(self,original,*,reason):
        """Explicitly recover one infrastructure interruption, at most once."""
        original=Path(original).resolve()
        with self._registry() as db:
            self._reconcile(db)
            found=db.execute('SELECT key FROM tasks WHERE original=?',(str(original),)).fetchone()
            if found is None:raise CoordinatorConflict('Original task is not registered')
            key=found[0];record=self._load(db,key)
            self._history(record)
            if len(record['attempts'])==1:
                if record['attempts'][0]['lifecycle']=='not_started':raise CoordinatorConflict('Task has not started; use explicit resume after resource wait')
                recovery=recover_task(original,host_lock=self.host_lock,reason=reason)
                first=record['attempts'][0]
                first['previous_lifecycle']=first['lifecycle'];first['lifecycle']='recovered'
                first['recovery_file_sha256']=file_hash(original.with_name(original.name+'.recovery')/'recovery.json')
                destination=Path(recovery['retry_output'])
                if destination.exists():raise CoordinatorConflict('Unregistered retry output already exists')
                record['attempts'].append(dict(output=str(destination),lifecycle='registered',
                                              parent_output=str(original),recovery_sha256=recovery['recovery_sha256']))
                self._store(db,key,record,'explicit_single_retry_registered')
            result=self._invoke(db,key,record,lambda:retry_task(original,host_lock=self.host_lock))
            self._settle(db,key,record)
            return dict(result,history=self._history(record),registry=str(self.registry_path))
