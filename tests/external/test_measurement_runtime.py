"""Owned measurement tasks are complete without becoming posterior samples."""
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
pytestmark=pytest.mark.skipif(sys.platform!='darwin',reason='Native Mac coordinator')


def test_available_measurement_remains_nonposterior_and_resumes_without_execution(tmp_path):
    from formal_coordinator import TaskCoordinator
    from formal_runtime import file_hash
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys
from pathlib import Path
out=Path(sys.argv[2])
(out/'observations.bin').write_bytes(b'four-measurements-not-posterior')
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',artifact_kind='cache_measurement',measurement_available=True,samples_eligible=False)))
''')
    task=dict(id='measurement',protocol_sha256='unit-measurement',artifact_kind='cache_measurement')
    c=TaskCoordinator(tmp_path/'shared.lock');out=tmp_path/'task'
    result=c.run(task,{},worker,out,1024,2**30)
    assert result['status']=='completed'
    assert result['samples_eligible'] is False
    assert result['measurement_available'] is True
    assert result['history']['summary']['outcome']=='measurement_available'
    before={str(p.relative_to(out)):file_hash(p) for p in out.rglob('*') if p.is_file()}
    resumed=c.run(task,{},worker,out,1024,2**30,resume=True)
    assert not resumed['newly_executed']
    assert before=={str(p.relative_to(out)):file_hash(p) for p in out.rglob('*') if p.is_file()}


def test_measurement_history_is_rejected_by_posterior_inference_analysis(tmp_path):
    from formal_outcomes import analyze_attempt_costs,summarize_attempts
    row=dict(attempt_id='measurement',binding_sha256='same',outcome='measurement_available',
             seconds=1.,artifact_kind='cache_measurement')
    assert summarize_attempts([row])['outcome']=='measurement_available'
    with pytest.raises(ValueError,match='not posterior'):
        analyze_attempt_costs(None,{'method':{0:[row]}})
    with pytest.raises(ValueError,match='valid posterior'):
        summarize_attempts([dict(row,outcome='valid')])


def test_unknown_artifact_kind_is_rejected_before_registering_a_phantom_process(tmp_path):
    from formal_coordinator import TaskCoordinator
    worker=tmp_path/'worker.py'
    worker.write_text('import json,sys\nfrom pathlib import Path\n(Path(sys.argv[2])/"worker-result.json").write_text(json.dumps(dict(status="completed",samples_eligible=True)))')
    c=TaskCoordinator(tmp_path/'lock');out=tmp_path/'out'
    task=dict(id='input-validation',protocol_sha256='unit',artifact_kind='unknown')
    with pytest.raises(ValueError,match='artifact kind'):
        c.run(task,{},worker,out,1024,2**30)
    assert not out.exists()
    task['artifact_kind']='posterior'
    assert c.run(task,{},worker,out,1024,2**30)['status']=='completed'


@pytest.mark.parametrize('declared,reported,eligible',[
    ('cache_measurement','cache_measurement',True),
    ('cache_measurement','posterior',True),
    ('posterior','cache_measurement',False),
])
def test_worker_cannot_switch_artifact_role_or_promote_measurements(tmp_path,declared,reported,eligible):
    from formal_coordinator import TaskCoordinator
    worker=tmp_path/'wrong.py'
    result=dict(status='completed',artifact_kind=reported,samples_eligible=eligible,measurement_available=reported=='cache_measurement')
    worker.write_text('import sys\nfrom pathlib import Path\n(Path(sys.argv[2])/"worker-result.json").write_text('+repr(json.dumps(result))+')\n')
    c=TaskCoordinator(tmp_path/'shared.lock')
    out=c.run(dict(id='mismatch',protocol_sha256='unit',artifact_kind=declared),{},worker,tmp_path/'out',1024,2**30)
    assert out['status']=='interrupted'
    assert out['samples_eligible'] is False and out['measurement_available'] is False
    assert out['history']['summary']['outcome']=='infrastructure_interruption'


def test_interrupted_measurement_is_preserved_without_retrying_warm_replays(tmp_path):
    from formal_coordinator import TaskCoordinator
    from formal_recovery import RecoveryConflict
    from formal_runtime import file_hash
    worker=tmp_path/'exit.py';worker.write_text('import sys;sys.exit(7)')
    c=TaskCoordinator(tmp_path/'lock');out=tmp_path/'original'
    result=c.run(dict(id='interrupted',protocol_sha256='unit',artifact_kind='cache_measurement'),{},worker,out,1024,2**30)
    assert result['status']=='interrupted' and not result['measurement_available']
    before={str(p.relative_to(out)):file_hash(p) for p in out.rglob('*') if p.is_file()}
    with pytest.raises(RecoveryConflict,match='measurement.*retr'):
        c.retry(out,reason='Do not manufacture three successful replays')
    assert before=={str(p.relative_to(out)):file_hash(p) for p in out.rglob('*') if p.is_file()}
    assert not out.with_name(out.name+'.retry').exists()


def test_measurement_memory_guard_retains_resource_failure(tmp_path):
    from formal_coordinator import TaskCoordinator
    worker=tmp_path/'allocate.py'
    worker.write_text('import time\nallocated=bytearray(128*1024**2)\ntime.sleep(2)\n')
    result=TaskCoordinator(tmp_path/'lock').run(
        dict(id='resource',protocol_sha256='unit',artifact_kind='cache_measurement'),
        {},worker,tmp_path/'out',1024,64*1024**2)
    assert result['status']=='failed'
    assert result['history']['summary']['outcome']=='resource_failure'
    assert not result['samples_eligible'] and not result['measurement_available']
    assert result['memory']['sampled_peak_tree_rss_bytes']>64*1024**2


def test_live_measurement_blocks_posterior_work_after_supervisor_loss(tmp_path):
    import os,signal,subprocess,time
    from formal_coordinator import TaskCoordinator,CoordinatorBusy
    def wait(predicate):
        end=time.monotonic()+10
        while not predicate():
            if time.monotonic()>end:raise AssertionError('Fixture observation deadline')
            time.sleep(.01)
    def absent(pid):
        try:os.killpg(pid,0)
        except ProcessLookupError:return True
        return False
    worker=tmp_path/'measure.py';release=tmp_path/'release';out=tmp_path/'measurement';lock=tmp_path/'shared.lock'
    worker.write_text('''import json,sys,time
