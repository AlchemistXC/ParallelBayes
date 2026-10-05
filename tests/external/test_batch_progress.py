"""A retained interrupted task must not prevent unrelated queued work."""
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_exhausted_task_is_retained_while_next_task_executes(tmp_path):
    from measured_coordinator import MeasuredCoordinator
    from batch_progress import advance
    from formal_runtime import file_hash
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys
from pathlib import Path
request=json.loads(Path(sys.argv[1]).read_text()); out=Path(sys.argv[2])
if request['interrupt']:sys.exit(7)
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True)))
''')
    c=MeasuredCoordinator(tmp_path/'host.lock',tmp_path/'calls')
    job=dict(task=dict(id='unavailable',protocol_sha256='fixture'),request=dict(interrupt=True),
             worker=worker,output=tmp_path/'unavailable',required_disk_bytes=0,max_tree_rss_bytes=2**30)
    assert c.run(**job)['status']=='interrupted'
    assert c.retry(job['output'],reason='One explicit fixture retry')['status']=='interrupted'
    before={str(p.relative_to(tmp_path)):file_hash(p) for folder in (job['output'],job['output'].with_name('unavailable.retry')) for p in folder.rglob('*') if p.is_file()}
    result=advance(c,job)
    assert result['status']=='interrupted' and result['samples_eligible'] is False
    assert result['operation']=='retain_without_reexecution'
    assert result['retry_available'] is False and not result['newly_executed']
    assert result['costs']['actual_attempts']==2
    assert result['costs']['recorded_invocations']==2
    following=dict(job,task=dict(id='following',protocol_sha256='fixture'),request=dict(interrupt=False),output=tmp_path/'following')
    assert advance(c,following)['status']=='completed'
    assert c.report(job['output'])['recorded_invocations']==2
    assert before=={str(p.relative_to(tmp_path)):file_hash(p) for folder in (job['output'],job['output'].with_name('unavailable.retry')) for p in folder.rglob('*') if p.is_file()}
    # A skipped call must validate its requested identity too.
    with pytest.raises(ValueError,match='identity'):
        advance(c,dict(job,request=dict(interrupt=False)))
    assert not job['output'].with_name('unavailable.retry.retry').exists()


def test_unsealed_task_requires_actual_group_absence_before_advancing(tmp_path):
    import json,os,signal,subprocess,time
    from batch_progress import advance
    from measured_coordinator import MeasuredCoordinator
    from formal_coordinator import CoordinatorBusy
    def wait_for(predicate):
        deadline=time.monotonic()+8
        while not predicate():
            if time.monotonic()>deadline:raise AssertionError('Owned fixture did not reach expected lifecycle')
            time.sleep(.02)
    def absent(pid):
        try:os.killpg(pid,0);return False
        except ProcessLookupError:return True
    worker=tmp_path/'worker.py';release=tmp_path/'release'
    worker.write_text('''import json,sys,time
from pathlib import Path
request=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2])
if request.get('release'):
 (out/'ready').write_text('ready')
 while not Path(request['release']).exists():time.sleep(.02)
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True)))
''')
    job=dict(task=dict(id='lost-supervisor',protocol_sha256='fixture'),request=dict(release=str(release)),
             worker=worker,output=tmp_path/'lost',required_disk_bytes=0,max_tree_rss_bytes=2**30)
    manifest={k:str(v) if isinstance(v,Path) else v for k,v in job.items()}
    plan=tmp_path/'job.json';plan.write_text(json.dumps(manifest))
    script=tmp_path/'driver.py'
    script.write_text('''import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from measured_coordinator import MeasuredCoordinator
root=Path(sys.argv[2]);job=json.loads((root/'job.json').read_text())
MeasuredCoordinator(root/'host.lock',root/'calls').run(**job)
''')
    c=MeasuredCoordinator(tmp_path/'host.lock',tmp_path/'calls')
    with (tmp_path/'driver.log').open('wb') as log:
        driver=subprocess.Popen([sys.executable,str(script),str(ROOT/'scripts/completion'),str(tmp_path)],stdout=log,stderr=subprocess.STDOUT)
        pid=None
        try:
            wait_for(lambda:(job['output']/'attempt-0001/ready').exists())
            pid=json.loads((job['output']/'attempt-0001/process.json').read_text())['pid']
            driver.kill();driver.wait(timeout=5)
            with pytest.raises(CoordinatorBusy,match='live'):
                advance(c,job)
            release.write_text('owned worker may finish')
            wait_for(lambda:absent(pid));pid=None
            result=advance(c,job)
            assert result['status']=='interrupted' and not result['samples_eligible']
            assert result['costs']['complete_invocation_seconds'] is None
            assert result['costs']['unfinished_invocations']==1
            assert result['retry_available'] and not result['newly_executed']
            following=dict(job,task=dict(id='next',protocol_sha256='fixture'),request={},output=tmp_path/'next')
            assert advance(c,following)['status']=='completed'
            assert not (job['output']/'state.json').exists()
            assert not job['output'].with_name('lost.retry').exists()
        finally:
            release.write_text('cleanup')
            if driver.poll() is None:driver.kill();driver.wait(timeout=5)
            if pid is not None:
                try:os.killpg(pid,signal.SIGKILL)
                except ProcessLookupError:pass
