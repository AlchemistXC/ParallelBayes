"""Cache statistics use whole input repetitions, never executor replays as n."""
from pathlib import Path
import copy
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def fixture(n=4):
    from batch_contract import create_tasks,WORKFLOWS
    from formal_measurement_plan import create_measurement_plan
    from formal_runtime import fingerprint
    identity='artificial-cache-statistics-fixture'
    tasks=create_tasks(identity,[dict(models=['G1'],replicates=list(range(n)),budgets=[8,16],workflows=list(WORKFLOWS))],batch_size=n)
    allocation=create_measurement_plan(identity,tasks,batch_size=n,selected_per_batch=n)
    bindings={};observations={}
    for probe in allocation['probes']:
        i=probe['replicate'];b=probe['budget']
        config=dict(kernel=probe['kernel'],executor=probe['executor'],device=probe['device'],chains=4,
                    draws=b+4,step_size=.1,initial=[[float(i),0.]]*4,atol=1e-10,rtol=1e-10,
                    window=4,max_iter=100,audit=False,on_failure='error')
        binding=dict(input_file_sha256=fingerprint(['input',i]),tape_sha256=fingerprint(['tape',i,b]),
                     target_id=fingerprint('artificial-target'),config=config)
        # Literal worked medians 2,4,8,16 versus 1 for sequential/Picard.
        median=([2.,4.,8.,16.][i%4] if probe['executor']=='sequential' else 1.)
        records=[dict(execution_index=j,has_prior_execution=j>0,status='candidate',samples_eligible=False,
                technical_output_valid=True,executor_wall_seconds=s,
                tape_sha256=binding['tape_sha256'],target_id=binding['target_id'],config=copy.deepcopy(config))
                 for j,s in enumerate([10.,median-.5,median,median+.5])]
        bindings[probe['id']]=binding
        observations[probe['id']]=dict(execution_outcomes=['valid']*4,records=records)
    return allocation,tasks,bindings,observations


def get_probe(allocation,workflow,rep,budget=8):
    return next(p for p in allocation['probes'] if (p['workflow'],p['replicate'],p['budget'])==(workflow,rep,budget))


def test_paired_cache_analysis_preserves_failed_missing_and_unstarted_selected_inputs():
    from cache_probe_analysis import create_cache_plan,analyze_cache_probes
    allocation,tasks,bindings,observations=fixture()
    seq='cpu-rwm-sequential';par='cpu-rwm-online_picard'
    failed=observations[get_probe(allocation,seq,1)['id']]
    failed['execution_outcomes'][0]='numerical_failure';failed['records'][0]['technical_output_valid']=False
    interrupted=observations[get_probe(allocation,seq,3)['id']]
    interrupted.update(execution_outcomes=['valid','infrastructure_interruption','not_run','not_run'],
                       records=[interrupted['records'][0],None,None,None])
    observations[get_probe(allocation,par,2)['id']]=dict(execution_outcomes=['not_run']*4,records=[None]*4)
    observations[get_probe(allocation,par,3)['id']]=dict(execution_outcomes=['resource_failure']+['not_run']*3,records=[None]*4)
    plan=create_cache_plan(allocation,tasks,'G1')
    report=analyze_cache_probes(allocation,tasks,plan,bindings,observations)
    a=report['workflows'][seq+'@8'];b=report['workflows'][par+'@8']
    pair=next(p for p in report['pairs'] if p['workflow_a']==seq+'@8')
    assert a['planned_inputs']==4 and a['available_cache_points']==2
    assert a['availability_counts']==dict(available=2,failed=1,interrupted=1,not_run=0,incomplete_record=0)
    assert b['availability_counts']==dict(available=2,failed=1,interrupted=0,not_run=1,incomplete_record=0)
    assert a['known_executor_seconds']==82. and a['complete_executor_seconds'] is None
    assert a['recorded_executions']==13 and a['planned_executions']==16
    assert a['mean_cached_seconds']==5. and a['confidence_interval'] is None
    assert pair['validity_table']==dict(n11=1,n10=1,n01=1,n00=1)
    assert pair['geometric_mean_ratio']==2. and pair['ratio_confidence_interval'] is None
    assert report['new_independent_repetitions']==0 and report['samples_eligible'] is False
    assert report['resampling']['planned_repetitions']==4
    assert all(p['resampling_plan_sha256']==plan.sha256 for p in report['pairs'])
    incomplete=dict(observations);incomplete.pop(next(iter(incomplete)))
    with pytest.raises(ValueError,match='planned probe'):
        analyze_cache_probes(allocation,tasks,plan,bindings,incomplete)


