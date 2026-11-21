"""Hierarchical logistic target for the prospective PyTorch benchmark."""
import numpy as np
import torch


class HierarchicalLogistic:
    def __init__(self, trials, successes, device):
        self.device = torch.device(device)
        trials = np.asarray(trials)
        successes = np.asarray(successes)
        if trials.shape != (128,) or successes.shape != (128,):
            raise ValueError("expected 128 group counts")
        if (not np.isfinite(trials).all() or not np.isfinite(successes).all()
                or np.any(trials < 0) or np.any(successes < 0)
                or np.any(successes > trials)
                or np.any(trials != np.floor(trials)) or np.any(successes != np.floor(successes))):
            raise ValueError("invalid binomial group counts")
        self.trials = torch.as_tensor(trials, dtype=torch.float64, device=self.device)
        self.successes = torch.as_tensor(successes, dtype=torch.float64, device=self.device)

    def log_density(self, q):
        mu, log_scale = q[0], q[1]
        local = q[2:]
        logits = mu + torch.exp(log_scale)*local
        zero = torch.zeros_like(logits)
        likelihood = (self.successes * (-torch.logaddexp(zero, -logits))
                      - (self.trials-self.successes)*torch.logaddexp(zero, logits)).sum()
        return likelihood - (mu/2).square()/2 - log_scale.square()/2 - local.square().sum()/2

    def functions(self, q):
        mu, log_scale = q[0], q[1]
        scale = torch.exp(log_scale)
        return torch.stack((mu, scale, torch.sigmoid(mu + scale*q[2:]).mean()))
