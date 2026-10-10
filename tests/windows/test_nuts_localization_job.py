"""Real Windows kernel tests. Never substitute portable stubs for this gate."""
from pathlib import Path
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/followups'))
from nuts_job import ObservedJob
from job_objects import observe_named_job


def test_observed_owned_exit_code_private_memory_and_commit_limit(tmp_path):
    name='Local\\ParallelBayes-localization-test-'+uuid.uuid4().hex
    observations=[]
    with (tmp_path/'out').open('wb') as out,(tmp_path/'err').open('wb') as err,ObservedJob(name,512*1024**2) as job:
        primary=job.launch_suspended([sys.executable,'-c','import time; x=bytearray(8*1024**2);time.sleep(.5);raise SystemExit(7)'],ROOT,out,err)
        before=job.observe();job.resume();deadline=time.monotonic()+30
        assert before['hard_job_commit_limit_bytes']==512*1024**2
        while True:
            state=job.observe();observations.append(state)
            if state['active_processes']==0 and job.poll() is not None:break
            assert time.monotonic()<deadline,'Kernel fixture did not terminate'
            time.sleep(.02)
        assert job.poll()==7
        primary_states=[p for o in observations for p in o['retained_process_handles']
            if p['pid']==primary['pid'] and p['creation_filetime']==primary['creation_filetime']]
        assert any(p['private_bytes'] is not None and p['private_bytes']>0 for p in primary_states)
        assert primary_states[-1]['state']=='exited' and primary_states[-1]['exit_code']==7
        assert all(o['hard_job_commit_limit_bytes']==512*1024**2 for o in observations)
        # We save packets but do not require a particular packet to arrive.
        assert all(not m['delivery_guaranteed'] for o in observations for m in o['completion_messages'])
    assert observe_named_job(name)['state']=='absent'
