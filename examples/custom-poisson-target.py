"""Extend the public Python Model contract without changing the sampling core.
Run: .venv/bin/python examples/custom-poisson-target.py
R can call run_example through reticulate::import_from_path; no new pb_model kind
is registered by this external example.
"""
from pathlib import Path
import json
import numpy as np
import jax.numpy as jnp
from parallelbayes.models import Model
from parallelbayes.sampling import validate_model,sample,random_tape,settings


def poisson_target():
    rng=np.random.Generator(np.random.Philox(684321))
    x=np.column_stack([np.ones(32),rng.normal(size=32)])
    y=rng.poisson(np.exp(x@np.array([.2,-.4])))
    xx,yy=jnp.asarray(x),jnp.asarray(y)
    def logp(q):
        eta=xx@q
        return jnp.sum(yy*eta-jnp.exp(eta))-.5*jnp.sum(q*q)/4.
    def reference(q):
        eta=np.einsum('ij,j->i',x,q)
        return float(np.sum(y*eta-np.exp(eta))-.5*np.sum(q*q)/4.)
    def gradient(q):
        eta=np.einsum('ij,j->i',x,q)
        return np.einsum('ij,i->j',x,y-np.exp(eta))-q/4.
    spec=dict(kind='custom_poisson_regression',dimension=2,coordinate_id='identity',X=x.tolist(),y=y.tolist(),prior_sd=2.)
    return Model(spec,2,logp,reference,gradient,lambda q:q,['beta0','beta1'])


def run_example(output='execution/custom-target-example.json'):
    model=poisson_target();points=np.array([[0.,0.],[1.,-1.],[-2.,2.],[3.,-3.]])
    validation=validate_model(model,points)
    assert validation['passed']
    results=[];last=None
    for kernel,executor,step in [('mala','quasi_deer',.01),('rwm','online_picard',.08)]:
        c=settings(dict(kernel=kernel,draws=128,chains=2,seed=9921,solver_seed=9922,step_size=step,window=16,max_iter=1024,audit=True))
        tape=random_tape(c,model.dimension)
        seq=sample(model,c,tape=tape);par=sample(model,dict(c,executor=executor),tape=tape)
        assert seq['status']==par['status']=='completed'
        delta=float(np.max(np.abs(seq['draws']-par['draws'])))
        assert delta<1e-7 and sum(par['audit']['acceptance_mismatches'])==0
        results.append(dict(kernel=kernel,executor=executor,path_difference=delta,audit=par['audit']))
        last=par['draws']
    record=dict(validation=validation,comparisons=results,scope='Extension interface and fixed-noise correctness example; not convergence or performance evidence')
    from parallelbayes.experiment import write_json
    if output:write_json(output,record)
    return dict(record=record,draws=np.transpose(last,(1,0,2)))

if __name__=='__main__':print(json.dumps(run_example()['record'],indent=2))
