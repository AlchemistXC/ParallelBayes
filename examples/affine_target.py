"""Fixed affine coordinates through the existing public Model contract.

q = center + factor @ z. This changes coordinates and the isotropic MH kernel,
not the posterior in original outputs. Geometry must be fixed before sampling.
No adaptation, covariance estimation, regularization or backend translation.
"""
import numpy as np
from parallelbayes.reference import Model


def affine_model(base, center, factor):
    if not isinstance(base,Model) or base.backend not in ('numpy','torch'):
        raise ValueError('An explicit NumPy or torch Model is required')
    d=base.dimension
    center=np.array(center,dtype=float,copy=True)
    factor=np.array(factor,dtype=float,copy=True)
    if center.shape!=(d,) or factor.shape!=(d,d) or not np.isfinite(center).all() or not np.isfinite(factor).all():
        raise ValueError('Invalid fixed affine geometry')
    sign,logdet=np.linalg.slogdet(factor)
    if sign==0 or not np.isfinite(logdet):raise ValueError('Singular affine factor')
    def to_base(z):
        return np.asarray(z,dtype=float)@factor.T+center
    def from_base(q):
        a=np.asarray(q,dtype=float)
        if a.shape[-1:]!=(d,):raise ValueError('Invalid coordinate shape')
        return np.linalg.solve(factor,(a-center).reshape(-1,d).T).T.reshape(a.shape)
    def reference(z):
        return base.reference(to_base(z))+logdet
    def gradient(z):
        return factor.T@base.gradient_reference(to_base(z))
    spec=dict(kind='fixed_affine',dimension=d,coordinate_id='fixed-affine-'+base.spec['coordinate_id'],
        base_target_id=base.target_id,base_spec=base.spec,center=center.tolist(),factor=factor.tolist(),
        log_abs_determinant=float(logdet),coordinate_equation='q = center + factor @ z')
    model=Model(spec,d,reference,reference,gradient,lambda z:base.constrain(to_base(z)),list(base.names),base.backend)
    model.to_base=to_base;model.from_base=from_base
    if base.backend=='torch':
        import torch
        model.device=base.device
        c=torch.tensor(center,dtype=torch.float64,device=base.device)
        matrix=torch.tensor(factor,dtype=torch.float64,device=base.device)
        model.log_density=lambda z:base.log_density(c+matrix@z)+float(logdet)
        model.constrain_device=lambda z:base.constrain_device(z@matrix.T+c)
    return model
