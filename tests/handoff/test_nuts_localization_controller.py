"""Controller simulation only; deliberately does not certify a Windows sampler."""
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/followups'))
import run_nuts_localization as runner
from nuts_events import atomic_json,sha
from nuts_registry import Registry,MODELS,CONDITIONS,schedule
from nuts_runtime import seal


def setup_study(tmp_path):
    root=tmp_path/'study';root.mkdir();(root/'calls').mkdir();(root/'prepared-cases').mkdir();(root/'rng').mkdir()
    study=dict(schedule_seed=20261010,rscript='unused',r_library='unused')
    current=dict(binding_sha256='simulation',source_commit='simulation')
    atomic_json(root/'STUDY.json',study);atomic_json(root/'prepared-checksums.json',{})
    registry=Registry(root/'calls.sqlite',study);qualified=[]
    for i,(workers,enabled) in enumerate(CONDITIONS):
        item=dict(id=f'q{i}',phase='qualification',round=0,binding_sha256='simulation',workers=workers,diagnostics_enabled=enabled)
        registry.register(item);registry.finish(item['id'],dict(status='completed',managed_active_processes=0,kernel_terminal_verified=True));qualified.append(item['id'])
    for model in MODELS:
        atomic_json(root/'prepared-cases'/f'{model}.json',dict(target_spec={'dimension':1},target_id='simulation',
            initial=[[0.]]*4,chain_seeds=[1,2,3,4],original_task={'budget':4096},source_capsule={'controls':{
                'nuts_warmup':1024,'nuts_tree_depth':8,'nuts_target_accept':.8,'nuts_full_mass':False,'memory_limit_mb':2048}}))
        atomic_json(root/'rng'/f'{model}.json',{'states':['simulation']*4})
    protocol=dict(binding_sha256='simulation',study_sha256=sha(root/'STUDY.json'),
        prepared_sha256=sha(root/'prepared-checksums.json'),qualification_ids=qualified,
        schedule=schedule(),maximum_confirmation_calls=8,
        confirmation_pair_order=[[[4,True],[4,False]],[[1,True],[1,False]],[[1,True],[4,True]],[[1,False],[4,False]]])
    atomic_json(root/'protocol.json',protocol);atomic_json(root/'protocol.sha256.json',dict(sha256=sha(root/'protocol.json')))
    return root,study,current,registry


def test_full_finite_schedule_confirm_selection_and_zero_execution_resume(tmp_path,monkeypatch):
    root,study,current,registry=setup_study(tmp_path);executed=[]
    monkeypatch.setattr(runner,'qualification_check',lambda *args:{'passed':True})
    def simulated_execute(directory,study_root,request,reg):
        assert reg.register(request);executed.append(request['id']);directory.mkdir()
        status='failed' if request['model'] in MODELS[:6] and request['workers']==4 and request['diagnostics_enabled'] else 'completed'
        reg.finish(request['id'],seal(directory,dict(status=status,managed_active_processes=0,kernel_terminal_verified=True)))
    monkeypatch.setattr(runner,'execute',simulated_execute)
    runner.formal(root,study,current,registry)
    assert len(executed)==44 and len(registry.records())==48
    confirmed=[r['request'] for r in registry.records() if r['phase']=='confirmation']
    assert {r['model'] for r in confirmed}==set(MODELS[:4])
    assert all(r['workers']==4 for r in confirmed)
    assert sum(r['phase']=='main' for r in registry.records())==36
    runner.formal(root,study,current,registry)
    assert len(executed)==44 and len(registry.records())==48
    registry.close()


def test_frozen_binding_and_qualification_gate_stop_before_any_new_calls(tmp_path,monkeypatch):
    root,study,current,registry=setup_study(tmp_path)
    monkeypatch.setattr(runner,'execute',lambda *args:pytest.fail('Must not execute'))
    with pytest.raises(ValueError,match='Source/environment'):
        runner.formal(root,study,dict(current,binding_sha256='changed'),registry)
    monkeypatch.setattr(runner,'qualification_check',lambda *args:{'passed':False})
    with pytest.raises(ValueError,match='qualification'):
        runner.formal(root,study,current,registry)
    assert len(registry.records())==4
    registry.close()
