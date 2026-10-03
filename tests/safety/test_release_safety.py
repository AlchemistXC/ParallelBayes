import numpy as np
import pytest
from parallelbayes import sample,make_model
from parallelbayes.sampling import settings


def tape(n=1,d=1):
    return dict(noise=np.zeros((1,n,d)),log_uniform=np.full((1,n),-1.),directions=np.ones((1,n,d)))


@pytest.mark.parametrize('mu',[1000.,-1000.])
@pytest.mark.parametrize('provider',['native',pytest.param('stan',marks=pytest.mark.stan)])
def test_extreme_positive_transform_cannot_return_normal_draws(mu,provider):
    model=make_model({'kind':'lognormal','mu':mu})
    if provider=='stan':model.backend='bridgestan';model.compile_seconds=0.
    r=sample(model,{'draws':1,'initial':[mu],'audit':provider=='native'},tape())
    assert r['status']=='failed' and r['draws'] is None
    assert r['failed_trajectory'][0,0,0]==mu
    assert r['transform_error']
    if provider=='native':assert r['stopping_reason']=='transform_failed'


def test_partial_block_ignores_fictitious_suffix():
    p=np.array([[1.,.5],[.5,1.]])
    t=tape(5,2);t['noise'][0,-1,0]=1.
    r=sample({'kind':'gaussian','dimension':2,'covariance':np.linalg.inv(p).tolist()},
        {'draws':5,'window':4,'max_iter':1,'step_size':.1,'executor':'quasi_deer','audit':True},t)
    assert r['status']=='completed'
    np.testing.assert_allclose(r['draws'][0,-1],[np.sqrt(.2),0.])


def test_fallback_preserves_primary_trajectory():
    c={'draws':31,'window':8,'max_iter':1,'executor':'quasi_deer','on_failure':'sequential','audit':True}
    r=sample({'kind':'gaussian','dimension':3},c)
    assert r['status']=='completed' and r['fallback']
    assert r['primary_failed_trajectory'].shape==r['draws'].shape
    assert np.any(r['primary_diagnostics']['status'])


def test_oracle_exception_preserves_native_raw_path(monkeypatch):
    import parallelbayes.sampling as sampling
    def bad(*args,**kwargs):raise FloatingPointError('injected oracle failure')
    monkeypatch.setattr(sampling,'numpy_reference',bad)
    r=sample({'kind':'gaussian','dimension':1},{'draws':8,'audit':True})
    assert r['status']=='failed' and r['failed_trajectory'].shape==(1,8,1)
    assert 'injected' in r['audit']['error']


@pytest.mark.stan
def test_stan_provider_retains_partial_failed_chain():
    from parallelbayes.stan import sample_stan
    model=make_model({'kind':'gaussian','dimension':1})
    model.backend='bridgestan';model.compile_seconds=0.
    calls=[0]
    def density(q):
        calls[0]+=1
        if calls[0]>4:raise RuntimeError('injected failure at third transition')
        return -.5*np.sum(q*q)
    model.reference=density
    r=sample_stan(model,settings({'kernel':'rwm','draws':4}),tape(4))
    assert r['status']=='failed' and r['diagnostics']['completed_steps'].tolist()==[2]
    assert np.isfinite(r['failed_trajectory'][0,:2]).all()
    assert np.isnan(r['failed_trajectory'][0,2:]).all()


def test_nuts_output_gate_retains_unconstrained_path():
    model=make_model({'kind':'gaussian','dimension':1})
    model.constrain=lambda q:np.full_like(q,np.inf)
    r=sample(model,{'kernel':'nuts','draws':4,'warmup':32})
    assert r['status']=='failed' and r['draws'] is None
    assert r['failed_trajectory'].shape==(1,4,1) and r['transform_error']


def test_resume_environment_change_is_rejected(tmp_path,monkeypatch):
    from parallelbayes.experiment import freeze,run_protocol
    root=tmp_path/'root';(root/'environment/locks').mkdir(parents=True)
    (root/'environment/locks/python-core.txt').write_text('')
    protocol=tmp_path/'p.json'
    freeze(protocol,dict(platforms=['cpu'],models={'g':{'kind':'gaussian','dimension':1}},
        defaults={'draws':4},tasks=[dict(model='g',config={})]),root)
    output=tmp_path/'runs';run_protocol(protocol,output,root)
    assert len(list((output/'sessions').glob('*.json')))==1
    monkeypatch.setenv('OMP_NUM_THREADS','77')
    with pytest.raises(ValueError,match='environment changed'):run_protocol(protocol,output,root)


@pytest.mark.stan
def test_stan_cannot_silently_ignore_requested_independent_audit():
    model=make_model({'kind':'gaussian','dimension':1});model.backend='bridgestan'
    with pytest.raises(ValueError,match='unavailable'):
        sample(model,{'audit':True})


def test_transitive_lock_tampering_is_rejected(tmp_path):
    from parallelbayes.experiment import freeze,load_protocol
    locks=tmp_path/'environment/locks';locks.mkdir(parents=True)
    (locks/'python-core.txt').write_text('')
    extra=locks/'python-runtime-transitive.txt';extra.write_text('numpy==2.2.6\n')
    protocol=tmp_path/'p.json';freeze(protocol,{},tmp_path)
    load_protocol(protocol,tmp_path)
    extra.write_text('numpy==2.2.5\n')
    with pytest.raises(ValueError,match='Transitive'):load_protocol(protocol,tmp_path)
