"""Pyro NUTS CPU baseline, chains serialized to avoid Windows multiprocessing.

No MH fixed-tape/path comparison and no CUDA NUTS claim. Adaptation is additional.
"""
import time
import numpy as np
import torch
import pyro
from pyro.infer.mcmc import MCMC,NUTS
from .models import make_model
from ..output import constrain_checked


def sample_cpu_nuts(spec,draws=256,warmup=256,chains=4,seed=912,max_tree_depth=7):
    if min(draws,warmup,chains,max_tree_depth)<1:
        raise ValueError("positive NUTS budgets required")
    model=make_model(spec,"cpu")
    paths=[];diagnostics=[];rng_states=[];timing=dict(warmup=0.,sample=0.)
    started=time.perf_counter()
    for i in range(chains):
        pyro.set_rng_seed(seed+i)
        rng_states.append(torch.get_rng_state().numpy().copy())
        stage_start=[time.perf_counter()];warm_done=[False]
        def hook(kernel,params,stage,index):
            if stage=="Sample" and not warm_done[0]:
                now=time.perf_counter();timing["warmup"]+=now-stage_start[0]
                stage_start[0]=now;warm_done[0]=True
        kernel=NUTS(potential_fn=lambda state:-model.log_density(state["q"]),
                    max_tree_depth=max_tree_depth,jit_compile=False,target_accept_prob=.8)
        mcmc=MCMC(kernel,num_samples=draws,warmup_steps=warmup,num_chains=1,
                  initial_params={"q":torch.zeros(model.dimension,dtype=torch.float64)},
                  hook_fn=hook,disable_progbar=True)
        mcmc.run()
        timing["sample"]+=time.perf_counter()-stage_start[0]
        paths.append(mcmc.get_samples()["q"].detach().numpy())
        diagnostics.append(mcmc.diagnostics())
    path=np.stack(paths)
    theta,error=constrain_checked(model,path)
    valid=bool(np.isfinite(path).all() and error is None)
    timing["total"]=time.perf_counter()-started
    return dict(status="completed" if valid else "failed",draws=theta if valid else None,
        unconstrained=path if valid else None,failed_trajectory=None if valid else path,
        initial_rng_states=np.stack(rng_states),diagnostics=diagnostics,timing=timing,
        transform_error=error,provider="pyro_cpu_nuts",pyro_version=pyro.__version__,
        seed=seed,chains=chains,warmup=warmup,retained_draws=draws,target_id=model.target_id,
        fixed_mh_tape_comparison=False,windows_multiprocessing=False)
