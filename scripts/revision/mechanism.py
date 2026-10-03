"""Small CPU mechanism protocol: production timing plus deliberately segmented replay.
Segmented replay inserts synchronization and Python control, so its stage costs
explain that diagnostic execution only and are never an additive decomposition
of the fused production executable. All random inputs/round logs are retained.
"""
import argparse,os,json,time,threading,hashlib
from pathlib import Path
import numpy as np
import psutil,jax,jax.numpy as jnp
from parallelbayes.sampling import settings,prepare,sample,random_tape
from parallelbayes.models import make_model,benchmark_model,fingerprint
from parallelbayes.kernels import transition
from parallelbayes.executors import affine_scan
from parallelbayes.experiment import write_json,file_hash,source_hash

p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--limit',type=int);p.add_argument('--protocol',default='benchmark/protocols/cpu-mechanism-v1.json');a=p.parse_args()
protocol_path=Path(a.protocol);out=Path('execution/cpu-revision-v1')/protocol_path.stem;out.mkdir(parents=True,exist_ok=True)
if a.freeze:
 if protocol_path.exists():raise RuntimeError('Existing protocol is immutable')
 main=json.loads(Path('benchmark/protocols/protocol-v1.json').read_text());tasks=[]
 for model in ['G1','G2','L1']:
  for chains in [1,4]:
   for rep in range(3):
    for kernel,executor in [('mala','quasi_deer'),('rwm','online_picard')]:
     step=next(t['config']['step_size'] for t in main['tasks'] if t['model']==model and t['config']['kernel']==kernel)
     for w in [16,64]:tasks.append(dict(model=model,chains=chains,replicate=rep,kernel=kernel,executor=executor,window=w,draws=256,step_size=step,seed=(340100 if "development" in protocol_path.stem else 341100)+rep,solver_seed=(340200 if "development" in protocol_path.stem else 341200)+rep))
 np.random.Generator(np.random.Philox(334891)).shuffle(tasks)
 payload=dict(version=protocol_path.stem,created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),source_sha256=source_hash('.'),script_sha256=file_hash(__file__),
  tasks=tasks,models={k:main['models'][k] for k in ['G1','G2','L1']},repeat_timing=7,minimum_timing_window_seconds=.2,
  interpretation='Post-review small CPU mechanism experiment; three independent noise tapes; timing replays are technical repeats. No claim of finding a positive crossover. No resampling based on outcome.',
  segmented_scope='Single-chain replay with separately compiled stage calls, synchronizations and Python control. Measures its own stage distribution, not additive production costs. Production chain-batching timing stays separate.',
  utilization='Process user+system CPU seconds / wall seconds for at least seven warmed production runs spanning at least 0.2 seconds, plus 10 ms sampled system utilization; core equivalents are observed consumption, not physical-core affinity.',
  output_policy='No failure deletion or automatic failed-task rerun; terminal status and all raw arrays retained.',normal_workflow='New direct audit=False run, with model construction, transform and in-memory Rhat/basic posterior-function diagnostics measured. Save only ordinary posterior output separately; evidence archive overhead separately timed.')
 payload['protocol_sha256']=fingerprint(payload);write_json(protocol_path,payload);print('Frozen',len(tasks),'tasks');raise SystemExit
frozen=json.loads(protocol_path.read_text());unsigned=dict(frozen);digest=unsigned.pop('protocol_sha256')
assert fingerprint(unsigned)==digest and file_hash(__file__)==frozen['script_sha256'] and source_hash('.')==frozen['source_sha256']

class Meter:
 def __enter__(self):
  self.p=psutil.Process();self.c0=self.p.cpu_times();self.t0=time.perf_counter();self.samples=[];self.stop=threading.Event()
  def watch():
   psutil.cpu_percent(None,percpu=True)
   while not self.stop.wait(.01):self.samples.append(psutil.cpu_percent(None,percpu=True))
  self.thread=threading.Thread(target=watch,daemon=True);self.thread.start();return self
 def __exit__(self,*args):
  self.stop.set();self.thread.join();self.wall=time.perf_counter()-self.t0;c=self.p.cpu_times();self.cpu=c.user-self.c0.user+c.system-self.c0.system
  self.record=dict(wall=self.wall,process_cpu_seconds=self.cpu,core_equivalents=self.cpu/self.wall,system_per_logical_cpu_percent=self.samples,system_samples=len(self.samples))


