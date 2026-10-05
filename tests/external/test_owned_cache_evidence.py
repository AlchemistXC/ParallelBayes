"""Read-only owned measurement intake preserves the full planned failure frame."""
from pathlib import Path
import copy,json,shutil,sqlite3,sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
pytestmark=pytest.mark.skipif(sys.platform!='darwin',reason='Fixture producer uses native Mac process ownership')


def fixture(tmp_path,**controls):
    from batch_contract import BatchPlan,create_tasks
    from formal_inputs import build_payload
    from formal_measurement_plan import create_measurement_plan
    from formal_runtime import atomic_json,file_hash,fingerprint
    from mechanism_runner import actual_hash
    root=tmp_path/'original';root.mkdir();(root/'inputs').mkdir()
    p=json.loads((ROOT/'benchmark/protocols/owned-cache-runtime-mac-short-v2.json').read_text())
    p.pop('protocol_sha256');p['identity']='owned-cache-intake-test-fixture'
    p['targets']=[t for t in p['targets'] if t['name']=='G1']
    p['groups']=[dict(models=['G1'],replicates=[0,1],budgets=[8],workflows=['cpu-rwm-sequential','cpu-rwm-online_picard','cpu-mala-sequential','cpu-mala-quasi_deer'])]
    p['controls'].update(controls);p['tasks']=create_tasks(p['identity'],p['groups']);p['inputs']={}
    p['source_files']={n:file_hash(ROOT/n) for n in p['source_files']}
    for rep in (0,1):
        values=build_payload(p['identity'],'G1',rep,p['targets'][0]['dimension'],16,4)
        name=f'G1-rep{rep:04d}.npz';np.savez_compressed(root/'inputs'/name,**values)
        p['inputs'][name]=dict(model='G1',replicate=rep,dimension=p['targets'][0]['dimension'],chains=4,steps=16,sha256=file_hash(root/'inputs'/name),actual_sha256=actual_hash(values))
    allocation=create_measurement_plan(p['identity'],p['tasks']);p['cache_allocation_sha256']=allocation['allocation_sha256']
    p['protocol_sha256']=fingerprint(p);plan=BatchPlan(p)
    atomic_json(root/'protocol.json',p);atomic_json(root/'allocation.json',allocation)
    return root,plan,allocation


def job(root,plan,probe,worker=None,**limits):
    c,h=plan.capsule(probe['primary_task_id'])
    return dict(task=dict(id=probe['id'],protocol_sha256=plan.protocol_sha256,artifact_kind='cache_measurement'),
        request=dict(capsule=c,capsule_sha256=h,probe=probe,inputs=str(root/'inputs')),
        worker=worker or ROOT/'scripts/completion/owned_cache_worker.py',output=root/'tasks'/probe['id'],
        required_disk_bytes=limits.get('disk',0),max_tree_rss_bytes=limits.get('rss',2**30))


def relocate(root,plan,allocation,measured,tmp_path):
    from formal_runtime import atomic_json,file_hash,fingerprint
    # Tests serialize access; a production exporter must additionally hold both
    # coordinator and host leases while snapshotting a quiescent database.
    snapshot=root/'registry.sqlite3'
    with sqlite3.connect(measured.coordinator.registry_path/'registry.sqlite3') as src:
        with sqlite3.connect(snapshot) as dst:src.backup(dst)
    locations={};probes={}
    for p in allocation['probes']:
        original=str(root/'tasks'/p['id']);locations[original]='tasks/'+p['id']
        call='calls/'+fingerprint(original)
        probes[p['id']]=dict(original=original,calls=call if (root/call).is_dir() else None)
    descriptor=dict(schema='owned-cache-evidence-v1',protocol='protocol.json',allocation='allocation.json',
        inputs='inputs',snapshot='registry.sqlite3',snapshot_sha256=file_hash(snapshot),locations=locations,probes=probes)
    atomic_json(root/'owned-cache-layout.json',descriptor)
    moved=tmp_path/'moved';shutil.copytree(root,moved);shutil.rmtree(root)
    return moved,file_hash(moved/'owned-cache-layout.json')


def test_unstarted_and_disk_refused_measurements_survive_relocation(tmp_path):
    from measured_coordinator import MeasuredCoordinator
    from formal_runtime import ResourceWait
    from owned_cache_evidence import OwnedCacheEvidence
    root,plan,allocation=fixture(tmp_path);m=MeasuredCoordinator(tmp_path/'host.lock',root/'calls')
    first=allocation['probes'][0]
    with pytest.raises(ResourceWait):m.run(**job(root,plan,first,disk=2**80))
    moved,digest=relocate(root,plan,allocation,m,tmp_path)
    with OwnedCacheEvidence(moved,'owned-cache-layout.json',digest) as evidence:
        rows=[evidence.read_probe(pid) for pid in evidence.probe_ids]
    assert len(rows)==8 and all(r['task_outcome']=='not_run' for r in rows)
    assert all(r['observation']['records']==[None]*4 for r in rows)
    assert all(not r['measurement_available'] and not r['samples_eligible'] for r in rows)
    refused=next(r for r in rows if r['probe']['id']==first['id'])
    assert refused['history']['lifecycle']=='not_started'
    assert refused['outer_costs']['known_invocation_seconds']>0
    assert refused['outer_costs']['actual_attempts']==0
    assert refused['numerical_evidence_kind']=='absent'


