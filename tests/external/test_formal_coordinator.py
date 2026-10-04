"""Public coordinator behavior with actual owned native process groups."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
pytestmark=pytest.mark.skipif(sys.platform!='darwin',reason='Native Mac process-group profile')


def wait_for(predicate,driver=None):
    deadline=time.monotonic()+10
    while not predicate():
        if driver is not None and driver.poll() is not None:
            raise AssertionError(driver.communicate()[1].decode())
        if time.monotonic()>deadline:raise AssertionError('Fixture observation deadline')
        time.sleep(.01)


def group_absent(pid):
    try:os.killpg(pid,0)
    except ProcessLookupError:return True
    return False


def test_lost_supervisor_blocks_other_output_directories_until_group_is_absent(tmp_path):
    from formal_coordinator import TaskCoordinator, CoordinatorBusy
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys,time
from pathlib import Path
out=Path(sys.argv[2]);request=json.loads(Path(sys.argv[1]).read_text())
(out/'ready').write_text('ready')
if 'release' in request:
    while not Path(request['release']).exists():time.sleep(.01)
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True)))
''')
    original=tmp_path/'study-a'/'initial';other=tmp_path/'study-b'/'initial'
    lock=tmp_path/'shared.lock';release=tmp_path/'release'
    script='''import sys
sys.path.insert(0,sys.argv[1])
from formal_coordinator import TaskCoordinator
TaskCoordinator(sys.argv[4]).run({'id':'a','protocol_sha256':'fixture'},
    {'release':sys.argv[5]},sys.argv[2],sys.argv[3],1024,2**30)
'''
    driver=subprocess.Popen([sys.executable,'-c',script,str(ROOT/'scripts/completion'),str(worker),str(original),str(lock),str(release)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    pid=None
    try:
        wait_for(lambda:(original/'attempt-0001/ready').exists() and (original/'attempt-0001/process.json').exists(),driver)
        pid=json.loads((original/'attempt-0001/process.json').read_text())['pid']
        driver.kill();driver.wait(timeout=3)
        coordinator=TaskCoordinator(lock)
        with pytest.raises(CoordinatorBusy,match='live'):
            coordinator.run({'id':'b','protocol_sha256':'fixture'},{},worker,other,1024,2**30)
        assert not other.exists()
        release.write_text('release')
        wait_for(lambda:group_absent(pid))
        pid=None
        done=coordinator.run({'id':'b','protocol_sha256':'fixture'},{},worker,other,1024,2**30)
        assert done['status']=='completed' and done['newly_executed']
        assert not (original/'state.json').exists()
        first=coordinator.history(original)
        assert first['lifecycle']=='stopped_unsealed'
        assert first['summary']['outcome']=='infrastructure_interruption'
        assert first['summary']['total_seconds'] is None
        assert first['summary']['attempt_count']==1
    finally:
        release.write_text('cleanup')
        if driver.poll() is None:driver.kill();driver.wait(timeout=3)
        if pid is not None:
            try:os.killpg(pid,signal.SIGKILL)
            except ProcessLookupError:pass


def test_explicit_retry_preserves_both_attempts_costs_and_cannot_change_identity(tmp_path):
    from formal_coordinator import TaskCoordinator, CoordinatorConflict
    from formal_recovery import RecoveryConflict
    from formal_runtime import file_hash
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys
from pathlib import Path
out=Path(sys.argv[2]);data=Path(sys.argv[1]).read_bytes()
(out/'request-copy.bin').write_bytes(data)
if out.parent.name=='original':sys.exit(7)
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True)))
''')
    c=TaskCoordinator(tmp_path/'host.lock');original=tmp_path/'original'
    task={'id':'retry','protocol_sha256':'fixture'};request={'noise':[1.,-2.,.25]}
    first=c.run(task,request,worker,original,1024,2**30)
    assert first['status']=='interrupted'
    before={str(p.relative_to(original)):file_hash(p) for p in original.rglob('*') if p.is_file()}
    second=c.retry(original,reason='Injected nonzero worker exit')
    assert second['status']=='completed' and second['newly_executed']
    assert second['history']['summary']['attempt_count']==2
    assert second['history']['summary']['total_seconds']>second['completion']['inclusive_preflight_through_terminal_seconds']
    assert second['history']['summary']['prior_interruption_known_seconds']==first['completion']['inclusive_preflight_through_terminal_seconds']
    assert before=={str(p.relative_to(original)):file_hash(p) for p in original.rglob('*') if p.is_file()}
    retry=original.with_name('original.retry')
    assert (retry/'attempt-0001/request-copy.bin').read_bytes()==(original/'attempt-0001/request-copy.bin').read_bytes()
    assert not c.retry(original,reason='Read existing retry')['newly_executed']
    assert not c.run(task,request,worker,original,1024,2**30,resume=True)['newly_executed']
    with pytest.raises(CoordinatorConflict,match='identity'):
        c.run(task,request,worker,tmp_path/'new-directory',1024,2**30)
    with pytest.raises(CoordinatorConflict,match='identity'):
        c.run(task,{'noise':[0.]},worker,original,1024,2**30,resume=True)
    with pytest.raises(CoordinatorConflict,match='identity'):
        c.run(dict(task,kernel='changed-under-same-id'),request,worker,tmp_path/'new-fields',1024,2**30)
    assert not (tmp_path/'new-fields').exists()
    with pytest.raises(CoordinatorConflict,match='registered'):
        c.retry(retry,reason='Forbidden third attempt')
    failed_worker=tmp_path/'failed.py'
    failed_worker.write_text('''import json,sys
from pathlib import Path
(Path(sys.argv[2])/'worker-result.json').write_text(json.dumps(dict(status='failed',samples_eligible=False,failure_category='numerical_failure')))
''')
    failed=tmp_path/'failed'
    c.run({'id':'failed','protocol_sha256':'fixture'},{},failed_worker,failed,1024,2**30)
    with pytest.raises(RecoveryConflict,match='failed'):
        c.retry(failed,reason='Cannot replace numerical failure')
    assert c.history(failed)['summary']['outcome']=='numerical_failure'


def test_prelaunch_resource_wait_does_not_become_a_phantom_live_attempt(tmp_path):
    from formal_coordinator import TaskCoordinator, CoordinatorConflict
    from formal_runtime import ResourceWait
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys
from pathlib import Path
(Path(sys.argv[2])/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True)))
''')
    c=TaskCoordinator(tmp_path/'host.lock');out=tmp_path/'waiting'
    task={'id':'waiting','protocol_sha256':'fixture'}
    with pytest.raises(ResourceWait):c.run(task,{},worker,out,2**62,2**30)
    assert not out.exists()
    history=c.history(out)
    assert history['lifecycle']=='not_started' and history['summary']['outcome']=='not_run'
    assert history['summary']['attempt_count']==0
    assert not history['attempts']
    with pytest.raises(ResourceWait):c.run(task,{},worker,out,2**62,2**30,resume=True)
    assert c.history(out)['summary']['attempt_count']==0
    with pytest.raises(CoordinatorConflict,match='not started'):
        c.retry(out,reason='Resource wait is not an executed interruption')
    other=c.run({'id':'other','protocol_sha256':'fixture'},{},worker,tmp_path/'other',0,2**30)
    assert other['status']=='completed'


def test_completed_worker_with_live_descendant_does_not_release_other_tasks(tmp_path):
    from formal_coordinator import TaskCoordinator, CoordinatorBusy
    worker=tmp_path/'worker.py';release=tmp_path/'release'
    worker.write_text('''import json,subprocess,sys
from pathlib import Path
out=Path(sys.argv[2]);request=json.loads(Path(sys.argv[1]).read_text())
if 'release' in request:
    subprocess.Popen([sys.executable,'-c',"import time,sys;from pathlib import Path;\\nwhile not Path(sys.argv[1]).exists():time.sleep(.01)",request['release']])
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True)))
''')
    c=TaskCoordinator(tmp_path/'host.lock');original=tmp_path/'parent'
    pid=None
    try:
        with pytest.raises(CoordinatorBusy,match='live'):
            c.run({'id':'parent','protocol_sha256':'fixture'},{'release':str(release)},worker,original,0,2**30)
        pid=json.loads((original/'attempt-0001/process.json').read_text())['pid']
        assert json.loads((original/'state.json').read_text())['status']=='completed'
        with pytest.raises(CoordinatorBusy,match='live'):
            c.run({'id':'other','protocol_sha256':'fixture'},{},worker,tmp_path/'other',0,2**30)
        release.write_text('finish owned child')
        wait_for(lambda:group_absent(pid));pid=None
        assert c.history(original)['summary']['outcome']=='valid'
        assert c.run({'id':'other','protocol_sha256':'fixture'},{},worker,tmp_path/'other',0,2**30)['status']=='completed'
    finally:
        release.write_text('cleanup')
        if pid is not None:
            try:os.killpg(pid,signal.SIGKILL)
            except ProcessLookupError:pass


def test_missing_process_receipt_and_changed_registry_history_fail_closed(tmp_path):
    from formal_coordinator import TaskCoordinator, CoordinatorConflict
    worker=tmp_path/'worker.py';release=tmp_path/'release'
    worker.write_text('''import json,sys,time
from pathlib import Path
out=Path(sys.argv[2]);request=json.loads(Path(sys.argv[1]).read_text())
(out/'ready').write_text('ready')
while not Path(request['release']).exists():time.sleep(.01)
(out/'worker-result.json').write_text(json.dumps(dict(status='failed',samples_eligible=False)))
''')
    original=tmp_path/'lost';lock=tmp_path/'host.lock'
    script='''import sys
sys.path.insert(0,sys.argv[1])
from formal_coordinator import TaskCoordinator
TaskCoordinator(sys.argv[4]).run({'id':'missing','protocol_sha256':'fixture'},
    {'release':sys.argv[5]},sys.argv[2],sys.argv[3],0,2**30)
'''
    driver=subprocess.Popen([sys.executable,'-c',script,str(ROOT/'scripts/completion'),str(worker),str(original),str(lock),str(release)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    pid=None
    try:
        wait_for(lambda:(original/'attempt-0001/ready').exists() and (original/'attempt-0001/process.json').exists(),driver)
        receipt=original/'attempt-0001/process.json';saved=receipt.read_bytes();pid=json.loads(saved)['pid']
        driver.kill();driver.wait(timeout=3);release.write_text('finish')
        wait_for(lambda:group_absent(pid));pid=None
        receipt.unlink()  # Artificial corruption, never a recovery procedure.
        c=TaskCoordinator(lock)
        with pytest.raises(CoordinatorConflict,match='No process receipt'):
            c.run({'id':'other','protocol_sha256':'fixture'},{},worker,tmp_path/'other',0,2**30)
        assert not (tmp_path/'other').exists()
        receipt.write_bytes(saved)
        assert c.history(original)['summary']['outcome']=='output_failure_unclassified'
        from formal_recovery import RecoveryConflict
        with pytest.raises(RecoveryConflict,match='failed'):
            c.retry(original,reason='Must not erase worker failure')
        import sqlite3
        with sqlite3.connect(c.registry_path/'registry.sqlite3') as db:
            db.execute("UPDATE events SET checksum='corrupted' WHERE ordinal=0")
        with pytest.raises(CoordinatorConflict,match='history'):
            c.history(original)
    finally:
        release.write_text('cleanup')
        if driver.poll() is None:driver.kill();driver.wait(timeout=3)
        if pid is not None:
            try:os.killpg(pid,signal.SIGKILL)
            except ProcessLookupError:pass
