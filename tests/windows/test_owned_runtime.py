import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import subprocess
import sys
import time
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/windows'),str(ROOT/'scripts/completion')]
from owned_runtime import Coordinator,assets,HostBusy,ResumeConflict,ResourceWait
from formal_runtime import file_hash,atomic_json
from job_objects import observe_named_job,identity,K,open_process,process_times,close,check

WORKER=Path(__file__).with_name('runtime_fixture.py')
LIMITS=dict(rss_bytes=2*1024**3,job_commit_bytes=4*1024**3,disk_start_bytes=64*1024**2,
            disk_floor_bytes=16*1024**2,poll_seconds=.03)


def spec(folder,mode='ok',kind='posterior'):
    folder=Path(folder);folder.mkdir(exist_ok=True)
    return dict(task=dict(id=folder.name,protocol_sha256='artificial-windows-fixture-v1',artifact_kind=kind),
        request=dict(mode=mode,artifact_kind=kind),worker=str(WORKER),output=str(folder/'task'),limits=dict(LIMITS))


def await_file(path,seconds=20):
    end=time.monotonic()+seconds
    while not path.exists():
        if time.monotonic()>end:raise AssertionError('Fixture readiness timeout, not proof of process exit')
        time.sleep(.03)
    return json.loads(path.read_text())


def stop_fixture_manager(record):
    """Kill only the created fixture manager, with an identity-bound OS handle."""
    h=check(open_process(0x1001,False,record['pid']))
    try:
        creation,ending,kernel,user=(W.FILETIME() for _ in range(4))
        check(process_times(h,C.byref(creation),C.byref(ending),C.byref(kernel),C.byref(user)))
        assert (creation.dwHighDateTime<<32)|creation.dwLowDateTime==record['creation_filetime']
        f=K.TerminateProcess;f.argtypes=[W.HANDLE,W.UINT];f.restype=W.BOOL
        check(f(h,19))
    finally:close(h)


@pytest.mark.parametrize('kind',('posterior','cache_measurement'))
def test_completion_zero_recompute_and_kind_separation(tmp_path,kind):
    c=Coordinator(tmp_path/'shared.lock');s=spec(tmp_path/'run',kind=kind)
    first=c.run(**s);original=assets(Path(s['output']))
    assert first['samples_eligible']==(kind=='posterior')
    assert first['measurement_available']==(kind=='cache_measurement')
    second=c.run(**s,resume=True)
    assert second['newly_executed'] is False and assets(Path(s['output']))==original
    assert first['job_final']['active_processes']==0
    c.snapshot(tmp_path/'registry-snapshot.json')


def test_identity_input_source_and_unknown_kind_refusal(tmp_path):
    c=Coordinator(tmp_path/'lock');s=spec(tmp_path/'one')
    bound=tmp_path/'input';bound.write_bytes(b'actual input')
    s['request']['input_files']={str(bound):file_hash(bound)}
    c.run(**s)
    bound.write_bytes(b'changed')
    with pytest.raises(ResumeConflict):c.run(**s,resume=True)
    s['request']['input_files'][str(bound)]=file_hash(bound)
    with pytest.raises(ResumeConflict):c.run(**s,resume=True)
    s['task']['id']='different';s['task']['artifact_kind']='unknown'
    before=c.registry.read_bytes()
    with pytest.raises(ValueError):c.run(**s)
    assert c.registry.read_bytes()==before


def test_worker_source_and_task_configuration_changes_refused(tmp_path):
    c=Coordinator(tmp_path/'lock');s=spec(tmp_path/'one')
    copied=tmp_path/'fixture.py';copied.write_bytes(WORKER.read_bytes());s['worker']=str(copied)
    # Copy still finds the real repo through an explicit non-frozen artificial wrapper.
    copied.write_text('import runpy,sys\nsys.argv[0]='+repr(str(WORKER))+'\nrunpy.run_path(sys.argv[0],run_name="__main__")\n')
    c.run(**s);copied.write_text(copied.read_text()+'# changed source\n')
    with pytest.raises(ResumeConflict):c.run(**s,resume=True)
    s['task']['budget']=999
    with pytest.raises(ResumeConflict):c.run(**s,resume=True)


def test_existing_failure_and_contradictory_measurement_are_not_retried(tmp_path):
    c=Coordinator(tmp_path/'lock')
    for mode in ('numerical_failure','contradiction'):
        s=spec(tmp_path/mode,mode=mode,kind='cache_measurement' if mode=='contradiction' else 'posterior')
        result=c.run(**s)
        assert result['outcome']==('numerical_failure' if mode=='numerical_failure' else 'output_failure_unclassified')
        assert not result['samples_eligible'] and not result['measurement_available']
        with pytest.raises(ResumeConflict):c.run(**s,retry=True)


