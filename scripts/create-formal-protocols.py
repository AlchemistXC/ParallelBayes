"""Freeze the CPU/GPU protocol before examining formal outputs."""
from pathlib import Path
import json
import numpy as np
from parallelbayes.models import benchmark_model
from parallelbayes.experiment import freeze,write_json,file_hash
root=Path.cwd()
models={n:benchmark_model(n).spec for n in ['G1','G2','L1','L2','H1','H2','A1','M1']}
steps={'G1':(.1,.5),'G2':(.1,1.),'L1':(.005,.1),'L2':(.0005,.03),'H1':(.01,.2),'H2':(.1,.5),'A1':(.02,.3),'M1':(.1,.5)}
# Common bounded functions avoid rare enormous moments in the funnel stress case.
functions=dict(gaussian=['standardized_q0','standardized_q0_squared','standardized_q0_above_1'],
 logistic=['q0','q1','sigmoid(q0)','q0_above_0'],
 funnel=['v_over_3','tanh(v_over_3)','x1_above_0','cos(x1_exp_minus_v_over_2)'],
 mixture=['q0_over_sqrt26','q0_positive','q1','q1_squared'])
policy=dict(replicates=24,retained_draws=[256,2048],chains=4,discard_mh=512,warmup_nuts=512,
 fixed_steps=steps,functions=functions,scales=dict(gaussian=[1,1,1],logistic=[1,1,1,1],funnel=[1,1,1,1],mixture=[1,1,1,1]),
 epsilon=[.1,.2],solver_window=64,order_seed=86172,
 interpretation='Specified fixed-kernel workflows vs adapted four-chain BlackJAX NUTS; not optimal-algorithm ranking',
 statistical_precision='24 independent replications, paired tapes for MH executor contrasts. Pointwise 95% bootstrap intervals and MCSE; intervals are not simultaneous. No optional stopping or post hoc favorable-budget selection.',
 precision_design_amendment='Initial plan MCSE/epsilon^2=0.1 is not asserted for every stress target. Fixed 24 repetitions retain broad uncertainty; a threshold is undetermined when its upper confidence bound crosses it. Formal outcomes never trigger selective replication.',
 failure='All failed/unfinished tasks counted; conditional error only, no unconditional accuracy claim with any failures. NUTS divergences remain reported.',
 timing='JIT compile + warmup + sample + transfer + independent audit; task wall time includes model build/output. Cached timing replays are ancillary, separately charged.',
 reference='Analytic where available; independent NUTS reference with reported between-fit uncertainty for logistic. Squared discrepancy is not unbiased MSE.',
 exploratory_boundaries='Synthetic targets across five structural families; H1/H2 same family. No empirical-domain generalization, selector or modern-multichain-superiority claim.')
tasks=[]
for name in models:
 for retained in [256,2048]:
  for repeat in range(24):
   for kernel,executor in [('mala','sequential'),('mala','quasi_deer'),('rwm','sequential'),('rwm','online_picard'),('nuts','sequential')]:
    cfg=dict(kernel=kernel,executor=executor,draws=retained if kernel=='nuts' else retained+512,
             step_size=steps[name][0 if kernel=='mala' else 1],seed=200000+repeat,solver_seed=300000+repeat)
    tasks.append(dict(model=name,replicate=repeat,retained_draws=retained,discard=0 if kernel=='nuts' else 512,config=cfg))
np.random.default_rng(86172).shuffle(tasks)
freeze('benchmark/protocols/protocol-v1.json',dict(name='protocol-v1',stage='formal',platforms=['cpu','gpu'],models=models,tasks=tasks,
 defaults=dict(chains=4,audit=True,max_iter=4096,atol=1e-10,rtol=1e-10,on_failure='error',memory_limit_mb=2048,
               window=64,warmup=512,max_tree_depth=8,timing_repeats=3),policy=policy),root)
refs=[]
for name in ['L1','L2']:
 for repeat in range(4): refs.append(dict(model=name,reference_repeat=repeat,config=dict(kernel='nuts',executor='sequential',seed=900100+repeat)))
freeze('benchmark/protocols/reference-v1.json',dict(name='reference-v1',stage='reference',platforms=['cpu','gpu'],models={n:models[n] for n in ['L1','L2']},tasks=refs,
 defaults=dict(chains=4,draws=16384,warmup=1024,max_tree_depth=10,audit=False,memory_limit_mb=2048),
 policy=dict(independence='Disjoint seeds, independent of algorithm runs',quantity='Reference discrepancy, not exact truth',
 acceptance='Report split Rhat, divergences, between-fit MCSE and batch-mean MCSE; unresolved reference yields undetermined comparisons')),root)
# New source version of the identical development grid is shipped for the GPU gate.
pilot=json.loads(Path('benchmark/protocols/pilot-v1.json').read_text())
for key in ['source_sha256','runtime_lock_sha256','protocol_sha256','frozen_at']:pilot.pop(key,None)
pilot.update(name='pilot-v2',revision_reason='Same development grid with release source, cached timing support and raw tape export')
freeze('benchmark/protocols/pilot-v2.json',pilot,root)
freeze('benchmark/protocols/statistical-v1.json',dict(name='statistical-v1',replicates=64,platforms=['cpu','gpu'],
 seed=551002,script='scripts/statistical-validation.py',scope='Generative conjugate-normal SBC, thinned ranks; diagnostics not proof',
 changes_from_pilot='64 independent generated data sets; same methods and draw counts; all failures retained',
 script_sha256=file_hash('scripts/statistical-validation.py')),root)
print('formal tasks',len(tasks),'reference tasks',len(refs))
