"""Join modern posterior diagnostics with frozen function errors and cost tiers."""
from pathlib import Path
import json,csv
import numpy as np
from parallelbayes.experiment import write_json,file_hash
out=Path('output/cpu-revision')
records=[json.loads(p.read_text()) for p in sorted((out/'modern').glob('formal-*.json'))]
if len(records)!=1920:raise RuntimeError(f'Modern diagnostics incomplete: {len(records)}/1920')
lookup={(r['identity']['model'],r['identity']['method'],int(r['identity']['retained_draws']),int(r['identity']['replicate'])):r for r in records}
original=json.loads(Path('benchmark/analysis/outputs/cpu-formal/formal-summary.json').read_text())
metrics=json.loads(Path('benchmark/analysis/outputs/cpu-formal/run-metrics.json').read_text())
rows=[]
def valid(values):return [v for v in values if v is not None and np.isfinite(v)]
for g in original['groups']:
 rr=[x for x in metrics if x['model']==g['model'] and x['method']==g['method'] and x['retained_draws']==g['retained_draws']]
 diag=[lookup[(x['model'],x['method'],x['retained_draws'],x['replicate'])] for x in rr]
 row=dict(model=g['model'],method=g['method'],retained_draws=g['retained_draws'],repetitions=len(rr),
   divergences=sum(x.get('divergences',0) for x in rr),divergent_fits=sum(x.get('divergences',0)>0 for x in rr),
   transitions=24*4*g['retained_draws'],step_cap_hits=sum(x.get('retained_transitions_at_step_cap',0) for x in rr),
   max_function_squared_error=g['max_mean_squared_error'],error_95=g['error_with_reference_sensitivity_95'],reference_usable=g['reference_usable'],
   precision=g['precision_assessment'][0]['status'])
 row['divergence_fraction']=row['divergences']/row['transitions'];row['step_cap_fraction']=row['step_cap_hits']/row['transitions']
 for kind in ['parameter','function']:
  vs=[v for d in diag for v in d['variables'] if v['kind']==kind]
  rhs=valid([v['rhat'] for v in vs]);eb=valid([v['ess_bulk'] for v in vs]);et=valid([v['ess_tail'] for v in vs])
  row[kind+'_diagnostics']=dict(total=len(vs),undefined_rhat=sum(v['rhat'] is None for v in vs),max_rhat=max(rhs) if rhs else None,
     min_bulk_ess=min(eb) if eb else None,min_tail_ess=min(et) if et else None,
     fits_with_any_undefined=sum(any(v['rhat'] is None for v in d['variables'] if v['kind']==kind) for d in diag),
     fits_with_rhat_above_1_01=sum(any(v['rhat'] is not None and v['rhat']>1.01 for v in d['variables'] if v['kind']==kind) for d in diag))
 rows.append(row)
write_json(out/'grouped-diagnostics.json',dict(groups=rows,scope='Post-review diagnostics; 24 paired repetitions per group, no inference that selected function accuracy proves global exploration',input_hashes={p.name:file_hash(p) for p in sorted((out/'modern').glob('*.json'))}))
fields=['model','method','retained_draws','repetitions','divergences','divergent_fits','transitions','divergence_fraction','step_cap_hits','step_cap_fraction','max_function_squared_error','reference_usable','precision']
with (out/'nuts-by-model-budget.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:x[k] for k in fields} for x in rows if x['method']=='nuts/sequential')
for x in rows:
 if x['method']=='nuts/sequential':print(x['model'],x['retained_draws'],x['divergences'],x['step_cap_hits'],x['precision'],x['parameter_diagnostics']['max_rhat'])
refrows=[json.loads(p.read_text()) for p in sorted((out/'modern').glob('reference-*.json'))]
assert len(refrows)==8
write_json(out/'reference-modern.json',dict(fits=refrows,scope='Per-reference-fit modern diagnostics. Constant sign event remains undefined; no upgrade of L2 reference usability.'))
