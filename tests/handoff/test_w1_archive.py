"""W1 final evidence packaging guards; no numerical work is performed."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/analysis'))
import export_w1_evidence as e


def test_archive_stream_verification_and_portable_identity(tmp_path):
    a=tmp_path/'a';a.mkdir();file=a/'sample.json';file.write_text('{"fixture":true}\n')
    meta={'identity':'fixture','uploaded':False}
    receipt=e.write_archive({'nested/sample.json':file},meta,tmp_path/'first.tar')
    assert receipt['verified_members']==2 and receipt['manifest_members']==1
    assert receipt['new_target_evaluations']==0 and not receipt['portable_rebuild_verified']
    with tarfile.open(tmp_path/'first.tar') as archive:
        manifest=json.load(archive.extractfile('MANIFEST.json'))
        assert manifest['files']['nested/sample.json']['sha256']==hashlib.sha256(file.read_bytes()).hexdigest()
        assert set(archive.getnames())=={'nested/sample.json','README.md','MANIFEST.json'}
    b=tmp_path/'relocated';b.mkdir();shutil.copyfile(file,b/'sample.json')
    other=e.write_archive({'nested/sample.json':b/'sample.json'},meta,tmp_path/'second.tar')
    assert other['sha256']==receipt['sha256']
    with pytest.raises(ValueError,match='fresh .tar'):e.write_archive({},meta,tmp_path/'first.tar')


def test_archive_refuses_insufficient_disk_and_preserves_inputs(tmp_path,monkeypatch):
    file=tmp_path/'source';file.write_bytes(b'original')
    monkeypatch.setattr(e.shutil,'disk_usage',lambda p:SimpleNamespace(free=1))
    with pytest.raises(ValueError,match='disk reserve'):
        e.write_archive({'source':file},{},tmp_path/'refused.tar')
    assert file.read_bytes()==b'original' and not (tmp_path/'refused.tar').exists()


def test_changed_input_during_pack_fails_integrity(tmp_path,monkeypatch):
    file=tmp_path/'source';file.write_bytes(b'original')
    original_open=e.tarfile.open
    def changing_open(*args,**kwargs):
        if kwargs.get('mode')=='w':file.write_bytes(b'modified')
        return original_open(*args,**kwargs)
    monkeypatch.setattr(e.tarfile,'open',changing_open)
    with pytest.raises(ValueError,match='archive member differs'):
        e.write_archive({'source':file},{},tmp_path/'failed.tar')
    assert (tmp_path/'failed.tar').exists()
    assert not (tmp_path/'failed.receipt.json').exists()


def test_resume_requires_zero_new_work_and_all_previous_assets(tmp_path):
    with pytest.raises(ValueError,match='zero-work resume'):e.resume_receipts(tmp_path,10)
    calls=tmp_path/'invocations';calls.mkdir();path=calls/'1.json'
    for new,count,reused in [(1,10,True),(0,9,True),(0,10,False)]:
        path.write_text(json.dumps(dict(new_evaluations=new,verified_assets=count,reused_complete=reused)))
        with pytest.raises(ValueError,match='all prior assets'):e.resume_receipts(tmp_path,10)
    path.write_text(json.dumps(dict(new_evaluations=0,verified_assets=10,reused_complete=True)))
    assert e.resume_receipts(tmp_path,10)==[path]


def test_unfinished_work_cannot_be_archived(tmp_path):
    raw=tmp_path/'raw';raw.mkdir()
    with pytest.raises(ValueError,match='completed W1 evidence'):
        e.build(ROOT,raw,tmp_path,tmp_path,tmp_path,tmp_path,tmp_path/'refused.tar')
    assert not (tmp_path/'refused.tar').exists()


def test_relative_inputs_reject_escape_and_symlink(tmp_path):
    root=tmp_path/'root';root.mkdir();file=root/'a';file.write_text('x')
    assert e.relative_file(root,'a')==file
    with pytest.raises(ValueError,match='unsafe'):e.relative_file(root,'../a')
    linked=root/'link';linked.symlink_to(file)
    with pytest.raises(ValueError,match='linked'):e.relative_file(root,'link')
