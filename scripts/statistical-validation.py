"""Small generative SBC and analytic validation; diagnostic, not a proof.

Independent unit = newly simulated parameter and data set. Correlated posterior
rank draws are thinned; raw draws are retained and no uniformity test is asserted.
"""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import jax
from scipy.stats import beta as beta_dist
from parallelbayes import sample
from parallelbayes.experiment import write_json,source_hash,file_hash

parser=argparse.ArgumentParser();parser.add_argument('--replicates',type=int,default=12);parser.add_argument('--protocol')
parser.add_argument('--platform',default='cpu');parser.add_argument('--output',default='execution/statistical-pilot')
args=parser.parse_args()
data_seed=551002
sampling_seed=73000
if args.protocol:
 from parallelbayes.experiment import load_protocol
 frozen=load_protocol(args.protocol,'.')
 data_seed=frozen['seed'];sampling_seed=frozen.get('sampling_seed',73000)
 if args.replicates!=frozen['replicates'] or args.platform not in frozen['platforms']:
  raise RuntimeError('Statistical run differs from frozen protocol')
 if file_hash(__file__)!=frozen['script_sha256']:
  raise RuntimeError('Statistical validation script differs from freeze')
out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
manifest=dict(replicates=args.replicates,source_sha256=source_hash('.'),platform=args.platform,
             seed=data_seed,sampling_seed=sampling_seed,prior='theta ~ N(0,1)',likelihood='8 independent y ~ N(theta,1)',
             methods=['mala/sequential','mala/quasi_deer','rwm/sequential','rwm/online_picard','nuts/sequential'],
             mh_discard=1024,nuts_warmup=512,rank_thinning=32,interval=.90,
             scope='Small SBC pipeline/analytic check; finite power and autocorrelation remain. No proof of calibration.')
manifest_path=out/'manifest.json'
if manifest_path.exists() and json.loads(manifest_path.read_text())!=manifest: raise RuntimeError('Different validation manifest')
write_json(manifest_path,manifest)
for r in range(args.replicates):
 rng=np.random.Generator(np.random.Philox(np.random.SeedSequence([data_seed,r])))
 truth=float(rng.normal()); y=rng.normal(truth,1.,8)
 spec=dict(kind='normal_mean',y=y.tolist()); exact_mean=float(y.sum()/9); exact_sd=1/3
 for kernel,executor in [('mala','sequential'),('mala','quasi_deer'),('rwm','sequential'),('rwm','online_picard'),('nuts','sequential')]:
  name=f'{r:03d}-{kernel}-{executor}';receipt=out/(name+'.json')
  if receipt.exists():continue
  c=dict(kernel=kernel,executor=executor,chains=1,draws=3072 if kernel!='nuts' else 2048,
    warmup=512,seed=sampling_seed+r,step_size=.07 if kernel=='mala' else .8,window=64,max_iter=4096,
    audit=True,platform=args.platform)
  result=sample(spec,c);record=dict(replicate=r,theta=truth,y=y.tolist(),exact_mean=exact_mean,
    exact_sd=exact_sd,config=c,status=result['status'],timing=result['timing'],
    diagnostics=result.get('diagnostics'),audit=result.get('audit'),
    divergences=int(np.sum(result.get('diagnostics',{}).get('divergent',[]))))
  if result['status']=='completed':
   raw=result['draws'][0,:,0]; kept=raw[1024:] if kernel!='nuts' else raw
   ranks=kept[31::32];lo,hi=np.quantile(kept,[.05,.95]);
   np.savez_compressed(out/(name+'.npz'),draws=raw,y=y)
   record.update(rank=int(np.sum(ranks<truth)),rank_draws=len(ranks),covered=bool(lo<=truth<=hi),
      mean=float(kept.mean()),mean_error=float(kept.mean()-exact_mean),
      variance=float(kept.var()),lag1_rank_draw_correlation=float(np.corrcoef(ranks[:-1],ranks[1:])[0,1]),
      raw_sha256=file_hash(out/(name+'.npz')))
  else:record['diagnostics']=result.get('primary_diagnostics',result.get('diagnostics'))
  write_json(receipt,record); print(name,result['status'],flush=True);jax.clear_caches()
summary=[]
for kernel,executor in [('mala','sequential'),('mala','quasi_deer'),('rwm','sequential'),('rwm','online_picard'),('nuts','sequential')]:
 rows=[json.loads(p.read_text()) for p in out.glob(f'*-{kernel}-{executor}.json')]
 ok=[x for x in rows if x['status']=='completed'];k=sum(x['covered'] for x in ok);n=len(ok)
 interval=[0 if k==0 else float(beta_dist.ppf(.025,k,n-k+1)),1 if k==n else float(beta_dist.ppf(.975,k+1,n-k))] if n else [None,None]
 summary.append(dict(method=f'{kernel}/{executor}',attempted=len(rows),failed=len(rows)-n,coverage=k/n if n else None,
                     coverage_95_binomial_interval=interval,divergences=sum(x.get('divergences',0) for x in rows),
                     divergent_fits=sum(x.get('divergences',0)>0 for x in rows),mean_squared_error=float(np.mean([x['mean_error']**2 for x in ok])) if n else None,
                     rank_histogram=np.histogram([x['rank'] for x in ok],bins=np.linspace(0,65,6))[0].tolist()))
write_json(out/'summary.json',dict(manifest=manifest,methods=summary))
