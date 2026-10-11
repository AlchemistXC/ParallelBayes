#!/usr/bin/env python3
"""Verify a pinned submission inventory and safely relocate chosen evidence.

Only standard-library file operations. No sampler, RNG or scientific backend.
Locations are supplied separately and are never written to the public receipt.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_pinned(path, digest):
    if sha(path) != digest:
        raise ValueError('External manifest SHA256 mismatch')
    return json.loads(Path(path).read_text(encoding='utf-8'))


def relative(name):
    p = PurePosixPath(name)
    if not name or '\\' in name or p.is_absolute() or '..' in p.parts or ':' in name:
        raise ValueError('Unsafe member path')
    return p


def check_file(path, record):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing regular file')
    if path.stat().st_size != record['bytes'] or sha(path) != record['sha256']:
        raise ValueError('File size/SHA256 mismatch')


def tree_members(directory):
    files = set()
    for p in directory.rglob('*'):
        if p.is_symlink():
            raise ValueError('Symlink in evidence tree')
        if p.is_file():
            files.add(p.relative_to(directory).as_posix())
    return files


def verify_component(component, location):
    path = Path(location['path'])
    if component['kind'] == 'file':
        check_file(path, component)
        return dict(id=component['id'], passed=True, bytes=component['bytes'], files=1,
                    verified='archive/file bytes; scientific replay is a separate stage')
    if component['kind'] != 'tree' or path.is_symlink() or not path.is_dir():
        raise ValueError('Invalid evidence directory')
    m = read_pinned(location['manifest'], component['manifest_sha256'])
    files = m['files']
    if len(files) != component['files'] or sum(v['bytes'] for v in files.values()) != component['bytes']:
        raise ValueError('Component counts differ from inventory')
    extra = component.get('receiver_files', {})
    expected = set(files) | set(extra)
    if tree_members(path) != expected:
        raise ValueError('Missing or additional evidence member')
    for name, record in {**files, **extra}.items():
        child = path / relative(name)
        if not child.resolve().is_relative_to(path.resolve()):
            raise ValueError('Evidence member escaped directory')
        check_file(child, record)
    return dict(id=component['id'], passed=True, bytes=component['bytes'],
                files=len(files), receiver_metadata_files=len(extra),
                verified='every original member size and SHA256 plus exact membership')


def verify(manifest, digest, locations, output):
    out = Path(output)
    if out.exists():
        raise FileExistsError('Receipt exists; use a new path')
    inventory = read_pinned(manifest, digest)
    bindings = json.loads(Path(locations).read_text(encoding='utf-8'))
    components = inventory['components']
    ids = [c['id'] for c in components]
    if len(set(ids)) != len(ids) or set(bindings) != set(ids):
        raise ValueError('Location IDs must exactly cover the inventory')
    result = dict(identity=inventory['identity'], manifest_sha256=digest,
                  new_sampler_calls=0, new_independent_repetitions=0,
                  public_or_external_reviewer_access_tested=False, components=[])
    out.parent.mkdir(parents=True, exist_ok=True)
    for c in components:
        try:
            r = verify_component(c, bindings[c['id']])
        except Exception as e:
            r = dict(id=c['id'], passed=False, error_type=type(e).__name__,
                     error='Component verification failed; original files retained')
            result['components'].append(r)
            result['passed'] = False
            out.write_text(json.dumps(result, indent=2) + '\n')
            raise
        result['components'].append(r)
        print(json.dumps(r), flush=True)
    result['passed'] = True
    result['component_count'] = len(components)
    out.write_text(json.dumps(result, indent=2) + '\n')
    return result


def extract(manifest, digest, locations, component_id, output, max_bytes):
    inventory = read_pinned(manifest, digest)
    components = [c for c in inventory['components'] if c['id'] == component_id]
    if len(components) != 1 or components[0]['kind'] != 'file':
        raise ValueError('Extraction requires one archive component')
    c = components[0]
    path = Path(json.loads(Path(locations).read_text())[component_id]['path'])
    check_file(path, c)
    out = Path(output)
    if out.exists():
        raise FileExistsError('Use a fresh extraction directory')
    with tarfile.open(path) as tar:
        members = tar.getmembers()
        names = [str(relative(m.name)) for m in members]
        if len(set(names)) != len(names) or len({n.casefold() for n in names}) != len(names):
            raise ValueError('Duplicate or case-aliased archive member')
        if any(not (m.isfile() or m.isdir()) for m in members):
            raise ValueError('Links and special archive members are not accepted')
        if sum(m.size for m in members) > max_bytes:
            raise ValueError('Extraction exceeds declared disk allowance')
        if any(out.resolve().is_relative_to(p.resolve()) or p.resolve().is_relative_to(out.resolve())
               for p in (path, Path(manifest), Path(locations))):
            raise ValueError('Output overlaps an input')
        out.mkdir(parents=True)
        for m in members:
            dest = out / relative(m.name)
            if m.isdir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(m) as src, dest.open('xb') as dst:
                while block := src.read(1024 * 1024):
                    dst.write(block)
    receipt = dict(component=component_id, archive_sha256=c['sha256'],
                   members=len(members), extracted_bytes=sum(m.size for m in members),
                   new_sampler_calls=0,
                   scope='Safe relocation of pinned archive; use its scientific verifier next')
    out.with_name(out.name + '.extraction.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('verify', 'extract'))
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--locations', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--component')
    p.add_argument('--max-bytes', type=int, default=8 * 1024**3)
    a = p.parse_args()
    if a.action == 'verify':
        verify(a.manifest, a.manifest_sha256, a.locations, a.output)
    else:
        print(json.dumps(extract(a.manifest, a.manifest_sha256, a.locations,
                                 a.component, a.output, a.max_bytes)))
