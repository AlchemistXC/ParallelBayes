"""Actual small cached paths and audit records; no fabricated timing backend."""
from pathlib import Path
import copy
import json
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python')]


def fixture(tmp_path,kernel='rwm',executor='online_picard',**controls):
    from batch_contract import BatchPlan,create_tasks
    from formal_inputs import build_payload
    from formal_measurement_plan import create_measurement_plan
    from formal_runtime import file_hash,fingerprint
    from mechanism_runner import actual_hash
    p=json.loads((ROOT/'benchmark/protocols/batch-schema-maximum-mac-v1.json').read_text())
    p['identity']='cache-execution-test-only';p['targets']=[t for t in p['targets'] if t['name']=='G1']
    p['groups']=[dict(models=['G1'],replicates=[0],budgets=[8],workflows=['cpu-'+kernel+'-sequential','cpu-'+kernel+'-'+('online_picard' if kernel=='rwm' else 'quasi_deer')])]
    p['tasks']=create_tasks(p['identity'],p['groups']);p['controls'].update(mh_discard=8,window=4,memory_limit_mb=128);p['controls'].update(controls)
    p['source_files']['scripts/completion/cache_probe_execution.py']=file_hash(ROOT/'scripts/completion/cache_probe_execution.py')
    values=build_payload(p['identity'],'G1',0,p['targets'][0]['dimension'],16,4)
    inputs=tmp_path/'inputs';inputs.mkdir();name='G1-rep0000.npz';np.savez_compressed(inputs/name,**values)
    p['inputs']={name:dict(model='G1',replicate=0,dimension=p['targets'][0]['dimension'],chains=4,steps=16,
                         sha256=file_hash(inputs/name),actual_sha256=actual_hash(values))}
    p.pop('protocol_sha256');p['protocol_sha256']=fingerprint(p)
    plan=BatchPlan(p);allocation=create_measurement_plan(p['identity'],p['tasks'])
    probe=next(x for x in allocation['probes'] if x['executor']==executor)
    capsule,digest=plan.capsule(probe['primary_task_id'])
    return capsule,digest,probe,inputs


@pytest.mark.parametrize('kernel,executor',[('rwm','sequential'),('rwm','online_picard'),('mala','sequential'),('mala','quasi_deer')])
def test_cached_probe_without_primary_fit_is_audited_but_never_a_posterior_sample(tmp_path,kernel,executor):
    from cache_probe_execution import execute_cached_probe,read_cached_probe
    capsule,digest,probe,inputs=fixture(tmp_path,kernel,executor)
    report=execute_cached_probe(capsule,digest,probe,inputs,tmp_path/'probe')
    assert report['artifact_kind']=='cache_measurement' and report['measurement_available'] is True
    assert report['samples_eligible'] is False and report['summary']['statistical_repetitions_added']==0
    assert report['observation']['execution_outcomes']==['valid']*4
    assert report['summary']['observed_executions']==4 and report['summary']['cached_seconds']>0
    assert all(r['audit']['passed'] and r['audit']['acceptance_mismatches']==[0]*4 for r in report['observation']['records'])
    assert all(r['samples_eligible'] is False for r in report['observation']['records'])
    assert read_cached_probe(tmp_path/'probe')==report
    with pytest.raises(FileExistsError):
        execute_cached_probe(capsule,digest,probe,inputs,tmp_path/'probe')


def test_archive_error_preserves_actual_executor_cost_and_unexecuted_replays(tmp_path,monkeypatch):
    from cache_probe_execution import execute_cached_probe,read_cached_probe
    capsule,digest,probe,inputs=fixture(tmp_path)
    # Inject a storage-boundary failure after actual numerical execution. The
    # sampler, numerical audit and clocks are not mocked.
    def unavailable_storage(*args,**kwargs):raise OSError('explicit archive-write failure fixture')
    monkeypatch.setattr(np,'savez_compressed',unavailable_storage)
    with pytest.raises(OSError,match='archive-write'):
        execute_cached_probe(capsule,digest,probe,inputs,tmp_path/'probe')
    saved=read_cached_probe(tmp_path/'probe')
    assert saved['status']=='interrupted' and saved['samples_eligible'] is False
    assert saved['observation']['execution_outcomes']==['infrastructure_interruption']+['not_run']*3
    assert saved['summary']['known_executor_seconds']>0
    assert saved['summary']['observed_executions']==1 and saved['summary']['complete_executor_seconds'] is None
    assert saved['summary']['cached_seconds'] is None


def test_solver_and_preparation_failures_preserve_planned_frames(tmp_path):
    from cache_probe_execution import execute_cached_probe,read_cached_probe
    failed=tmp_path/'solver';failed.mkdir()
    capsule,digest,probe,inputs=fixture(failed,'mala','quasi_deer',quasi_deer_max_iter=1)
    report=execute_cached_probe(capsule,digest,probe,inputs,failed/'probe')
    assert report['measurement_available'] is False and report['samples_eligible'] is False
    assert report['observation']['execution_outcomes']==['numerical_failure']*4
    assert report['summary']['complete_executor_seconds']>0 and report['summary']['cached_seconds'] is None
    assert report['summary']['observed_executions']==4
    assert read_cached_probe(failed/'probe')==report
    resource=tmp_path/'resource';resource.mkdir()
    capsule,digest,probe,inputs=fixture(resource,window=4096,memory_limit_mb=1)
    report=execute_cached_probe(capsule,digest,probe,inputs,resource/'probe')
    assert report['observation']['execution_outcomes']==['resource_failure']+['not_run']*3
    assert report['summary']['observed_executions']==0 and report['summary']['complete_executor_seconds'] is None
    assert report['samples_eligible'] is False
    assert read_cached_probe(resource/'probe')==report


def test_actual_input_change_is_rejected_and_sealed_evidence_is_portable(tmp_path):
    import shutil
    from cache_probe_execution import execute_cached_probe,read_cached_probe
    capsule,digest,probe,inputs=fixture(tmp_path)
    report=execute_cached_probe(capsule,digest,probe,inputs,tmp_path/'probe')
    shutil.copytree(tmp_path/'probe',tmp_path/'moved')
    assert read_cached_probe(tmp_path/'moved')==report
    raw=tmp_path/'moved/execution-0.npz';raw.write_bytes(raw.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='hash'):
        read_cached_probe(tmp_path/'moved')
    inp=inputs/'G1-rep0000.npz'
    with np.load(inp,allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
    data['noise'][0,0,0]+=1;np.savez_compressed(inp,**data)
    with pytest.raises(ValueError,match='Actual input file'):
        execute_cached_probe(capsule,digest,probe,inputs,tmp_path/'changed-input')
    assert not list((tmp_path/'changed-input').glob('execution-*.npz'))
