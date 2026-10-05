"""Prespecified probes preserve paired inputs without selecting successful runs."""
from pathlib import Path
import sys
import copy
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_probe_allocation_balances_batches_and_preserves_every_paired_slot():
    from batch_contract import create_tasks,WORKFLOWS
    from formal_measurement_plan import create_measurement_plan,validate_measurement_plan
    identity='measurement-allocation-fixture'
    tasks=create_tasks(identity,[dict(models=['G1','L1'],replicates=list(range(8)),
        budgets=[8,16],workflows=list(WORKFLOWS))],batch_size=4)
    plan=create_measurement_plan(identity,tasks,batch_size=4,selected_per_batch=2,replays=3)
    validate_measurement_plan(plan,tasks)
    assert len(tasks)==288 and len(plan['probes'])==128
    assert plan['total_executor_calls']==512 and plan['statistical_repetitions_added']==0
    assert len({p['primary_task_id'] for p in plan['probes']})==128
    assert all(p['kernel']!='nuts' and p['initial_calls']==1 and p['prepared_replays']==3 for p in plan['probes'])
    for model in ['G1','L1']:
        chosen=[p for p in plan['probes'] if p['model']==model]
        assert len({p['replicate'] for p in chosen})==4
        for batch in [0,1]:
            assert len({p['replicate'] for p in chosen if p['batch']==batch})==2
        for rep in {p['replicate'] for p in chosen}:
            rows=[p for p in chosen if p['replicate']==rep]
            assert len(rows)==16 and len({p['input'] for p in rows})==1
            assert {(p['device'],p['kernel'],p['executor'],p['budget']) for p in rows}=={
                (d,k,e,b) for d in ['cpu','cuda'] for b in [8,16] for k,e in
                [('rwm','sequential'),('rwm','online_picard'),('mala','sequential'),('mala','quasi_deer')]}
    # Canonical selection does not depend on runtime completion or incoming row order.
    assert create_measurement_plan(identity,list(reversed(tasks)),batch_size=4,selected_per_batch=2,replays=3)==plan
    invalid=copy.deepcopy(plan);invalid['probes'].pop()
    with pytest.raises(ValueError,match='allocation'):
        validate_measurement_plan(invalid,tasks)
    with pytest.raises(ValueError,match='complete|pair'):
        create_measurement_plan(identity,[t for t in tasks if t['workflow']!='cuda-rwm-sequential'],batch_size=4,selected_per_batch=2,replays=3)
    changed=copy.deepcopy(tasks);changed[0]['input']='elsewhere.npz'
    with pytest.raises(ValueError,match='identity'):
        create_measurement_plan(identity,changed,batch_size=4,selected_per_batch=2,replays=3)


def test_failed_probe_cannot_be_replaced_by_its_fast_valid_replays():
    from formal_measurement_plan import summarize_probe
    probe=dict(id='probe-fixture',primary_task_id='primary-fixture',prepared_replays=3,initial_calls=1)
    records=[dict(execution_index=i,has_prior_execution=i>0,status='candidate',samples_eligible=False,
        technical_output_valid=True,executor_wall_seconds=t,tape_sha256='a'*64,target_id='fixed',config={'window':32})
        for i,t in enumerate([9.,1.,7.,3.])]
    result=summarize_probe(probe,records,expected_tape_sha256='a'*64,expected_target_id='fixed',expected_config={'window':32})
    assert result['cached_seconds']==3. and result['known_executor_seconds']==20.
    assert result['samples_eligible'] is False and result['statistical_repetitions_added']==0
    failed=copy.deepcopy(records);failed[2].update(status='failed',technical_output_valid=False)
    result=summarize_probe(probe,failed,expected_tape_sha256='a'*64,expected_target_id='fixed',expected_config={'window':32})
    assert result['cached_seconds'] is None and result['known_executor_seconds']==20.
    assert result['valid_executions']==3 and not result['all_executions_valid']
    missing=records[:2]+[None,None]
    result=summarize_probe(probe,missing,expected_tape_sha256='a'*64,expected_target_id='fixed',expected_config={'window':32})
    assert result['cached_seconds'] is None and result['known_executor_seconds']==10.
    assert result['complete_executor_seconds'] is None and result['missing_executions']==2
    altered=copy.deepcopy(records);altered[1]['tape_sha256']='b'*64
    with pytest.raises(ValueError,match='input|identity'):
        summarize_probe(probe,altered,expected_tape_sha256='a'*64,expected_target_id='fixed',expected_config={'window':32})
