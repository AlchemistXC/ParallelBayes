from pathlib import Path
import csv,json
import numpy as np
from parallelbayes.experiment import write_json
root=Path('benchmark/runs/cpu-pilot-v1')
rows=[]
for statefile in root.glob('tasks/*/state.json'):
 state=json.loads(statefile.read_text());task=state['task'];r=json.loads((statefile.parent/state['attempt']/'result.json').read_text());c=task['config']
 rows.append(dict(model=task['model'],**c,status=state['status'],**{f't_{k}':v for k,v in r.get('timing',{}).items()},
                  max_path_error=max((r.get('audit') or {}).get('max_abs_path_error',[float('nan')])),
                  iterations=float(np.mean(r.get('diagnostics',{}).get('iterations',[float('nan')]))),
                  peak_rss=r.get('host_process_peak_rss_bytes_sampled')))
Path('benchmark/analysis/outputs').mkdir(parents=True,exist_ok=True)
with open('benchmark/analysis/outputs/pilot-raw.csv','w') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
summary=[]
for model in ['G1','G2','L1','L2']:
 for kernel in ['mala','rwm']:
  for n in [256,2048]:
   for w in [16,64,256]:
    group=[r for r in rows if r['model']==model and r['kernel']==kernel and r['draws']==n and r['executor']!='sequential' and r['window']==w]
    ratios=[];complete=[]
    for r in group:
     base=next(b for b in rows if b['model']==model and b['kernel']==kernel and b['draws']==n and b['seed']==r['seed'] and b['executor']=='sequential')
     if r['status']=='completed' and base['status']=='completed':
      ratios.append(base['t_sample']/r['t_sample']);complete.append(base['t_total']/r['t_total'])
    summary.append(dict(model=model,kernel=kernel,draws=n,window=w,attempted=len(group),failed=sum(r['status']!='completed' for r in group),
                        median_execution_speedup=float(np.median(ratios)) if ratios else None,
                        median_complete_speedup=float(np.median(complete)) if complete else None))
write_json('benchmark/analysis/outputs/pilot-summary.json',dict(tasks=len(rows),failed=sum(r['status']!='completed' for r in rows),
 max_path_error=max(r['max_path_error'] for r in rows),groups=summary,
 limitation='3 paired tapes; first tasks overlapped initial Stan compilation; developmental timings, not final performance evidence'))
print('tasks',len(rows),'failed',sum(r['status']!='completed' for r in rows),'path error',max(r['max_path_error'] for r in rows))
for name in ['G1','G2','L1','L2']:
 print(name,[r for r in summary if r['model']==name and r['draws']==2048 and r['window']==64])
