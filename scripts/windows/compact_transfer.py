"""Bounded per-file chunk delivery, without ever creating a full tar.

Plan hashes source bytes once. Emit writes one selected <=1GiB block. Ingest
validates it before append, verifies existing partial prefixes, and promotes
complete files without overwriting. Receiver state is outside the delivery.
Both platforms keep one original tree; the transfer cache can be one block.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_runtime import atomic_json,file_hash,fingerprint,host_lease

BUFFER=1024**2
MAX_BLOCK=1024**3
SCHEMA='compact-bounded-delivery-v1'
RESERVED={'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}


def safe(root,name):
    if not isinstance(name,str) or re.search(r'[\\:<>"|?*\x00-\x1f]',name) or not name:raise ValueError('Canonical member path required')
    p=PurePosixPath(name)
    if p.is_absolute() or p.as_posix()!=name or any(x in ('.','..','') or x.rstrip(' .')!=x or
        x.split('.')[0].upper() in RESERVED for x in p.parts):raise ValueError('Unsafe delivery path')
    if Path(root).is_symlink():raise ValueError('Redirected root refused')
    root=Path(root).resolve();path=root.joinpath(*p.parts)
    if not path.is_relative_to(root) or any(q.is_symlink() for q in [path,*path.parents] if q.is_relative_to(root)):
        raise ValueError('Redirected delivery path refused')
    return path


def _validate(p):
    unsigned=dict(p);digest=unsigned.pop('manifest_sha256')
    if p.get('schema')!=SCHEMA or fingerprint(unsigned)!=digest or not 1<=p['block_limit_bytes']<=MAX_BLOCK:
        raise ValueError('Bounded delivery manifest/checksum differs')
    seen=set();coverage={name:0 for name in p['files']}
    for name,value in p['files'].items():
        safe(Path.cwd(),name)
        if name.casefold() in seen or name=='WINDOWS-RETURN-MANIFEST.json':
            raise ValueError('Aliased or reserved delivery member')
        seen.add(name.casefold())
        if type(value['bytes']) is not int or value['bytes']<0 or not re.fullmatch('[0-9a-f]{64}',value['sha256']):
            raise ValueError('Invalid file size/hash')
    for i,chunk in enumerate(p['chunks']):
        if type(chunk['index']) is not int or type(chunk['bytes']) is not int or chunk['index']!=i or chunk['name']!=f'part-{i:06d}.bin' or not 0<chunk['bytes']<=p['block_limit_bytes']:
            raise ValueError('Missing/reordered or oversized block')
        position=0
        for seg in chunk['segments']:
            n=seg['path']
            if any(type(seg[k]) is not int for k in ('file_offset','chunk_offset','bytes')) or n not in coverage or seg['file_offset']!=coverage[n] or seg['chunk_offset']!=position or seg['bytes']<=0:
                raise ValueError('File/chunk segment coverage differs')
            coverage[n]+=seg['bytes'];position+=seg['bytes']
            if coverage[n]>p['files'][n]['bytes']:raise ValueError('Segment exceeds declared file')
        if position!=chunk['bytes'] or not re.fullmatch('[0-9a-f]{64}',chunk['sha256']):raise ValueError('Chunk size/hash invalid')
    if coverage!={n:v['bytes'] for n,v in p['files'].items()}:raise ValueError('Incomplete file coverage')
    return p


def load(path,expected_sha256):
    path=Path(path)
    if file_hash(path)!=expected_sha256:raise ValueError('Externally supplied manifest SHA differs')
    return _validate(json.loads(path.read_text()))


def plan(root,output,*,block_bytes=256*1024**2):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists() or output.is_relative_to(root) or not 1<=block_bytes<=MAX_BLOCK:
        raise ValueError('Fresh external manifest and <=1GiB block required')
    files={};chunks=[];segments=[];h=hashlib.sha256();position=0
    def close():
        nonlocal segments,h,position
        if position:
            i=len(chunks);chunks.append(dict(index=i,name=f'part-{i:06d}.bin',bytes=position,sha256=h.hexdigest(),segments=segments))
        segments=[];h=hashlib.sha256();position=0
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ValueError('Source symlinks refused')
        if not path.is_file():continue
        name=path.relative_to(root).as_posix();safe(root,name)
        size=path.stat().st_size;fh=hashlib.sha256();offset=0
        with path.open('rb') as source:
            while offset<size:
                length=min(size-offset,block_bytes-position)
                segments.append(dict(path=name,file_offset=offset,chunk_offset=position,bytes=length))
                left=length
                while left:
                    data=source.read(min(BUFFER,left))
                    if not data:raise ValueError('Source changed while planning')
                    fh.update(data);h.update(data);left-=len(data)
                offset+=length;position+=length
                if position==block_bytes:close()
            if source.read(1):raise ValueError('Source grew while planning')
        if path.stat().st_size!=size:raise ValueError('Source changed while planning')
        files[name]=dict(bytes=size,sha256=fh.hexdigest())
    close()
    p=dict(schema=SCHEMA,files=files,chunks=chunks,block_limit_bytes=block_bytes,copy_buffer_bytes=BUFFER,
        whole_tar_created=False,source_root_is_not_receiver_binding=True,statistical_repetitions_added=0)
    p['manifest_sha256']=fingerprint(p);_validate(p);atomic_json(output,p)
    return dict(files=len(files),chunks=len(chunks),bytes=sum(v['bytes'] for v in files.values()),
        manifest_file_sha256=file_hash(output),whole_tar_created=False)


def emit(root,manifest,manifest_sha256,index,output):
    p=load(manifest,manifest_sha256)
    if type(index) is not int or not 0<=index<len(p['chunks']):raise ValueError('Unknown block index')
    chunk=p['chunks'][index];output=Path(output)
    if output.exists():raise FileExistsError('Never overwrite a transfer block')
    partial=output.with_name(output.name+'.partial')
    if partial.exists():raise FileExistsError('Prior partial block retained; use a fresh cache directory')
    h=hashlib.sha256()
    with partial.open('xb') as target:
        for seg in chunk['segments']:
            path=safe(root,seg['path'])
            if path.stat().st_size!=p['files'][seg['path']]['bytes']:raise ValueError('Source size changed')
            with path.open('rb') as source:
                source.seek(seg['file_offset']);left=seg['bytes']
                while left:
                    data=source.read(min(BUFFER,left))
                    if not data:raise ValueError('Source ended unexpectedly')
                    target.write(data);h.update(data);left-=len(data)
        target.flush();os.fsync(target.fileno())
    if partial.stat().st_size!=chunk['bytes'] or h.hexdigest()!=chunk['sha256']:
        raise ValueError('Source bytes differ from frozen delivery plan; partial retained')
    partial.rename(output)
    return dict(index=index,bytes=chunk['bytes'],sha256=chunk['sha256'],maximum_buffer_bytes=BUFFER)


def _state(output,p,manifest_sha256):
    root=Path(output).resolve();state=root.with_name(root.name+'.receive-state')
    descriptor=dict(schema=SCHEMA,manifest_file_sha256=manifest_sha256,manifest_sha256=p['manifest_sha256'],output=str(root))
    if state.exists():
        if json.loads((state/'identity.json').read_text())!=descriptor:raise ValueError('Receiver identity changed')
    else:
        if root.exists():raise ValueError('Existing unregistered receiver root refused')
        state.mkdir(parents=True,exist_ok=False);root.mkdir()
        atomic_json(state/'identity.json',descriptor);atomic_json(state/'progress.json',dict(completed_chunks=0))
    return root,state


def ingest(manifest,manifest_sha256,index,chunk,output):
    p=load(manifest,manifest_sha256)
    if type(index) is not int or not 0<=index<len(p['chunks']):raise ValueError('Unknown block index')
    expected=p['chunks'][index];chunk=Path(chunk)
    # Missing/corrupt input is refused before creating or changing the receiver.
    if not chunk.is_file() or chunk.stat().st_size!=expected['bytes'] or file_hash(chunk)!=expected['sha256']:
        raise ValueError('Missing, corrupt or foreign block; no receiver writes')
    output=Path(output).resolve()
    with host_lease(output.with_name(output.name+'.receiver.lock'),'bounded receive'):
        root,state=_state(output,p,manifest_sha256);progress=json.loads((state/'progress.json').read_text())
        next_index=progress['completed_chunks']
        if index>next_index:raise ValueError('Missing preceding block; no out-of-order assembly')
        if index<next_index:return dict(index=index,newly_ingested_bytes=0,already_verified=True)
        newly=0
        with chunk.open('rb') as source:
            for seg in expected['segments']:
                path=safe(root,seg['path']);item=p['files'][seg['path']]
                if path.exists():
                    if path.stat().st_size!=item['bytes'] or file_hash(path)!=item['sha256']:
                        raise ValueError('Existing receiver file differs; never overwrite')
                    continue
                path.parent.mkdir(parents=True,exist_ok=True)
                # Failed original .partial files are ordinary evidence members.
                # Receive temporaries live in the sibling state tree, never at
                # a filename that can alias a retained original asset.
                partial=safe(state/'partials',seg['path']);partial.parent.mkdir(parents=True,exist_ok=True)
                size=partial.stat().st_size if partial.exists() else 0
                if not seg['file_offset']<=size<=seg['file_offset']+seg['bytes']:
                    raise ValueError('Partial receiver coverage differs; retained')
                source.seek(seg['chunk_offset'])
                # A crashed append can be continued only after byte comparison
                # with the same SHA-verified block; no truncation/regeneration.
                prefix=size-seg['file_offset']
                if prefix:
                    with partial.open('rb') as old:
                        old.seek(seg['file_offset']);left=prefix
                        while left:
                            n=min(BUFFER,left)
                            if old.read(n)!=source.read(n):raise ValueError('Partial prefix differs; retained without overwrite')
                            left-=n
                with partial.open('ab') as target:
                    left=seg['bytes']-prefix
                    while left:
                        data=source.read(min(BUFFER,left))
                        if not data:raise ValueError('Block unexpectedly ended')
                        target.write(data);newly+=len(data);left-=len(data)
                    target.flush();os.fsync(target.fileno())
                if partial.stat().st_size==item['bytes']:
                    if file_hash(partial)!=item['sha256']:raise ValueError('Assembled file hash differs; partial retained')
                    partial.rename(path)
        atomic_json(state/f'chunk-{index:06d}.json',dict(index=index,sha256=expected['sha256'],bytes=expected['bytes']))
        atomic_json(state/'progress.json',dict(completed_chunks=index+1))
        return dict(index=index,newly_ingested_bytes=newly,already_verified=False)


def verify_received(manifest,manifest_sha256,output):
    p=load(manifest,manifest_sha256);root=Path(output).resolve();state=root.with_name(root.name+'.receive-state')
    if not state.exists():raise ValueError('No receiver state')
    _state(root,p,manifest_sha256)
    progress=json.loads((state/'progress.json').read_text())
    if progress['completed_chunks']!=len(p['chunks']):raise ValueError('Missing blocks; receiver incomplete')
    for i,chunk in enumerate(p['chunks']):
        saved=json.loads((state/f'chunk-{i:06d}.json').read_text())
        if saved!=dict(index=i,sha256=chunk['sha256'],bytes=chunk['bytes']):raise ValueError('Chunk receipt differs')
    for name,record in p['files'].items():
        path=safe(root,name)
        if record['bytes']==0 and not path.exists():path.parent.mkdir(parents=True,exist_ok=True);path.touch(exist_ok=False)
        if path.stat().st_size!=record['bytes'] or file_hash(path)!=record['sha256']:raise ValueError('Received file differs: '+name)
    allowed=set(p['files'])|{'WINDOWS-RETURN-MANIFEST.json'}
    actual={q.relative_to(root).as_posix() for q in root.rglob('*') if q.is_file()}
    if not actual<=allowed:raise ValueError('Unexpected delivered members or partial files')
    # The normal immutable index/reader consumes this explicit file manifest.
    delivery=dict(files=p['files'],source_manifest_sha256=manifest_sha256,
        scope='Complete bounded receive; native processes were validated at origin, not live at receiver')
    dest=root/'WINDOWS-RETURN-MANIFEST.json'
    if dest.exists():
        if json.loads(dest.read_text())!=delivery:raise ValueError('Existing return manifest differs')
    else:atomic_json(dest,delivery)
    receipt=dict(passed=True,files=len(p['files']),chunks=len(p['chunks']),new_sampler_calls=0,
        manifest_file_sha256=manifest_sha256,return_manifest_sha256=file_hash(dest),whole_tar_created=False)
    atomic_json(state/'RECEIVED.json',receipt);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('plan');q.add_argument('--root',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q.add_argument('--block-bytes',type=int,default=256*1024**2)
    for name in ('emit','ingest','verify'):
        q=s.add_parser(name);q.add_argument('--manifest',type=Path,required=True);q.add_argument('--manifest-sha256',required=True)
        q.add_argument('--output',type=Path,required=True)
        if name!='verify':q.add_argument('--index',type=int,required=True)
        if name=='emit':q.add_argument('--root',type=Path,required=True)
        if name=='ingest':q.add_argument('--chunk',type=Path,required=True)
    args=vars(p.parse_args());cmd=args.pop('command')
    print(json.dumps({'plan':plan,'emit':emit,'ingest':ingest,'verify':verify_received}[cmd](**args),indent=2))
