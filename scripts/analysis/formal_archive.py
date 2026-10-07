"""Stream an integrity manifest into an immutable, relocatable evidence index.

The index is a receiver artifact. It never writes into delivered evidence and
does not treat file hashes as proof of numerical correctness or live OS state.
"""
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_freeze import relative_file
from task_journal import read_task_export

SCHEMA='formal-delivery-index-v1'
HISTORY=re.compile(r'(?:(formal-runs/batch-(\d{2})/))?(main|cache)/visits/[^/]+/([0-9a-f]{24})\.history\.json$')


class _JSONStream:
    """Bound individual JSON values, not the whole files object in a manifest."""
    def __init__(self,stream):
        self.stream=stream;self.buffer='';self.eof=False;self.decoder=json.JSONDecoder(object_pairs_hook=self.unique)

    @staticmethod
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON field: '+key)
            result[key]=value
        return result

    def fill(self):
        text=self.stream.read(65536);self.eof=not bool(text);self.buffer+=text
        if len(self.buffer)>2*1024**2:raise ValueError('A manifest field exceeds the metadata allowance')

    def ready(self):
        while True:
            self.buffer=self.buffer.lstrip()
            if self.buffer or self.eof:return
            self.fill()

    def token(self,wanted):
        self.ready()
        if not self.buffer.startswith(wanted):raise ValueError('Malformed manifest JSON')
        self.buffer=self.buffer[len(wanted):]

    def value(self):
        self.ready()
        while True:
            try:value,end=self.decoder.raw_decode(self.buffer)
            except json.JSONDecodeError:
                if self.eof:raise ValueError('Truncated or invalid manifest field')
                self.fill();continue
            # Numeric values at a chunk edge may still have more digits.
            if end==len(self.buffer) and not self.eof:self.fill();continue
            self.buffer=self.buffer[end:];return value

    def fields(self):
        self.token('{');first=True
        while True:
            self.ready()
            if self.buffer.startswith('}'):self.token('}');return
            if not first:self.token(',')
            name=self.value()
            if not isinstance(name,str):raise ValueError('JSON object keys must be strings')
            self.token(':');yield name
            first=False


def manifest_records(path):
    """Yield ('file',path,record) or ('metadata',key,value), once per field."""
    with Path(path).open(encoding='utf-8') as source:
        parser=_JSONStream(source);seen=set()
        for key in parser.fields():
            if key in seen:raise ValueError('Duplicate top-level manifest field')
            seen.add(key)
            if key=='files':
                for name in parser.fields():yield 'file',name,parser.value()
            else:yield 'metadata',key,parser.value()
        parser.ready()
        if parser.buffer or not parser.eof:raise ValueError('Trailing manifest content')
        if 'files' not in seen:raise ValueError('Delivery file inventory is missing')


def build_index(delivery, bundle_relative, manifest_sha256, output):
    """Verify all delivered files once, then create indexed task-local lookups.

    The externally checked manifest SHA256 must be supplied. Partial index
    builds are retained and refused on reuse. No extraction occurs here.
    """
    delivery=Path(delivery).resolve();output=Path(output).resolve()
    bundle=relative_file(delivery,bundle_relative) if bundle_relative else delivery
    if not bundle.is_dir():raise ValueError('Delivered bundle directory is missing')
    if output.exists() or output.is_relative_to(delivery) or delivery.is_relative_to(output):
        raise ValueError('Fresh index directory separate from delivery required')
    manifest=delivery/'WINDOWS-RETURN-MANIFEST.json'
    if manifest.is_symlink() or file_hash(manifest)!=manifest_sha256:raise ValueError('Delivery manifest identity differs')
    output.mkdir(parents=True);db=sqlite3.connect(output/'files.sqlite3')
    db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA cache_size=-2048')
    db.execute('CREATE TABLE files (archive_path TEXT PRIMARY KEY, path TEXT UNIQUE, bytes INTEGER NOT NULL, sha256 TEXT NOT NULL)')
    db.execute('CREATE TABLE histories (path TEXT PRIMARY KEY, phase TEXT NOT NULL, batch INTEGER NOT NULL, task_id TEXT NOT NULL, events INTEGER NOT NULL)')
    db.execute('CREATE INDEX histories_by_task ON histories(batch,phase,task_id,events)')
    count=0;bundle_count=0;size=0;metadata={};prefix=bundle_relative+'/' if bundle_relative else ''
    try:
        for kind,name,value in manifest_records(manifest):
            if kind=='metadata':metadata[name]=value;continue
            path=relative_file(delivery,name)
            if name=='WINDOWS-RETURN-MANIFEST.json' or not isinstance(value,dict) or set(value)!={'bytes','sha256'}:
                raise ValueError('Unexpected delivery record')
            if (type(value['bytes']) is not int or value['bytes']<0 or not isinstance(value['sha256'],str) or
                    not re.fullmatch('[0-9a-f]{64}',value['sha256'])):raise ValueError('Invalid file size/checksum')
            if not path.is_file() or path.stat().st_size!=value['bytes'] or file_hash(path)!=value['sha256']:
                raise ValueError('Delivered file differs: '+name)
            local=name[len(prefix):] if name.startswith(prefix) else None
            if local is not None:relative_file(bundle,local)
            db.execute('INSERT INTO files VALUES (?,?,?,?)',(name,local,value['bytes'],value['sha256']))
            count+=1;bundle_count+=local is not None;size+=value['bytes']
            match=HISTORY.fullmatch(local or '')
            if match:
                _,batch,phase,identifier=match.groups();export=read_task_export(path)
                task=export['entry']['task']
                if task['id']!=identifier or task['batch']!=int(batch or 0) or task['artifact_kind']!=('posterior' if phase=='main' else 'cache_measurement'):
                    raise ValueError('History path and declared task differ')
                db.execute('INSERT INTO histories VALUES (?,?,?,?,?)',(local,phase,int(batch or 0),identifier,len(export['events'])))
            if count%1000==0:db.commit()
        db.commit()
        actual=0
        for path in delivery.rglob('*'):
            if path.is_symlink():raise ValueError('Symlinked delivered evidence')
            if not path.is_file() or path==manifest:continue
            if db.execute('SELECT 1 FROM files WHERE archive_path=?',(path.relative_to(delivery).as_posix(),)).fetchone() is None:
                raise ValueError('Unlisted delivered file: '+str(path))
            actual+=1
        if actual!=count or not bundle_count:raise ValueError('Incomplete delivery inventory')
        if file_hash(manifest)!=manifest_sha256:raise ValueError('Manifest changed during indexing')
        receipt=dict(schema=SCHEMA,manifest_sha256=manifest_sha256,bundle_relative=bundle_relative,
            delivered_files=count,bundle_files=bundle_count,total_bytes=size,delivery_metadata=metadata,
            history_exports=db.execute('SELECT COUNT(*) FROM histories').fetchone()[0],
            numerical_results_validated=False,live_processes_observed=False)
        db.close();receipt['database_sha256']=file_hash(output/'files.sqlite3')
        atomic_json(output/'INDEX.json',receipt)
        return receipt
    except BaseException:
        db.close();raise