@pytest.mark.parametrize('workflow,controls,outcome,known_calls',[
    ('cpu-rwm-sequential',{},'measurement_available',4),
    ('cpu-mala-quasi_deer',{'quasi_deer_max_iter':1},'numerical_failure',4),
    ('cpu-rwm-online_picard',{'window':4096,'memory_limit_mb':1},'resource_failure',0),
])
def test_completed_and_failed_numerical_artifacts_keep_their_original_scope(tmp_path,workflow,controls,outcome,known_calls):
    from measured_coordinator import MeasuredCoordinator
    from owned_cache_evidence import OwnedCacheEvidence
    root,plan,allocation=fixture(tmp_path,**controls);m=MeasuredCoordinator(tmp_path/'host.lock',root/'calls')
    probe=next(p for p in allocation['probes'] if p['workflow']==workflow)
    m.run(**job(root,plan,probe))
    moved,digest=relocate(root,plan,allocation,m,tmp_path)
    with OwnedCacheEvidence(moved,'owned-cache-layout.json',digest) as evidence:row=evidence.read_probe(probe['id'])
    assert row['task_outcome']==outcome and row['measurement_available']==(outcome=='measurement_available')
    assert row['numerical_summary']['observed_executions']==known_calls
    assert row['numerical_evidence_kind']=='sealed'
    assert row['outer_costs']['known_invocation_seconds']>0
    assert row['samples_eligible'] is False
    if known_calls:assert row['numerical_summary']['known_executor_seconds']>0
    else:assert row['numerical_summary']['cached_seconds'] is None


def write_fault_worker(path,stage):
    path.write_text('''import json,os,sys
from pathlib import Path
sys.path[:0]=[sys.argv[3]] if len(sys.argv)>3 else []
sys.path.insert(0,''' + repr(str(ROOT/'scripts/completion')) + ''')
from owned_cache_worker import run
replace=os.replace
def fault(source,destination):
    replace(source,destination)
    p=Path(destination)
    if p.parent.name=='probe' and p.name==''' + repr(stage) + ''':os._exit(17)
os.replace=fault
run(sys.argv[1],sys.argv[2])
''')


@pytest.mark.parametrize('stage,kind,known_calls',[
    ('candidate-0.json','partial',1),('MANIFEST.json','sealed',4),
])
def test_storage_boundary_interruption_preserves_timed_calls_without_granting_completion(tmp_path,stage,kind,known_calls):
    from measured_coordinator import MeasuredCoordinator
    from owned_cache_evidence import OwnedCacheEvidence
    root,plan,allocation=fixture(tmp_path);m=MeasuredCoordinator(tmp_path/'host.lock',root/'calls')
    probe=next(p for p in allocation['probes'] if p['workflow']=='cpu-rwm-sequential')
    worker=tmp_path/'fault.py';write_fault_worker(worker,stage)
    result=m.run(**job(root,plan,probe,worker))
    assert result['status']=='interrupted'
    moved,digest=relocate(root,plan,allocation,m,tmp_path)
    with OwnedCacheEvidence(moved,'owned-cache-layout.json',digest) as evidence:row=evidence.read_probe(probe['id'])
    assert row['task_outcome']=='infrastructure_interruption' and not row['measurement_available']
    assert row['numerical_evidence_kind']==kind
    assert row['numerical_summary']['observed_executions']==known_calls
    assert row['numerical_summary']['known_executor_seconds']>0
    assert row['samples_eligible'] is False
    if kind=='partial':assert row['observation']['execution_outcomes']==['infrastructure_interruption']+['not_run']*3
    else:assert row['numerical_summary']['all_executions_valid']


