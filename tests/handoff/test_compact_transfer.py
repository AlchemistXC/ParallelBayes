"""Real bounded byte delivery, unsafe members, missing blocks and crash replay."""
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/windows'),str(ROOT/'scripts/completion')]
from compact_transfer import plan,emit,ingest,verify_received,safe,MAX_BLOCK
from formal_runtime import file_hash


def fixture(tmp_path):
    root=tmp_path/'source';root.mkdir();(root/'sub').mkdir()
    (root/'sub/data.npz').write_bytes(bytes(range(256))*4)
    (root/'small.json').write_text('{"status":"failed","time":null}\n')
    (root/'empty.log').touch()
    manifest=tmp_path/'transfer.json';plan(root,manifest,block_bytes=173)
    return root,manifest,file_hash(manifest),json.loads(manifest.read_text())


def test_bounded_transfer_all_members_zero_replay(tmp_path):
    root,m,h,p=fixture(tmp_path);receiver=tmp_path/'received'
    original={f.relative_to(root).as_posix():file_hash(f) for f in root.rglob('*') if f.is_file()}
    for i,c in enumerate(p['chunks']):
        chunk=tmp_path/c['name'];r=emit(root,m,h,i,chunk)
        assert r['bytes']<=173 and r['maximum_buffer_bytes']<=MAX_BLOCK
        ingest(m,h,i,chunk,receiver)
    receipt=verify_received(m,h,receiver)
    assert receipt['passed'] and receipt['new_sampler_calls']==0 and not receipt['whole_tar_created']
    before={f.relative_to(receiver).as_posix():file_hash(f) for f in receiver.rglob('*') if f.is_file()}
    for i,c in enumerate(p['chunks']):assert ingest(m,h,i,tmp_path/c['name'],receiver)['newly_ingested_bytes']==0
    verify_received(m,h,receiver)
    assert before=={f.relative_to(receiver).as_posix():file_hash(f) for f in receiver.rglob('*') if f.is_file()}
    assert original=={f.relative_to(root).as_posix():file_hash(f) for f in root.rglob('*') if f.is_file()}
    assert all(file_hash(receiver/name)==digest for name,digest in original.items())


def test_missing_corrupt_and_out_of_order_blocks_refused(tmp_path):
    root,m,h,p=fixture(tmp_path);receiver=tmp_path/'received'
    with pytest.raises(ValueError):ingest(m,h,0,tmp_path/'absent',receiver)
    assert not receiver.exists()
    bad=tmp_path/'bad';bad.write_bytes(b'bad')
    with pytest.raises(ValueError):ingest(m,h,0,bad,receiver)
    assert not receiver.exists()
    last=tmp_path/'last';emit(root,m,h,len(p['chunks'])-1,last)
    with pytest.raises(ValueError):ingest(m,h,len(p['chunks'])-1,last,receiver)
    with pytest.raises(ValueError):verify_received(m,h,receiver)


def test_partial_prefix_replay_is_checked_not_truncated(tmp_path):
    root,m,h,p=fixture(tmp_path);receiver=tmp_path/'received'
    chunk=tmp_path/'chunk';emit(root,m,h,0,chunk)
    # Simulate a real interrupted append before the per-block receipt was sealed.
    from compact_transfer import _state
    _state(receiver,p,h)
    seg=p['chunks'][0]['segments'][0];target=receiver/seg['path'];target.parent.mkdir(parents=True,exist_ok=True)
    partial=target.with_name(target.name+'.partial')
    raw=chunk.read_bytes();partial.write_bytes(raw[:7])
    ingest(m,h,0,chunk,receiver)
    assert json.loads((receiver.with_name(receiver.name+'.receive-state')/'progress.json').read_text())['completed_chunks']==1
    # A foreign receiver is never overwritten, even with a valid incoming block.
    other=tmp_path/'foreign';_state(other,p,h);target=other/seg['path'];target.parent.mkdir(parents=True,exist_ok=True)
    partial=target.with_name(target.name+'.partial');partial.write_bytes(b'changed')
    before=partial.read_bytes()
    with pytest.raises(ValueError):ingest(m,h,0,chunk,other)
    assert partial.read_bytes()==before


@pytest.mark.parametrize('name',['../escape','/absolute','C:/secret','a\\b','a/../x','NUL.txt','a.','AUX/x','x:stream'])
def test_member_path_refusal(tmp_path,name):
    with pytest.raises(ValueError):safe(tmp_path,name)


def test_source_tamper_and_existing_destination_retained(tmp_path):
    root,m,h,p=fixture(tmp_path);(root/'sub/data.npz').write_bytes(b'x'*1024)
    with pytest.raises(ValueError):emit(root,m,h,len(p['chunks'])-1,tmp_path/'block')
    assert (tmp_path/'block.partial').exists()
    with pytest.raises(ValueError):plan(root,tmp_path/'large.json',block_bytes=MAX_BLOCK+1)
@pytest.mark.parametrize('index',[-1,True,9999])
def test_invalid_block_index_refused(tmp_path,index):
    root=tmp_path/'source';root.mkdir();(root/'a').write_bytes(b'a')
    manifest=tmp_path/'manifest.json';plan(root,manifest,block_bytes=8)
    digest=file_hash(manifest)
    with pytest.raises(ValueError):emit(root,manifest,digest,index,tmp_path/'part')
    with pytest.raises(ValueError):ingest(manifest,digest,index,tmp_path/'part',tmp_path/'received')

