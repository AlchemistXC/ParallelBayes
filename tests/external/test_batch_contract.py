"""A complete declared grid supplies stable tasks and shared actual inputs."""
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_declared_grid_is_complete_stable_and_pairs_actual_input_roles():
    from batch_contract import create_tasks
    groups=[dict(models=['G1','G2'],replicates=[0,1],budgets=[8,16],
                 workflows=['cpu-rwm-sequential','cpu-rwm-online_picard','cpu-nuts-spawn_chains'])]
    tasks=create_tasks('batch-contract-fixture',groups,batch_size=1)
    assert tasks==create_tasks('batch-contract-fixture',groups,batch_size=1)
    assert len(tasks)==len({t['id'] for t in tasks})==24
    assert [t['batch'] for t in tasks]==[0]*12+[1]*12
    assert len({t['input'] for t in tasks})==4
    for model in ['G1','G2']:
        for rep in [0,1]:
            rows=[t for t in tasks if t['model']==model and t['replicate']==rep]
            assert {(r['budget'],r['kernel'],r['executor']) for r in rows}=={
                (b,k,e) for b in [8,16] for k,e in [('rwm','sequential'),('rwm','online_picard'),('nuts','spawn_chains')]}
            assert len({t['input'] for t in rows})==1
    with pytest.raises(ValueError,match='Duplicate'):
        create_tasks('batch-contract-fixture',groups+groups,batch_size=1)
    with pytest.raises(ValueError,match='workflow'):
        create_tasks('batch-contract-fixture',[dict(groups[0],workflows=['cuda-nuts-spawn_chains'])],batch_size=1)


def test_compact_task_contract_keeps_budget_input_and_kernel_bound_to_plan():
    from batch_contract import BatchPlan,create_tasks,validate_capsule,mh_config
    from formal_runtime import fingerprint
    groups=[dict(models=['G1'],replicates=[0],budgets=[8,16],workflows=['cpu-rwm-online_picard'])]
    doc=dict(schema=1,identity='capsule-fixture',scope_kind='technical_batch_validation',required_platform='darwin',
        batch_size=32,groups=groups,tasks=create_tasks('capsule-fixture',groups),
        targets=[dict(name='G1',dimension=2,base_target_id='test-target',step_rwm=.2,step_mala=.1,geometry={})],
        controls=dict(chains=4,mh_discard=512,nuts_warmup=1024,nuts_tree_depth=8,nuts_target_accept=.8,
            nuts_full_mass=False,nuts_workers=4,nuts_threads=1,torch_threads=4,window=32,quasi_deer_max_iter=2048,
            atol=1e-10,rtol=1e-10,memory_limit_mb=2048,maximum_member_bytes=128*1024**2),
        inputs={'G1-rep0000.npz':dict(model='G1',replicate=0,dimension=2,chains=4,steps=528,sha256='a'*64,actual_sha256='b'*64)},
        source_files={},required_versions={},required_R_version='fixture',required_R_posterior='fixture',
        source_commit='fixture',cost_policy='separate ordinary process and post-exit audit',
        process_tree_rss_limit_bytes=4*1024**3,required_disk_bytes_per_task=512*1024**2)
    doc['protocol_sha256']=fingerprint(doc)
    plan=BatchPlan(doc);task=next(t for t in plan.tasks() if t['budget']==8)
    capsule,digest=plan.capsule(task['id']);validate_capsule(capsule,digest)
    assert 'tasks' not in capsule and capsule['task']['budget']==8
    assert capsule['input']['steps']==528 and capsule['protocol_sha256']==doc['protocol_sha256']
    config=mh_config(capsule,[[0.,0.]]*4)
    assert config['draws']==config['max_iter']==520
    assert config['audit'] is False and config['on_failure']=='error'
    doc['targets'][0]['step_rwm']=999.
    assert plan.capsule(task['id'])[0]['target']['step_rwm']==.2
    capsule['task']['kernel']='mala'
    with pytest.raises(ValueError,match='checksum'):validate_capsule(capsule,digest)
    with pytest.raises(ValueError,match='workflow'):validate_capsule(capsule,fingerprint(capsule))
