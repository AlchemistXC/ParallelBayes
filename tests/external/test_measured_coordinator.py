"""External timing retains interruptions, explicit recovery and verification."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_interrupted_and_retried_task_retains_all_measured_calls(tmp_path):
    from measured_coordinator import MeasuredCoordinator
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys,time
from pathlib import Path
out=Path(sys.argv[2]);time.sleep(.04)
if not out.parent.name.endswith('.retry'):sys.exit(7)
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True)))
''')
    task=dict(id='artificial-two-attempts',protocol_sha256='fixture-protocol')
    job=dict(task=task,request={},worker=worker,output=tmp_path/'task',required_disk_bytes=1024,max_tree_rss_bytes=2**30)
    measured=MeasuredCoordinator(tmp_path/'host.lock',tmp_path/'costs')
    assert measured.run(**job)['status']=='interrupted'
    assert measured.retry(job['output'],reason='Intentional process-exit fixture')['status']=='completed'
    assert not measured.run(**job,resume=True)['newly_executed']
    report=measured.report(job['output'])
    assert report['outcome']=='valid' and report['actual_attempts']==2
    assert report['recorded_invocations']==3 and report['verification_only_invocations']==1
    assert report['unfinished_invocations']==report['attempts_missing_outer_measurement']==0
    assert report['complete_invocation_seconds']>=.08
    assert report['by_action']['run']['calls']==2 and report['by_action']['retry']['calls']==1
    assert report['by_action']['retry']['known_seconds']>.04
    assert report['attempts_are_statistical_replicates'] is False
    assert [r['outcome'] for r in report['history']['attempts']]==['infrastructure_interruption','valid']
    # Loss-injection fixture: preserve the receipt elsewhere, then verify that
    # the shorter successful resume cannot stand in for the missing outer time.
    lost=Path(report['ledger_directory'])/'call-000000/finished.json'
    lost.rename(tmp_path/'retained-original-timing.json')
    uncertain=measured.report(job['output'])
    assert uncertain['complete_invocation_seconds'] is None
    assert uncertain['unfinished_invocations']==1
    assert uncertain['attempts_missing_outer_measurement']==1
    assert uncertain['known_invocation_seconds']>0 and not uncertain['unknown_time_imputed']


def test_prelaunch_resource_refusal_retains_measured_cost_without_an_attempt(tmp_path):
    import pytest
    from formal_runtime import ResourceWait
    from measured_coordinator import MeasuredCoordinator
    worker=tmp_path/'never-run.py';worker.write_text("raise AssertionError('Sampler must not launch')\n")
    c=MeasuredCoordinator(tmp_path/'host.lock',tmp_path/'costs')
    with pytest.raises(ResourceWait):
        c.run(task=dict(id='resource-refusal',protocol_sha256='fixture-protocol'),request={},worker=worker,
              output=tmp_path/'refused',required_disk_bytes=10**18,max_tree_rss_bytes=2**30)
    report=c.report(tmp_path/'refused')
    assert report['actual_attempts']==0 and report['outcome']=='not_run'
    assert report['recorded_invocations']==1 and report['complete_invocation_seconds']>0
    assert report['calls'][0]['error']['type']=='ResourceWait'
    assert not (tmp_path/'refused').exists()
