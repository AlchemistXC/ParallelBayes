"""Independent NumPy target for hierarchical logistic fixed-tape auditing."""
import numpy as np
from scipy.special import expit


def log_density(q, trials, successes):
    mu, log_scale = q[:2]
    local = q[2:]
    logits = mu + np.exp(log_scale)*local
    likelihood = np.sum(successes*logits-trials*np.logaddexp(0., logits))
    return likelihood - (mu/2)**2/2 - log_scale**2/2 - np.dot(local, local)/2


def gradient(q, trials, successes):
    mu, log_scale = q[:2]
    local = q[2:]
    scale = np.exp(log_scale)
    residual = successes-trials*expit(mu+scale*local)
    return np.r_[residual.sum()-mu/4, residual@(scale*local)-log_scale, scale*residual-local]
