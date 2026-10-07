"""Extract only regular verified return members into a fresh directory."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import tarfile
import time


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path);p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    if a.destination.exists() or a.receipt.exists():
        raise ValueError('Destination and receipt must be new; preserve previous extraction attempts')
    digest=sha(a.archive)
    if a.archive.with_suffix(a.archive.suffix+'.sha256').read_text().split()[0]!=digest:
        raise ValueError('Archive checksum differs')
    start=time.perf_counter()
    root=a.destination.resolve()
    with tarfile.open(a.archive,'r') as archive:
        members=archive.getmembers();names=[m.name for m in members]
        if len(names)!=len(set(n.casefold() for n in names)):
            raise ValueError('Duplicate or Windows case-colliding members')
        manifest=json.load(archive.extractfile('WINDOWS-RETURN-MANIFEST.json'))
        if set(names)!=set(manifest['files'])|{'WINDOWS-RETURN-MANIFEST.json'}:
            raise ValueError('Unexpected or missing archive members')
        for member in members:
            n=PurePosixPath(member.name)
            if not member.isfile() or n.is_absolute() or '..' in n.parts or '\\' in member.name or PureWindowsPath(member.name).drive:
                raise ValueError('Unsafe or non-regular archive member')
            if not (root/member.name).resolve().is_relative_to(root):
                raise ValueError('Member escapes extraction root')
            if member.name!='WINDOWS-RETURN-MANIFEST.json':
                expected=manifest['files'][member.name]
                actual=hashlib.file_digest(archive.extractfile(member),'sha256').hexdigest()
                if member.size!=expected['bytes'] or actual!=expected['sha256']:
                    raise ValueError('Archive member size/checksum differs: '+member.name)
        root.mkdir(parents=True,exist_ok=False)
        archive.extractall(root,filter='data')
    for name,expected in manifest['files'].items():
        f=root/name
        if f.is_symlink() or f.stat().st_size!=expected['bytes'] or sha(f)!=expected['sha256']:
            raise ValueError('Relocated member size/checksum differs: '+name)
    result=dict(status='passed',archive=str(a.archive.resolve()),archive_sha256=digest,
        destination=str(root),checked_files=len(manifest['files']),
        source_commit=manifest['source_commit'],no_sampler_calls=True,
        safe_extraction_and_readback_seconds=time.perf_counter()-start)
    a.receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