def test_disk_refusal_before_process_and_low_rss_only_kills_fixture(tmp_path):
    c=Coordinator(tmp_path/'lock');s=spec(tmp_path/'disk');s['limits']['disk_start_bytes']=10**20
    with pytest.raises(ResourceWait):c.run(**s)
    assert not Path(s['output']).exists()
    unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
    try:
        s=spec(tmp_path/'memory',mode='memory');s['limits']['rss_bytes']=64*1024**2
        r=c.run(**s)
        assert r['outcome']=='resource_failure' and r['job_final']['active_processes']==0
        assert unrelated.poll() is None
    finally:unrelated.terminate();unrelated.wait()


def test_one_explicit_infrastructure_retry_and_no_cache_retry(tmp_path):
    c=Coordinator(tmp_path/'lock')
    for kind in ('posterior','cache_measurement'):
        s=spec(tmp_path/kind,mode='interrupted',kind=kind);r=c.run(**s)
        assert r['outcome']=='infrastructure_interruption'
        if kind=='posterior':
            second=c.run(**s,retry=True);assert second['attempt_id']=='attempt-0002'
        with pytest.raises(ResumeConflict):c.run(**s,retry=True)


def test_real_manager_crash_cooperative_lock_descendants_and_safe_continue(tmp_path):
    c=Coordinator(tmp_path/'lock');s=spec(tmp_path/'managed',mode='descendants',kind='cache_measurement')
    s['request']['release']=str(Path(s['output'])/'attempt-0001/fixture-release')
    invocation=tmp_path/'launch.json';atomic_json(invocation,dict(s,host_lock=str(c.lock)))
    with (tmp_path/'manager.log').open('wb') as log:
        manager=subprocess.Popen([sys.executable,str(WORKER),'manager',str(invocation)],stdout=log,stderr=log)
        try:
            record=await_file(tmp_path/'managed/manager.json')
            grandchild=await_file(Path(s['output'])/'attempt-0001/grandchild.json')
            receipt=await_file(Path(s['output'])/'attempt-0001/job.json')
            observed=observe_named_job(receipt['name'])
            assert observed['active_processes']>=3
            assert grandchild['pid'] in {p['pid'] for p in observed['members']}
            # Measurement owns the same lease that would guard posterior inference.
            with pytest.raises(HostBusy):c.run(**spec(tmp_path/'competitor'))
            stop_fixture_manager(record);manager.wait(timeout=20)
            end=time.monotonic()+20
            while observe_named_job(receipt['name'])['state']!='absent':
                assert time.monotonic()<end
                time.sleep(.03)
            proof=observe_named_job(receipt['name'])
            atomic_json(tmp_path/'manager-crash-proof.json',dict(before=observed,after=proof,
                manager=record,grandchild=grandchild,PID_disappearance_is_not_proof=True))
            with pytest.raises(ResumeConflict):c.run(**s,retry=True)
            result=c.run(**spec(tmp_path/'after'))
            assert result['outcome']=='valid'
        finally:
            if manager.poll() is None:
                if (tmp_path/'managed/manager.json').exists():stop_fixture_manager(json.loads((tmp_path/'managed/manager.json').read_text()))
                manager.wait(timeout=20)


def test_cuda_synchronization_and_recoverable_resource_error(tmp_path):
    c=Coordinator(tmp_path/'lock');s=spec(tmp_path/'cuda',mode='cuda')
    r=c.run(**s);assert r['outcome']=='valid'
    sample=json.loads((Path(s['output'])/'attempt-0001/cuda.json').read_text())
    assert sample['device']=='cuda:0' and sample['dtype']=='torch.float64' and sample['synchronized_seconds']>=0
    refusal=spec(tmp_path/'cuda-refused',mode='cuda');refusal['request']['reject_free_bytes']=10**20
    r=c.run(**refusal);assert r['outcome']=='resource_failure' and not r['samples_eligible']
    assert c.run(**s,resume=True)['newly_executed'] is False


def test_saved_numeric_failure_before_manager_seal_cannot_retry(tmp_path):
    c=Coordinator(tmp_path/'lock');s=spec(tmp_path/'managed',mode='failed_then_wait')
    invocation=tmp_path/'launch.json';atomic_json(invocation,dict(s,host_lock=str(c.lock)))
    with (tmp_path/'manager.log').open('wb') as log:
        manager=subprocess.Popen([sys.executable,str(WORKER),'manager',str(invocation)],stdout=log,stderr=log)
        record=await_file(tmp_path/'managed/manager.json')
        await_file(Path(s['output'])/'attempt-0001/worker-result.json')
        stop_fixture_manager(record);manager.wait(timeout=20)
    with pytest.raises(ResumeConflict):c.run(**s,retry=True)
    snapshot=tmp_path/'snapshot.json';c.snapshot(snapshot)
    entry=next(iter(json.loads(snapshot.read_text())['tasks'].values()))
    assert entry['attempts'][0]['outcome']=='numerical_failure'