class EvidenceIndex:
    def __init__(self,delivery,index):
        self.delivery=Path(delivery).resolve();self.directory=Path(index).resolve()
        self.receipt=json.loads((self.directory/'INDEX.json').read_text())
        if self.receipt['schema']!=SCHEMA or file_hash(self.directory/'files.sqlite3')!=self.receipt['database_sha256']:
            raise ValueError('Receiver index changed')
        if file_hash(self.delivery/'WINDOWS-RETURN-MANIFEST.json')!=self.receipt['manifest_sha256']:
            raise ValueError('Relocated delivery manifest differs')
        name=self.receipt['bundle_relative'];self.root=relative_file(self.delivery,name) if name else self.delivery
        self.db=sqlite3.connect((self.directory/'files.sqlite3').as_uri()+'?mode=ro',uri=True)

    def close(self):self.db.close()

    def record(self,name):
        relative_file(self.root,name)
        row=self.db.execute('SELECT bytes,sha256 FROM files WHERE path=?',(name,)).fetchone()
        if row is None:raise ValueError('Evidence file is absent from verified delivery: '+name)
        return dict(bytes=row[0],sha256=row[1])

    def path(self,name):
        record=self.record(name);path=relative_file(self.root,name)
        if not path.is_file() or path.stat().st_size!=record['bytes'] or file_hash(path)!=record['sha256']:
            raise ValueError('Indexed evidence changed: '+name)
        return path

    def json(self,name):return json.loads(self.path(name).read_text())

    def subtree(self,name):
        relative_file(self.root,name)
        return dict(self.db.execute('SELECT path,sha256 FROM files WHERE path=? OR (path>=? AND path<?)',(name,name+'/',name+'0')))

    def task_evidence(self,task,phase,phase_root):
        """Select the longest compatible exported event history, not newest mtime.

        No export means an evidence gap, even if output or status files exist.
        Divergent export chains and active states are never replaced by a less
        recent successful snapshot. The lifecycle reader makes the final check.
        """
        directory=phase_root+'/tasks/'+task['id'];ledger=phase_root+'/call-costs/'+task['id']
        candidates=self.db.execute('SELECT path FROM histories WHERE batch=? AND phase=? AND task_id=? ORDER BY events,path',
            (task['batch'],phase,task['id'])).fetchall()
        assets=self.subtree(directory);costs=self.subtree(ledger);assets.update(costs)
        previous=None;selected=None
        for (name,) in candidates:
            if not name.startswith(phase_root+'/visits/'):raise ValueError('History stored in another phase layout')
            current=read_task_export(self.path(name))
            if current['entry']['task']!=task:raise ValueError('History task differs from complete frozen frame')
            if previous is not None:
                if (current['events'][:len(previous['events'])]!=previous['events'] or
                        current['live_identity']!=previous['live_identity'] or
                        current['entry']['binding']!=previous['entry']['binding'] or
                        current['entry']['output']!=previous['entry']['output']):
                    raise ValueError('Conflicting exported histories for one task')
            previous=current;selected=name;assets[name]=self.record(name)['sha256']
        return dict(history_export=selected,directory=directory,ledger=ledger if costs else None,
            manifest=assets,evidence_status='available' if selected else 'evidence_gap',
            history_exports=len(candidates),task_files=len(assets),
            known_output_without_export=selected is None and bool(self.subtree(directory)))

    def verify_local_files(self,manifest):
        for name,digest in manifest.items():
            if self.record(name)['sha256']!=digest:raise ValueError('Analysis input binding differs from delivery')
            self.path(name)
