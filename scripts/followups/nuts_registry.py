"""Finite append-only technical-call accounting, independent of sampler code."""
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import time

MODELS=('G1','L1','L2','H1','H2','M1','G2','A1','W1')
CONDITIONS=((1,True),(4,True),(1,False),(4,False))

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def schedule(seed=20261010):
    rng=random.Random(seed);models=list(MODELS);rng.shuffle(models)
    result=[]
    for row,model in enumerate(models):
        offset=row%4
        for workers,enabled in CONDITIONS[offset:]+CONDITIONS[:offset]:
            result.append(dict(id=f'main-{model}-w{workers}-d{int(enabled)}',phase='main',model=model,
                workers=workers,diagnostics_enabled=enabled))
    return result

class Registry:
    """Caller holds the shared host lease; SQLite also serializes reservations.

    Registration consumes quota even when spawning fails. No delete/reset/retry
    API is provided. Only a kernel-verified terminated call may be finalized.
    """
    def __init__(self,path,study):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path);self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS identity (value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, phase TEXT NOT NULL, request TEXT NOT NULL, request_sha TEXT NOT NULL, registered_ns INTEGER NOT NULL, outcome TEXT)')
        value=json.dumps(study,sort_keys=True,allow_nan=False)
        rows=self.db.execute('SELECT value FROM identity').fetchall()
        if not rows:self.db.execute('INSERT INTO identity VALUES (?)',(value,));self.db.commit()
        elif rows!=[(value,)]:raise ValueError('Study identity differs; do not reset the registry')

    def records(self):
        return [dict(id=i,phase=p,request=json.loads(r),request_sha256=s,registered_ns=t,outcome=json.loads(o) if o else None)
            for i,p,r,s,t,o in self.db.execute('SELECT * FROM calls ORDER BY registered_ns,id')]

    def register(self,request):
        if request['phase'] not in ('qualification','main','confirmation','diagnostic'):raise ValueError('Unknown phase')
        digest=fingerprint(request)
        try:
            self.db.execute('BEGIN IMMEDIATE')
            old=self.db.execute('SELECT request_sha FROM calls WHERE id=?',(request['id'],)).fetchone()
            if old:
                if old[0]!=digest:raise ValueError('Existing call identity differs')
                self.db.commit();return False
            counts=dict(self.db.execute('SELECT phase,count(*) FROM calls GROUP BY phase'))
            counted=sum(v for k,v in counts.items() if k!='diagnostic')
            if request['phase']!='diagnostic' and counted>=48:raise RuntimeError('All 48 technical-call registrations consumed')
            cap={'qualification':12,'main':36,'confirmation':8,'diagnostic':9}[request['phase']]
            if counts.get(request['phase'],0)>=cap:raise RuntimeError('Phase registration limit consumed')
            self.db.execute('INSERT INTO calls VALUES (?,?,?,?,?,NULL)',(request['id'],request['phase'],
                json.dumps(request,sort_keys=True,allow_nan=False),digest,time.time_ns()))
            self.db.commit();return True
        except BaseException:self.db.rollback();raise

    def finish(self,identity,outcome):
        if outcome.get('managed_active_processes')!=0 or not outcome.get('kernel_terminal_verified'):
            raise ValueError('Finalization requires observed process termination, not a status file')
        value=json.dumps(outcome,sort_keys=True,allow_nan=False)
        row=self.db.execute('SELECT outcome FROM calls WHERE id=?',(identity,)).fetchone()
        if row is None:raise KeyError('Unregistered call')
        if row[0] is not None:
            if row[0]!=value:raise ValueError('Terminal outcome is immutable')
            return
        self.db.execute('UPDATE calls SET outcome=? WHERE id=? AND outcome IS NULL',(value,identity));self.db.commit()

    def close(self):self.db.close()
