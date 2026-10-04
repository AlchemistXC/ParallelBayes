"""Public Model contract and whole-workflow checks for the external wells case."""
import importlib.util
from pathlib import Path
import math
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]


def factory():
    spec=importlib.util.spec_from_file_location("external_wells",ROOT/"examples/external_wells.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_flat_target_preserves_distance_units_and_hand_worked_likelihood():
    # p(y=0 at 0m)=1/4, p(y=1 at 100m)=6/7: product 3/14.
    model=factory().make_wells(dict(N=2,dist=[0.,100.],switched=[0,1]))
    q=np.array([math.log(3),math.log(2)])
    assert model.log_density(q)==pytest.approx(math.log(3/14),abs=1e-14)
    np.testing.assert_allclose(model.gradient_reference(q),[-17/28,1/7],rtol=1e-14)
    np.testing.assert_array_equal(model.constrain(q),q)
    assert model.names==["alpha","beta[1]"]


def test_torch_target_derivatives_match_hand_worked_bernoulli_example():
    import torch
    model=factory().make_wells(dict(N=2,dist=[0.,100.],switched=[0,1]),backend="torch")
    q=torch.tensor([math.log(3),math.log(2)],dtype=torch.float64)
    grad=torch.func.grad(model.log_density)
    _,hvp=torch.func.jvp(grad,(q,),(torch.tensor([1.,-2.],dtype=torch.float64),))
    assert float(model.log_density(q))==pytest.approx(math.log(3/14),abs=1e-14)
    np.testing.assert_allclose(grad(q).numpy(),[-17/28,1/7],rtol=1e-14)
    np.testing.assert_allclose(hvp.numpy(),[-3/16+6/49,6/49],rtol=1e-14)
    assert model.device.type=="cpu" and model.backend=="torch"


def test_repeated_opposite_outcomes_provide_a_valid_propriety_certificate():
    f=factory()
    # Two paired logits are alpha and alpha+2*beta. Their linear change of
    # variables has determinant 2, so integral exp(-|u|-|v|) is 4/2=2.
    data=dict(N=6,dist=[0.,0.,100.,100.,200.,200.],switched=[0,1,0,1,0,1])
    proof=f.propriety_certificate(data)
    assert proof["certified"] is True
    assert proof["integral_upper_bound"]==pytest.approx(2.)
    assert len(proof["witnesses"])==2
    # No certificate must not be called a proof of an improper posterior.
    assert f.propriety_certificate(dict(N=2,dist=[0.,100.],switched=[0,1]))["certified"] is False