from pathlib import Path
out=Path(sys.argv[2]);request=json.loads(Path(sys.argv[1]).read_text())
(out/'ready').touch()
while not Path(request['release']).exists():time.sleep(.01)
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',artifact_kind='cache_measurement',samples_eligible=False,measurement_available=True)))
''')
    code='''import sys
sys.path.insert(0,sys.argv[1])
from formal_coordinator import TaskCoordinator
TaskCoordinator(sys.argv[4]).run(dict(id='measure',protocol_sha256='unit',artifact_kind='cache_measurement'),dict(release=sys.argv[5]),sys.argv[2],sys.argv[3],1024,2**30)
'''
    process=subprocess.Popen([sys.executable,'-c',code,str(ROOT/'scripts/completion'),str(worker),str(out),str(lock),str(release)])
    pid=None
    try:
        wait(lambda:(out/'attempt-0001/ready').exists() and (out/'attempt-0001/process.json').exists())
        pid=json.loads((out/'attempt-0001/process.json').read_text())['pid']
        process.kill();process.wait(timeout=3)
        posterior=tmp_path/'posterior.py'
        posterior.write_text('import json,sys\nfrom pathlib import Path\n(Path(sys.argv[2])/"worker-result.json").write_text(json.dumps(dict(status="completed",samples_eligible=True)))')
        c=TaskCoordinator(lock);job=dict(task=dict(id='posterior',protocol_sha256='unit'),request={},worker=posterior,output=tmp_path/'posterior',required_disk_bytes=1024,max_tree_rss_bytes=2**30)
        with pytest.raises(CoordinatorBusy):c.run(**job)
        assert not job['output'].exists()
        release.touch();wait(lambda:absent(pid));pid=None
        assert c.run(**job)['samples_eligible'] is True
        history=c.history(out)
        assert history['summary']['outcome']=='infrastructure_interruption'
        assert history['summary']['total_seconds'] is None
        assert history['attempts'][0]['artifact_kind']=='cache_measurement'
    finally:
        release.touch()
        if process.poll() is None:process.kill();process.wait(timeout=3)
        if pid is not None:
            try:os.killpg(pid,signal.SIGKILL)
            except ProcessLookupError:pass
