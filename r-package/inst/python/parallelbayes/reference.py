"""Independent NumPy targets and serial oracle. No JAX or torch imports.

Analytical formulas retained from the 0.1.1 independent reference.
"""
from dataclasses import dataclass
from typing import Callable
import hashlib
import json
import numpy as np
from scipy.special import expit, logsumexp


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


@dataclass
class Model:
    spec: dict
    dimension: int
    log_density: Callable
    reference: Callable
    gradient_reference: Callable
    constrain: Callable
    names: list
    backend: str = "numpy"

    @property
    def target_id(self):
        return fingerprint(self.spec)


def make_reference(spec):
    spec = json.loads(json.dumps(spec))
    kind = spec.get("kind", "gaussian")
    dimension = spec.get("dimension", 8)
    if isinstance(dimension, bool) or not np.isfinite(dimension) or int(dimension) != dimension:
        raise ValueError("dimension must be an integer")
    d = int(dimension)
    if d < 1:
        raise ValueError("dimension must be positive")
    if kind == "stan":
        raise ValueError("NumPy oracle does not compile or translate Stan")
    if kind == "gaussian":
        mean = np.asarray(spec.get("mean", np.zeros(d)), dtype=float)
        covariance = np.asarray(spec.get("covariance", np.eye(d)), dtype=float)
        if mean.shape != (d,) or covariance.shape != (d, d) or not np.isfinite(mean).all() or not np.isfinite(covariance).all():
            raise ValueError("invalid Gaussian mean/covariance shape")
        if not np.allclose(covariance, covariance.T):
            raise ValueError("covariance must be symmetric")
        np.linalg.cholesky(covariance)
        precision = np.linalg.inv(covariance)
        ref = lambda q: -0.5 * np.einsum("i,ij,j->", q-mean, precision, q-mean)
        grad = lambda q: -np.einsum("ij,j->i", precision, q-mean)
        spec.update(mean=mean.tolist(), covariance=covariance.tolist())
    elif kind == "logistic":
        x, y = np.asarray(spec["X"], float), np.asarray(spec["y"], float)
        if x.ndim != 2 or y.shape != (x.shape[0],) or not np.isin(y, [0, 1]).all():
            raise ValueError("X must be a matrix and y a binary observation vector")
        if not np.isfinite(x).all():
            raise ValueError("nonfinite predictors")
        d = x.shape[1]
        if d < 1 or x.shape[0] < 1:
            raise ValueError("logistic data must have positive dimensions")
        scale = float(spec.get("prior_scale", 2.5))
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError("prior_scale must be positive")
        ref = lambda q: np.sum(y*(np.einsum("ij,j->i", x, q))-np.logaddexp(0., np.einsum("ij,j->i", x, q)))-0.5*np.sum((q/scale)**2)
        grad = lambda q: np.einsum("ij,i->j", x, y-expit(np.einsum("ij,j->i", x, q)))-q/scale**2
        spec.update(prior_scale=scale)
    elif kind == "lognormal":
        # theta = exp(q); lognormal density includes -log(theta), cancelled by Jacobian q.
        d = 1
        mu, sd = float(spec.get("mu", 0.)), float(spec.get("sigma", 1.))
        if not np.isfinite(sd) or not np.isfinite(mu) or sd <= 0:
            raise ValueError("sigma must be positive")
        ref = lambda q: -0.5*np.sum(((q-mu)/sd)**2)
        grad = lambda q: -(q-mu)/sd**2
        spec.update(mu=mu, sigma=sd)
    elif kind in ("funnel", "funnel_noncentered"):
        d = int(spec.get("dimension", 9))
        if d < 2: raise ValueError("funnel dimension must be >= 2")
        if kind == "funnel":
            ref = lambda q: -q[0]**2/18.-(d-1)*q[0]/2.-.5*np.sum(q[1:]**2)*np.exp(-q[0])
            def grad(q):
                return np.concatenate(([-q[0]/9.-(d-1)/2.+.5*np.sum(q[1:]**2)*np.exp(-q[0])],-q[1:]*np.exp(-q[0])))
        else:
            ref = lambda q: -.5*(q[0]**2/9.+np.sum(q[1:]**2))
            grad = lambda q: np.concatenate(([-q[0]/9.],-q[1:]))
    elif kind == "mixture":
        separation = float(spec.get("separation", 5.))
        if not np.isfinite(separation) or separation <= 0: raise ValueError("invalid separation")
        means=np.zeros((2,d));means[:,0]=[-separation,separation]
        ref = lambda q: logsumexp(-.5*np.sum((q-means)**2,axis=1))-np.log(2.)
        def grad(q):
            weights=-.5*np.sum((q-means)**2,axis=1); weights=np.exp(weights-logsumexp(weights))
            return np.sum(weights[:,None]*(means-q),axis=0)
        spec.update(separation=separation)
    elif kind == "normal_mean":
        # Conjugate generative fixture for end-to-end SBC (prior N(0,1), noise sd=1).
        d = 1
        y = np.asarray(spec["y"], float)
        if y.ndim != 1 or not len(y) or not np.isfinite(y).all(): raise ValueError("invalid observations")
        ref = lambda q: -0.5*np.sum(q*q)-0.5*np.sum((y-q[0])**2)
        grad = lambda q: np.asarray([np.sum(y)-(len(y)+1)*q[0]])
    else:
        raise ValueError(f"unsupported target kind: {kind}")
    spec["kind"], spec["dimension"] = kind, d
    spec.setdefault("coordinate_id", "log-positive" if kind == "lognormal" else "identity")
    transform = np.exp if kind == "lognormal" else lambda q: q
    if kind == "funnel_noncentered":
        transform = lambda q: np.concatenate((q[..., :1], q[..., 1:]*np.exp(q[..., :1]/2)), axis=-1)
    return Model(spec, d, ref, ref, grad, transform,
                 ["theta" if kind == "lognormal" else f"q[{i+1}]" for i in range(d)])


