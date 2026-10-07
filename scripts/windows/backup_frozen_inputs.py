"""Copy a sealed formal input/control inventory to a distinct physical volume.

First-party frozen files only; no sampler, environment mutation or raw results.
Partial/colliding destinations are retained and refused, never overwritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    root,bundle,out=(q.resolve() for q in (a.root,a.bundle,a.output))
    if out.drive.lower()==bundle.drive.lower():raise ValueError('Distinct volume required')
    if out.exists():raise FileExistsError('Retain existing backup; do not overwrite')
    sys.path[:0]=[str(root/'scripts/completion'),str(root/'scripts/windows')]
    from formal_freeze import verify_sealed_study,relative_file
    from formal_runtime import file_hash,atomic_json
    marker,protocol=verify_sealed_study(bundle)
    files=json.loads((bundle/'freeze-manifest.json').read_text())
    files.update({n:file_hash(bundle/n) for n in ('freeze-manifest.json','FROZEN.json')})
    sizes={n:relative_file(bundle,n).stat().st_size for n in files}
    if shutil.disk_usage(out.parent if out.parent.exists() else out.anchor).free<sum(sizes.values())+400*1024**3:
        raise OSError('Backup plus declared C-volume OS margin does not fit')
    out.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter()
    atomic_json(out/'BACKUP-INTENT.json',dict(source=str(bundle),identity=marker['identity'],
        protocol_sha256=protocol['protocol_sha256'],freeze_sha256=file_hash(bundle/'FROZEN.json'),
        inventory=files,files=len(files),file_bytes=sum(sizes.values()),
        scope='Frozen inputs/control/source/environment evidence only; no scientific trajectory backup'))
    for i,(name,expected) in enumerate(sorted(files.items())):
        src=relative_file(bundle,name);dst=relative_file(out/'frozen',name)
        dst.parent.mkdir(parents=True,exist_ok=True)
        if src.is_symlink() or file_hash(src)!=expected:raise ValueError('Source changed: '+name)
        with src.open('rb') as inp,dst.open('xb') as dest:
            shutil.copyfileobj(inp,dest,1024*1024);dest.flush();os.fsync(dest.fileno())
        if dst.stat().st_size!=sizes[name] or file_hash(dst)!=expected:raise ValueError('Backup differs: '+name)
        if (i+1)%128==0:print(json.dumps(dict(copied=i+1,total=len(files))),flush=True)
    atomic_json(out/'BACKUP-COMPLETED.json',dict(files=len(files),file_bytes=sum(sizes.values()),
        all_member_hashes_match=True,seconds=time.perf_counter()-start,
        independent_full_trajectory_backup=False,sampler_calls=0))
    print(json.dumps(dict(files=len(files),file_bytes=sum(sizes.values()),passed=True)),flush=True)


if __name__=='__main__':main()
