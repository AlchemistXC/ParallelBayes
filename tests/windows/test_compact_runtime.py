"""Actual native boundary behavior using artificial workers, not MCMC evidence."""
import json
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/windows'),str(ROOT/'scripts/completion')]
pytestmark=pytest.mark.skipif(sys.platform!='win32',reason='Actual native Windows required')
from formal_runtime import file_hash
from compact_control import request_pause,pause_pending,acknowledge_pause


def test_native_compact_boundary_pause_and_zero_recompute(tmp_path,monkeypatch):
    import compact_batch
    from formal_owned_runtime import Coordinator
    from job_objects import observe_named_job
    work=tmp_path/'artificial-worker-root';worker=work/'scripts/windows/compact_worker.py';worker.parent.mkdir(parents=True)
    worker.write_text("import json,os,sys,time\nfrom pathlib import Path\n"
        +f"sys.path.insert(0,{str(ROOT/'scripts/windows')!r})\n"
        +"from job_objects import Job,identity\n"
        +"out=Path(sys.argv[2])\n"
        +"with Job(os.environ['PB_OWNED_JOB'],existing=True) as owned:\n"
        +" member=identity(os.getpid(),owned.handle)\n"
        +" assert member['member_of_owned_job']\n"
        +" (out/'READY.json').write_text(json.dumps(member))\n"
        +" time.sleep(.75)\n"
        +" (out/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True,measurement_available=False,artificial_fixture=True)))\n",
        encoding='utf-8')
    monkeypatch.setattr(compact_batch,'ROOT',work)
    protocol='c'*64
    tasks=[dict(id=n*24,protocol_sha256=protocol,artifact_kind='posterior',batch=0) for n in ('a','b')]
    class Dispatch:
        plan=SimpleNamespace(protocol_sha256=protocol)
        def slots(self,batch,phase):return (dict(task=t) for t in tasks)
        def summarize_phase(self,batch,phase,rows):return dict(closed=len(rows)==2,visited=len(rows),planned=2)
    coordinator=Coordinator(tmp_path/'fixture-shared.lock')
    phase_root=tmp_path/'artificial-study/formal-runs/batch-00/main'
    invocation=tmp_path/'artificial-study/driver-invocations/first';invocation.mkdir(parents=True)
    pause_bundle=tmp_path/'artificial-study'
    limits=dict(rss_bytes=512*1024**2,job_commit_bytes=1024**3,disk_start_bytes=1024**2,disk_floor_bytes=1024**2,poll_seconds=.02)
    observation={};errors=[]
    def request_at_ready():
        try:
            end=time.monotonic()+15
            folder=phase_root/'tasks'/tasks[0]['id']/'attempt-0001'
            while not (folder/'READY.json').exists():
                if time.monotonic()>end:raise RuntimeError('Artificial fixture did not become ready')
                time.sleep(.01)
            name=json.loads((folder/'job.json').read_text())['name']
            observation.update(observe_named_job(name))
            assert observation['state']=='present' and observation['active_processes']>0
            request_pause(pause_bundle,protocol,'Artificial fixture boundary test; not a scientific repetition')
        except BaseException as exc:errors.append(exc)
    thread=threading.Thread(target=request_at_ready);thread.start()
    kwargs=dict(dispatch=Dispatch(),batch=0,phase='main',coordinator=coordinator,phase_root=phase_root,
        make_request=lambda _:dict(input_files={},source_files={str(worker):file_hash(worker)}),limits=limits,
        pause_check=lambda:pause_pending(pause_bundle,protocol))
    result=compact_batch.execute_slots(invocation=invocation,**kwargs)
    thread.join(timeout=20)
    assert not thread.is_alive() and not errors
    assert result['status']=='paused_at_task_boundary' and result['newly_executed']==1 and result['remaining']==1
    assert not (phase_root/'tasks'/tasks[1]['id']).exists()
    folder=phase_root/'tasks'/tasks[0]['id']/'attempt-0001';state=json.loads((folder/'state.json').read_text())
    proof=observe_named_job(state['job_final']['job_name'])
    assert proof['state']=='absent' or proof['active_processes']==0
    assert state['job_final']['active_processes']==0
    (tmp_path/'native-pause-proof.json').write_text(json.dumps(dict(while_active=observation,after=proof,checkpoint=result),indent=2))
    before=compact_batch.task_assets(phase_root/'tasks'/tasks[0]['id'])
    acknowledge_pause(pause_bundle,protocol,'Explicit continuation of artificial fixture only')
    later=pause_bundle/'driver-invocations/second';later.mkdir()
    result=compact_batch.execute_slots(invocation=later,resume=True,**kwargs)
    assert result['newly_executed']==1 and result['closed']
    assert before==compact_batch.task_assets(phase_root/'tasks'/tasks[0]['id'])
    original=compact_batch.task_assets(phase_root/'tasks')
    for i in range(2):
        out=pause_bundle/f'driver-invocations/verify-{i}';out.mkdir()
        r=compact_batch.execute_slots(invocation=out,verify_only=True,**kwargs)
        assert r['newly_executed']==0 and r['closed']
        assert original==compact_batch.task_assets(phase_root/'tasks')
