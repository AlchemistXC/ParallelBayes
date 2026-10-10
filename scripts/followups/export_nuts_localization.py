#!/usr/bin/env python3
"""Export all technical evidence and each committed source binding, no publish."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from nuts_events import atomic_json,sha
from nuts_runtime import host_lease,tree_bytes
from run_nuts_localization import load,restore_all
from nuts_instrumented_worker import require_windows
ROOT=Path(__file__).resolve().parents[2]


def export(root,analysis,destination,host_lock):
    require_windows();root=root.resolve();analysis=analysis.resolve();destination=destination.resolve()
    if destination.exists():raise FileExistsError('Archive must be new')
    if destination.is_relative_to(root) or destination.is_relative_to(analysis):raise ValueError('Archive must be outside evidence and analysis')
    with host_lease(host_lock.resolve(),'NUTS localization evidence export'):
        study,current,registry=load(root)
        try:restore_all(root,registry)
        finally:registry.close()
        # Completed analysis is required, but the study itself may legitimately
        # end with failed qualification or resource-stopped incomplete calls.
        from run_nuts_localization import verify_files
        verify_files(analysis,json.loads((analysis/'checksums.json').read_text()))
        if json.loads((analysis/'SUMMARY.json').read_text())['registry_sha256']!=sha(root/'calls.sqlite'):
            raise ValueError('Analysis predates the current call registry; rebuild in a new directory')
        members=[];total=0
        for prefix,directory in [('study',root),('analysis',analysis)]:
            for path in sorted(directory.rglob('*')):
                if path.is_symlink():raise ValueError('Do not export symlinks')
                if path.is_file():
                    name=prefix+'/'+str(path.relative_to(directory)).replace('\\','/')
                    members.append((name,path));total+=path.stat().st_size
        source=[];seen=set()
        for path in sorted((root/'bindings').glob('*.json')):
            binding=json.loads(path.read_text());commit=binding['source_commit'];identity=binding['binding_sha256']
            for name,digest in binding['identity']['source_files'].items():
                data=subprocess.check_output(['git','show',f'{commit}:{name}'],cwd=ROOT)
                if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Historical source snapshot differs')
                archive_name='source/'+identity+'/'+name
                if archive_name not in seen:source.append((archive_name,data));seen.add(archive_name);total+=len(data)
            for name in ('LICENSE','r-package/LICENSE'):
                result=subprocess.run(['git','show',f'{commit}:{name}'],cwd=ROOT,capture_output=True)
                if result.returncode==0:source.append(('source/'+identity+'/'+name,result.stdout));total+=len(result.stdout)
        destination.parent.mkdir(parents=True,exist_ok=True)
        if total*2>20*1024**3 or shutil.disk_usage(destination.parent).free<total+4*1024**3:
            raise OSError('Incremental study plus one archive or free-disk allocation exceeded')
        manifest={}
        with tarfile.open(destination,'x') as archive:
            for name,path in members:
                manifest[name]=dict(size=path.stat().st_size,sha256=sha(path));archive.add(path,arcname=name,recursive=False)
            for name,data in source:
                entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o644;archive.addfile(entry,io.BytesIO(data))
                manifest[name]=dict(size=len(data),sha256=hashlib.sha256(data).hexdigest())
            data=json.dumps(manifest,sort_keys=True,indent=2).encode()+b'\n';entry=tarfile.TarInfo('MANIFEST.json');entry.size=len(data);archive.addfile(entry,io.BytesIO(data))
        checked=0
        with tarfile.open(destination,'r') as archive:
            names=archive.getnames()
            if len(names)!=len(set(names)) or set(names)!=set(manifest)|{'MANIFEST.json'}:raise ValueError('Archive member set differs')
            for member in archive:
                if member.name=='MANIFEST.json':continue
                stream=archive.extractfile(member)
                digest=hashlib.file_digest(stream,'sha256').hexdigest()
                if member.size!=manifest[member.name]['size'] or digest!=manifest[member.name]['sha256']:raise ValueError('Archive content differs')
                checked+=1
        result=dict(archive=destination.name,bytes=destination.stat().st_size,sha256=sha(destination),verified_members=checked,
            public_upload=False,managed_active_processes=0,new_sampler_calls=0)
        atomic_json(destination.with_suffix(destination.suffix+'.receipt.json'),result)
        print(json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('study','analysis','destination','host-lock'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();export(a.study,a.analysis,a.destination,a.host_lock)
