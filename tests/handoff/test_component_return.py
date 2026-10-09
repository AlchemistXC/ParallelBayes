"""Artificial bounded-return safety checks, never scientific repetitions."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/delivery'))
from compact_component_return import remove_acknowledged_cache, return_component, emit_prepared
from compact_transfer import plan, load, emit
from formal_runtime import fingerprint


def receipt(name, size, digest):
    return dict(status='verified_additive_upload', final_draft=True,
        appended_or_reused=[dict(name=name,size=size,digest='sha256:'+digest,state='uploaded')])


def cache_file(tmp_path):
    cache=tmp_path/'cache';cache.mkdir();file=cache/'part-000000.bin';file.write_bytes(b'evidence')
    expected=dict(bytes=file.stat().st_size,sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    return cache,file,expected


def test_only_acknowledged_disposable_file_removed(tmp_path):
    cache,file,expected=cache_file(tmp_path)
    original=tmp_path/'original.bin';original.write_bytes(file.read_bytes())
    remove_acknowledged_cache(file,cache,expected,receipt('block',expected['bytes'],expected['sha256']),'block')
    assert not file.exists() and original.read_bytes()==b'evidence'


@pytest.mark.parametrize('change', ['digest','state','draft','name'])
def test_wrong_acknowledgement_retains_cache(tmp_path,change):
    cache,file,expected=cache_file(tmp_path);r=receipt('block',expected['bytes'],expected['sha256'])
    if change=='draft':r['final_draft']=False
    else:r['appended_or_reused'][0][change]=('other' if change=='name' else 'wrong')
    with pytest.raises(ValueError):remove_acknowledged_cache(file,cache,expected,r,'block')
    assert file.read_bytes()==b'evidence'


def test_original_outside_cache_cannot_be_removed(tmp_path):
    cache,file,expected=cache_file(tmp_path)
    with pytest.raises(ValueError):remove_acknowledged_cache(file,tmp_path/'other',expected,
        receipt('block',expected['bytes'],expected['sha256']),'block')
    assert file.exists()


def test_small_component_streams_once_and_keeps_originals(tmp_path):
    root=tmp_path/'original';root.mkdir();(root/'data').write_bytes(b'0123456789')
    manifest=tmp_path/'manifest.json';summary=plan(root,manifest,block_bytes=4)
    calls=[]
    def publisher(asset_plan,digest,output):
        assert hashlib.sha256(asset_plan.read_bytes()).hexdigest()==digest
        item=json.loads(asset_plan.read_text())['assets'][0]
        assert len(list((tmp_path/'return/cache').iterdir()))<=1
        assert Path(item['path']).read_bytes()
        calls.append(item['name'])
        r=receipt(item['name'],item['bytes'],item['sha256']);output.write_text(json.dumps(r))
        return r
    result=return_component(root,manifest,summary['manifest_file_sha256'],'fixture',tmp_path/'return',publisher=publisher)
    assert result['blocks']==3 and len(calls)==4
    assert not list((tmp_path/'return/cache').iterdir())
    assert (root/'data').read_bytes()==b'0123456789'


def test_upload_failure_stops_preserving_block_and_original(tmp_path):
    root=tmp_path/'original';root.mkdir();(root/'data').write_bytes(b'0123456789')
    manifest=tmp_path/'manifest.json';summary=plan(root,manifest,block_bytes=4)
    def publisher(asset_plan,digest,output):
        item=json.loads(asset_plan.read_text())['assets'][0]
        if item['name'].endswith('.bin'):raise RuntimeError('injected unavailable transport')
        return receipt(item['name'],item['bytes'],item['sha256'])
    with pytest.raises(RuntimeError):return_component(root,manifest,summary['manifest_file_sha256'],
        'fixture',tmp_path/'return',publisher=publisher)
    assert (root/'data').read_bytes()==b'0123456789'
    assert (tmp_path/'return/cache/part-000000.bin').read_bytes()==b'0123'
    assert (tmp_path/'return/failed.json').is_file()


def test_prepared_emitter_bytes_match_frozen_emitter(tmp_path):
    root=tmp_path/'original';root.mkdir();(root/'data').write_bytes(b'0123456789')
    manifest=tmp_path/'manifest.json';summary=plan(root,manifest,block_bytes=4)
    digest=summary['manifest_file_sha256'];p=load(manifest,digest);signature=fingerprint(p)
    for i in range(3):
        old=tmp_path/f'old-{i}';new=tmp_path/f'new-{i}'
        emit(root,manifest,digest,i,old)
        emit_prepared(root,manifest,digest,p,signature,i,new)
        assert old.read_bytes()==new.read_bytes()


@pytest.mark.parametrize('which', ['file','memory'])
def test_prepared_manifest_tampering_refused_before_writes(tmp_path,which):
    root=tmp_path/'original';root.mkdir();(root/'data').write_bytes(b'0123456789')
    manifest=tmp_path/'manifest.json';summary=plan(root,manifest,block_bytes=4)
    digest=summary['manifest_file_sha256'];p=load(manifest,digest);signature=fingerprint(p)
    if which=='file':manifest.write_bytes(manifest.read_bytes()+b' ')
    else:p['chunks'][0]['sha256']='0'*64
    out=tmp_path/'block'
    with pytest.raises(ValueError):emit_prepared(root,manifest,digest,p,signature,0,out)
    assert not out.exists() and not out.with_name('block.partial').exists()


def test_prepared_emitter_preserves_changed_source_partial(tmp_path):
    root=tmp_path/'original';root.mkdir();(root/'data').write_bytes(b'0123456789')
    manifest=tmp_path/'manifest.json';summary=plan(root,manifest,block_bytes=4)
    digest=summary['manifest_file_sha256'];p=load(manifest,digest);signature=fingerprint(p)
    (root/'data').write_bytes(b'changed!!!')
    out=tmp_path/'block'
    with pytest.raises(ValueError):emit_prepared(root,manifest,digest,p,signature,0,out)
    assert not out.exists() and out.with_name('block.partial').exists()
    assert (root/'data').read_bytes()==b'changed!!!'
