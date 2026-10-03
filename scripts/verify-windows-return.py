"""Independently verify every archived member against WINDOWS-RETURN-MANIFEST.

Does not extract or execute content. An adjacent archive .sha256 is also checked.
"""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path,PurePosixPath


def digest(stream):
    h=hashlib.sha256()
    for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def verify(path):
    path=Path(path)
    with path.open('rb') as f:archive_sha=digest(f)
    if path.with_suffix(path.suffix+'.sha256').read_text().split()[0]!=archive_sha:
        raise ValueError('archive checksum mismatch')
    with tarfile.open(path,'r') as archive:
        members=archive.getmembers();names=[m.name for m in members]
        if len(names)!=len(set(names)):raise ValueError('duplicate archive members')
        manifest=json.load(archive.extractfile('WINDOWS-RETURN-MANIFEST.json'))
        expected=manifest['files']
        if set(names)!=set(expected)|{'WINDOWS-RETURN-MANIFEST.json'}:
            raise ValueError('unexpected or missing members')
        for member in members:
            name=PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or not member.isfile():
                raise ValueError('non-regular or unsafe member')
            if member.name=='WINDOWS-RETURN-MANIFEST.json':continue
            record=expected[member.name]
            if member.size!=record['bytes'] or digest(archive.extractfile(member))!=record['sha256']:
                raise ValueError('member checksum mismatch: '+member.name)
    return dict(status='passed',archive=str(path.resolve()),archive_sha256=archive_sha,
                checked_files=len(expected),source_commit=manifest['source_commit'],branch=manifest['branch'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=verify(args.archive)
    body=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(body,encoding='utf-8')
    print(body)
