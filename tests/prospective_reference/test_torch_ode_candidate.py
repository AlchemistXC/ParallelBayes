from pathlib import Path
import json
import sys

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_torch"))
sys.path.insert(0, str(Path(__file__).parent))
from ode_candidate import OdeCandidate
from ode_reference import density_and_gradient, states_and_sensitivities
from validate_torch_ode_real_candidate import validate


def test_batch_matches_individual_and_gradients():
    center = np.log([.5,.025,.75,.025,24,12,.2,.2])
    model = OdeCandidate(np.zeros((21,2)), center, substeps=2)
    q = torch.tensor(np.stack([center, center+.01]), dtype=torch.float64, requires_grad=True)
    batch = model.log_density(q)
    separate = torch.stack([model.log_density(row) for row in q])
    torch.testing.assert_close(batch, separate, rtol=1e-13, atol=1e-13)
    assert torch.isfinite(torch.autograd.grad(batch.sum(), q)[0]).all()
    assert model.trajectory(q).shape == (2,21,2)


def test_invalid_configuration_rejected():
    center = np.log([.5,.025,.75,.025,24,12,.2,.2])
    with pytest.raises(ValueError):
        OdeCandidate(np.zeros((21,2)), center, substeps=1025)
    model = OdeCandidate(np.zeros((21,2)), center, substeps=1)
    with pytest.raises(ValueError):
        model.log_density(torch.zeros(8, dtype=torch.float32))


def test_candidate_hash_mismatch_rejected_before_output(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"data_sha256":"0"*64, "initials_sha256":"0"*64}))
    (tmp_path / "data.npz").write_bytes(b"tampered")
    output = tmp_path / "result.json"
    with pytest.raises(ValueError, match="hash mismatch"):
        validate(tmp_path, output, 80)
    assert not output.exists()


def test_independent_scipy_gradient_matches_density_difference():
    center = np.log([.5,.025,.75,.025,24,12,.2,.2])
    states, _ = states_and_sensitivities(center)
    observations = states + np.random.default_rng(891).normal(scale=.2,size=states.shape)
    _, gradient = density_and_gradient(center, observations, center, .5)
    h = 1e-5
    numeric = []
    for direction in np.eye(8):
        upper = density_and_gradient(center+h*direction,observations,center,.5)[0]
        lower = density_and_gradient(center-h*direction,observations,center,.5)[0]
        numeric.append((upper-lower)/(2*h))
    np.testing.assert_allclose(gradient, numeric, rtol=1e-6, atol=2e-5)
