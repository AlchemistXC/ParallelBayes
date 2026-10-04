"""Read immutable coordinator snapshots without a live host or old paths.

This is an analysis adapter, not a recovery/launch interface. The caller pins
the snapshot hash and declares exact old-output -> relative-archive mappings.
No operating-system process observation or registry mutation occurs here.
"""
import json
from pathlib import Path
import sqlite3

from formal_runtime import file_hash,fingerprint
from formal_outcomes import read_attempt,summarize_attempts


def inside(root,name):
    root=Path(root).resolve();relative=Path(name)
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('Evidence path must be relative and contained')
    path=root/relative
    if not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in [path,*path.parents] if p!=root and p.is_relative_to(root)):
        raise ValueError('Evidence path escapes its archive or uses a symlink')
    return path


class RuntimeEvidence:
    """Context-managed read-only snapshot; one task history at a time."""
    def __init__(self,snapshot,expected_sha256,root,locations):
        self.snapshot=Path(snapshot).resolve();self.expected_sha256=expected_sha256
        self.root=Path(root).resolve();self.locations=dict(locations)
        if file_hash(self.snapshot)!=expected_sha256:raise ValueError('Registry snapshot checksum differs')
        paths=[inside(self.root,x) for x in self.locations.values()]
        if len(paths)!=len(set(paths)):raise ValueError('Multiple original outputs map to one evidence directory')
        self.db=sqlite3.connect(self.snapshot.as_uri()+'?mode=ro&immutable=1',uri=True)
        self.db.execute('PRAGMA query_only=ON');self.db.execute('PRAGMA cache_size=-2048')
        if self.db.execute('PRAGMA quick_check').fetchone()!=('ok',):
            self.db.close();raise ValueError('Invalid registry snapshot')

    def __enter__(self):return self

    def __exit__(self,kind,value,traceback):
        self.db.close()
        if file_hash(self.snapshot)!=self.expected_sha256:raise ValueError('Registry snapshot changed while reading')

    def _location(self,original):
        if original not in self.locations:raise ValueError('Explicit archived location missing: '+original)
        return inside(self.root,self.locations[original])

    def _record(self,task,original):
        key=fingerprint({k:task[k] for k in ('id','protocol_sha256')})
        row=self.db.execute('SELECT original,record,checksum,active FROM tasks WHERE key=?',(key,)).fetchone()
        if row is None:
            if self._location(original).exists():raise ValueError('Unregistered evidence exists for a planned task')
            return None
        record=json.loads(row[1])
        if fingerprint(record)!=row[2]:raise ValueError('Registered record checksum differs')
        if record['original']!=original or row[0]!=original or record['binding']['task']!=task:
            raise ValueError('Registered task identity differs')
        previous=None;last=None;number=0
        for ordinal,payload,digest in self.db.execute('SELECT ordinal,payload,checksum FROM events WHERE key=? ORDER BY ordinal',(key,)):
            event=json.loads(payload)
            if ordinal!=number or event['ordinal']!=ordinal or event['previous_sha256']!=previous or fingerprint(event)!=digest:
                raise ValueError('Registered event history checksum/order differs')
            previous=digest;last=event;number+=1
        if last is None or last['record']!=record or bool(row[3])!=any(a['lifecycle']=='registered' for a in record['attempts']):
            raise ValueError('Registered current state and history differ')
        attempts=record['attempts']
        if not 1<=len(attempts)<=2 or attempts[0]['output']!=original:
            raise ValueError('Invalid initial/retry attempt history')
        if len(attempts)==2 and (attempts[1]['output']!=original+'.retry' or attempts[1]['parent_output']!=original or attempts[0]['lifecycle']!='recovered'):
            raise ValueError('Retry lineage differs')
        return record

    @staticmethod
    def _snapshot(directory):
        paths=sorted(directory.rglob('*'))
        if any(p.is_symlink() for p in paths):raise ValueError('Evidence contains a symlink')
        return {p.relative_to(directory).as_posix():file_hash(p) for p in paths if p.is_file()}

    def history(self,task,original):
        """Verify lineage and assets; only the last eligible attempt is usable.

        Original absolute path strings remain historical IDs. Files are read
        solely via declared relative locations, never through those old IDs.
        Missing planned tasks remain explicit not-run entries.
        """
        record=self._record(task,original);rows=[];eligible=None
        if record is None:
            return dict(task=task,original=original,lifecycle='not_registered',attempts=[],
                        summary=summarize_attempts([]),eligible_directory=None,
                        snapshot_sha256=self.expected_sha256,attempts_are_statistical_replicates=False)
        for a in record['attempts']:
            source=a['output'];directory=self._location(source);life=a['lifecycle']
            if life=='registered':raise ValueError('Unresolved registered process; snapshot cannot prove it stopped')
            if life=='not_started':
                if directory.exists():raise ValueError('Evidence appeared after a non-launch record')
                continue
            observed=a.get('group_observation',{})
            if observed.get('observed')!='absent':raise ValueError('Missing recorded group-absence observation')
            if not directory.is_dir():raise ValueError('Recorded attempt evidence is missing')
            actual=self._snapshot(directory)
            if life=='stopped_unsealed':
                if actual!=a['snapshot']:raise ValueError('Unsealed evidence checksum differs')
                worker=directory/'attempt-0001/worker-result.json'
                result=json.loads(worker.read_text()) if worker.exists() else {}
                outcome='output_failure_unclassified' if result.get('status')=='failed' else 'infrastructure_interruption'
                row=dict(attempt_id=source,binding_sha256=fingerprint(record['binding']),outcome=outcome,
                         seconds=None,evidence_sha256=fingerprint(actual),cost_scope='runtime_v1_preflight_through_terminal',
                         fixed_task=task,unknown_time_imputed=False)
            elif life in ('sealed','recovered'):
                if life=='recovered':
                    recovery=directory.with_name(directory.name+'.recovery')/'recovery.json'
                    if file_hash(recovery)!=a['recovery_file_sha256']:raise ValueError('Recovery file checksum differs')
                    recover=json.loads(recovery.read_text())
                    if recover['original']!=source or recover['retry_output']!=source+'.retry':raise ValueError('Recovery source lineage differs')
                    if len(record['attempts'])==2 and record['attempts'][1]['recovery_sha256']!=recover['recovery_sha256']:
                        raise ValueError('Retry recovery identity differs')
                row=read_attempt(directory)
                if life=='sealed' and (row['evidence_sha256']!=a['evidence_sha256'] or file_hash(directory/'completion.json')!=a['completion_sha256']):
                    raise ValueError('Sealed evidence checksum differs')
                row['attempt_id']=source
            else:raise ValueError('Unknown registered lifecycle')
            if json.loads((directory/'binding.json').read_text())!=record['binding'] or row['fixed_task']!=task or row['binding_sha256']!=fingerprint(record['binding']):
                raise ValueError('Archived binding identity differs')
            rows.append(row)
            eligible=str(directory) if row['outcome']=='valid' else None
        return dict(task=task,original=original,lifecycle=record['attempts'][-1]['lifecycle'],attempts=rows,
                    summary=summarize_attempts(rows),eligible_directory=eligible,
                    snapshot_sha256=self.expected_sha256,attempts_are_statistical_replicates=False,
                    cost_scope='Runtime-v1 attempt boundaries only; coordinator/recovery/inter-call cost is excluded')
