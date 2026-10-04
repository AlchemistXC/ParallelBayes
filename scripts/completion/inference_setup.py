"""Deterministic geometry for F3 development; no reference draws or tuning data.

The Laplace option is limited to named log-concave targets. It is a proposal
coordinate choice, not a posterior approximation used as inferential truth.
Failure never silently substitutes identity geometry or repairs eigenvalues.
"""
import time
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


def prepare_geometry(model,method='identity'):
    started=time.perf_counter();d=model.dimension;s=model.spec
    record=dict(target_id=model.target_id,method=method,reference_draws_used=False,
        eigenvalue_repairs=0,optimizer=None)
    if method=='identity':
        center=np.zeros(d);factor=np.eye(d)
    elif method=='laplace':
        kind=s['kind']
        if kind=='gaussian':
            center=np.asarray(s['mean'],float);factor=np.linalg.cholesky(s['covariance'])
            record['construction']='closed-form curvature from target parameters'
        elif kind in ('logistic','external_wells_distance','normal_mean'):
            if kind=='normal_mean':
                y=np.asarray(s['y']);x=np.ones((len(y),1));prior=1.
                def information(q):return np.asarray([[len(y)+1.]])
            else:
                x=np.asarray(s['X'],float) if kind=='logistic' else np.column_stack((np.ones(s['N']),np.asarray(s['dist'])/100.))
                prior=1./s['prior_scale']**2 if kind=='logistic' else 0.
                def information(q):
                    eta=np.einsum('ij,j->i',x,q,optimize=False);weights=expit(eta)*expit(-eta)
                    return np.einsum('ni,nj,n->ij',x,x,weights,optimize=False)+prior*np.eye(d)
            history=[]
            def callback(q):history.append(np.asarray(q).tolist())
            result=minimize(lambda q:-model.reference(q),np.zeros(d),
                jac=lambda q:-model.gradient_reference(q),hess=information,
                method='trust-exact',callback=callback,options=dict(gtol=1e-8,maxiter=300))
            center=np.asarray(result.x,float)
            error=float(np.max(np.abs(model.gradient_reference(center))))
            record['optimizer']=dict(method='scipy trust-exact',success=bool(result.success),
                message=str(result.message),iterations=int(result.nit),function_evaluations=int(result.nfev),
                gradient_evaluations=int(result.njev),hessian_evaluations=int(result.nhev),
                gradient_max_abs=error,iterates=history,
                acceptance='finite objective and max absolute analytic gradient <= 1e-7; optimizer flag retained')
            if not np.isfinite(model.reference(center)) or not np.isfinite(error) or error>1e-7:
                raise ValueError('Laplace center failed the recorded gradient criterion: '+str(record['optimizer']))
            precision=information(center)
            np.linalg.cholesky(precision)  # Reject nonpositive information, without repair.
            covariance=np.linalg.solve(precision,np.eye(d))
            factor=np.linalg.cholesky((covariance+covariance.T)/2)
            record['construction']='analytic observed information at numerical mode'
            record['information_eigenvalues']=np.linalg.eigvalsh(precision).tolist()
        else:raise ValueError('Laplace geometry unsupported for target kind: '+kind)
    else:raise ValueError('Unknown fixed geometry method')
    record.update(center=center.tolist(),factor=factor.tolist(),
        factor_condition_number=float(np.linalg.cond(factor)),
        setup_seconds=time.perf_counter()-started)
    return record
