"""Independent iid mixture reference; not MCMC and not a certified error bound."""
import math
import numpy as np
from scipy.special import expit, log_expit, logsumexp, gammaln, log_ndtr
from scipy.stats import truncnorm
from scipy.optimize import minimize


class LogisticTarget:
    def __init__(self, spec):
        self.x=np.asarray(spec['X'],dtype=np.float64);self.y=np.asarray(spec['y'],dtype=np.float64)
        self.scale=float(spec['prior_scale']);self.d=self.x.shape[1]
        if (self.x.ndim!=2 or self.y.shape!=(self.x.shape[0],) or not np.isfinite(self.x).all()
            or not np.isin(self.y,[0,1]).all() or self.scale<=0):raise ValueError('Invalid logistic target')
        self.signed=2*self.y-1
        self.log_prior_constant=-self.d*math.log(self.scale*math.sqrt(2*math.pi))

    def logp(self, q):
        q=np.atleast_2d(q)
        if q.shape[1]!=self.d or len(q)>256:raise ValueError('Target chunk/dimension guard')
        eta=np.einsum("bi,ni->bn",q,self.x)
        return log_expit(eta*self.signed).sum(axis=1)-np.sum(q*q,axis=1)/(2*self.scale**2)+self.log_prior_constant

    def gradient(self,q):return np.einsum("ni,n->i",self.x,self.y-expit(np.einsum("ni,i->n",self.x,q)))-q/self.scale**2

    def information(self,q):
        eta=np.einsum("ni,i->n",self.x,q);w=expit(eta)*expit(-eta)
        return np.einsum("ni,n,nj->ij",self.x,w,self.x)+np.eye(self.d)/self.scale**2


def covariance(target,q):
    info=target.information(q);v,u=np.linalg.eigh(info)
    floor=max(1e-12,float(v.max())*1e-10)
    repaired=np.maximum(v,floor)
    cov=np.einsum("ik,jk,k->ij",u,u,1/repaired)
    np.linalg.cholesky(cov)
    return cov,dict(original_eigenvalues=v.tolist(),floor=floor,used_eigenvalues=repaired.tolist())


def fit_proposal_geometry(target):
    modes=[];records=[]
    for event in (False,True):
        result=minimize(lambda q:-float(target.logp(q)[0]),np.zeros(target.d),
            jac=lambda q:-target.gradient(q),method='L-BFGS-B',
            bounds=[(0.,None)]+[(None,None)]*(target.d-1) if event else None,
            options=dict(maxiter=1000,ftol=1e-14,gtol=1e-8,maxls=50))
        q=result.x;g=target.gradient(q).copy()
        if event and q[0]==0:g[0]=max(0.,g[0])
        residual=float(np.max(np.abs(g)))
        if not result.success or not np.isfinite(q).all() or residual>1e-4:
            raise ValueError('MAP qualification failed: '+str(result.message)+' gradient='+str(residual))
        cov,repair=covariance(target,q)
        if event:
            # Preserve conditional covariance/regression; match the positive
            # coordinate scale to the boundary slope when the mode is at zero.
            regression=cov[1:,0]/cov[0,0]
            conditional=cov[1:,1:]-np.outer(cov[1:,0],cov[0,1:])/cov[0,0]
            sd=math.sqrt(cov[0,0]);slope=float(target.gradient(q)[0])
            if q[0]==0 and slope<0:sd=min(sd,1/abs(slope))
            factor=np.zeros_like(cov);factor[0,0]=sd;factor[1:,0]=regression*sd
            factor[1:,1:]=np.linalg.cholesky(conditional)
            cov=np.einsum("ik,jk->ij",factor,factor)
        modes.append((q,cov))
        records.append(dict(event=event,mode=q.tolist(),covariance=cov.tolist(),
            gradient=target.gradient(q).tolist(),projected_gradient_max=residual,
            iterations=int(result.nit),function_evaluations=int(result.nfev),message=str(result.message),information=repair))
    return modes,records


