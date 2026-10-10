"""Adversarial metadata/input/qualification checks, no scientific executions."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'scripts/analysis')]
from compact_contract import create_plan,CompactPlan
from compact_freeze import protocol_document,MARKER_SCHEMA
from compact_execution import validate_worker_scope
from compact_cache_summary import summarize_probe,analyze
from formal_freeze import InputArchive,FreezeConflict
from formal_runtime import ResourceWait,fingerprint
from batch_contract import BatchPlan


def document(technical=False):
    plan=create_plan(ROOT,technical=technical)
    inventory={n:{k:r[k] for k in ('model','replicate','dimension','chains','steps')}|dict(sha256='1'*64,actual_sha256='2'*64)
        for n,r in plan['input_requirements'].items()}
    binding=dict(source_commit='3'*40,source_files={},required_versions={},required_R_version='fixture R',
        required_R_posterior='fixture posterior',windows_limits=dict(rss_bytes=8*1024**3,disk_start_bytes=4*1024**3),
        minimum_available_ram_bytes=12*1024**3,external_files={})
    return plan,protocol_document(plan,inventory,binding,ROOT)


def test_old_new_executable_schema_and_marker_mixing_rejected():
    plan,p=document(technical=True);new=CompactPlan(p);c,h=new.capsule(p['tasks'][0]['id'])
    with pytest.raises(ValueError):BatchPlan(p)
    req=dict(compact_execution_contract='windows-compact-contract-v1',native_runtime_schema='windows-owned-runtime-v2',phase='main')
    marker=dict(schema=MARKER_SCHEMA,source_files_sha256=fingerprint({}),source_commit=p['source_commit'],
        identity=p['identity'],protocol_sha256=p['protocol_sha256'],sampling_authorized_by_this_document=False,
        inputs=2,main_tasks=18,cache_probes=16,formal_scientific_repetitions=0)
    validate_worker_scope(c,req,marker)
    from formal_execution import validate_worker_scope as historical_scope
    with pytest.raises(ValueError):historical_scope(c,req,marker)
    for change in (dict(schema='formal-study-freeze-v1'),dict(inputs=216),dict(formal_scientific_repetitions=24),dict(source_files_sha256='9'*64)):
        with pytest.raises(ValueError):validate_worker_scope(c,req,dict(marker,**change))
    with pytest.raises(ValueError):validate_worker_scope(dict(c,compact_execution_contract='unknown'),req,marker)


def test_verified_actual_input_not_regenerated_and_tamper_refused(tmp_path,monkeypatch):
    import formal_freeze
    req=dict(model='G1',replicate=0,dimension=2,chains=4,steps=8,
        roles=['initial','noise','log_uniform','directions','nuts_seeds'])
    a=InputArchive(tmp_path/'fixture','artificial-compact-input-guard-v1',{'G1-rep0000.npz':req},{'source':'fixture'})
    first=a.prepare('G1-rep0000.npz',disk_floor_bytes=1)
    monkeypatch.setattr(formal_freeze,'build_payload',lambda *_:pytest.fail('Verified input regenerated'))
    assert a.prepare('G1-rep0000.npz',disk_floor_bytes=1)==first
    raw=a.directory/'inputs/G1-rep0000.npz';raw.write_bytes(raw.read_bytes()+b'changed')
    with pytest.raises(FreezeConflict):a.prepare('G1-rep0000.npz',disk_floor_bytes=1)


def test_preparation_disk_and_member_guard_before_rng(tmp_path,monkeypatch):
    import formal_freeze
    req=dict(model='G1',replicate=0,dimension=2,chains=4,steps=8,
        roles=['initial','noise','log_uniform','directions','nuts_seeds'])
    a=InputArchive(tmp_path/'fixture','artificial-compact-resource-guard-v1',{'G1-rep0000.npz':req},{'source':'fixture'})
    monkeypatch.setattr(formal_freeze,'build_payload',lambda *_:pytest.fail('Resource refusal invoked RNG'))
    monkeypatch.setattr(formal_freeze.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
    with pytest.raises(ResourceWait):a.prepare('G1-rep0000.npz',disk_floor_bytes=1)
    assert not list((a.directory/'intents').iterdir())
    monkeypatch.setattr(formal_freeze.shutil,'disk_usage',lambda _:SimpleNamespace(free=1024**3))
    with pytest.raises(MemoryError):a.prepare('G1-rep0000.npz',disk_floor_bytes=1,maximum_member_bytes=1)
    assert not list((a.directory/'intents').iterdir())


def records(config=None):
    config={} if config is None else config
    return [dict(execution_index=i,has_prior_execution=i>0,tape_sha256='tape',target_id='target',config=config,
        samples_eligible=False,status='candidate',technical_output_valid=True,executor_wall_seconds=float(i+1)) for i in range(4)]


@pytest.mark.parametrize('bad', ['failed_initial','failed_replay','missing','unknown_time'])
def test_no_success_subcall_median_and_unknown_time_kept(bad):
    r=records();probe=dict(id='fixture',primary_task_id='fixture primary',initial_calls=1,prepared_replays=3)
    if bad=='failed_initial':r[0].update(status='failed',technical_output_valid=False)
    elif bad=='failed_replay':r[2].update(status='failed',technical_output_valid=False)
    elif bad=='missing':r[2]=None
    else:r[2]['executor_wall_seconds']=None
    s=summarize_probe(probe,r,expected_tape_sha256='tape',expected_target_id='target',expected_config={})
    assert s['cached_seconds'] is None and not s['all_executions_valid'] and s['samples_eligible'] is False
    if bad=='unknown_time':assert s['complete_executor_seconds'] is None and s['known_executor_seconds']==7


def test_cache_n4_no_bootstrap_and_outer_interruption_invalidates_point(monkeypatch):
    p=create_plan(ROOT);alloc=p['cache_allocation'];probes=[x for x in alloc['probes'] if x['model']=='G1']
    import formal_uncertainty
    monkeypatch.setattr(formal_uncertainty,'create_plan',lambda *_:pytest.fail('n4 BCa was invoked'))
    bindings={};observations={}
    for probe in probes:
        cfg=dict(executor=probe['executor'],max_iter=512+probe['budget'] if probe['executor']=='online_picard' else 2048,step_size=.1)
        bindings[probe['id']]=dict(input_file_sha256='file',tape_sha256='tape',target_id='target',config=cfg)
        observations[probe['id']]=dict(records=records(cfg),execution_outcomes=['valid']*4,task_outcome='measurement_available')
    observations[probes[0]['id']]['task_outcome']='infrastructure_interruption'
    result=analyze(alloc,p['tasks'],'G1',bindings,observations)
    assert not result['confidence_intervals_generated'] and result['resampling'] is None
    assert all(w['planned_inputs']==4 for w in result['workflows'].values())
    assert all(x['ratio_confidence_interval'] is None for x in result['pairs'])
    row=next(r for r in result['probes'] if r['probe_id']==probes[0]['id'])
    assert row['cached_seconds'] is None and row['candidate_cached_seconds']==3
    assert row['known_executor_seconds']==10
