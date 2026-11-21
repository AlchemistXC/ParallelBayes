"""Development-only ODE adapter for fixed-tape sampler path validation."""
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "r-package/inst/python"))
from parallelbayes.reference import Model
from ode_candidate import OdeCandidate
import ode_reference


def build(observations, center, device, *, substeps=80, prior_scale=.5):
    target = OdeCandidate(observations, center, device=device, substeps=substeps, prior_scale=prior_scale)
    obs = np.asarray(observations, dtype=float).copy()
    center = np.asarray(center, dtype=float).copy()
    spec = {"kind":"experimental_prospective_ode", "coordinate_id":"log-eight-v1", "dimension":8,
            "observations":obs.tolist(), "center":center.tolist(), "prior_scale":prior_scale,
            "substeps_per_year":substeps, "status":"development_not_formal"}
    model = Model(spec, 8, target.log_density,
                  lambda q:ode_reference.density_and_gradient(q, obs, center, prior_scale)[0],
                  lambda q:ode_reference.density_and_gradient(q, obs, center, prior_scale)[1],
                  lambda q:np.asarray(q), ["log_alpha","log_beta","log_gamma","log_delta",
                                         "log_hare0","log_lynx0","log_sigma_hare","log_sigma_lynx"],
                  backend="torch")
    model.device = torch.device(device)
    model.constrain_device = lambda q:q
    return model
