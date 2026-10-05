"""Batch preparation/archive work remains distinct from fitted-task costs."""
from pathlib import Path
import sys
import hashlib
import json
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_planned_batch_work_keeps_failed_pending_and_successful_costs(tmp_path):
    from batch_cost_ledger import BatchCostLedger,read_batch_costs
    spec=dict(study_identity='batch-cost-artificial-fixture',design_sha256='a'*64,
        operations=[dict(id='prepare',stage='input_preparation'),dict(id='pack',stage='archive'),
                    dict(id='transfer',stage='transfer'),dict(id='verify',stage='verification')])
    ledger=BatchCostLedger(tmp_path/'costs',spec,tmp_path/'host.lock')
    data=tmp_path/'input.bin'
    result=ledger.run('prepare',lambda:(data.write_bytes(b'actual fixture input'),
        {'sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'bytes':data.stat().st_size})[1])
    assert result['outcome']=='completed' and result['seconds']>=0
    def fail_archive():
        raise OSError('intentional archive-write fixture')
    with pytest.raises(OSError,match='intentional'):
        ledger.run('pack',fail_archive)
    report=read_batch_costs(tmp_path/'costs')
    assert [x['outcome'] for x in report['operations']]==['completed','failed','not_run','not_run']
    assert report['known_seconds']>=0 and report['complete_seconds'] is None
    assert report['planned_operations']==4 and report['finished_operations']==2
    assert report['unrecorded_operations']==2
    assert report['per_fit_cost_allocation'] is None and not report['proves_process_termination']
    assert report['operations'][0]['result']['bytes']==20
    before=report
    with pytest.raises(ValueError,match='recorded'):
        ledger.run('prepare',lambda:pytest.fail('Must not redo input creation'))
    assert read_batch_costs(tmp_path/'costs')==before
    changed=dict(spec,design_sha256='b'*64)
    with pytest.raises(ValueError,match='identity'):
        BatchCostLedger(tmp_path/'costs',changed,tmp_path/'host.lock')


def test_abrupt_recorder_exit_remains_unknown_after_other_batch_work(tmp_path):
    import subprocess
    import os
    import shutil
    from batch_cost_ledger import BatchCostLedger,read_batch_costs
    spec=dict(study_identity='abrupt-cost-fixture',design_sha256='c'*64,
        operations=[dict(id='lost',stage='archive'),dict(id='check',stage='verification')])
    request=tmp_path/'request.json';request.write_text(json.dumps(spec))
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from batch_cost_ledger import BatchCostLedger
spec=json.loads(Path(sys.argv[2]).read_text())
ledger=BatchCostLedger(sys.argv[3],spec,sys.argv[4])
ledger.run('lost',lambda:os._exit(7))
''')
    env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run([sys.executable,str(worker),str(ROOT/'scripts/completion'),str(request),
        str(tmp_path/'costs'),str(tmp_path/'host.lock')],env=env)
    assert result.returncode==7  # Actual child is terminal; no stale marker inference.
    ledger=BatchCostLedger(tmp_path/'costs',spec,tmp_path/'host.lock')
    ledger.run('check',lambda:{'original_retained':True})
    report=read_batch_costs(tmp_path/'costs')
    assert report['unfinished_operations']==1 and report['unrecorded_operations']==0
    assert report['operations'][0]['seconds'] is None
    assert report['complete_seconds'] is None and report['known_seconds']>0
    with pytest.raises(ValueError,match='recorded'):
        ledger.run('lost',lambda:pytest.fail('An unfinished operation cannot be overwritten'))
    shutil.copytree(tmp_path/'costs',tmp_path/'relocated')
    assert read_batch_costs(tmp_path/'relocated')==report