def test_memory_observer_failure_stops_owned_job(tmp_path,monkeypatch):
    from job_objects import Job
    original=Job.observe;injected=False
    def failing(job):
        nonlocal injected
        if job.process and not injected:
            injected=True;raise PermissionError('Artificial memory observer denial')
        return original(job)
    monkeypatch.setattr(Job,'observe',failing)
    s=spec(tmp_path/'observer',mode='memory')
    result=Coordinator(tmp_path/'lock').run(**s)
    assert result['outcome']=='resource_failure' and result['job_final']['active_processes']==0


def test_portable_cost_policy_accepts_native_call_ledger(tmp_path):
    from measured_runtime import invoke
    from measured_coordinator import read_calls
    from formal_outcomes import summarize_attempts
    from formal_cost_policy import summarize_task_costs
    c=Coordinator(tmp_path/'lock');s=spec(tmp_path/'cost');ledger=tmp_path/'call-cost'
    first=invoke(c,s,ledger);invoke(c,s,ledger,resume=True)
    identity,calls=read_calls(ledger)
    attempt=dict(attempt_id=first['attempt_id'],binding_sha256=first['binding_sha256'],outcome='valid',seconds=first['invocation_seconds'],artifact_kind='posterior')
    history=dict(task=s['task'],original=str(Path(s['output']).resolve()),attempts=[attempt],summary=summarize_attempts([attempt]))
    report=summarize_task_costs(history,identity,calls,{first['attempt_id']:None})
    assert report['verification_only_invocations']==1
    assert report['phases']['ordinary_workflow']['complete_seconds'] is None
    assert report['phases']['research_execution']['complete_seconds']>0


def test_cuda_manager_death_ends_owned_descendants_preserves_other_context(tmp_path):
    import torch
    other=torch.ones(2,device='cuda',dtype=torch.float64)
    c=Coordinator(tmp_path/'lock');s=spec(tmp_path/'cuda-managed',mode='descendants',kind='cache_measurement')
    s['request'].update(cuda_fixture=True,release=str(Path(s['output'])/'attempt-0001/fixture-release'))
    invocation=tmp_path/'launch.json';atomic_json(invocation,dict(s,host_lock=str(c.lock)))
    with (tmp_path/'manager.log').open('wb') as log:
        manager=subprocess.Popen([sys.executable,str(WORKER),'manager',str(invocation)],stdout=log,stderr=log)
        try:
            record=await_file(tmp_path/'cuda-managed/manager.json')
            grandchild=await_file(Path(s['output'])/'attempt-0001/grandchild.json')
            assert grandchild['device']=='cuda:0' and grandchild['dtype']=='torch.float64'
            job=await_file(Path(s['output'])/'attempt-0001/job.json')
            before=observe_named_job(job['name'])
            assert grandchild['pid'] in {p['pid'] for p in before['members']}
            with pytest.raises(HostBusy):c.run(**spec(tmp_path/'posterior-competitor'))
            stop_fixture_manager(record);manager.wait(timeout=20)
            end=time.monotonic()+20
            while observe_named_job(job['name'])['state']!='absent':
                assert time.monotonic()<end;time.sleep(.03)
            after=observe_named_job(job['name'])
            assert float(other.sum())==2.0
            atomic_json(tmp_path/'cuda-manager-death-proof.json',dict(before=before,after=after,manager=record,
                grandchild=grandchild,unrelated_test_context_preserved=True,device_free_snapshot=torch.cuda.mem_get_info()[0],
                whole_device_memory_attribution=False,statistical_repetitions_added=0))
            c.snapshot(tmp_path/'quiescent.json')
        finally:
            if manager.poll() is None:
                stop_fixture_manager(json.loads((tmp_path/'cuda-managed/manager.json').read_text()));manager.wait(timeout=20)


@pytest.mark.parametrize('limit_mb,denied',[(64,True),(256,False)])
def test_kernel_commit_limit_denies_small_owned_allocation(tmp_path,limit_mb,denied):
    s=spec(tmp_path/'commit-limit',mode='commit-limit');s['limits']['job_commit_bytes']=limit_mb*1024**2
    result=Coordinator(tmp_path/'lock').run(**s)
    proof=json.loads((Path(s['output'])/'attempt-0001/commit-proof.json').read_text())
    assert proof['allocation_denied'] is denied
    assert result['outcome']==('resource_failure' if denied else 'valid') and result['job_final']['active_processes']==0
    assert result['job_final']['hard_job_commit_limit_bytes']==limit_mb*1024**2
