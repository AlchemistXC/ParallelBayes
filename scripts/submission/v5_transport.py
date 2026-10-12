#!/usr/bin/env python3
"""Relocate the pinned v5 ZIP. Existing tar/tree verification remains unchanged."""
import argparse
import json
from pathlib import Path
import shutil
import stat
import zipfile

from reproduction import check_file, read_pinned, relative


def extract_zip(manifest, digest, locations, component, output, max_bytes):
    inventory = read_pinned(manifest, digest)
    selected = [c for c in inventory['components'] if c['id'] == component]
    if len(selected) != 1 or selected[0]['kind'] != 'file':
        raise ValueError('One ZIP file component required')
    record = selected[0]
    archive = Path(json.loads(Path(locations).read_text(encoding='utf-8'))[component]['path'])
    check_file(archive, record)
    out = Path(output)
    if out.exists() or out.is_symlink():
        raise FileExistsError('Use a new extraction directory')
    for path in (archive, Path(manifest), Path(locations)):
        if out.resolve().is_relative_to(path.resolve()) or path.resolve().is_relative_to(out.resolve()):
            raise ValueError('Output overlaps an input')
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        names = [relative(m.filename).as_posix() for m in members]
        if len(set(names)) != len(names) or len({n.casefold() for n in names}) != len(names):
            raise ValueError('Duplicate or case-aliased ZIP member')
        if any(m.is_dir() or stat.S_ISLNK(m.external_attr >> 16) or m.flag_bits & 1 for m in members):
            raise ValueError('Only unencrypted regular ZIP files are accepted')
        if max_bytes < 0 or sum(m.file_size for m in members) > max_bytes:
            raise ValueError('Extraction exceeds disk allowance')
        # CRC errors stop before creation; partial extraction is retained on I/O errors.
        if bundle.testzip() is not None:
            raise ValueError('ZIP CRC failure')
        out.mkdir(parents=True)
        for member, name in zip(members, names):
            dest = out/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as src, dest.open('xb') as dst:
                shutil.copyfileobj(src, dst, length=1024*1024)
    receipt = dict(component=component, archive_sha256=record['sha256'],
                   members=len(members), extracted_bytes=sum(m.file_size for m in members),
                   new_sampler_calls=0, scope='ZIP relocation only; BUILD.py verifies the content manifest')
    out.with_name(out.name+'.extraction.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','locations','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--component',required=True)
    parser.add_argument('--max-bytes',type=int,default=512*1024**2)
    args = parser.parse_args()
    print(json.dumps(extract_zip(args.manifest,args.manifest_sha256,args.locations,
                                 args.component,args.output,args.max_bytes)))
