#!/usr/bin/env python3
"""Verify and extract the exact first-party S2 input package into a new folder."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import tarfile
ROOT=Path(__file__).resolve().parents[2]


def unpack(archive,output):
    expected=json.loads((ROOT/'handoff/windows-nuts-localization/input-package.json').read_text())
    with archive.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    if archive.stat().st_size!=expected['bytes'] or digest!=expected['sha256']:raise ValueError('Input archive differs')
    if output.exists():raise FileExistsError('New extraction directory required')
    with tarfile.open(archive,'r') as t:
        members=t.getmembers();names=[m.name for m in members]
        if len(names)!=len(set(names)) or set(names)!=set(expected['files'])|{'MANIFEST.json'}:raise ValueError('Archive member set differs')
        if any(not m.isfile() or len(PurePosixPath(m.name).parts)!=1 or '\\' in m.name for m in members):raise ValueError('Unsupported archive member')
        for m in members:
            if m.name=='MANIFEST.json':
                if m.size>65536:raise ValueError('Manifest too large')
                if json.load(t.extractfile(m))!=expected['files']:raise ValueError('Internal manifest differs')
            else:
                if m.size!=expected['files'][m.name]['bytes']:raise ValueError('Member size differs')
                if hashlib.file_digest(t.extractfile(m),'sha256').hexdigest()!=expected['files'][m.name]['sha256']:raise ValueError('Member hash differs')
        output.mkdir(parents=True)
        for m in members:
            if m.name=='MANIFEST.json':continue
            with t.extractfile(m) as source,(output/m.name).open('xb') as dest:
                while data:=source.read(1024**2):dest.write(data)
        for name,value in expected['files'].items():
            with (output/name).open('rb') as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=value['sha256']:raise ValueError('Extracted member differs')
    print(json.dumps(dict(verified_members=len(expected['files']),archive_sha256=digest,new_sampler_calls=0)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();unpack(a.archive,a.output)
