from pathlib import Path
import numpy as np
import jax
from parallelbayes.models import benchmark_model
from parallelbayes import sample,validate_model
from parallelbayes.experiment import write_json,source_hash
steps={'G1':(.1,.5),'G2':(.1,1.),'L1':(.005,.1),'L2':(.0005,.03),'H1':(.01,.2),'H2':(.1,.5),'A1':(.02,.3),'M1':(.1,.5)}
rows=[]
for name,(h,s) in steps.items():
 m=benchmark_model(name);check=validate_model(m)
 assert check['passed'],(name,check)
 for kernel,executor in [('mala','quasi_deer'),('rwm','online_picard'),('nuts','sequential')]:
  r=sample(m,dict(kernel=kernel,executor=executor,draws=256,chains=4,warmup=512,
             step_size=h if kernel=='mala' else s,window=64,max_iter=4096,audit=True,seed=8842))
  record=dict(model=name,method=f'{kernel}/{executor}',status=r['status'],timing=r['timing'],audit=r.get('audit'),
              diagnostics=r.get('diagnostics'))
  rows.append(record);print(name,kernel,r['status'],flush=True)
  jax.clear_caches()
write_json('execution/model-preflight.json',dict(source_sha256=source_hash('.'),steps=steps,results=rows))
