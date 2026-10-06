"""Transactional, indexed task identities and event history for owned runtimes.

This module never observes or terminates processes and never grants sample
eligibility. The caller holds its shared host lease across read/modify/write
and kernel observation. One task and its history are read on access; only
indexed active tasks are visited before unrelated launches.
"""
import copy
import json
from pathlib import Path
import sqlite3
import time

from formal_runtime import atomic_json, fingerprint

SCHEMA = 'owned-task-journal-v1'


class JournalConflict(RuntimeError):
    pass


class TaskJournal:
    """Durably bind tasks, retain attempts, and export individual histories.

Identity is supplied by the native runtime and includes its host lock/schema.
Opening a partially created or relocated live journal fails closed; read-only
exports are the portable evidence, not a claim that the live lease relocated.
Checksums detect accidental damage, not an adversary rewriting all records.
"""

    def __init__(self, directory, identity):
        self.directory = Path(directory).resolve()
        self.identity = copy.deepcopy(identity)
        self.connection = None

    def __enter__(self):
        directory = self.directory
        new = not directory.exists()
        descriptor = directory/'identity.json'
        database = directory/'tasks.sqlite3'
        expected = dict(schema=SCHEMA, identity=self.identity)
        if not new:
            if (not descriptor.is_file() or not database.is_file() or
                    descriptor.is_symlink() or database.is_symlink()):
                raise JournalConflict('Incomplete journal; preserve it, do not initialize over it')
            if json.loads(descriptor.read_text()) != expected:
                raise JournalConflict('Live journal identity differs')
        else:
            directory.mkdir(parents=True, exist_ok=False)
        db = sqlite3.connect(database)
        self.connection = db
        try:
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('PRAGMA cache_size=-2048')
            db.execute('PRAGMA foreign_keys=ON')
            if new:
                with db:
                    db.execute('CREATE TABLE tasks (key TEXT PRIMARY KEY, output TEXT UNIQUE NOT NULL, '
                               'record TEXT NOT NULL, checksum TEXT NOT NULL, active INTEGER NOT NULL, '
                               'protocol TEXT NOT NULL, batch INTEGER NOT NULL, outcome TEXT NOT NULL)')
                    db.execute('CREATE TABLE events (task_key TEXT NOT NULL REFERENCES tasks(key), '
                               'ordinal INTEGER NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL, '
                               'PRIMARY KEY(task_key,ordinal))')
                    db.execute('CREATE INDEX active_tasks ON tasks(active)')
                    db.execute('CREATE INDEX task_batch ON tasks(protocol,batch,key)')
                atomic_json(descriptor, expected)
            else:
                tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if tables!={'tasks','events'}:
                    raise JournalConflict('SQLite journal schema differs')
            return self
        except BaseException:
            db.close(); self.connection = None
            raise

    def __exit__(self, *exc):
        self.connection.close()
        self.connection = None

    @staticmethod
    def key(task):
        if not all(isinstance(task.get(k),str) and task[k] for k in ('id','protocol_sha256')):
            raise JournalConflict('Explicit protocol and task identity required')
        return fingerprint(dict(protocol=task['protocol_sha256'], id=task['id']))

    @staticmethod
    def _metadata(entry):
        task = entry['task']
        if task != entry['binding']['task'] or entry['output'] != entry['binding']['output']:
            raise JournalConflict('Task binding or output differs')
        if type(task.get('batch')) is not int or task['batch'] < 0:
            raise JournalConflict('Nonnegative batch required')
        attempts = entry['attempts']
        if not isinstance(attempts,list) or not isinstance(entry['calls'],list):
            raise JournalConflict('Explicit attempt and invocation histories required')
        active = any(a['outcome']=='active' for a in attempts)
        if active and (attempts[-1]['outcome']!='active' or sum(a['outcome']=='active' for a in attempts)!=1):
            raise JournalConflict('Only the latest attempt may be active')
        return (entry['output'], int(active), task['protocol_sha256'], task['batch'],
                attempts[-1]['outcome'] if attempts else 'not_run')

    def read(self, key):
        row = self.connection.execute(
            'SELECT output,record,checksum,active,protocol,batch,outcome FROM tasks WHERE key=?',(key,)).fetchone()
        if row is None:
            return None
        entry = json.loads(row[1])
        if (fingerprint(entry)!=row[2] or self.key(entry['task'])!=key or
                self._metadata(entry)!=(row[0],row[3],row[4],row[5],row[6])):
            raise JournalConflict('Task record or indexed identity differs')
        previous = None
        last = None
        for ordinal,payload,digest in self.connection.execute(
                'SELECT ordinal,payload,checksum FROM events WHERE task_key=? ORDER BY ordinal',(key,)):
            event = json.loads(payload)
            if (ordinal!=(0 if last is None else last['index']+1) or event['index']!=ordinal or
                    event['task_key']!=key or event['previous']!=previous or fingerprint(event)!=digest):
                raise JournalConflict('Per-task event chain differs')
            previous=digest;last=event
        if last is None or last['entry_sha256']!=row[2]:
            raise JournalConflict('Latest event does not bind the current task record')
        return entry

    def save(self, key, entry, kind, details=None):
        """Commit record and chained event atomically; never rebind an identity."""
        entry = copy.deepcopy(entry)
        if self.key(entry['task']) != key:
            raise JournalConflict('Task key differs')
        metadata = self._metadata(entry)
        old = self.read(key)
        if old is not None:
            if any(entry[k]!=old[k] for k in ('binding','output','task')):
                raise JournalConflict('Immutable task identity or binding changed')
            if len(entry['attempts']) < len(old['attempts']) or len(entry['calls']) < len(old['calls']):
                raise JournalConflict('Attempt/invocation history was truncated')
            for prior,current in zip(old['attempts'],entry['attempts']):
                if any(current.get(k)!=prior[k] for k in ('id','directory','job_name') if k in prior):
                    raise JournalConflict('Attempt identity changed')
                if prior['outcome']!='active' and prior!=current:
                    raise JournalConflict('Closed attempt changed')
            for prior,current in zip(old['calls'],entry['calls']):
                if (prior.get('seconds') is not None or prior.get('outcome')!='active') and prior!=current:
                    raise JournalConflict('Completed invocation changed')
        last = self.connection.execute(
            'SELECT ordinal,checksum FROM events WHERE task_key=? ORDER BY ordinal DESC LIMIT 1',(key,)).fetchone()
        checksum = fingerprint(entry)
        event = dict(index=last[0]+1 if last else 0, previous=last[1] if last else None,
                     task_key=key, kind=kind, details=copy.deepcopy(details),
                     recorded_ns=time.time_ns(), entry_sha256=checksum)
        output,active,protocol,batch,outcome=metadata
        try:
            with self.connection:
                self.connection.execute(
                    'INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET '
                    'record=excluded.record,checksum=excluded.checksum,active=excluded.active,outcome=excluded.outcome',
                    (key,output,json.dumps(entry,sort_keys=True,allow_nan=False),checksum,active,protocol,batch,outcome))
                self.connection.execute('INSERT INTO events VALUES (?,?,?,?)',
                    (key,event['index'],json.dumps(event,sort_keys=True,allow_nan=False),fingerprint(event)))
        except sqlite3.IntegrityError as exc:
            raise JournalConflict('Output identity or event conflicts with stored history') from exc
        return checksum

    def active(self):
        """Read indexed pending records only; OS proof is the caller's job."""
        keys=[r[0] for r in self.connection.execute('SELECT key FROM tasks WHERE active=1 ORDER BY key')]
        return {key:self.read(key) for key in keys}

    def keys(self, protocol, batch=None):
        query='SELECT key FROM tasks WHERE protocol=?';args=[protocol]
        if batch is not None:
            query+=' AND batch=?';args.append(batch)
        yield from (r[0] for r in self.connection.execute(query+' ORDER BY key',args))

    def check_database(self):
        """Explicit whole-database check; never hidden in a task invocation."""
        messages=[r[0] for r in self.connection.execute('PRAGMA integrity_check')]
        if messages!=['ok']:raise JournalConflict('SQLite integrity check failed: '+str(messages))
        return dict(integrity='ok',scope='SQLite structure, not all task identities or OS lifecycle')

    def export(self, key, destination):
        """Export a checked task/history without reading unrelated task bodies."""
        path=Path(destination)
        if path.exists():raise FileExistsError('No evidence overwrite')
        entry=self.read(key)
        if entry is None:raise JournalConflict('Task is not registered')
        events=[]
        for payload,digest in self.connection.execute(
                'SELECT payload,checksum FROM events WHERE task_key=? ORDER BY ordinal',(key,)):
            events.append(dict(json.loads(payload),sha256=digest))
        value=dict(schema=SCHEMA,live_identity=self.identity,task_key=key,
                   entry=entry,events=events,export_is_live_registry=False,
                   process_termination_proven=False)
        atomic_json(path,dict(value,sha256=fingerprint(value)))
        return fingerprint(value)
