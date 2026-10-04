"""Whole-repetition uncertainty checked against the public SciPy bootstrap."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.stats import bootstrap

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_complete_paired_loss_intervals_match_independent_scipy_oracle():
    from formal_uncertainty import create_plan, analyze_function
    ids=tuple(f'r{i:02}' for i in range(32))
    a=np.linspace(-1,2,32)
    b=.6*a + .2*np.sin(np.arange(32))
    plan=create_plan('uncertainty-contract','G1',ids,n_resamples=9999)
    report=analyze_function(plan,{'a':dict(zip(ids,a)), 'b':dict(zip(ids,b))},
                            dict(kind='analytic',value=0.,mcse=0.),pairs=[('a','b')])
    oracle=bootstrap((a,),lambda x,axis:np.mean(x*x,axis=axis),vectorized=True,
                     method='BCa',n_resamples=9999,batch=64,rng=np.random.default_rng(plan.rng_seed))
    pair=bootstrap((a,b),lambda x,y,axis:np.mean(x*x-y*y,axis=axis),vectorized=True,
                   paired=True,method='BCa',n_resamples=9999,batch=64,rng=np.random.default_rng(plan.rng_seed))
    actual=report['workflows']['a']['confidence_interval']
    paired=report['pairs'][0]['confidence_interval']
    assert actual['low']==pytest.approx(oracle.confidence_interval.low,rel=2e-12)
    assert actual['high']==pytest.approx(oracle.confidence_interval.high,rel=2e-12)
    assert paired['low']==pytest.approx(pair.confidence_interval.low,rel=2e-12)
    assert paired['high']==pytest.approx(pair.confidence_interval.high,rel=2e-12)
    np.testing.assert_allclose(report['bootstrap_statistics']['workflow:a'],oracle.bootstrap_distribution,rtol=2e-14,atol=1e-14)
    np.testing.assert_allclose(report['bootstrap_statistics']['pair:0'],pair.bootstrap_distribution,rtol=2e-14,atol=1e-14)
    assert report['pairs'][0]['validity_table']==dict(n11=32,n10=0,n01=0,n00=0)
    assert report['resampling']['independent_unit']=='complete_four_chain_repetition'


def test_archived_plan_replays_common_success_pairing_across_functions(tmp_path):
    from formal_uncertainty import create_plan, analyze_function, save_plan, load_plan
    ids=tuple(f'rep-{i}' for i in range(40))
    a=np.linspace(-2,3,40); b=.7*a+.1
    a[:6]=np.nan; b[6:12]=np.nan
    values=lambda x: {key:None if np.isnan(value) else float(value) for key,value in zip(ids,x)}
    plan=create_plan('missing-pair-contract','H1',ids)
    folder=tmp_path/'plan'
    save_plan(plan,folder)
    restored=load_plan(folder)
    assert restored.receipt()==plan.receipt()
    np.testing.assert_array_equal(restored.indices,plan.indices)
    report=analyze_function(restored,{'a':values(a),'b':dict(reversed(list(values(b).items())))},
                            dict(kind='analytic',value=0.,mcse=0.),pairs=[('a','b')])
    pair=report['pairs'][0]
    assert pair['validity_table']==dict(n11=28,n10=6,n01=6,n00=0)
    assert pair['unconditional_mean_loss_difference'] is None
    assert report['workflows']['a']['valid']==34
    oracle=bootstrap((a,b),lambda x,y,axis:np.nanmean(x*x-y*y,axis=axis),vectorized=True,
                     paired=True,method='BCa',n_resamples=9999,batch=64,rng=np.random.default_rng(plan.rng_seed))
    assert pair['confidence_interval']['low']==pytest.approx(oracle.confidence_interval.low,rel=2e-12)
    assert pair['confidence_interval']['high']==pytest.approx(oracle.confidence_interval.high,rel=2e-12)
    np.testing.assert_allclose(report['bootstrap_statistics']['pair:0'],oracle.bootstrap_distribution,atol=1e-14)
    scaled=analyze_function(restored,{'a':values(2*a),'b':values(2*b)},
                            dict(kind='analytic',value=0.,mcse=0.),pairs=[('a','b')])
    assert scaled['resampling']['sha256']==report['resampling']['sha256']
    np.testing.assert_allclose(scaled['bootstrap_statistics']['pair:0'],4*report['bootstrap_statistics']['pair:0'],atol=1e-14)
    with pytest.raises(FileExistsError):save_plan(plan,folder)


def test_unavailable_intervals_preserve_degeneracy_reference_and_overflow_reasons():
    from formal_uncertainty import create_plan, analyze_function
    ids=tuple(str(i) for i in range(32)); plan=create_plan('unavailable','W1',ids)
    const=dict.fromkeys(ids,0.)
    unresolved=analyze_function(plan,{'zero':const},dict(kind='unresolved',value=0.,mcse=None))
    row=unresolved['workflows']['zero']
    assert row['observed_estimate_mean']==0 and row['confidence_interval'] is None
    assert row['conditional_squared_discrepancy'] is None and row['interval_status']=='unresolved_reference'
    constant=analyze_function(plan,{'zero':const},dict(kind='analytic',value=1.,mcse=0.))
    row=constant['workflows']['zero']
    assert row['conditional_squared_discrepancy']==1 and row['confidence_interval'] is None
    assert row['interval_status'].startswith('degenerate_empirical')
    sparse={key:float(i) if i<4 else None for i,key in enumerate(ids)}
    small=analyze_function(plan,{'pilot':sparse},dict(kind='analytic',value=0.,mcse=0.))
    assert small['workflows']['pilot']['interval_status']=='fewer_than_20_valid_repetitions'
    assert small['workflows']['pilot']['valid']==4
    extreme=analyze_function(plan,{'huge':dict.fromkeys(ids,1e300),'zero':const},
                             dict(kind='analytic',value=0.,mcse=0.),pairs=[('huge','zero')])
    assert extreme['workflows']['huge']['interval_status']=='nonfinite_loss'
    assert extreme['workflows']['huge']['conditional_squared_discrepancy'] is None
    assert extreme['pairs'][0]['interval_status']=='nonfinite_loss'
    assert extreme['pairs'][0]['conditional_mean_loss_difference'] is None


def test_cost_summary_keeps_failed_run_costs_and_pairs_only_common_valid_runs():
    from formal_uncertainty import create_plan, analyze_costs
    ids=tuple(str(i) for i in range(32)); plan=create_plan('cost-contract','G2',ids)
    a=np.arange(1.,33.); b=1.5*a+.3
    a[:4]=100.;b[-4:]=50.
    sa=dict.fromkeys(ids,'valid'); sb=dict.fromkeys(ids,'valid')
    for key in ids[:4]:sa[key]='numerical_failure'
    for key in ids[-4:]:sb[key]='numerical_failure'
    report=analyze_costs(plan,{'a':dict(zip(ids,a)),'b':dict(zip(ids,b))},
                         {'a':sa,'b':sb},pairs=[('a','b')],phase='sampling')
    assert report['workflows']['a']['total_recorded_seconds']==918.
    assert report['workflows']['a']['unusable_output_cost_seconds']==400.
    assert report['workflows']['b']['total_recorded_seconds']==pytest.approx(817.4)
    assert report['workflows']['b']['unusable_output_cost_seconds']==200.
    assert report['workflows']['a']['failure_rate']==.125
    pair=report['pairs'][0]
    assert pair['validity_table']==dict(n11=24,n10=4,n01=4,n00=0)
    assert pair['ratio_definition']=='geometric_mean_of_A_seconds_divided_by_B_seconds'
    la=np.log(a);lb=np.log(b);la[:4]=np.nan;lb[-4:]=np.nan
    oracle=bootstrap((la,lb),lambda x,y,axis:np.nanmean(x-y,axis=axis),vectorized=True,
                     paired=True,method='BCa',n_resamples=9999,batch=64,rng=np.random.default_rng(plan.rng_seed))
    assert pair['ratio_confidence_interval']['low']==pytest.approx(np.exp(oracle.confidence_interval.low),rel=2e-12)
    assert pair['ratio_confidence_interval']['high']==pytest.approx(np.exp(oracle.confidence_interval.high),rel=2e-12)
    assert report['resampling']['sha256']==plan.sha256
