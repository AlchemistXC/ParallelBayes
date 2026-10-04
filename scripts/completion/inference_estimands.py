"""Historical inference functions evaluated on original parameter outputs.

Same definitions as scripts/windows/analyze_study.py and the Mac study, plus
the seven already-audited wells functions. Coordinate choices do not alter them.
"""
import numpy as np
from scipy.special import expit
from scipy.stats import norm


def evaluate(spec,draws):
    x=np.asarray(draws,float)
    if x.ndim!=3 or x.shape[-1]<2 or not np.isfinite(x).all():raise ValueError('Finite original-parameter chain/draw/variable array required')
    while spec['kind']=='fixed_affine':spec=spec['base_spec']
    kind=spec['kind'];truth=None
    with np.errstate(over='raise',invalid='raise',divide='raise'):
        if kind=='gaussian':
            q=(x[...,0]-spec['mean'][0])/np.sqrt(spec['covariance'][0][0])
            values=np.stack((q,q*q,q>1),axis=-1)
            names=['standard_q1','standard_q1_squared','standard_q1_gt1'];truth=[0.,1.,float(norm.sf(1))]
        elif kind=='logistic':
            values=np.stack((x[...,0],x[...,1],expit(x[...,0]),x[...,0]>0),axis=-1)
            names=['q1','q2','sigmoid_q1','q1_positive']
        elif kind in ('funnel','funnel_noncentered'):
            v=x[...,0];z=x[...,1]*np.exp(-v/2)
            values=np.stack((v/3,np.tanh(v/3),x[...,1]>0,np.cos(z)),axis=-1)
            names=['v_over_3','tanh_v_over_3','x1_positive','cos_z1'];truth=[0.,0.,.5,float(np.exp(-.5))]
        elif kind=='mixture':
            values=np.stack((x[...,0]/np.sqrt(1+spec['separation']**2),x[...,0]>0,x[...,1],x[...,1]**2),axis=-1)
            names=['standard_q1','q1_positive','q2','q2_squared'];truth=[0.,.5,0.,1.]
        elif kind=='external_wells_distance':
            a=x[...,0];b=x[...,1]
            values=np.stack((a,b,a*a,b*b,expit(a),expit(a+b),b>0),axis=-1)
            names=['alpha','beta','alpha_squared','beta_squared','p_switch_0m','p_switch_100m','beta_positive']
        else:raise ValueError('Unsupported estimand target: '+kind)
    if not np.isfinite(values).all():raise FloatingPointError('Nonfinite estimand evaluation')
    return dict(values=values,names=names,analytic_reference=truth,parameter_scope='original model outputs, not affine sampling coordinates')
