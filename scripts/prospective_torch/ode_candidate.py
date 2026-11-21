"""Experimental fixed-step ODE target for qualification only, not formal use.

The four-stage RK solver uses a fixed, bounded number of subdivisions. A
finite answer is not evidence of sufficient integration accuracy: qualification
must compare the actual target, gradients and HVP against independent references.
"""
import numpy as np
import torch


class OdeCandidate:
    def __init__(self, observations, center, *, device="cpu", substeps=80, prior_scale=.5):
        obs = np.asarray(observations, dtype=np.float64)
        center = np.asarray(center, dtype=np.float64)
        if obs.shape != (21, 2) or center.shape != (8,) or not np.isfinite(obs).all() or not np.isfinite(center).all():
            raise ValueError("expected finite 21-by-2 log observations and eight log-prior centers")
        if type(substeps) is not int or not 1 <= substeps <= 1024:
            raise ValueError("substeps per year must be an integer between 1 and 1024")
        if not np.isfinite(prior_scale) or prior_scale <= 0:
            raise ValueError("prior scale must be positive and finite")
        self.observations = torch.as_tensor(obs, dtype=torch.float64, device=device)
        self.center = torch.as_tensor(center, dtype=torch.float64, device=device)
        self.substeps = substeps
        self.prior_scale = float(prior_scale)

    @staticmethod
    def _rhs(state, rates):
        alpha, beta, gamma, delta = rates.unbind(-1)
        x, y = state.exp().unbind(-1)
        return torch.stack((alpha-beta*y, delta*x-gamma), dim=-1)

    def trajectory(self, q):
        if q.shape[-1:] != (8,) or q.dtype != torch.float64 or q.device != self.center.device:
            raise ValueError("q must have last dimension eight and match the target device and float64 dtype")
        rates = q[..., :4].exp()
        state = q[..., 4:6]
        states = [state]
        h = 1.0/self.substeps
        for _ in range(20):
            for _ in range(self.substeps):
                k1 = self._rhs(state, rates)
                k2 = self._rhs(state + (h/2)*k1, rates)
                k3 = self._rhs(state + (h/2)*k2, rates)
                k4 = self._rhs(state + h*k3, rates)
                state = state + (h/6)*(k1 + 2*k2 + 2*k3 + k4)
            states.append(state)
        return torch.stack(states, dim=-2)

    def log_density(self, q):
        states = self.trajectory(q)
        standardized = (self.observations - states)*torch.exp(-q[..., None, 6:])
        prior = (q-self.center)/self.prior_scale
        return (-standardized.square().sum(dim=(-2, -1))/2
                - 21*q[..., 6:].sum(dim=-1) - prior.square().sum(dim=-1)/2)

    def functions(self, q):
        states = self.trajectory(q)
        return torch.stack((q[..., 0].exp(), states[..., -1, 0].exp()), dim=-1)
