"""Explicit device and coordinate identities at the agreed target seam."""
from pathlib import Path
import copy
import math
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'r-package/inst/python'), str(ROOT/'scripts/completion')]


@pytest.mark.parametrize('device', ['cpu', 'cuda:0'])
def test_frozen_target_preserves_hand_density_jacobian_and_requested_device(device):
    import torch
    from inference_targets import build_target
    from parallelbayes.reference import benchmark_model
    if device.startswith('cuda') and not torch.cuda.is_available():
        pytest.skip('No CUDA here; Windows must execute this case')
    base = benchmark_model('G1')
    item = dict(name='G1', dimension=8, base_target_id=base.target_id,
                geometry=dict(center=[1.]*8, factor=(2*np.eye(8)).tolist()))
    model = build_target(item, None, device)
    q = torch.zeros(8, dtype=torch.float64, device=device)
    value = model.log_density(q)
    assert value.device == q.device and model.device.type == q.device.type
    # q_base = 1 + 2*z: log N up to its constant is -4 at z=0;
    # the change of variables contributes 8*log(2).
    assert float(value) == pytest.approx(-4+8*math.log(2), abs=1e-12)
    assert model.reference(np.zeros(8)) == pytest.approx(-4+8*math.log(2), abs=1e-12)
    np.testing.assert_allclose(torch.func.grad(model.log_density)(q).cpu(), [-2.]*8, atol=1e-12)
    np.testing.assert_array_equal(model.constrain(np.zeros(8)), np.ones(8))
    wrong = copy.deepcopy(item); wrong['base_target_id'] = 'another posterior'
    with pytest.raises(ValueError, match='target identity'):
        build_target(wrong, None, device)
    wrong = copy.deepcopy(item); wrong['geometry']['target_id'] = 'another posterior'
    with pytest.raises(ValueError, match='geometry identity'):
        build_target(wrong, None, device)
    with pytest.raises(ValueError, match='explicit cpu/cuda'):
        build_target(item, None, 'mps')
