"""Summarize every frozen mechanism task, preserving failed denominators."""
from pathlib import Path
import json,csv
import numpy as np
from parallelbayes.experiment import write_json,file_hash
from parallelbayes.models import fingerprint
p=json.loads(Path('benchmark/protocols/cpu-mechanism-v1.json').read_text());root=Path('execution/cpu-revision-v1/cpu-mechanism-v1');rows=[];inputs={}
expected={fingerprint(t)[:20]:t for t in p['tasks']}
assert {x.parent.name for x in root.glob('*/state.json')}==set(expected)
for tid,t in expected.items():
 folder=root/tid;s=json.loads((folder/'state.json').read_text());assert s['task']==t and s['protocol_sha256']==p['protocol_sha256'] and s['status'] in ['completed','failed']
 for f,h in s['checksums'].items():assert file_hash(folder/f)==h
 r=json.loads((folder/'result.json').read_text());assert r['status']==s['status'];inputs[tid]=file_hash(folder/'state.json')
 row=dict(t,status=r['status'])
 if r['status']=='completed':
  par=r['production'][t['executor']];seq=r['production']['sequential'];trace=r['trace'];rounds=trace['rounds'];n=t['draws']*t['chains']
  row.update(cached_speed_ratio=float(np.median(seq['cached_seconds'])/np.median(par['cached_seconds'])),normal_speed_ratio=seq['normal_in_memory_seconds']/par['normal_in_memory_seconds'],
    seconds_per_transition=float(np.median(par['cached_seconds'])/n),batch_throughput_factor=trace['batch_throughput_factor'],
    forward_per_transition=sum(par['diagnostics']['forward_evals'])/n,jvp_per_transition=sum(par['diagnostics']['jvp_evals'])/n,
    rounds_total=sum(par['diagnostics']['iterations']),core_equivalents=par['cpu']['core_equivalents'],sequential_core_equivalents=seq['cpu']['core_equivalents'],
    segmented_path_difference=trace['max_path_difference'],acceptance_mismatches=trace['acceptance_mismatches'],
    single_chain_rounds=len(rounds),confirmed_per_round=(t['draws']/len(rounds) if t['kernel']=='rwm' else None),
    mean_rounds_per_window=(len(rounds)/(t['draws']/t['window']) if t['kernel']=='mala' else None),
    segmented_seconds=trace['segmented_seconds'],stage_seconds=trace['stage_seconds'],control_seconds=trace['python_control_and_other'],
    normal_parallel_seconds=par['normal_in_memory_seconds'],normal_sequential_seconds=seq['normal_in_memory_seconds'])
 else:row['error']=r['error']
 rows.append(row)
groups=[]
for key in sorted({(r['model'],r['kernel'],r['chains'],r['window']) for r in rows}):
 rr=[r for r in rows if (r['model'],r['kernel'],r['chains'],r['window'])==key];ok=[r for r in rr if r['status']=='completed']
 g=dict(zip(['model','kernel','chains','window'],key));g.update(planned=len(rr),completed=len(ok),failed=len(rr)-len(ok))
 for k in ['cached_speed_ratio','normal_speed_ratio','seconds_per_transition','batch_throughput_factor','forward_per_transition','jvp_per_transition','core_equivalents','sequential_core_equivalents','confirmed_per_round','mean_rounds_per_window']:
  vs=[r[k] for r in ok if r[k] is not None];g[k]=dict(median=float(np.median(vs)),minimum=min(vs),maximum=max(vs)) if vs else None
 stages=sorted({s for r in ok for s in r['stage_seconds']})+['python_control_and_other']
 g['segmented_fraction_median']={s:float(np.median([(r['control_seconds'] if s=='python_control_and_other' else r['stage_seconds'].get(s,0))/r['segmented_seconds'] for r in ok])) for s in stages} if ok else {}
 groups.append(g)
write_json('output/cpu-revision/mechanism-summary.json',dict(protocol_sha256=p['protocol_sha256'],source_sha256=p['source_sha256'],script_sha256=file_hash(__file__),input_sha256=inputs,rows=rows,groups=groups,planned=len(rows),failed=sum(r['status']!='completed' for r in rows),scope='3 independent tapes per cell, technical timing repeats not independent evidence. Segmented costs describe instrumented execution only.'))
with open('output/cpu-revision/mechanism-groups.csv','w') as f:
 fields=['model','kernel','chains','window','planned','failed','cached_speed_ratio','batch_throughput_factor','forward_per_transition','jvp_per_transition','core_equivalents','confirmed_per_round','mean_rounds_per_window'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for g in groups:w.writerow({k:g[k]['median'] if isinstance(g[k],dict) else g[k] for k in fields})
print('Mechanism:',len(rows),'tasks',sum(r['status']!='completed' for r in rows),'failed')
for kernel in ['mala','rwm']:
 gs=[g for g in groups if g['kernel']==kernel]
 print(kernel, {k:(min(g[k]['median'] for g in gs),max(g[k]['median'] for g in gs)) for k in ['cached_speed_ratio','batch_throughput_factor','forward_per_transition','core_equivalents']})
