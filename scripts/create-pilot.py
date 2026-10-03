"""Create a development probe, not a formal performance claim."""
from pathlib import Path
import numpy as np
from parallelbayes.models import benchmark_model
from parallelbayes.experiment import freeze
models={name:benchmark_model(name).spec for name in ['G1','G2','L1','L2','T1']}
tasks=[]
for name in ['G1','G2','L1','L2']:
 for n in [256,2048]:
  for seed in [3101,3102,3103]:
   for kernel in ['mala','rwm']:
    scale=({'G1':.1,'G2':.1,'L1':.005,'L2':.0005} if kernel=='mala' else {'G1':.5,'G2':1.,'L1':.1,'L2':.03})[name]
    for executor,window in [('sequential',64)]+[(('quasi_deer' if kernel=='mala' else 'online_picard'),w) for w in [16,64,256]]:
     tasks.append(dict(model=name,config=dict(kernel=kernel,executor=executor,draws=n,seed=seed,window=window,step_size=scale)))
np.random.default_rng(7331).shuffle(tasks)
freeze('benchmark/protocols/pilot-v1.json',dict(name='pilot-v1',stage='development',platforms=['cpu','gpu'],models=models,tasks=tasks,
 defaults=dict(chains=1,audit=True,max_iter=4096,atol=1e-10,rtol=1e-10,on_failure='error',memory_limit_mb=2048),
 policy=dict(independent_tapes=3,window_grid=[16,64,256],fixed_N=[256,2048],order_seed=7331,
             complete_cost_includes_audit=True,claims='Development cost probe, not formal statistical ranking')),Path.cwd())
