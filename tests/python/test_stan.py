from pathlib import Path
import numpy as np
import pytest
from parallelbayes import make_model,sample
from parallelbayes.models import benchmark_model
from parallelbayes.stan import cross_validate

ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.stan
@pytest.mark.parametrize('name',['G1','L1','T1'])
def test_bridgestan_against_native_density_gradient_transform_and_path(name):
    native=benchmark_model(name); spec=native.spec; d=native.dimension
    if spec['kind']=='gaussian':
        data=dict(D=d,mu=spec['mean'],precision=np.linalg.inv(spec['covariance']).tolist())
    elif spec['kind']=='logistic':
        data=dict(N=len(spec['y']),D=d,X=spec['X'],y=spec['y'],prior_scale=spec['prior_scale'])
    else: data=dict(mu=spec['mu'],sigma=spec['sigma'])
    stan=make_model(dict(kind='stan',stan_file=str(ROOT/'models/stan'/f'{spec["kind"]}.stan'),data=data,
                        coordinate_id=spec['coordinate_id']))
    points=np.array([np.zeros(d),np.ones(d),-np.ones(d),np.full(d,5.),np.full(d,-12.)])
    assert cross_validate(stan,native,points)['passed']
    for kernel in ['mala','rwm']:
        config=dict(kernel=kernel,draws=32,step_size=.005)
        a=sample(stan,config); b=sample(native,config)
        assert a['status']=='completed'
        np.testing.assert_allclose(a['draws'],b['draws'],atol=1e-10)
        np.testing.assert_array_equal(a['diagnostics']['accept'],b['diagnostics']['accept'])
    with pytest.raises(ValueError): sample(stan,dict(executor='quasi_deer'))
