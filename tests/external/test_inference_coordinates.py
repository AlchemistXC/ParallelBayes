"""F3: the agreed public target/coordinates and audited sampling seams."""
from pathlib import Path
import sys
import math
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'r-package/inst/python'))
sys.path.insert(0,str(ROOT/'examples'))


def test_affine_coordinates_preserve_hand_worked_gaussian_and_original_outputs():
    import torch
    from parallelbayes import make_model, validate_model
    from affine_target import affine_model
    base=make_model(dict(kind='gaussian',dimension=2,mean=[1.,-2.],covariance=[[4.,2.],[2.,10.]]),backend='torch')
    model=affine_model(base,[1.,-2.],[[2.,0.],[1.,3.]])
    z=np.array([.5,-1.]);q=torch.tensor(z,dtype=torch.float64)
    assert float(model.log_density(q))==pytest.approx(math.log(6)-.625,abs=1e-14)
    assert model.reference(z)==pytest.approx(math.log(6)-.625,abs=1e-14)
    np.testing.assert_allclose(model.gradient_reference(z),[-.5,1.],atol=1e-14)
    np.testing.assert_allclose(torch.func.grad(model.log_density)(q),[-.5,1.],atol=1e-14)
    np.testing.assert_allclose(model.constrain(z),[2.,-4.5],atol=1e-14)
    np.testing.assert_allclose(model.from_base([[2.,-4.5],[1.,-2.]]),[[.5,-1.],[0.,0.]],atol=1e-14)
    assert model.spec['base_target_id']==base.target_id
    assert model.names==base.names and model.target_id!=base.target_id
    assert validate_model(model,[[0.,0.],[.5,-1.],[4.,-3.]],backend='torch')['passed']


def test_fixed_geometry_can_be_estimated_from_a_target_without_reference_draws():
    from parallelbayes.reference import make_reference
    sys.path.insert(0,str(ROOT/'scripts/completion'))
    from inference_setup import prepare_geometry
    # The actual target is N((1,-2), [[4,2],[2,10]]); no sample covariance.
    base=make_reference(dict(kind='gaussian',dimension=2,mean=[1.,-2.],covariance=[[4.,2.],[2.,10.]]))
    fit=prepare_geometry(base,'laplace')
    np.testing.assert_allclose(fit['center'],[1.,-2.],atol=1e-10)
    np.testing.assert_allclose(fit['factor'],[[2.,0.],[1.,3.]],atol=1e-10)
    assert fit['target_id']==base.target_id
    assert fit['reference_draws_used'] is False
    # Binary intercept-only likelihood with N(0,1) prior, y=(0,1).
    # Mode zero; observed information 1 + 2/4 = 3/2.
    logistic=make_reference(dict(kind='logistic',X=[[1.],[1.]],y=[0,1],prior_scale=1))
    fit=prepare_geometry(logistic,'laplace')
    np.testing.assert_allclose(fit['center'],[0.],atol=1e-10)
    np.testing.assert_allclose(fit['factor'],[[math.sqrt(2/3)]],atol=1e-10)
    with pytest.raises(ValueError,match='unsupported'):
        prepare_geometry(make_reference(dict(kind='mixture',dimension=2)),'laplace')


def test_affine_composes_with_positive_transform_and_both_audited_executors():
    from parallelbayes import make_model,sample
    from affine_target import affine_model
    base=make_model(dict(kind='lognormal',mu=1.,sigma=2.),backend='torch')
    model=affine_model(base,[1.],[[2.]])
    tape=dict(noise=np.array([[[1.],[-1.]]]),log_uniform=np.array([[-1.,-1.]]),directions=np.ones((1,2,1)))
    rwm=sample(model,dict(kernel='rwm',executor='online_picard',chains=1,draws=2,window=2,step_size=.25),tape,backend='torch')
    assert rwm['status']=='completed' and rwm['audit']['passed']
    np.testing.assert_allclose(rwm['draws'][0,:,0],[math.exp(1.5),math.exp(1.)],rtol=1e-13)
    np.testing.assert_array_equal(rwm['accept'],[[True,True]])
    for executor in ['sequential','quasi_deer']:
        result=sample(model,dict(kernel='mala',executor=executor,chains=1,draws=2,window=2,step_size=.1,max_iter=32),tape,backend='torch')
        assert result['status']=='completed' and result['audit']['passed']
    with pytest.raises(ValueError,match='Singular'):
        affine_model(base,[1.],[[0.]])
