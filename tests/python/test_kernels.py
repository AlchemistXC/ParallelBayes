import importlib.util
from pathlib import Path
import numpy as np
import pytest
import jax
import jax.numpy as jnp
from parallelbayes import sample, validate_model, make_model
from parallelbayes.models import benchmark_model
from parallelbayes.sampling import settings, random_tape, prepare
from parallelbayes.kernels import transition, numpy_reference
from parallelbayes.executors import affine_scan


@pytest.mark.parametrize('name', ['G1', 'G2', 'L1', 'L2', 'T1'])
def test_independent_density_gradient(name):
    assert validate_model(benchmark_model(name))['passed']


@pytest.mark.parametrize('kernel,executor', [('mala','sequential'),('rwm','sequential'),
    ('mala','quasi_deer'),('rwm','online_picard')])
@pytest.mark.parametrize('name', ['G1','G2','L1','T1'])
def test_fixed_tape_against_independent_reference(kernel,executor,name):
    result = sample(benchmark_model(name),dict(kernel=kernel,executor=executor,
        draws=64,window=16,step_size=0.005,chains=2,audit=True))
    assert result['status']=='completed', result['primary_diagnostics']
    assert result['audit']['acceptance_mismatches']==[0,0]
    assert max(result['audit']['max_abs_path_error']) < 1e-7


def test_partial_window_and_rejection_self_loops():
    for method,kernel in [('online_picard','rwm'),('quasi_deer','mala')]:
        r=sample({'kind':'gaussian','dimension':3},dict(executor=method,kernel=kernel,
            draws=37,window=8,step_size=0.5,audit=True))
        assert r['status']=='completed'
        assert r['draws'].shape==(1,37,3)
        q=np.vstack((np.zeros(3),r['draws'][0]))
        rejected=~r['diagnostics']['accept'][0]
        np.testing.assert_allclose(q[1:][rejected],q[:-1][rejected],atol=1e-9)


def test_solver_failure_kept_and_same_tape_fallback():
    spec={'kind':'gaussian','dimension':3}
    c=dict(executor='quasi_deer',draws=32,window=16,max_iter=1,step_size=.1)
    bad=sample(spec,c)
    assert bad['status']=='failed' and bad['draws'] is None
    fallback=sample(spec,dict(c,on_failure='sequential'))
    seq=sample(spec,dict(c,executor='sequential'))
    assert fallback['fallback'] and fallback['timing']['fallback']>0
    assert fallback['tape_sha256']==seq['tape_sha256']
    np.testing.assert_array_equal(fallback['draws'],seq['draws'])
    assert np.any(fallback['primary_diagnostics']['status'])


def test_picard_prefix_and_same_noise_replay():
    c=dict(kernel='rwm',executor='online_picard',draws=32,window=8,max_iter=1,
           step_size=1.5,on_failure='sequential')
    r=sample({'kind':'gaussian','dimension':2},c)
    assert r['fallback']
    seq=sample({'kind':'gaussian','dimension':2},dict(c,executor='sequential'))
    np.testing.assert_array_equal(r['draws'],seq['draws'])


def test_nonfinite_target_not_silently_repaired():
    m=make_model({'kind':'gaussian','dimension':2})
    m.log_density=lambda q: jnp.nan+jnp.sum(q)
    r=sample(m,dict(draws=8))
    assert r['status']=='failed' and r['draws'] is None
    assert r['diagnostics']['status'][0]==2


def test_memory_guard_before_large_allocation():
    with pytest.raises(MemoryError):
        sample({'kind':'gaussian','dimension':8},dict(draws=100000,memory_limit_mb=1))


@pytest.mark.parametrize('config',[dict(kernel='mala',executor='online_picard'),
    dict(kernel='nuts',executor='quasi_deer'),dict(step_size=0),dict(draws=1.2),dict(unknown=1)])
def test_capability_and_input_rejection(config):
    with pytest.raises(ValueError): sample({'kind':'gaussian','dimension':2},config)


def test_error_injection_jacobian_scale_acceptance():
    m=make_model({'kind':'lognormal','mu':.4,'sigma':1.3})
    m.log_density=lambda q: -0.5*jnp.sum(((q-.4)/1.3)**2)-jnp.sum(q)
    assert not validate_model(m)['passed']  # omitted exp-transform Jacobian
    correct=make_model({'kind':'gaussian','dimension':2})
    c=settings(dict(draws=64)); tape=random_tape(c,2)
    reference,acc=numpy_reference(correct,'mala',np.zeros(2),tape['noise'][0],
                                  tape['log_uniform'][0],c['step_size'])
    wrong,wrongacc=numpy_reference(correct,'mala',np.zeros(2),tape['noise'][0],
                                   tape['log_uniform'][0],c['step_size']*2)
    assert np.max(np.abs(reference-wrong)) > .01
    # Mutate the target used by the compiled kernel: acceptance now follows a
    # different variance; the independent fixed-tape oracle must detect branches.
    correct.log_density = lambda q: -50*jnp.sum(q*q)
    broken=sample(correct,dict(draws=64,step_size=.4,audit=True))
    assert broken["status"]=="failed" and broken["draws"] is None
    assert broken["audit"]["acceptance_mismatches"][0]>0


def test_affine_scan_matches_sequential_and_upstream():
    rng=np.random.default_rng(11)
    a=rng.uniform(-.8,.8,(32,4)); b=rng.normal(size=(32,4)); q0=rng.normal(size=4)
    q=q0.copy(); expected=[]
    for ai,bi in zip(a,b): q=ai*q+bi; expected.append(q.copy())
    actual=affine_scan(jnp.array(a),jnp.array(b),jnp.array(q0))
    np.testing.assert_allclose(actual,expected,atol=1e-12)
    path=Path(__file__).resolve().parents[2]/'software/parallel-mcmc-upstream/qdeer.py'
    module_spec=importlib.util.spec_from_file_location('upstream_qdeer',path)
    upstream=importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(upstream)
    original=upstream.diagonal_matmul_recursive(jnp.array(a),jnp.array(b),jnp.array(q0))[1:]
    np.testing.assert_allclose(actual,original,atol=1e-12)


def test_nuts_smoke_and_adaptation_cost():
    r=sample({'kind':'gaussian','dimension':2},dict(kernel='nuts',draws=32,warmup=64,chains=2))
    assert r['status']=='completed' and r['draws'].shape==(2,32,2)
    assert r['timing']['warmup']>0 and r['timing']['compile']>0
