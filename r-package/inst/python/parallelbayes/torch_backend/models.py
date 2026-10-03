"""Torch targets behind the shared Model numerical interface.

Only continuous latent parameters are sampled; logistic observations are binary.
The independent oracle lives in parallelbayes.reference and never calls torch.
"""
import numpy as np
import torch
from ..reference import Model, make_reference


def make_model(spec, device="cpu"):
    ref = make_reference(spec)
    s, d = ref.spec, ref.dimension
    kind = s["kind"]
    device = torch.device(device)
    if device.type not in ("cpu", "cuda"):
        raise ValueError("only native cpu/cuda supported")
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; CPU substitution is forbidden")
    def tensor(x):
        return torch.as_tensor(x, dtype=torch.float64, device=device)
    if kind == "gaussian":
        mean = tensor(s["mean"])
        precision = tensor(np.linalg.inv(np.asarray(s["covariance"])))
        def logp(q):
            delta = q - mean
            return -0.5 * delta @ precision @ delta
    elif kind == "logistic":
        x, y = tensor(s["X"]), tensor(s["y"])
        scale = s["prior_scale"]
        def logp(q):
            eta = x @ q
            return (y * eta - torch.logaddexp(torch.zeros_like(eta), eta)).sum() - 0.5 * (q / scale).square().sum()
    elif kind == "lognormal":
        def logp(q):
            # lognormal(exp(q)) + log|d exp(q)/dq|, algebraically cancelled.
            return -0.5 * ((q - s["mu"]) / s["sigma"]).square().sum()
    elif kind == "funnel":
        def logp(q):
            return -q[0].square()/18 - (d-1)*q[0]/2 - 0.5*q[1:].square().sum()*torch.exp(-q[0])
    elif kind == "funnel_noncentered":
        def logp(q):
            return -0.5*(q[0].square()/9 + q[1:].square().sum())
    elif kind == "mixture":
        means = np.zeros((2,d)); means[:,0] = [-s["separation"], s["separation"]]
        means = tensor(means)
        def logp(q):
            return torch.logsumexp(-0.5*(q-means).square().sum(-1), dim=0)-np.log(2.)
    elif kind == "normal_mean":
        y = tensor(s["y"])
        def logp(q):
            return -0.5*q.square().sum()-0.5*(y-q[0]).square().sum()
    else:
        raise ValueError("unimplemented torch target")
    def constrain(q):
        if kind == "lognormal":
            return torch.exp(q)
        if kind == "funnel_noncentered":
            return torch.cat((q[...,:1], q[...,1:]*torch.exp(q[...,:1]/2)), dim=-1)
        return q
    model = Model(s, d, logp, ref.reference, ref.gradient_reference,
                  ref.constrain, ref.names, backend="torch")
    model.device = device
    model.constrain_device = constrain
    return model


def validate_model(spec, points=None):
    model = spec if isinstance(spec, Model) else make_model(spec)
    d = model.dimension
    points = np.asarray(points if points is not None else [np.zeros(d),np.ones(d),-np.ones(d),np.full(d,5.)],float)
    if points.ndim != 2 or points.shape[1] != d or not np.isfinite(points).all():
        raise ValueError("invalid validation points")
    gradient = torch.func.grad(model.log_density)
    rows = []
    for p in points:
        q = torch.tensor(p,dtype=torch.float64,device=model.device)
        v = torch.ones_like(q)
        val = float(model.log_density(q).detach().cpu())
        g = gradient(q).detach().cpu().numpy()
        _, hv = torch.func.jvp(gradient,(q,),(v,))
        # Independent derivative of analytical NumPy gradient by central difference.
        eps = 1e-5
        expected = (model.gradient_reference(p+eps)-model.gradient_reference(p-eps))/(2*eps)
        theta = model.constrain_device(q).detach().cpu().numpy()
        rows.append(dict(density_offset=val-float(model.reference(p)),
                         gradient=float(np.max(np.abs(g-model.gradient_reference(p)))),
                         hvp=float(np.max(np.abs(hv.detach().cpu().numpy()-expected))),
                         constrain=float(np.max(np.abs(theta-model.constrain(p))))))
    offset = rows[0]["density_offset"]
    errors = dict(relative_density=max(abs(r["density_offset"]-offset) for r in rows),
                  gradient=max(r["gradient"] for r in rows),
                  hvp=max(r["hvp"] for r in rows),constrain=max(r["constrain"] for r in rows))
    return dict(target_id=model.target_id, device=str(model.device), errors=errors,
                passed=all(np.isfinite(v) for v in errors.values()) and errors["relative_density"]<1e-8
                and errors["gradient"]<1e-7 and errors["hvp"]<1e-5 and errors["constrain"]<1e-8,
                hvp_reference="central difference of independent analytic NumPy gradient; epsilon=1e-5")
