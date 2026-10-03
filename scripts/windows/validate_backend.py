"""Save actual CPU/CUDA/oracle comparison arrays and negative replay evidence."""
import argparse
import time
from pathlib import Path
import numpy as np
from parallelbayes import make_model,validate_model,sample
from parallelbayes.reference import benchmark_model
from parallelbayes.torch_backend.sampling import settings,random_tape
from parallelbayes.torch_backend.nuts_baseline import sample_cpu_nuts
from evidence import ROOT,configure,write_json,save_result,source_files,git,runtime

p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
configure();out=args.output
if out.exists():raise FileExistsError('preserve previous validation attempt')
out.mkdir(parents=True)
rows=[];models={}
for name in ['G1','G2','L1','L2','T1','H1','H2','A1','M1']:
    spec=benchmark_model(name).spec;models[name]=spec
    for device in ['cpu','cuda']:
        model=make_model(spec,backend='torch',device=device)
        v=validate_model(model)
        write_json(out/name/device/'density.json',v)
        if not v['passed']:raise RuntimeError(str(v))
        for kernel,executor in [('mala','sequential'),('mala','quasi_deer'),('rwm','sequential'),('rwm','online_picard')]:
            c=settings(dict(device=device,kernel=kernel,executor=executor,draws=37,chains=2,window=8,step_size=.001))
            tape=random_tape(c,model.dimension)
            r=sample(model,c,tape)
            checks,_=save_result(out/name/device/executor/kernel,r,tape)
            rows.append(dict(model=name,device=device,kernel=kernel,executor=executor,status=r['status'],checksums=checks,audit=r['audit']))
for executor,kernel in [('quasi_deer','mala'),('online_picard','rwm')]:
    c=settings(dict(device='cuda',kernel=kernel,executor=executor,draws=31,window=8,max_iter=1,step_size=.7))
    tape=random_tape(c,3);spec=dict(kind='gaussian',dimension=3)
    for label,extra in [('exhausted',{}),('replay',{}),('fallback',{'on_failure':'sequential'})]:
        r=sample(spec,dict(c,**extra),tape,backend='torch')
        save_result(out/'negative'/executor/label,r,tape)
        rows.append(dict(model='negative',device='cuda',executor=executor,case=label,status=r['status'],expected='completed' if label=='fallback' else 'failed'))
write_json(out/'models.json',models)
summary=dict(source_commit=git('rev-parse','HEAD'),source_files=source_files(),runtime=runtime(),rows=rows,
    positive_passed=sum(r['status']=='completed' for r in rows if r['model']!='negative'),
    positive_failed=sum(r['status']!='completed' for r in rows if r['model']!='negative'))
write_json(out/'summary.json',summary)
print(summary['positive_passed'],'positive passed;',summary['positive_failed'],'positive failed; negative arrays saved')
if summary['positive_failed']:raise SystemExit(1)