def benchmark_model(name, seed=20261003):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 11]))
    if name == "G1":
        return make_reference({"kind": "gaussian", "dimension": 8})
    if name == "G2":
        rotation, _ = np.linalg.qr(rng.normal(size=(64, 64)))
        cov = np.einsum("ik,jk,k->ij", rotation, rotation, np.geomspace(1., 100., 64))
        return make_reference({"kind": "gaussian", "dimension": 64, "covariance": cov.tolist()})
    if name in ("L1", "L2"):
        n = 256 if name == "L1" else 4096
        data_rng = np.random.default_rng(np.random.SeedSequence([seed, 12, n]))
        beta = rng.normal(0, 2.5, 8)
        x = data_rng.normal(size=(n, 8))
        x[:, 0] = 1
        x[:, 1:] = (x[:, 1:]-x[:, 1:].mean(0))/x[:, 1:].std(0)
        y = data_rng.binomial(1, expit(np.einsum("ij,j->i", x, beta)))
        return make_reference({"kind": "logistic", "X": x.tolist(), "y": y.tolist(),
                           "generator_seed": seed, "generator_beta": beta.tolist()})
    if name in ("H1", "H2"):
        return make_reference(dict(kind="funnel" if name=="H1" else "funnel_noncentered",dimension=9))
    if name == "M1":
        return make_reference(dict(kind="mixture",dimension=8,separation=5.))
    if name == "A1":
        d=64; phi=.9
        prior=phi**np.abs(np.arange(d)[:,None]-np.arange(d)[None,:])
        innovations=rng.normal(size=d); latent=np.empty(d); latent[0]=innovations[0]
        for i in range(1,d): latent[i]=phi*latent[i-1]+np.sqrt(1-phi**2)*innovations[i]
        y=latent+rng.normal(size=d)
        precision=np.linalg.inv(prior)+np.eye(d)
        covariance=np.linalg.inv(precision)
        mean=np.einsum("ij,j->i",covariance,y)
        return make_reference(dict(kind="gaussian",dimension=d,mean=mean.tolist(),covariance=covariance.tolist(),
                               family="latent_AR1_gaussian",phi=phi,y=y.tolist(),generator_seed=seed))
    if name == "T1":
        return make_reference({"kind": "lognormal"})
    raise ValueError(f"unknown benchmark: {name}")


class ReferenceFailure(FloatingPointError):
    """Available prefix and stopping location from an independent serial kernel."""
    def __init__(self, message, draws, accepts, step, state):
        super().__init__(message)
        self.draws=np.asarray(draws).reshape(-1,len(state))
        self.accepts=np.asarray(accepts,dtype=bool)
        self.step=step
        self.state=np.asarray(state).copy()


def numpy_reference(model, kernel, q0, noise, logu, step_size, strict=True):
    q = np.array(q0, float, copy=True)
    draws, accepts = [], []
    for index,(z,u) in enumerate(zip(noise,logu)):
        try:
            lp = model.reference(q)
            if kernel == "mala":
                g = model.gradient_reference(q)
                proposed = q+step_size*g+np.sqrt(2*step_size)*z
                g2 = model.gradient_reference(proposed)
                rev, fwd = q-proposed-step_size*g2, proposed-q-step_size*g
                ratio = model.reference(proposed)-lp-(np.sum(rev**2)-np.sum(fwd**2))/(4*step_size)
            else:
                proposed = q+step_size*z
                ratio = model.reference(proposed)-lp
            if strict and (not np.isfinite(lp) or not np.isfinite(ratio) or not np.isfinite(proposed).all()):
                raise FloatingPointError("nonfinite target, proposal or acceptance ratio")
            accepted = bool(u < ratio)
            if accepted:
                q = proposed
            draws.append(q.copy())
            accepts.append(accepted)
        except (RuntimeError,ValueError,FloatingPointError,OverflowError) as exc:
            raise ReferenceFailure(str(exc),draws,accepts,index,q) from exc
    return np.asarray(draws), np.asarray(accepts)
