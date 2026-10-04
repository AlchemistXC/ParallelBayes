"""Public task lifecycle: actual OS exclusion, preservation and resource guards."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_one_host_lock_excludes_another_output_and_releases_after_exception(tmp_path):
    from formal_runtime import host_lease,HostBusy
    lock=tmp_path/'one-host.lock'
    script='''import sys
sys.path.insert(0,sys.argv[1])
from formal_runtime import host_lease,HostBusy
try:
    with host_lease(sys.argv[2],"other-output"):
        print("acquired")
except HostBusy:
    print("busy")
'''
    with pytest.raises(RuntimeError,match='injected'):
        with host_lease(lock,'first-output'):
            child=subprocess.run([sys.executable,'-c',script,str(ROOT/'scripts/completion'),str(lock)],capture_output=True,text=True,check=True)
            assert child.stdout.strip()=='busy'
            raise RuntimeError('injected')
    child=subprocess.run([sys.executable,'-c',script,str(ROOT/'scripts/completion'),str(lock)],capture_output=True,text=True,check=True)
    assert child.stdout.strip()=='acquired'


def test_task_preserves_failed_output_and_resumes_without_launching_worker(tmp_path):
    import json
    from formal_runtime import execute_task,ResumeConflict
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys
from pathlib import Path
p=Path(sys.argv[2])
(p/'failed-path.bin').write_bytes(b"preserved-invalid-path")
(p/'worker-result.json').write_text(json.dumps(dict(status="failed",samples_eligible=False,reason="injected_numerical_failure")))
''')
    output=tmp_path/'task'
    kwargs=dict(task={'id':'failure-preservation','protocol':'technical-unit'},request={},
        worker=worker,output=output,host_lock=tmp_path/'shared.lock',required_disk_bytes=1024,
        max_tree_rss_bytes=2**30)
    first=execute_task(**kwargs)
    assert first['status']=='failed' and not first['samples_eligible']
    assert first['failure_kind']=='worker_output_standard'
    before={str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file()}
    resumed=execute_task(**kwargs,resume=True)
    assert resumed['resumed'] and not resumed['newly_executed']
    assert before=={str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file()}
    attempt=output/first['attempt']
    assert (attempt/'failed-path.bin').read_bytes()==b'preserved-invalid-path'
    (attempt/'failed-path.bin').write_bytes(b'corrupted')
    with pytest.raises(ResumeConflict,match='checksum'):execute_task(**kwargs,resume=True)


def test_phase_journal_keeps_failures_and_disk_gate_launches_no_task(tmp_path):
    import json,shutil,time
    from formal_runtime import PhaseLedger,execute_task,ResourceWait
    ledger=PhaseLedger(tmp_path/'phases.json')
    with ledger.phase('setup'):
        with pytest.raises(RuntimeError,match='overlap'):
            with ledger.phase('nested'):pass
        time.sleep(.001)
    with pytest.raises(ValueError,match='injected'):
        with ledger.phase('sampling'):
            raise ValueError('injected')
    record=json.loads((tmp_path/'phases.json').read_text())
    assert [p['name'] for p in record['phases']]==['setup','sampling']
    assert [p['status'] for p in record['phases']]==['completed','failed']
    assert record['phases'][0]['end_offset_seconds']<=record['phases'][1]['start_offset_seconds']
    assert all(p['wall_seconds']>=0 and p['process_cpu_seconds']>=0 for p in record['phases'])
    worker=tmp_path/'worker.py';worker.write_text('raise RuntimeError("must not launch")')
    output=tmp_path/'insufficient-disk'
    with pytest.raises(ResourceWait,match='no task launched'):
        execute_task({'id':'disk-wait'},{},worker,output,tmp_path/'host.lock',
                     required_disk_bytes=shutil.disk_usage(tmp_path).total+1,max_tree_rss_bytes=2**30)
    assert not output.exists()
