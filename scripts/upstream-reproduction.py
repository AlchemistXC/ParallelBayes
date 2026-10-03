from pathlib import Path
import importlib.util
import numpy as np
import jax
import jax.numpy as jnp
from parallelbayes import make_model
from parallelbayes.kernels import transition,numpy_reference
from parallelbayes.sampling import settings,random_tape,environment
from parallelbayes.experiment import write_json,file_hash

path=Path('software/parallel-mcmc-upstream/qdeer.py')
spec=importlib.util.spec_from_file_location('upstream_qdeer',path)
u=importlib.util.module_from_spec(spec); spec.loader.exec_module(u)
rows=[]
for target in [dict(kind='gaussian',dimension=2),dict(kind='gaussian',dimension=8)]:
 m=make_model(target); c=settings(dict(draws=64,step_size=.05)); tape=random_tape(c,m.dimension)
 inputs=jnp.concatenate((jnp.asarray(tape['noise'][0]),jnp.asarray(tape['log_uniform'][0])[:,None]),axis=1)
 step=transition(m.log_density,'mala')
 f=lambda q,x,p: step(q,x[:-1],x[-1],.05,surrogate=True)[0]
 out,it=jax.jit(lambda x:u.seq1d(f,jnp.zeros(m.dimension),x,dict(key=jax.random.PRNGKey(7103)),max_iter=1000,clip_val=1.))(inputs)
 ref,acc=numpy_reference(m,'mala',np.zeros(m.dimension),tape['noise'][0],tape['log_uniform'][0],.05)
 error=float(np.max(np.abs(np.asarray(out)-ref)))
 rows.append(dict(dimension=m.dimension,iterations=int(it),max_path_error=error,
                  upstream_update_tolerance='atol 1e-7, rtol 1e-4; not original-recurrence certification'))
 assert error<1e-3
write_json('execution/upstream-reproduction.json',dict(commit='5e5b637b1214580d0be4e495215e0e5ed6eb2688',
 source_sha256=file_hash(path),environment=environment(),results=rows,
 scope='Pinned upstream solver on independently specified fixed-noise MALA map; not a performance replication of the paper'))