class Mixture:
    def __init__(self, mean, covariance, event_mean, event_covariance, prior_scale, weights=(.45,.45,.10),df=5.):
        self.mean=np.asarray(mean,float);self.cov=np.asarray(covariance,float)
        self.event_mean=np.asarray(event_mean,float);self.event_cov=np.asarray(event_covariance,float)
        self.d=len(self.mean);self.scale=float(prior_scale);self.weights=np.asarray(weights,float);self.df=float(df)
        if self.d<2 or self.scale<=0 or self.df<=0 or not np.isclose(self.weights.sum(),1) or (self.weights<=0).any():raise ValueError('Invalid mixture')
        self.chol=np.linalg.cholesky(self.cov);self.ec=np.linalg.cholesky(self.event_cov)
        self.prec=np.linalg.inv(self.cov);self.ep=np.linalg.inv(self.event_cov)
        self.reg=self.event_cov[1:,0]/self.event_cov[0,0]
        conditional=self.event_cov[1:,1:]-np.outer(self.event_cov[1:,0],self.event_cov[0,1:])/self.event_cov[0,0]
        self.cc=np.linalg.cholesky(conditional);self.esd=math.sqrt(self.event_cov[0,0])
        self.cut=-self.event_mean[0]/self.esd;self.log_mass=float(log_ndtr(-self.cut))
        if not np.isfinite(self.log_mass):raise ValueError('Invalid truncation normalizer')
        self.log_t_const=float(gammaln((self.df+self.d)/2)-gammaln(self.df/2)-self.d/2*math.log(self.df*math.pi)-np.log(np.diag(self.chol)).sum())
        self.log_e_const=-self.d/2*math.log(2*math.pi)-np.log(np.diag(self.ec)).sum()-self.log_mass

    def sample(self,rng,n):
        components=rng.choice(3,size=n,p=self.weights);points=np.empty((n,self.d))
        for kind in range(3):
            where=np.flatnonzero(components==kind);k=len(where)
            if not k:continue
            if kind==0:
                z=rng.normal(size=(k,self.d));v=rng.chisquare(self.df,size=k)
                q=self.mean+np.einsum("bi,ji->bj",z,self.chol)/np.sqrt(v[:,None]/self.df)
            elif kind==1:
                z=truncnorm.rvs(self.cut,np.inf,size=k,random_state=rng)
                first=self.event_mean[0]+self.esd*z
                if np.any(first<=0):raise ValueError('Nonpositive event draw; never clip to zero')
                rest=self.event_mean[1:]+(first-self.event_mean[0])[:,None]*self.reg+np.einsum("bi,ji->bj",rng.normal(size=(k,self.d-1)),self.cc)
                q=np.column_stack([first,rest])
            else:q=rng.normal(0,self.scale,size=(k,self.d))
            points[where]=q
        if not np.isfinite(points).all():raise ValueError('Nonfinite proposals')
        return points,components

    def component_logpdf(self,q):
        q=np.atleast_2d(q);delta=q-self.mean;ed=q-self.event_mean
        t=self.log_t_const-(self.df+self.d)/2*np.log1p(np.einsum('bi,ij,bj->b',delta,self.prec,delta)/self.df)
        event=self.log_e_const-.5*np.einsum('bi,ij,bj->b',ed,self.ep,ed)
        event=np.where(q[:,0]>0,event,-np.inf)
        prior=-self.d*math.log(self.scale*math.sqrt(2*math.pi))-.5*np.sum((q/self.scale)**2,axis=1)
        return np.column_stack([t,event,prior])

    def logpdf(self,q):return logsumexp(self.component_logpdf(q)+np.log(self.weights),axis=1)

    def spec(self):return dict(mean=self.mean.tolist(),covariance=self.cov.tolist(),event_mean=self.event_mean.tolist(),
        event_covariance=self.event_cov.tolist(),prior_scale=self.scale,weights=self.weights.tolist(),df=self.df)


def quality(logw,event):
    logw=np.asarray(logw);event=np.asarray(event,bool)
    if not np.isfinite(logw).all() or not event.any():raise ValueError('Nonfinite weights or no event proposals')
    ld=float(logsumexp(logw));ln=float(logsumexp(logw[event]));p=math.exp(ln-ld)
    if not 0<p<1:raise ValueError('Unrepresentable probability ratio')
    return dict(probability=p,log_probability=ln-ld,draws=len(logw),event_proposals=int(event.sum()),
        denominator_ess=float(np.exp(2*ld-logsumexp(2*logw))),
        numerator_ess=float(np.exp(2*ln-logsumexp(2*logw[event]))),
        maximum_denominator_weight=float(np.exp(np.max(logw)-ld)),
        maximum_numerator_weight=float(np.exp(np.max(logw[event])-ln)),
        log_denominator_mean=ld-math.log(len(logw)),log_numerator_mean=ln-math.log(len(logw)))


def batch_summary(logweights,events):
    if len(logweights)!=8 or len(events)!=8 or len({len(x) for x in logweights})!=1:raise ValueError('Eight equal-size independent batches required')
    q=quality(np.concatenate(logweights),np.concatenate(events))
    shift=max(float(np.max(x)) for x in logweights)
    pairs=np.array([[np.mean(np.exp(w-shift)*e),np.mean(np.exp(w-shift))] for w,e in zip(logweights,events)])
    a,b=pairs.mean(axis=0);g=np.array([1.,-a/b])/b;cov=np.cov(pairs,rowvar=False,ddof=1)
    variance=float(np.einsum("i,ij,j->",g,cov,g)/8)
    if variance<0:raise ValueError('Negative delta variance')
    se=math.sqrt(variance);relative=se/q['probability']
    q.update(mcse=se,relative_mcse=relative,mcse_method='8 independent batch (A,B) covariance; delta approximation',
        batch_scaling_log_shift=shift,batch_scaled_numerator_denominator=pairs.tolist(),batch_joint_covariance=cov.tolist(),
        batches=[quality(w,e) for w,e in zip(logweights,events)],
        quality_targets_met=bool(relative<=.1 and q['numerator_ess']>=200 and q['denominator_ess']>=1000 and q['maximum_numerator_weight']<=.05 and q['maximum_denominator_weight']<=.01))
    return q
