"""Small paired analytic SBC; five workflows share each generated data set."""
import argparse
import time
import traceback
from pathlib import Path
import numpy as np
from scipy.stats import norm
from parallelbayes import sample
from parallelbayes.torch_backend.sampling import settings,random_tape
from parallelbayes.torch_backend.nuts_baseline import sample_cpu_nuts
from evidence import configure,write_json,save_result,git,source_files,runtime

p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
configure();out=a.output
if out.exists():raise FileExistsError('preserve prior statistical attempt')
out.mkdir(parents=True);rng=np.random.Generator(np.random.Philox(11043007));datasets=[]
for i in range(12):
    truth=float(rng.normal());y=rng.normal(truth,1,8)
    mean=float(y.sum()/9);sd=1/3
    datasets.append(dict(id=i,truth=truth,y=y.tolist(),mean=mean,sd=sd,
        interval=norm.ppf([.05,.95],loc=mean,scale=sd).tolist()))
design=dict(kind='development statistical validation, not formal performance comparison',datasets=datasets,
    independent_datasets=12,shared_workflows=5,chains=4,total_mh_transitions=1024,discard=256,
    retained_nuts_draws=768,nuts_warmup=256,rank_policy='one chain thinned every 16 after discard; finite-MCMC rank, no uniformity proof',
    seeds=[70000+i for i in range(12)],source_commit=git('rev-parse','HEAD'),source_files=source_files(),runtime=runtime())
write_json(out/'design.json',design)
rows=[]
for data in datasets:
    spec=dict(kind='normal_mean',y=data['y'])
    for kernel,executor in [('mala','sequential'),('mala','quasi_deer'),('rwm','sequential'),('rwm','online_picard'),('nuts','pyro_cpu')]:
        key=f"{data['id']:02d}-{kernel}-{executor}";folder=out/key
        tape=None
        try:
            if kernel=='nuts':
                r=sample_cpu_nuts(spec,draws=768,warmup=256,chains=4,seed=81000+data['id']*10)
                discard=0
            else:
                c=settings(dict(kernel=kernel,executor=executor,draws=1024,chains=4,window=16,
                    max_iter=1024,device='cuda',step_size=.05 if kernel=='mala' else .5,
                    seed=70000+data['id'],solver_seed=80000+data['id']))
                tape=random_tape(c,1);r=sample(spec,c,tape,backend='torch');discard=256
            checks,_=save_result(folder,r,tape)
            row=dict(dataset=data['id'],workflow=kernel+'/'+executor,status=r['status'],checksums=checks,
                     analytic_mean=data['mean'],analytic_sd=data['sd'],analytic_interval=data['interval'],
                     analytic_covered=data['interval'][0]<=data['truth']<=data['interval'][1])
            if r['status']=='completed':
                draws=r['draws'][:,discard:,0]
                interval=np.quantile(draws,[.05,.95])
                row.update(mean=float(draws.mean()),sd=float(draws.std(ddof=1)),interval=interval.tolist(),
                    covered=bool(interval[0]<=data['truth']<=interval[1]),mean_error=float(draws.mean()-data['mean']),
                    sd_error=float(draws.std(ddof=1)-data['sd']),endpoint_error=(interval-np.array(data['interval'])).tolist(),
                    rank=int(np.sum(draws[0,::16]<data['truth'])),rank_draws=len(draws[0,::16]))
                # R reads the exact chain/iteration table for modern diagnostics.
                table=np.column_stack((np.repeat(np.arange(4),draws.shape[1]),np.tile(np.arange(draws.shape[1]),4),draws.ravel()))
                np.savetxt(folder/'diagnostic-input.csv',table,delimiter=',',header='chain,iteration,q',comments='')
        except Exception as exc:
            row=dict(dataset=data['id'],workflow=kernel+'/'+executor,status='failed',error=str(exc),traceback=traceback.format_exc())
            write_json(folder/'exception.json',row)
        rows.append(row);write_json(out/'progress.json',rows)
        print(key,row['status'],flush=True)
write_json(out/'summary.json',dict(design=design,rows=rows,planned=60,completed=sum(r['status']=='completed' for r in rows),
    failed=sum(r['status']!='completed' for r in rows),interpretation='12 independent data sets, not 60 independent calibration replications; endpoint/moment differences paired by data set.'))
