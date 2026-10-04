"""Explicit recovery preserves interruption history and actual inputs."""
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


@pytest.mark.skipif(sys.platform!='darwin',reason='Native Mac process-group recovery profile')
def test_interrupted_attempt_is_sealed_then_retried_once_with_identical_request(tmp_path):
    from formal_runtime import execute_task, file_hash
    from formal_recovery import recover_task, retry_task, RecoveryConflict
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys
from pathlib import Path
request=Path(sys.argv[1]).read_bytes(); out=Path(sys.argv[2])
(out/'actual-request.bin').write_bytes(request)
if out.parent.name=="initial":
    (out/'partial.bin').write_bytes(b"keep partial")
    sys.exit(7)
(out/'worker-result.json').write_text(json.dumps(dict(status="completed",samples_eligible=True)))
''')
    original=tmp_path/'initial';lock=tmp_path/'host.lock'
    request=dict(actual_noise=[1.,-2.,.25],initial=[0.,0.],scope='technical fixture')
    first=execute_task(dict(id='retry-fixture'),request,worker,original,lock,1024,2**30)
    assert first['status']=='interrupted'
    before={str(p.relative_to(original)):file_hash(p) for p in original.rglob('*') if p.is_file()}
    recovery=recover_task(original,host_lock=lock,reason='Injected worker exit after preserved partial output')
    assert recovery['outcome']=='infrastructure_interruption'
    assert recovery['cost_seconds']>0 and not recovery['samples_eligible']
    result=retry_task(original,host_lock=lock)
    assert result['status']=='completed' and result['newly_executed']
    retry=Path(recovery['retry_output'])
    assert (retry/'attempt-0001/actual-request.bin').read_bytes()==(original/'attempt-0001/actual-request.bin').read_bytes()
    assert before=={str(p.relative_to(original)):file_hash(p) for p in original.rglob('*') if p.is_file()}
    replay=retry_task(original,host_lock=lock)
    assert replay['resumed'] and not replay['newly_executed']
    with pytest.raises(RecoveryConflict,match='completed'):
        recover_task(retry,host_lock=lock,reason='Must not redo completed output')
    (original/'attempt-0001/partial.bin').write_bytes(b'changed')
    with pytest.raises(RecoveryConflict,match='changed'):
        retry_task(original,host_lock=lock)


@pytest.mark.skipif(sys.platform!='darwin',reason='Native Mac process-group recovery profile')
def test_lost_supervisor_does_not_make_live_worker_safe_to_retry(tmp_path):
    import os
    import signal
    import subprocess
    import time
    from formal_recovery import recover_task, LiveAttempt
    worker=tmp_path/'orphan-worker.py'
    worker.write_text('''import json,sys,time
from pathlib import Path
out=Path(sys.argv[2]);request=json.loads(Path(sys.argv[1]).read_text())
(out/'ready').write_text('ready')
deadline=time.monotonic()+15
while not Path(request['release']).exists() and time.monotonic()<deadline:time.sleep(.01)
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True)))
''')
    original=tmp_path/'orphan';lock=tmp_path/'host.lock';release=tmp_path/'release'
    script='''import sys
sys.path.insert(0,sys.argv[1])
from formal_runtime import execute_task
execute_task({'id':'supervisor-loss-fixture'},{'release':sys.argv[5]},sys.argv[2],sys.argv[3],sys.argv[4],1024,2**30)
'''
    driver=subprocess.Popen([sys.executable,'-c',script,str(ROOT/'scripts/completion'),str(worker),str(original),str(lock),str(release)],
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    pid=None
    try:
        deadline=time.monotonic()+10
        while not (original/'attempt-0001/ready').exists():
            if driver.poll() is not None:raise AssertionError(driver.communicate()[1].decode())
            if time.monotonic()>deadline:raise AssertionError('Fixture worker not ready')
            time.sleep(.01)
        pid=json.loads((original/'attempt-0001/process.json').read_text())['pid']
        driver.kill();driver.wait(timeout=3)
        with pytest.raises(LiveAttempt,match='live'):
            recover_task(original,host_lock=lock,reason='Supervisor intentionally killed while worker lives')
        assert not original.with_name(original.name+'.recovery').exists()
        release.write_text('release owned fixture')
        deadline=time.monotonic()+10
        while True:
            try:os.killpg(pid,0)
            except ProcessLookupError:
                pid=None
                break
            if time.monotonic()>deadline:raise AssertionError('Owned fixture group did not finish')
            time.sleep(.01)
        record=recover_task(original,host_lock=lock,reason='Owned worker group observed absent after supervisor loss')
        assert record['original_status']=='unsealed'
        assert record['cost_seconds'] is None
        assert not record['samples_eligible']
        assert (original/'attempt-0001/worker-result.json').exists()
        assert not (original/'state.json').exists()
    finally:
        release.write_text('fixture cleanup')
        if driver.poll() is None:driver.kill();driver.wait(timeout=3)
        if pid is not None:
            try:os.killpg(pid,signal.SIGKILL)
            except ProcessLookupError:pass


@pytest.mark.skipif(sys.platform!='darwin',reason='Native Mac process-group recovery profile')
def test_numerical_and_resource_failures_cannot_be_retried_as_infrastructure(tmp_path):
    from formal_runtime import execute_task
    from formal_recovery import recover_task, RecoveryConflict
    worker=tmp_path/'failed-worker.py'
    worker.write_text('''import json,sys,time
from pathlib import Path
time.sleep(.15)
(Path(sys.argv[2])/'worker-result.json').write_text(json.dumps(dict(status='failed',samples_eligible=False)))
''')
    lock=tmp_path/'host.lock'
    for name,limit in [('numerical',2**30),('resource',1)]:
        result=execute_task({'id':name},{},worker,tmp_path/name,lock,1024,limit)
        assert result['status']=='failed'
        with pytest.raises(RecoveryConflict,match='failed'):
            recover_task(tmp_path/name,host_lock=lock,reason='Forbidden attempt to replace failed output')
        assert not (tmp_path/(name+'.recovery')).exists()


@pytest.mark.skipif(sys.platform!='darwin',reason='Native Mac process-group recovery profile')
def test_unsealed_failed_worker_output_cannot_be_retried(tmp_path):
    from formal_runtime import execute_task
    from formal_recovery import recover_task, RecoveryConflict
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys
from pathlib import Path
(Path(sys.argv[2])/'worker-result.json').write_text(json.dumps(dict(status='failed',samples_eligible=False)))
''')
    original=tmp_path/'unsealed-failure';lock=tmp_path/'host.lock'
    execute_task({'id':'missing-finalization'},{},worker,original,lock,1024,2**30)
    # Artificial fixture: retain the worker's explicit failed result while
    # removing only this fixture's supervisor finalization files.
    (original/'state.json').unlink();(original/'completion.json').unlink()
    with pytest.raises(RecoveryConflict,match='worker.*failed'):
        recover_task(original,host_lock=lock,reason='Supervisor finalization is absent')
    assert not original.with_name(original.name+'.recovery').exists()