def trace_chain(model,c,tape):
 w=c['window'];n=c['draws'];d=model.dimension;step=transition(model.log_density,c['kernel']);scale=c['step_size'];base=jnp.zeros(d);rounds=[]
 batch=jax.jit(jax.vmap(lambda q,z,u:step(q,z,u,scale)))
 def jvp_batch(q,z,u,v):
  return jax.vmap(lambda qi,zi,ui,vi:jax.jvp(lambda qi:step(qi,zi,ui,scale,surrogate=True)[0],(qi,),(vi,)))(q,z,u,v)
 jvp=jax.jit(jvp_batch);scan=jax.jit(affine_scan)
 prefix_sum=jax.jit(lambda origin,inc:origin+jnp.cumsum(inc,axis=0))
 zall=jnp.asarray(tape['noise'][0]);uall=jnp.asarray(tape['log_uniform'][0]);vall=jnp.asarray(tape['directions'][0]);q=jnp.zeros((w,d))
 # Compilation/warm calls are excluded from segmented component times and recorded.
 t=time.perf_counter();jax.block_until_ready(batch(q,zall[:w],uall[:w]));jax.block_until_ready(prefix_sum(base,q));
 if c['kernel']=='mala':jax.block_until_ready(jvp(q,zall[:w],uall[:w],vall[:w]));jax.block_until_ready(scan(q,q,base))
 warm=time.perf_counter()-t
 totals={};paths=[];accepts=[];all_started=time.perf_counter();calls=0
 def timed(name,fn,*args):
  t=time.perf_counter();res=fn(*args);jax.block_until_ready(res);totals[name]=totals.get(name,0.)+time.perf_counter()-t;return res
 if c['kernel']=='mala':
  for offset in range(0,n,w):
   path=jnp.broadcast_to(base,(w,d));z=zall[offset:offset+w];u=uall[offset:offset+w];v=vall[offset:offset+w]
   for it in range(c['max_iter']):
    prev=jnp.concatenate((base[None],path[:-1]));values,jv=timed('target_and_jvp',jvp,prev,z,u,v)
    diag=jnp.clip(v*jv,-c['jacobian_clip'],c['jacobian_clip']);path=timed('affine_scan',scan,diag,values-diag*prev,base)
    prev=jnp.concatenate((base[None],path[:-1]));target,acc,finite=timed('hard_event_recheck',batch,prev,z,u)
    err=float(jnp.max(jnp.abs(path-target)/(c['atol']+c['rtol']*jnp.abs(target))))
    rounds.append(dict(offset=offset,iteration=it+1,scaled_residual=err,confirmed=0));calls+=1
    if not bool(jnp.all(finite)):raise FloatingPointError('segmented nonfinite')
    if err<=1:break
   else:raise RuntimeError('segmented max_iter')
   paths.extend(np.asarray(path));accepts.extend(np.asarray(acc));base=path[-1]
 else:
  zz=jnp.pad(zall,((0,w),(0,0)));uu=jnp.pad(uall,((0,w),),constant_values=-1.)
  offset=0;guess=q
  while offset<n and calls<c['max_iter']:
   z=zz[offset:offset+w];u=uu[offset:offset+w]
   _,old,finite=timed('batch_target',batch,guess,z,u)
   inc=jnp.where(old[:,None],scale*z,0.);path=timed('prefix_scan',prefix_sum,guess[0],inc)
   prev=jnp.concatenate((guess[:1],path[:-1]));_,new,finite2=timed('event_recheck',batch,prev,z,u)
   prefix=min(int(jnp.sum(jnp.cumprod((old==new).astype(jnp.int32)))),n-offset);calls+=1
   rounds.append(dict(offset=offset,iteration=calls,confirmed=prefix))
   if prefix<=0:raise RuntimeError('segmented no progress')
   valid=jnp.arange(w)+offset<n
   if not bool(jnp.all((finite&finite2)|~valid)):raise FloatingPointError('segmented nonfinite')
   paths.extend(np.asarray(path[:prefix]));accepts.extend(np.asarray(old[:prefix]));indices=jnp.arange(w)+prefix
   guess=jnp.where((indices>=w)[:,None],path[-1],prev[jnp.minimum(indices,w-1)]);offset+=prefix
  if offset<n:raise RuntimeError('segmented max_iter')
 elapsed=time.perf_counter()-all_started
 return np.asarray(paths),np.asarray(accepts),dict(rounds=rounds,stage_seconds=totals,python_control_and_other=elapsed-sum(totals.values()),segmented_seconds=elapsed,warm_compile_seconds=warm)

