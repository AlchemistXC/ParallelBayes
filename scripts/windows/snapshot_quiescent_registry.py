"""Copy a quiescent shared registry under its actual cooperative lease."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import time


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--lock',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    sys.path[:0]=[str(a.root/'scripts/windows'),str(a.root/'scripts/completion')]
    from formal_runtime import host_lease,fingerprint
    from job_objects import observe_named_job
    if sys.platform!='win32' or a.output.exists():raise ValueError('Native, fresh snapshot required')
    lock=a.lock.resolve();journal=lock.with_name(lock.name+'.formal-journal')
    old=lock.with_suffix('.windows-registry.json');a.output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    with host_lease(lock,'quiescent v2 acceptance registry snapshot; no sampling'):
        db=sqlite3.connect((journal/'tasks.sqlite3').as_uri()+'?mode=ro',uri=True)
        try:
            if db.execute('SELECT COUNT(*) FROM tasks WHERE active=1').fetchone()[0]:
                raise RuntimeError('Active indexed tasks; retain evidence and refuse snapshot')
            records=[]
            for payload,checksum in db.execute('SELECT record,checksum FROM tasks'):
                entry=json.loads(payload)
                if fingerprint(entry)!=checksum:raise ValueError('Journal record checksum differs')
                records.append(entry)
        finally:db.close()
        legacy=json.loads(old.read_text());signature=legacy.pop('sha256')
        if fingerprint(legacy)!=signature:raise ValueError('Legacy registry checksum differs')
        legacy_records=list(legacy['tasks'].values())
        jobs={attempt['job_name'] for e in records+legacy_records for attempt in e['attempts']}
        proof={name:observe_named_job(name) for name in sorted(jobs)}
        if any(v['state']=='present' and v['active_processes'] for v in proof.values()):
            raise RuntimeError('A registered owned Job remains active; snapshot refused')
        files=[old,*[f for f in journal.rglob('*') if f.is_file()]]
        if any(f.is_symlink() for f in files):raise ValueError('Registry symlinks refused')
        before={str(f.relative_to(lock.parent)):sha(f) for f in files}
        for f in files:
            dest=a.output/f.relative_to(lock.parent);dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(f,dest)
        if any(sha(f)!=before[str(f.relative_to(lock.parent))] or sha(a.output/f.relative_to(lock.parent))!=before[str(f.relative_to(lock.parent))] for f in files):
            raise ValueError('Registry changed during protected copy')
        receipt=dict(status='passed',shared_lock=str(lock),indexed_tasks=len(records),legacy_tasks=len(legacy_records),
            indexed_active_count=0,registered_jobs_observed=len(proof),owned_active_processes=0,
            native_job_observations=proof,source_and_copied_sha256=before,
            scope='Quiescent registry copy; not a relocated live lease or whole-OS process census',
            snapshot_seconds=time.perf_counter()-started,no_sampling=True)
        (a.output/'snapshot-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('status','indexed_tasks','legacy_tasks','registered_jobs_observed','owned_active_processes')},indent=2))


if __name__=='__main__':main()
