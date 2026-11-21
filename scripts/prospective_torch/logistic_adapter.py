"""Connect the new target to the existing PyTorch fixed-tape sampler."""
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"r-package/inst/python"))
from parallelbayes.reference import Model
from logistic import HierarchicalLogistic
import logistic_reference


def build(trials, successes, device):
    target = HierarchicalLogistic(trials, successes, device)
    trials = np.asarray(trials, dtype=float).copy()
    successes = np.asarray(successes, dtype=float).copy()
    spec = {"kind":"prospective_hierarchical_logistic", "coordinate_id":"noncentered-log-tau-v1",
            "dimension":130, "trials":trials.tolist(), "successes":successes.tolist(),
            "mu_prior_sd":2., "log_tau_prior_sd":1., "local_prior_sd":1.}
    model = Model(spec, 130, target.log_density,
                  lambda q: logistic_reference.log_density(q, trials, successes),
                  lambda q: logistic_reference.gradient(q, trials, successes),
                  lambda q: np.asarray(q), ["mu", "log_tau"] + [f"z{j}" for j in range(128)],
                  backend="torch")
    model.device = torch.device(device)
    model.constrain_device = lambda q: q
    return model
