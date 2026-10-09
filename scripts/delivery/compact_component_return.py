"""Return one immutable component using one bounded disposable block cache.

The frozen manifest is uploaded first. Each block is emitted, remotely SHA/size
verified, then removed from this tool's own cache. Failures stop the finite
sequence and retain evidence. This tool never samples, retries, replaces assets,
publishes a Release, creates a complete tar, or deletes original members.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/windows'), str(ROOT/'scripts/completion')]
from compact_transfer import load, safe, BUFFER
from formal_runtime import atomic_json, file_hash, fingerprint
from compact_draft_upload import upload


def emit_prepared(root, manifest, manifest_sha256, p, signature, index, output):
    """Same block format, one fully validated metadata map instead of two.

    Rehash the external manifest and in-memory map on every block. Source paths,
    sizes, content hashes and exclusive/partial output rules remain checked.
    Receiver validation is unchanged. This is delivery-only, not frozen sampling.
    """
    if file_hash(manifest) != manifest_sha256 or fingerprint(p) != signature:
        raise ValueError('Prepared transfer manifest changed; no block writes')
    chunk=p['chunks'][index];output=Path(output)
    partial=output.with_name(output.name+'.partial')
    if output.exists() or partial.exists():
        raise FileExistsError('Existing/partial block retained; fresh cache required')
    h=hashlib.sha256()
    with partial.open('xb') as target:
        for seg in chunk['segments']:
            path=safe(root,seg['path'])
            if path.stat().st_size!=p['files'][seg['path']]['bytes']:
                raise ValueError('Source size changed')
            with path.open('rb') as source:
                source.seek(seg['file_offset']);left=seg['bytes']
                while left:
                    data=source.read(min(BUFFER,left))
                    if not data:raise ValueError('Source ended unexpectedly')
                    target.write(data);h.update(data);left-=len(data)
        target.flush();os.fsync(target.fileno())
    if partial.stat().st_size!=chunk['bytes'] or h.hexdigest()!=chunk['sha256']:
        raise ValueError('Source bytes differ from frozen plan; partial retained')
    if file_hash(manifest)!=manifest_sha256:
        raise ValueError('External manifest changed during emission; partial retained')
    partial.rename(output)
    return dict(index=index,bytes=chunk['bytes'],sha256=chunk['sha256'],
        maximum_buffer_bytes=BUFFER,fully_validated_metadata_reused=True)


def remove_acknowledged_cache(path, cache, expected, receipt, asset_name):
    """Only the exact newly emitted block, after remote verification."""
    path, cache = Path(path), Path(cache)
    if path.is_symlink() or cache.is_symlink():
        raise ValueError('Redirected cache file/directory refused')
    path, cache = path.resolve(), cache.resolve()
    if path.parent != cache:
        raise ValueError('Only a direct disposable cache file may be removed')
    if receipt.get('status') != 'verified_additive_upload' or receipt.get('final_draft') is not True:
        raise ValueError('Successful unchanged-draft acknowledgement required')
    matches = [r for r in receipt['appended_or_reused'] if r['name'] == asset_name]
    if len(matches) != 1:
        raise ValueError('Exactly one named remote acknowledgement required')
    remote = matches[0]
    if remote['size'] != expected['bytes'] or remote['digest'] != 'sha256:'+expected['sha256'] or remote['state'] != 'uploaded':
        raise ValueError('Remote size/SHA/state differs; cache retained')
    if path.stat().st_size != expected['bytes'] or file_hash(path) != expected['sha256']:
        raise ValueError('Cache differs after upload; preserve for diagnosis')
    path.unlink()


def return_component(root, manifest, manifest_sha256, prefix, output, *, publisher=upload):
    root, manifest, output = map(lambda x: Path(x).resolve(), (root, manifest, output))
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', prefix):
        raise ValueError('Safe unique component asset prefix required')
    p = load(manifest, manifest_sha256)
    prepared_signature = fingerprint(p)
    if output.exists() or output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError('Fresh, separate administrative output required')
    if p['block_limit_bytes'] > 256*1024**2:
        raise ValueError('This return uses at most one 256 MiB block')
    output.mkdir(parents=True, exist_ok=False)
    cache = output/'cache'; cache.mkdir()
    began = time.perf_counter()
    atomic_json(output/'started.json', dict(root=str(root), manifest=str(manifest),
        manifest_file_sha256=manifest_sha256, asset_prefix=prefix,
        started_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=file_hash(__file__),
        transfer_source_sha256=file_hash(ROOT/'scripts/windows/compact_transfer.py'),
        publisher_source_sha256=file_hash(ROOT/'scripts/delivery/compact_draft_upload.py'),
        whole_tar_created=False, maximum_disposable_block_bytes=256*1024**2,
        automatic_retries=False, new_sampler_calls=0))
    assets = []

    def send(name, path, size, digest, label):
        plan = output/(label+'-asset-plan.json')
        atomic_json(plan, dict(schema='compact-draft-assets-v1', assets=[
            dict(name=name, path=str(path), bytes=size, sha256=digest)]))
        receipt = publisher(plan, file_hash(plan), output/(label+'-upload-receipt.json'))
        asset = dict(local_name=label, release_name=name, bytes=size, sha256=digest,
            remote=receipt['appended_or_reused'][0])
        assets.append(asset)
        atomic_json(output/'progress.json', dict(assets=assets, planned_blocks=len(p['chunks']),
            acknowledged_blocks=sum(a['local_name'].startswith('part-') for a in assets)))
        print(json.dumps(dict(asset=name, bytes=size, remotely_verified=True)), flush=True)
        return receipt

    try:
        send(prefix+'-manifest.json', manifest, manifest.stat().st_size, manifest_sha256, 'manifest')
        for chunk in p['chunks']:
            name = chunk['name']; path = cache/name
            emitted = emit_prepared(root, manifest, manifest_sha256, p, prepared_signature, chunk['index'], path)
            atomic_json(output/(name+'.emit.json'), emitted)
            remote_name = prefix+'-'+name
            receipt = send(remote_name, path, chunk['bytes'], chunk['sha256'], name)
            remove_acknowledged_cache(path, cache, chunk, receipt, remote_name)
            atomic_json(output/(name+'.cache-removed.json'), dict(path=str(path),
                bytes=chunk['bytes'], sha256=chunk['sha256'],
                remote_sha_verified_before_removal=True, original_members_removed=0))
        if file_hash(manifest)!=manifest_sha256 or fingerprint(p)!=prepared_signature:
            raise ValueError('Final component manifest changed')
        result = dict(status='complete_component_remote_sha_verified',
            manifest_file_sha256=manifest_sha256, assets=assets,
            files=len(p['files']), bytes=sum(v['bytes'] for v in p['files'].values()),
            blocks=len(p['chunks']), elapsed_seconds=time.perf_counter()-began,
            original_members_removed=0, whole_tar_created=False,
            fully_validated_metadata_reused=True,
            independent_Mac_receive=False, new_sampler_calls=0)
        atomic_json(output/'finished.json', result)
        return result
    except BaseException as error:
        atomic_json(output/'failed.json', dict(error=type(error).__name__+': '+str(error),
            acknowledged_assets=assets, original_members_preserved=True,
            elapsed_seconds=time.perf_counter()-began, automatic_retries=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root','manifest','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--prefix', required=True)
    result = return_component(**vars(parser.parse_args()))
    print(json.dumps({k: result[k] for k in ('status','files','bytes','blocks')}))
