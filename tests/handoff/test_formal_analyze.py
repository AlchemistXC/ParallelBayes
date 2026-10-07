"""Receiver orchestration with real scientific files, no native execution."""
import copy
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'tests/handoff'),str(ROOT/'scripts/completion')]
from formal_analyze import analyze_frame,AnalysisStore,analyzer_sources
from formal_archive import build_index,EvidenceIndex
from formal_science import ScientificReader
from formal_runtime import fingerprint,file_hash,atomic_json
from batch_contract import create_tasks
from test_formal_science import specimen,RSCRIPT,RLIB
from test_formal_archive import delivery_manifest


class ArtificialFrame:
    """Explicit small fixture; CLI never selects this class."""
    counts=dict(main=2,cache=0)
    def __init__(self,c):
        self.c=copy.deepcopy(c)
        tasks=create_tasks(c['identity'],[dict(models=['G1'],replicates=[0],budgets=[16],workflows=['cpu-rwm-sequential','cpu-rwm-online_picard'])])
        self.tasks=sorted(tasks,key=lambda t:t['executor']!='sequential')
    def receipt(self):return dict(scope='artificial-analysis-orchestration',main_planned=2,cache_planned=0,formal_scientific_repetitions=0)
    def phase_root(self,batch,phase):return 'main'
    def slots(self):
        for i,t in enumerate(self.tasks,1):
            c=copy.deepcopy(self.c);c['task']=t
            yield 0,'main',i,dict(task=dict(t,protocol_sha256=c['protocol_sha256'],artifact_kind='posterior'),capsule=c,capsule_sha256=fingerprint(c),probe=None)


@pytest.fixture
def setup(specimen,tmp_path):
    f,c,_,_=specimen;root=tmp_path/'delivery';bundle=root/'validation'
    shutil.copytree(f.root,bundle);identifier=f.task['id']
    tasks=bundle/'main/tasks';tasks.mkdir(parents=True);shutil.move(bundle/'task',tasks/identifier)
    costs=bundle/'main/call-costs';costs.mkdir();shutil.move(bundle/'ledger',costs/identifier)
    visits=bundle/'main/visits/original';visits.mkdir(parents=True)
    shutil.copyfile(bundle/f.history,visits/(identifier+'.history.json'))
    digest=delivery_manifest(root);build_index(root,'validation',digest,tmp_path/'index')
    index=EvidenceIndex(root,tmp_path/'index');frame=ArtificialFrame(c)
    reader=ScientificReader(bundle,f.sources,rscript=RSCRIPT,r_library=RLIB)
    binding=dict(scope=frame.receipt(),index=index.receipt,analyzer='artificial-orchestration-fixture')
    try:yield index,frame,reader,binding
    finally:index.close()


def test_full_declared_frame_and_resume_do_not_rerun_R_or_replay(setup,tmp_path,monkeypatch):
    index,frame,reader,binding=setup;output=tmp_path/'analysis'
    result=analyze_frame(index,frame,reader,output,binding)
    assert result['visited']==2 and result['new_analyses']==2 and result['evidence_complete'] is False
    assert result['counts']['main']=={'analyzed':1,'evidence_gap':1}
    missing=json.loads((output/'tasks'/frame.tasks[1]['id']/'FRAME.json').read_text())
    assert missing['outcome'] is None and missing['means'] is None and missing['costs'] is None
    before={p.relative_to(output/'tasks').as_posix():file_hash(p) for p in (output/'tasks').rglob('*') if p.is_file()}
    def forbidden(*args,**kwargs):raise AssertionError('Completed receiver must not call numerical/R reader again')
    monkeypatch.setattr(reader,'read',forbidden)
    resumed=analyze_frame(index,frame,reader,output,binding,resume=True)
    assert resumed['new_analyses']==0 and resumed['reused_analyses']==2
    after={p.relative_to(output/'tasks').as_posix():file_hash(p) for p in (output/'tasks').rglob('*') if p.is_file()}
    assert before==after


def test_changed_analysis_environment_and_saved_output_refused(setup,tmp_path):
    index,frame,reader,binding=setup;output=tmp_path/'analysis'
    analyze_frame(index,frame,reader,output,binding)
    with pytest.raises(ValueError,match='identity'):analyze_frame(index,frame,reader,output,dict(binding,environment='changed'),resume=True)
    path=output/'tasks'/frame.tasks[0]['id']/'science/functions/posterior.json';path.write_text('{}')
    with pytest.raises(ValueError,match='Analysis files changed'):analyze_frame(index,frame,reader,output,binding,resume=True)


