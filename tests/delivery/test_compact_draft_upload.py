"""Network-free delivery safety tests; not scientific repeats or native acceptance."""
import hashlib
import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

spec=importlib.util.spec_from_file_location('compact_draft_upload',
    Path(__file__).resolve().parents[2]/'scripts/delivery/compact_draft_upload.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Remote:
    def __init__(self, count=0, draft=True):
        self.release=dict(id=module.RELEASE_ID,tag_name=module.TAG,draft=draft,
            target_commitish='original-target',html_url='https://github.com/example/draft',
            upload_url=f'https://uploads.github.com/repos/{module.REPO}/releases/{module.RELEASE_ID}/assets{{?name,label}}')
        self.assets=[dict(id=i+1,name=f'old-{i:03d}.bin',size=1,state='uploaded',digest='sha256:'+'1'*64) for i in range(count)]
        self.calls=[]
        self.corrupt_upload=False
        self.change_original=False

    def __call__(self, method, url, path=None):
        module.validate_endpoint(method,url)
        self.calls.append((method,url))
        parsed=urlsplit(url)
        if method=='POST':
            name=parse_qs(parsed.query)['name'][0]
            asset=dict(id=max([a['id'] for a in self.assets],default=0)+1,name=name,
                size=Path(path).stat().st_size,state='uploaded',
                digest='sha256:'+('0'*64 if self.corrupt_upload else module.sha(path)))
            self.assets.append(asset)
            if self.change_original:self.assets[0]['digest']='sha256:'+'9'*64
            return dict(asset)
        if parsed.path.endswith('/assets'):
            page=int(parse_qs(parsed.query)['page'][0])
            return [dict(a) for a in self.assets[(page-1)*100:page*100]]
        return dict(self.release)

    @property
    def posts(self):return sum(method=='POST' for method,_ in self.calls)


def plan(tmp_path, name='compact-test.bin'):
    raw=tmp_path/'raw.bin';raw.write_bytes(b'raw evidence only')
    item=dict(name=name,path=str(raw),bytes=raw.stat().st_size,sha256=module.sha(raw))
    path=tmp_path/'assets.json'
    path.write_text(json.dumps(dict(schema='compact-draft-assets-v1',assets=[item])))
    return path,module.sha(path),item


@pytest.mark.parametrize('method,url',[
    ('PATCH',f'{module.API}/releases/{module.RELEASE_ID}'),
    ('DELETE',f'{module.API}/releases/{module.RELEASE_ID}/assets'),
    ('POST',f'{module.API}/releases/{module.RELEASE_ID}'),
    ('GET','https://api.github.com/repos/unrelated/repo/releases/1'),
    ('POST',f'http://uploads.github.com/repos/{module.REPO}/releases/{module.RELEASE_ID}/assets'),
    ('GET',f'https://token@api.github.com/repos/{module.REPO}/releases/{module.RELEASE_ID}'),
])
def test_endpoint_scope_refuses_publication_replacement_and_foreign_hosts(method,url):
    with pytest.raises(ValueError):module.validate_endpoint(method,url)


def test_paginated_inventory_and_verified_append(tmp_path):
    p,h,_=plan(tmp_path);remote=Remote(count=105)
    r=module.upload(p,h,tmp_path/'receipt.json',request=remote)
    assert r['status']=='verified_additive_upload' and r['previous_assets_unchanged']
    assert len(r['previous_assets'])==105 and len(remote.assets)==106 and remote.posts==1
    assert any('page=2' in url for _,url in remote.calls)
    assert r['maximum_copy_buffer_bytes']==1024**2 and not r['credentials_persisted']


def test_public_release_refuses_before_mutation(tmp_path):
    p,h,_=plan(tmp_path);remote=Remote(draft=False)
    with pytest.raises(ValueError,match='unchanged draft'):module.upload(p,h,tmp_path/'receipt.json',request=remote)
    assert remote.posts==0


def test_changed_local_bytes_refuse_before_network(tmp_path):
    p,h,item=plan(tmp_path);Path(item['path']).write_bytes(b'changed')
    remote=Remote()
    with pytest.raises(ValueError,match='Local asset'):module.upload(p,h,tmp_path/'receipt.json',request=remote)
    assert remote.calls==[]


def test_existing_mismatched_remote_is_not_replaced(tmp_path):
    p,h,item=plan(tmp_path);remote=Remote()
    remote.assets=[dict(id=12,name=item['name'],size=item['bytes'],state='uploaded',digest='sha256:'+'0'*64)]
    out=tmp_path/'receipt.json'
    with pytest.raises(ValueError,match='never replace'):module.upload(p,h,out,request=remote)
    assert remote.posts==0 and remote.assets[0]['id']==12
    assert json.loads(out.read_text())['status']=='failed_originals_preserved'


def test_identical_remote_is_reused_without_writes(tmp_path):
    p,h,item=plan(tmp_path);remote=Remote()
    remote.assets=[dict(id=12,name=item['name'],size=item['bytes'],state='uploaded',digest='sha256:'+item['sha256'])]
    r=module.upload(p,h,tmp_path/'receipt.json',request=remote)
    assert remote.posts==0 and r['appended_or_reused'][0]['reused'] is True


def test_case_alias_refuses_before_append(tmp_path):
    p,h,item=plan(tmp_path);remote=Remote()
    remote.assets=[dict(id=12,name=item['name'].upper(),size=item['bytes'],state='uploaded',digest='sha256:'+item['sha256'])]
    with pytest.raises(ValueError,match='case-alias'):module.upload(p,h,tmp_path/'receipt.json',request=remote)
    assert remote.posts==0


def test_original_remote_change_invalidates_receipt(tmp_path):
    p,h,_=plan(tmp_path);remote=Remote(count=1);remote.change_original=True
    with pytest.raises(ValueError,match='previous remote asset changed'):module.upload(p,h,tmp_path/'receipt.json',request=remote)
    assert remote.posts==1


def test_corrupt_upload_digest_is_retained_as_failure(tmp_path):
    p,h,_=plan(tmp_path);remote=Remote();remote.corrupt_upload=True
    out=tmp_path/'receipt.json'
    with pytest.raises(ValueError,match='never replace'):module.upload(p,h,out,request=remote)
    assert remote.posts==1 and len(remote.assets)==1
    assert json.loads(out.read_text())['status']=='failed_originals_preserved'


def test_old_receipt_is_not_overwritten(tmp_path):
    p,h,_=plan(tmp_path);remote=Remote();out=tmp_path/'receipt.json';out.write_bytes(b'original receipt')
    with pytest.raises(FileExistsError):module.upload(p,h,out,request=remote)
    assert remote.calls==[] and out.read_bytes()==b'original receipt'
