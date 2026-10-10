from pathlib import Path
import json
import random
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/followups'))
from nuts_registry import Registry,schedule,CONDITIONS,MODELS
from nuts_runtime import seal,verify


def request(i,phase='main'):return dict(id=str(i),phase=phase,source='fixed-qualification-source')
def terminal():return dict(status='failed',managed_active_processes=0,kernel_terminal_verified=True)


def test_schedule_complete_balanced_deterministic_without_sampling_rng():
    before=random.getstate();a=schedule();assert random.getstate()==before
    assert a==schedule() and len(a)==36 and len({r['id'] for r in a})==36
    for model in MODELS:
        rows=[r for r in a if r['model']==model]
        assert {(r['workers'],r['diagnostics_enabled']) for r in rows}==set(CONDITIONS)
    for index in range(4):
        labels=[(a[row*4+index]['workers'],a[row*4+index]['diagnostics_enabled']) for row in range(9)]
        assert max(labels.count(c) for c in CONDITIONS)-min(labels.count(c) for c in CONDITIONS)<=1


def test_failures_and_unspawned_registrations_consume_durable_total(tmp_path):
    p=tmp_path/'calls.sqlite';r=Registry(p,{'study':'one'})
    for i in range(4):r.register(request(i,'qualification'));r.finish(str(i),terminal())
    for i in range(4,40):r.register(request(i));r.finish(str(i),terminal())
    for i in range(40,48):r.register(request(i,'confirmation'))
    r.close();r=Registry(p,{'study':'one'})
    assert len(r.records())==48
    with pytest.raises(RuntimeError,match='48'):r.register(request('extra','qualification'))
    assert not r.register(request(47,'confirmation'))
    with pytest.raises(ValueError,match='identity'):r.register({**request(47,'confirmation'),'source':'changed'})
    r.close()
    with pytest.raises(ValueError,match='Study identity'):Registry(p,{'study':'other'})


def test_terminal_claim_and_phase_limit_cannot_be_forged_by_status(tmp_path):
    r=Registry(tmp_path/'calls.sqlite',{'study':'one'})
    for i in range(12):r.register(request(i,'qualification'))
    with pytest.raises(RuntimeError,match='Phase'):r.register(request('extra','qualification'))
    with pytest.raises(ValueError,match='termination'):r.finish('0',dict(status='completed'))
    r.finish('0',terminal());r.finish('0',terminal())
    with pytest.raises(ValueError,match='immutable'):r.finish('0',{**terminal(),'status':'completed'})
    r.close()


def test_portable_integrity_rejects_edit_added_file_and_outcome_change(tmp_path):
    p=tmp_path/'draw.npy';p.write_bytes(b'actual-raw-evidence')
    outcome=seal(tmp_path,terminal());assert verify(tmp_path,outcome)==2
    p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='asset differs'):verify(tmp_path,outcome)
    p.write_bytes(b'actual-raw-evidence');extra=tmp_path/'extra';extra.write_text('not in manifest')
    with pytest.raises(ValueError,match='asset set'):verify(tmp_path,outcome)
    extra.unlink()
    with pytest.raises(ValueError,match='outcome differs'):verify(tmp_path,{**outcome,'status':'completed'})
