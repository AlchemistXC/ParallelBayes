from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.special import logsumexp,ndtr
from scipy.stats import multivariate_normal,multivariate_t
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/analysis'))
from rare_importance import Mixture,quality,batch_summary,LogisticTarget,fit_proposal_geometry


def proposal():return Mixture([-.8,.2],[[1.,.3],[.3,2.]],[0.,1.],[[.4,.15],[.15,1.3]],2.5)


def test_full_mixture_constants_and_event_support_against_scipy():
    m=proposal();x=np.array([[-.8,.2],[.2,.3],[3.,-4.],[0.,0.]])
    expected=np.column_stack([multivariate_t.logpdf(x,m.mean,m.cov,df=5),
        np.where(x[:,0]>0,multivariate_normal.logpdf(x,m.event_mean,m.event_cov)-np.log(ndtr(m.event_mean[0]/np.sqrt(m.event_cov[0,0]))),-np.inf),
        multivariate_normal.logpdf(x,np.zeros(2),np.eye(2)*2.5**2)])
    np.testing.assert_allclose(m.component_logpdf(x),expected,atol=2e-13,rtol=2e-13)
    np.testing.assert_allclose(m.logpdf(x),logsumexp(expected+np.log([.45,.45,.1]),axis=1),atol=2e-13)
    assert not np.allclose(m.logpdf(x),expected[:,0]) # omission of mixture components detected


def test_random_component_sampling_and_conditional_truncation():
    m=proposal();x,c=m.sample(np.random.default_rng(1784),120000);e=x[c==1]
    assert np.all(e[:,0]>0) and not np.any(e[:,0]==0)
    expected=np.sqrt(.4)*np.sqrt(2/np.pi)
    assert abs(e[:,0].mean()-expected)<.006
    residual=e[:,1]-1-m.reg[0]*e[:,0]
    assert abs(residual.mean())<.012
    assert abs(np.var(residual)-(1.3-.15**2/.4))<.03
    assert np.max(np.abs(np.bincount(c)/len(c)-m.weights))<.006


def test_normalized_gaussian_target_recovers_event_and_denominator():
    m=proposal();rng=np.random.default_rng(774);w=[];e=[]
    for i in range(8):
        x,c=m.sample(rng,12000)
        delta=x-np.array([-.8,.2]);cov=np.array([[1.,.3],[.3,2.]])
        truth=-np.log(2*np.pi)-.5*np.linalg.slogdet(cov)[1]-.5*np.einsum('bi,ij,bj->b',delta,np.linalg.inv(cov),delta)
        w.append(truth-m.logpdf(x));e.append(x[:,0]>0)
    r=batch_summary(w,e)
    assert abs(r['probability']-ndtr(-.8))<5*r['mcse']
    assert abs(np.exp(r['log_denominator_mean'])-1)<.02


def test_batch_delta_uses_joint_covariance_and_ratio_of_sums():
    rng=np.random.default_rng(83);w=[rng.normal(size=60) for _ in range(8)];e=[rng.random(60)<.2 for _ in range(8)]
    r=batch_summary(w,e);pairs=np.array([[np.mean(np.exp(x)*z),np.mean(np.exp(x))] for x,z in zip(w,e)])
    a,b=pairs.mean(0);g=np.array([1,-a/b])/b
    assert np.isclose(r['probability'],a/b)
    assert np.isclose(r['mcse'],np.sqrt(g@np.cov(pairs,rowvar=False)@g/8))
    assert not np.isclose(r['probability'],np.mean(pairs[:,0]/pairs[:,1]),rtol=1e-5)


def test_log_domain_prevents_raw_underflow():
    w=np.array([-1001.,-1002.,-1020.]);e=np.array([False,False,True])
    a=quality(w,e);b=quality(w+1000,e)
    assert a['probability']>0 and np.isclose(a['probability'],b['probability'])
    assert np.exp(w).sum()==0


def test_logistic_prior_defensive_bound_and_fit_geometry():
    t=LogisticTarget(dict(X=[[1,0],[1,1],[1,-1],[1,2]],y=[0,1,0,1],prior_scale=2.5))
    modes,r=fit_proposal_geometry(t);m=Mixture(*modes[0],*modes[1],2.5)
    x,c=m.sample(np.random.default_rng(99),100)
    assert np.all(t.logp(x)-m.logpdf(x)<=np.log(10)+1e-13)
    assert all(z['projected_gradient_max']<1e-4 for z in r)


def test_actual_proposals_resume_without_resampling_and_detect_tamper(tmp_path):
    from run_l2_importance import samples
    m=proposal();folder=tmp_path/'batch'
    a,c,new=samples(folder,m,128,[1,73],'test-identity')
    assert new
    b,d,new=samples(folder,m,128,[1,73],'test-identity')
    assert not new and np.array_equal(a,b) and np.array_equal(c,d)
    with pytest.raises(ValueError,match='Immutable'):samples(folder,m,128,[1,74],'test-identity')
    p=folder/'points.npz';p.write_bytes(p.read_bytes()+b'tamper')
    with pytest.raises(ValueError,match='recovery'):samples(folder,m,128,[1,73],'test-identity')


def test_weight_chunk_resume_and_tamper_without_new_points(tmp_path,monkeypatch):
    import run_l2_importance as runner
    t=LogisticTarget(dict(X=[[1,0],[1,1],[1,-1],[1,2]],y=[0,1,0,1],prior_scale=2.5));m=proposal();folder=tmp_path/'batch'
    x,c,new=runner.samples(folder,m,256,[3,72],'test-identity')
    monkeypatch.setattr(runner,'guard',lambda path:dict(rss_bytes=0,working_bytes=0))
    stats=dict(new_weight_chunks=0,reused_weight_chunks=0,rss_observed_max=0)
    a=runner.evaluate(folder,x,m,t,tmp_path,stats)
    b=runner.evaluate(folder,x,m,t,tmp_path,stats)
    assert stats['new_weight_chunks']==1 and stats['reused_weight_chunks']==1 and np.array_equal(a,b)
    p=folder/'weights-000000-000256.npy';p.write_bytes(p.read_bytes()+b'tamper')
    with pytest.raises(ValueError,match='recovery'):runner.evaluate(folder,x,m,t,tmp_path,stats)
