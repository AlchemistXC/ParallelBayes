"""Paired analytic intervals, endpoints, moments and rank outputs (not pooled evidence)."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.stats import beta
from evidence import write_json,sha,verify_checksums

p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run
summary=json.loads((root/'summary.json').read_text());rows=summary['rows'];datasets=summary['design']['datasets']
if len(rows)!=60 or len({(r['dataset'],r['workflow']) for r in rows})!=60:raise ValueError('incomplete SBC design')
groups=[]
for workflow in sorted({r['workflow'] for r in rows}):
    rr=[r for r in rows if r['workflow']==workflow];ok=[r for r in rr if r['status']=='completed']
    for r in ok:
        kernel,executor=workflow.split('/')
        verify_checksums(root/f"{r['dataset']:02d}-{kernel}-{executor}",r['checksums'])
    g=dict(workflow=workflow,planned=len(rr),completed=len(ok),failed=len(rr)-len(ok))
    if ok:
        g.update(covered=sum(r['covered'] for r in ok),analytic_covered=sum(r['analytic_covered'] for r in ok),
            coverage_disagreement_datasets=[r['dataset'] for r in ok if r['covered']!=r['analytic_covered']],
            mean_rmse=float(np.sqrt(np.mean([r['mean_error']**2 for r in ok]))),
            sd_rmse=float(np.sqrt(np.mean([r['sd_error']**2 for r in ok]))),
            endpoint_rmse=np.sqrt(np.mean(np.array([r['endpoint_error'] for r in ok])**2,axis=0)).tolist())
    groups.append(g)
covered=sum(d['interval'][0]<=d['truth']<=d['interval'][1] for d in datasets);n=len(datasets)
out=dict(independent_data_sets=n,workflows_share_data=True,planned_fits=60,completed=summary['completed'],failed=summary['failed'],
    analytic_covered=covered,analytic_coverage_ci95=[0 if covered==0 else beta.ppf(.025,covered,n-covered+1),1 if covered==n else beta.ppf(.975,covered+1,n-covered)],
    groups=groups,summary_sha256=sha(root/'summary.json'),modern_diagnostics_sha256=sha(root/'modern-diagnostics.json'),
    interpretation='Small development check only. Shared data and same-kernel replay do not supply independent calibration replications. Finite-chain ranks retained; no uniformity or general convergence claim.')
write_json(root/'paired-analytic-summary.json',out)
print(json.dumps(out,indent=2))
