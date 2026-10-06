"""Real Windows kernel cohort tests; fixtures are not statistical replicates."""
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/windows'))
from job_objects import Job, observe_named_job, identity


def test_atomic_assignment_and_descendant_accounting(tmp_path):
    script=tmp_path/'child.py'
    script.write_text('import subprocess,sys,time\np=subprocess.Popen([sys.executable,"-c","import time;time.sleep(2)"])\ntime.sleep(1)\np.wait()\n')
    name='Local\\ParallelBayes-'+uuid.uuid4().hex
    with (tmp_path/'out').open('wb') as out, (tmp_path/'err').open('wb') as err, Job(name,2*1024**3) as job:
        first=job.launch_suspended([sys.executable,script],ROOT,out,err)
        assert first['member_of_owned_job']
        assert job.observe()['active_processes']==1
        job.resume(); maximum=0
        while job.observe()['active_processes']:
            sample=job.observe();maximum=max(maximum,sample['active_processes'])
            assert all(p['member_of_owned_job'] for p in sample['members'])
            time.sleep(.03)
        assert job.poll()==0 and maximum>=2
        # Windows venv redirectors/conhost may add owned processes.
        assert job.observe()['total_processes']>=2
        (tmp_path/'kernel-final.json').write_text(json.dumps(job.observe(),indent=2))
    assert observe_named_job(name)['state']=='absent'


def test_last_handle_close_terminates_only_owned_cohort(tmp_path):
    unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
    try:
        with (tmp_path/'out').open('wb') as out, (tmp_path/'err').open('wb') as err:
            name='Local\\ParallelBayes-'+uuid.uuid4().hex
            job=Job(name); child=job.launch_suspended([sys.executable,'-c','import time;time.sleep(30)'],ROOT,out,err)
            job.resume();job.close()
            deadline=time.monotonic()+10
            while observe_named_job(name)['state']!='absent':
                assert time.monotonic()<deadline
                time.sleep(.02)
            assert unrelated.poll() is None
            # Do not use PID disappearance as the cohort proof.
            (tmp_path/'proof.json').write_text(json.dumps(dict(owned=child,job_absent=True,unrelated_alive=True)))
    finally:
        unrelated.terminate();unrelated.wait()