def test_unsealed_supervisor_interruption_keeps_valid_calls_and_unknown_outer_time(tmp_path):
    import os,signal,subprocess
    from measured_coordinator import MeasuredCoordinator
    from owned_cache_evidence import OwnedCacheEvidence
    import time
    def wait(predicate):
        end=time.monotonic()+15
        while not predicate():
            if time.monotonic()>end:raise AssertionError('Fixture observation deadline')
            time.sleep(.01)
    def absent(pid):
        try:os.killpg(pid,0)
        except ProcessLookupError:return True
        return False
    root,plan,allocation=fixture(tmp_path);lock=tmp_path/'host.lock'
    m=MeasuredCoordinator(lock,root/'calls')
    probe=next(p for p in allocation['probes'] if p['workflow']=='cpu-rwm-sequential')
    release=tmp_path/'release';worker=tmp_path/'wait-worker.py'
    worker.write_text('''import os,sys,time
from pathlib import Path
sys.path.insert(0,''' + repr(str(ROOT/'scripts/completion')) + ''')
from owned_cache_worker import run
replace=os.replace
def pause(source,destination):
    replace(source,destination)
    if Path(destination).name=='candidate-0.json':
        while not Path(''' + repr(str(release)) + ''').exists():time.sleep(.01)
os.replace=pause
run(sys.argv[1],sys.argv[2])
''')
    j=job(root,plan,probe,worker);request=tmp_path/'launch.json'
    request.write_text(json.dumps({k:str(v) if isinstance(v,Path) else v for k,v in j.items()}))
    code='''import json,sys
sys.path.insert(0,sys.argv[1])
from measured_coordinator import MeasuredCoordinator
MeasuredCoordinator(sys.argv[2],sys.argv[3]).run(**json.load(open(sys.argv[4])))
'''
    supervisor=subprocess.Popen([sys.executable,'-c',code,str(ROOT/'scripts/completion'),str(lock),str(root/'calls'),str(request)])
    out=j['output'];pid=None
    try:
        wait(lambda:(out/'attempt-0001/probe/candidate-0.json').exists())
        pid=json.loads((out/'attempt-0001/process.json').read_text())['pid']
        supervisor.kill();supervisor.wait(timeout=3);release.touch();wait(lambda:absent(pid));pid=None
        h=m.coordinator.history(out)
        assert h['lifecycle']=='stopped_unsealed' and h['summary']['total_seconds'] is None
        moved,digest=relocate(root,plan,allocation,m,tmp_path)
        with OwnedCacheEvidence(moved,'owned-cache-layout.json',digest) as evidence:row=evidence.read_probe(probe['id'])
        assert row['task_outcome']=='infrastructure_interruption'
        assert row['observation']['execution_outcomes']==['valid']*4
        assert row['numerical_summary']['known_executor_seconds']>0
        assert row['history']['attempts'][0]['seconds'] is None
        assert row['outer_costs']['unfinished_invocations']==1
        assert row['outer_costs']['complete_invocation_seconds'] is None
        assert not row['measurement_available'] and not row['samples_eligible']
        assert row['cached_seconds'] is None
        assert row['history']['attempts'][0]['artifact_kind']=='cache_measurement'
    finally:
        release.touch()
        if supervisor.poll() is None:supervisor.kill();supervisor.wait(timeout=3)
        if pid is not None:
            try:os.killpg(pid,signal.SIGKILL)
            except ProcessLookupError:pass


@pytest.mark.parametrize('change',['missing_probe','input_tamper','snapshot_tamper'])
def test_owned_archive_rejects_incomplete_frames_or_changed_evidence(tmp_path,change):
    from measured_coordinator import MeasuredCoordinator
    from formal_runtime import ResourceWait,file_hash
    from owned_cache_evidence import OwnedCacheEvidence
    root,plan,allocation=fixture(tmp_path);m=MeasuredCoordinator(tmp_path/'host.lock',root/'calls')
    with pytest.raises(ResourceWait):m.run(**job(root,plan,allocation['probes'][0],disk=2**80))
    moved,digest=relocate(root,plan,allocation,m,tmp_path)
    if change=='missing_probe':
        f=moved/'owned-cache-layout.json';layout=json.loads(f.read_text());layout['probes'].pop(next(iter(layout['probes'])))
        f.write_text(json.dumps(layout));digest=file_hash(f)
    elif change=='input_tamper':
        f=next((moved/'inputs').glob('*.npz'));f.write_bytes(f.read_bytes()+b'changed')
    else:
        f=moved/'registry.sqlite3';f.write_bytes(f.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='probe|input|snapshot|checksum|hash'):
        with OwnedCacheEvidence(moved,'owned-cache-layout.json',digest) as evidence:
            for pid in evidence.probe_ids:evidence.read_probe(pid)


def test_process_memory_failure_without_a_numerical_artifact_is_not_dropped(tmp_path):
    from measured_coordinator import MeasuredCoordinator
    from owned_cache_evidence import OwnedCacheEvidence
    root,plan,allocation=fixture(tmp_path);m=MeasuredCoordinator(tmp_path/'host.lock',root/'calls')
    probe=allocation['probes'][0];worker=tmp_path/'allocate.py'
    worker.write_text('import time\nallocation=bytearray(128*1024**2)\ntime.sleep(2)\n')
    result=m.run(**job(root,plan,probe,worker,rss=64*1024**2))
    assert result['failure_kind']=='process_tree_memory_guard'
    moved,digest=relocate(root,plan,allocation,m,tmp_path)
    with OwnedCacheEvidence(moved,'owned-cache-layout.json',digest) as evidence:row=evidence.read_probe(probe['id'])
    assert row['task_outcome']=='resource_failure' and row['numerical_evidence_kind']=='absent'
    assert row['observation']['execution_outcomes']==['not_run']*4
    assert row['numerical_summary']['observed_executions']==0 and row['cached_seconds'] is None
    assert row['outer_costs']['known_invocation_seconds']>0