from scipy.stats import rankdata
count=0
for task in frozen['tasks']:
 tid=fingerprint(task)[:20];dest=out/tid;receipt=dest/'state.json'
 if receipt.exists():
  record=json.loads(receipt.read_text())
  if record['status'] in ['completed','failed']:
   for name,h in record['checksums'].items():assert file_hash(dest/name)==h
   continue
 if a.limit is not None and count>=a.limit:break
 dest.mkdir(exist_ok=True);write_json(receipt,dict(status='running',task=task,protocol_sha256=digest))
 c=settings({k:v for k,v in task.items() if k not in ['model','replicate']});c.update(audit=True,max_iter=4096,atol=1e-10,rtol=1e-10)
 record=dict(task=task,protocol_sha256=digest,status='failed');raw={}
 try:
  # Production executable timings; fixed task order is frozen, within-task seq/par
  # order alternates with replicate. No other benchmark runners should coexist.
  model=make_model(frozen['models'][task['model']]);tape=random_tape(c,model.dimension);raw.update({f'tape__{k}':v for k,v in tape.items()});production={}
  for ex in ([c['executor'],'sequential'] if task['replicate']%2 else ['sequential',c['executor']]):
   cc=dict(c,executor=ex);fit=sample(model,cc,tape=tape);assert fit['status']=='completed'
   prepared=prepare(model,cc,tape);prepared.run();times=[]
   with Meter() as meter:
    while len(times)<frozen['repeat_timing'] or time.perf_counter()-meter.t0<frozen['minimum_timing_window_seconds']:
     _,_,duration,_=prepared.run();times.append(duration)
   production[ex]=dict(timing=fit['timing'],cached_seconds=times,diagnostics={k:v for k,v in fit['diagnostics'].items() if k!='accept'},audit=fit['audit'],cpu=meter.record)
   raw[ex+'__draws']=fit['draws'];raw[ex+'__accept']=fit['diagnostics']['accept']
   # Direct normal-use task; no audit and no evidence export in this clock.
   started=time.perf_counter();fresh=make_model(frozen['models'][task['model']]);normal=sample(fresh,dict(cc,audit=False),tape=tape)
   q=normal['draws'];assert normal['status']=='completed';means=q.mean(axis=1);variances=q.var(axis=1)
   within=np.mean(variances,axis=0);between=q.shape[1]*np.var(means,axis=0,ddof=1) if q.shape[0]>1 else np.full(model.dimension,np.nan)
   with np.errstate(divide='ignore',invalid='ignore'):rhat=np.sqrt(((q.shape[1]-1)/q.shape[1]*within+between/q.shape[1])/within)
   production[ex]['normal_in_memory_seconds']=time.perf_counter()-started
   t=time.perf_counter();np.savez_compressed(dest/(ex+'-ordinary-draws.npz'),draws=q);production[ex]['ordinary_output_seconds']=time.perf_counter()-t
   production[ex]['normal_scope']='Model build + current-process sampler audit=False + mean/variance/classic between-chain diagnostic; does not include R conversion or modern posterior diagnostics'
  traced,acc,trace=trace_chain(model,c,tape);diff=float(np.max(np.abs(traced-raw[c['executor']+'__draws'][0])))
  mismatch=int(np.sum(acc!=raw[c['executor']+'__accept'][0]));assert diff<1e-6 and mismatch==0
  trace.update(max_path_difference=diff,acceptance_mismatches=mismatch);raw['segmented_path']=traced
  # Same fixed predecessor states and input arrays, evaluated independently:
  # serial mapped calls versus vectorized calls measure batch throughput only.
  w=c['window'];predecessors=jnp.asarray(np.concatenate([np.zeros((1,model.dimension)),raw[c['executor']+'__draws'][0,:w-1]]))
  zz=jnp.asarray(tape['noise'][0,:w]);uu=jnp.asarray(tape['log_uniform'][0,:w]);step=transition(model.log_density,c['kernel'])
  batch=jax.jit(jax.vmap(lambda qi,zi,ui:step(qi,zi,ui,c['step_size'])))
  serial=jax.jit(lambda q,z,u:jax.lax.map(lambda xs:step(xs[0],xs[1],xs[2],c['step_size']),(q,z,u)))
  measurements={}
  for label,fun in [('batched',batch),('serial_mapped',serial)]:
   compiled=fun.lower(predecessors,zz,uu).compile();jax.block_until_ready(compiled(predecessors,zz,uu));tt=[]
   for _ in range(7):
    start=time.perf_counter();jax.block_until_ready(compiled(predecessors,zz,uu));tt.append(time.perf_counter()-start)
   measurements[label]=tt
  trace['fixed_state_batch_microbenchmark']=measurements
  trace['batch_throughput_factor']=float(np.median(measurements['serial_mapped'])/np.median(measurements['batched']))
  record.update(status='completed',production=production,trace=trace)
 except Exception as exc:
  import traceback
  record.update(error=str(exc),traceback=traceback.format_exc())
 t=time.perf_counter();np.savez_compressed(dest/'raw.npz',**raw);record['evidence_array_export_seconds']=time.perf_counter()-t
 write_json(dest/'result.json',record);checks={p.name:file_hash(p) for p in dest.iterdir() if p.is_file() and p.name!='state.json'}
 write_json(receipt,dict(status=record['status'],task=task,protocol_sha256=digest,checksums=checks))
 print(count+1,task,record['status'],flush=True);count+=1;jax.clear_caches()