def test_reader_error_is_not_sampler_failure_and_other_slots_continue(setup,tmp_path,monkeypatch):
    index,frame,reader,binding=setup
    monkeypatch.setattr(reader,'read',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('Artificial receiver failure')))
    output=tmp_path/'analysis';summary=analyze_frame(index,frame,reader,output,binding)
    assert summary['counts']['main']=={'reader_error':1,'evidence_gap':1}
    row=json.loads((output/'tasks'/frame.tasks[0]['id']/'FRAME.json').read_text())
    assert row['outcome'] is None and row['original_outcome_reclassified'] is False
    assert summary['every_planned_task_represented'] and not summary['evidence_complete']


def test_uncommitted_analysis_is_retained_and_not_automatically_restarted(setup,tmp_path,monkeypatch):
    index,frame,reader,binding=setup;output=tmp_path/'analysis';store=AnalysisStore(output,binding);store.close()
    partial=output/'tasks'/frame.tasks[0]['id']/'science';partial.mkdir(parents=True);(partial/'retained.txt').write_text('unfinished receiver output')
    calls=[];monkeypatch.setattr(reader,'read',lambda *a,**kw:calls.append(kw))
    with pytest.raises(ValueError,match='Uncommitted'):analyze_frame(index,frame,reader,output,binding,resume=True)
    assert calls==[] and (partial/'retained.txt').read_text()=='unfinished receiver output'


def test_foreign_analysis_rows_cannot_disappear_from_frame(setup,tmp_path):
    index,frame,reader,binding=setup;output=tmp_path/'analysis'
    analyze_frame(index,frame,reader,output,binding)
    store=AnalysisStore(output,binding,resume=True)
    store.db.execute('INSERT INTO results VALUES (?,?,?,?,?)',('unexpected','{}','evidence_gap','nonexistent','a'*64));store.db.commit();store.close()
    with pytest.raises(ValueError,match='complete planned frame'):analyze_frame(index,frame,reader,output,binding,resume=True)


def test_nested_receipts_and_index_output_are_not_excluded(setup,tmp_path):
    index,frame,reader,binding=setup;output=tmp_path/'analysis'
    with pytest.raises(ValueError,match='separate'):
        analyze_frame(index,frame,reader,index.directory/'analysis',binding)
    analyze_frame(index,frame,reader,output,binding)
    nested=output/'tasks'/frame.tasks[0]['id']/'science/RECEIPT.json';nested.write_text('{}')
    with pytest.raises(ValueError,match='Analysis files changed'):
        analyze_frame(index,frame,reader,output,binding,resume=True)


def test_checked_scalar_projection_retains_unknown_rows_and_rejects_resigned_change(setup,tmp_path):
    from formal_statistics import checked_rows
    index,frame,reader,_=setup;output=tmp_path/'analysis'
    frame.protocol=dict(source_files=reader.sources)
    binding=dict(index=index.receipt,frame=frame.receipt(),scientific_source_files=reader.sources,
        analyzer_sources=analyzer_sources())
    analyze_frame(index,frame,reader,output,binding)
    rows=list(checked_rows(output,frame,index))
    assert [r['disposition'] for r in rows]==['analyzed','evidence_gap']
    assert rows[1]['outcome'] is None and rows[0]['means'] is not None
    atomic_json(output/'identity.json',dict(binding,analyzer_sources={}))
    with pytest.raises(ValueError,match='Receiver source'):
        list(checked_rows(output,frame,index))
    atomic_json(output/'identity.json',binding)
    folder=output/'tasks'/frame.tasks[0]['id'];path=folder/'FRAME.json'
    changed=json.loads(path.read_text());changed['means'][0]+=1.;atomic_json(path,changed)
    receipt_path=folder/'RECEIPT.json';receipt=json.loads(receipt_path.read_text())
    receipt['files']['FRAME.json']=file_hash(path);atomic_json(receipt_path,receipt)
    store=AnalysisStore(output,binding,resume=True)
    store.db.execute('UPDATE results SET sha256=? WHERE id=?',(file_hash(receipt_path),frame.tasks[0]['id']));store.db.commit();store.close()
    with pytest.raises(ValueError,match='Projected scalar'):
        list(checked_rows(output,frame,index))
