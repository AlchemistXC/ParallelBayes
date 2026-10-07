"""Manifest/history/index contracts, using files and artificial task exports."""
import copy
import io
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'tests/handoff'),str(ROOT/'scripts/completion')]
from formal_archive import build_index,EvidenceIndex,manifest_records
from formal_runtime import atomic_json,file_hash
from task_journal import TaskJournal
from test_formal_native_evidence import Fixture


def delivery_manifest(root):
    path=root/'WINDOWS-RETURN-MANIFEST.json'
    files={p.relative_to(root).as_posix():dict(bytes=p.stat().st_size,sha256=file_hash(p)) for p in root.rglob('*') if p.is_file() and p!=path}
    atomic_json(path,dict(scope='Artificial integrity fixture, not native execution',source_commit='a'*40,branch='fixture',files=files))
    return file_hash(path)


def native_exports(tmp_path):
    original=tmp_path/'origin';original.mkdir();f=Fixture(original)
    f.task['id']='a'*24;f.add();f.ledger([(3.,'attempt-0001',True)])
    root=tmp_path/'delivery';bundle=root/'validation';bundle.mkdir(parents=True)
    taskroot=bundle/'main/tasks'/f.task['id'];taskroot.parent.mkdir(parents=True)
    shutil.copytree(f.root/'task',taskroot)
    costroot=bundle/'main/call-costs'/f.task['id'];costroot.parent.mkdir(parents=True);shutil.copytree(f.root/'ledger',costroot)
    visits=bundle/'main/visits';(visits/'first').mkdir(parents=True);(visits/'last').mkdir()
    with TaskJournal(tmp_path/'single-journal',f.identity) as journal:
        key=TaskJournal.key(f.task);journal.save(key,f.entry,'fixture-first')
        journal.export(key,visits/'first'/(f.task['id']+'.history.json'))
        f.entry['calls'].append(dict(fixture_only='additional verification'))
        journal.save(key,f.entry,'fixture-second');journal.export(key,visits/'last'/(f.task['id']+'.history.json'))
    return root,bundle,f


def test_streaming_records_cross_chunk_edges_and_unicode(tmp_path):
    path=tmp_path/'manifest.json'
    path.write_text(json.dumps(dict(scope='中文'+'x'*65517,files={'验证/a':dict(bytes=0,sha256='a'*64)}),ensure_ascii=False)+'\n')
    rows=list(manifest_records(path))
    assert rows[1]==('file','验证/a',dict(bytes=0,sha256='a'*64))
    assert rows[0][1]=='scope' and rows[0][2].startswith('中文')


@pytest.mark.parametrize('content',[
    '{"files":{},"files":{}}','{"files":{"a":{"bytes":1,"bytes":2,"sha256":"x"}}}',
    '{"files":{}} garbage','{"files":{"a":','{"files":{"a":{},}}','{"scope":"no files"}'])
def test_ambiguous_or_truncated_manifest_rejected(tmp_path,content):
    p=tmp_path/'bad.json';p.write_text(content)
    with pytest.raises(ValueError):list(manifest_records(p))


def test_relocated_index_selects_event_extension_not_file_time(tmp_path):
    root,bundle,f=native_exports(tmp_path);digest=delivery_manifest(root)
    report=build_index(root,'validation',digest,tmp_path/'index')
    assert report['history_exports']==2
    moved=tmp_path/'moved';shutil.move(root,moved)
    index=EvidenceIndex(moved,tmp_path/'index')
    try:
        assets=index.task_evidence(f.task,'main','main')
        assert assets['history_export'].endswith('last/'+f.task['id']+'.history.json')
        assert assets['history_exports']==2 and assets['ledger']=='main/call-costs/'+f.task['id']
        index.verify_local_files(assets['manifest'])
        unknown=dict(f.task,id='b'*24)
        gap=index.task_evidence(unknown,'main','main')
        assert gap['evidence_status']=='evidence_gap' and gap['history_export'] is None
        assert not gap['known_output_without_export']
        assert index.receipt['numerical_results_validated'] is False
    finally:index.close()


def test_divergent_history_is_not_replaced_by_successful_export(tmp_path):
    root,bundle,f=native_exports(tmp_path)
    path=bundle/'main/visits/last'/(f.task['id']+'.history.json');path.unlink()
    with TaskJournal(tmp_path/'unrelated-journal',f.identity) as journal:
        key=TaskJournal.key(f.task);journal.save(key,f.entry,'divergent');journal.export(key,path)
    build_index(root,'validation',delivery_manifest(root),tmp_path/'index')
    index=EvidenceIndex(root,tmp_path/'index')
    try:
        with pytest.raises(ValueError,match='Conflicting'):index.task_evidence(f.task,'main','main')
    finally:index.close()


def test_unlisted_and_changed_files_and_duplicate_paths_refused(tmp_path):
    root=tmp_path/'delivery';(root/'validation').mkdir(parents=True)
    p=root/'validation/a';p.write_text('a');digest=delivery_manifest(root)
    (root/'validation/extra').write_text('unexpected')
    with pytest.raises(ValueError,match='Unlisted'):build_index(root,'validation',digest,tmp_path/'bad-index')
    (root/'validation/extra').unlink();build_index(root,'validation',digest,tmp_path/'index')
    index=EvidenceIndex(root,tmp_path/'index')
    try:
        p.write_text('b')
        with pytest.raises(ValueError,match='changed'):index.path('a')
    finally:index.close()
    p.write_text('a');manifest=root/'WINDOWS-RETURN-MANIFEST.json';record=json.dumps(dict(bytes=1,sha256=file_hash(p)))
    manifest.write_text('{"files":{"validation/a":'+record+',"validation/a":'+record+'}}')
    with pytest.raises(Exception,match='UNIQUE'):build_index(root,'validation',file_hash(manifest),tmp_path/'duplicate-index')


def test_index_corruption_and_unsafe_paths_do_not_create_a_pass_receipt(tmp_path):
    root=tmp_path/'delivery';(root/'validation').mkdir(parents=True)
    (root/'validation/a').write_text('a');digest=delivery_manifest(root)
    build_index(root,'validation',digest,tmp_path/'index')
    with (tmp_path/'index/files.sqlite3').open('ab') as f:f.write(b'changed')
    with pytest.raises(ValueError,match='index changed'):EvidenceIndex(root,tmp_path/'index')
    atomic_json(root/'WINDOWS-RETURN-MANIFEST.json',dict(files={'../outside':dict(bytes=0,sha256='a'*64)}))
    with pytest.raises(ValueError):build_index(root,'validation',file_hash(root/'WINDOWS-RETURN-MANIFEST.json'),tmp_path/'unsafe-index')
    assert not (tmp_path/'unsafe-index/INDEX.json').exists()