def test_cache_ratios_reject_unpaired_actual_inputs_and_primary_bootstrap_frames():
    from cache_probe_analysis import create_cache_plan,analyze_cache_probes
    from formal_uncertainty import create_plan
    allocation,tasks,bindings,observations=fixture()
    plan=create_cache_plan(allocation,tasks,'G1')
    primary=create_plan(allocation['primary_identity'],'G1',list(plan.replicate_ids))
    with pytest.raises(ValueError,match='companion'):
        analyze_cache_probes(allocation,tasks,primary,bindings,observations)
    pid=get_probe(allocation,'cpu-rwm-online_picard',0)['id']
    changed=copy.deepcopy(bindings);changed[pid]['input_file_sha256']='0'*64
    with pytest.raises(ValueError,match='input'):
        analyze_cache_probes(allocation,tasks,plan,changed,observations)
    # Each timing record can agree with its local configuration, while the two
    # methods still implement different kernels. The pair must also agree.
    changed=copy.deepcopy(bindings);obs=copy.deepcopy(observations)
    changed[pid]['config']['step_size']=.2
    for r in obs[pid]['records']:r['config']['step_size']=.2
    with pytest.raises(ValueError,match='paired configuration'):
        analyze_cache_probes(allocation,tasks,plan,changed,obs)
    changed=copy.deepcopy(bindings);obs=copy.deepcopy(observations)
    changed[pid]['tape_sha256']='1'*64
    for r in obs[pid]['records']:r['tape_sha256']='1'*64
    with pytest.raises(ValueError,match='tape'):
        analyze_cache_probes(allocation,tasks,plan,changed,obs)


def test_cache_interval_matches_scipy_on_whole_input_rows_and_saved_indices(tmp_path):
    import math
    import numpy as np
    from scipy.stats import bootstrap
    from cache_probe_analysis import create_cache_plan,analyze_cache_probes
    from formal_uncertainty import save_plan,load_plan
    allocation,tasks,bindings,observations=fixture(32)
    seq='cpu-rwm-sequential';par='cpu-rwm-online_picard'
    for i in range(4):
        obs=observations[get_probe(allocation,seq,i)['id']]
        obs['execution_outcomes'][0]='numerical_failure';obs['records'][0]['technical_output_valid']=False
    plan=create_cache_plan(allocation,tasks,'G1')
    save_plan(plan,tmp_path/'indices')
    loaded=load_plan(tmp_path/'indices')
    report=analyze_cache_probes(allocation,tasks,loaded,bindings,observations)
    pair=next(p for p in report['pairs'] if p['workflow_a']==seq+'@8')
    logs=np.tile(np.log([2.,4.,8.,16.]),8);logs[:4]=np.nan
    oracle=bootstrap((logs,),np.nanmean,vectorized=True,method='BCa',batch=64,n_resamples=9999,rng=np.random.default_rng(plan.rng_seed))
    assert report['resampling']['planned_repetitions']==32
    assert report['workflows'][seq+'@8']['recorded_executions']==128
    assert pair['validity_table']==dict(n11=28,n10=0,n01=4,n00=0)
    assert pair['geometric_mean_ratio']==pytest.approx(math.sqrt(32.))
    assert pair['confidence_interval']['low']==pytest.approx(oracle.confidence_interval.low,rel=2e-12)
    assert pair['confidence_interval']['high']==pytest.approx(oracle.confidence_interval.high,rel=2e-12)
    assert pair['ratio_confidence_interval']['low']==pytest.approx(math.exp(oracle.confidence_interval.low),rel=2e-12)
    assert loaded.sha256==plan.sha256 and np.array_equal(loaded.indices,plan.indices)
    # A numerically valid output whose executor receipt is lost does not acquire
    # a made-up time or become an algorithm failure.
    obs=observations[get_probe(allocation,seq,4)['id']];obs['records'][2]=None
    missing=analyze_cache_probes(allocation,tasks,plan,bindings,observations)
    row=missing['workflows'][seq+'@8']
    assert row['availability_counts']['incomplete_record']==1
    assert row['execution_outcome_counts']['valid']==124
    assert row['complete_executor_seconds'] is None
    # Degeneracy is withheld, even with >=20 nominal pairs.
    for p in allocation['probes']:
        if p['workflow']==seq and p['budget']==16:
            for j,t in enumerate([10.,1.5,2.,2.5]):observations[p['id']]['records'][j]['executor_wall_seconds']=t
    degenerate=analyze_cache_probes(allocation,tasks,plan,bindings,observations)
    pair=next(p for p in degenerate['pairs'] if p['workflow_a']==seq+'@16')
    assert pair['geometric_mean_ratio']==2. and pair['ratio_confidence_interval'] is None
    assert pair['interval_status']=='degenerate_empirical_loss_or_difference'
