"""Rebuild summaries and check fixed claims against complete raw evidence.

Run after finish-local-after-benchmark.py; never launches a new sampler.
"""
from pathlib import Path
import json,sys,subprocess,hashlib
import numpy as np
root=Path.cwd()
analysis=root/'benchmark/analysis/outputs'
watched=[analysis/'reference-summary.json',analysis/'reference-summary.provenance.json']
watched += [analysis/'cpu-formal'/name for name in ['formal-summary.json','paired-speedups.json','run-metrics.json','diagnostic-costs.json']]
watched += [root/'execution/statistical-v4/likelihood-ranks.json']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(root)):digest(p) for p in watched}
for command in [
 ['reference','--protocol','benchmark/protocols/reference-v1.json','--runs','benchmark/runs/cpu-reference-v1','--output','benchmark/analysis/outputs/reference-summary.json'],
 ['formal','--protocol','benchmark/protocols/protocol-v1.json','--runs','benchmark/runs/cpu-formal-v1','--reference','benchmark/analysis/outputs/reference-summary.json','--output','benchmark/analysis/outputs/cpu-formal']]:
 subprocess.run([sys.executable,'benchmark/analysis/analyze.py',*command],check=True)
subprocess.run([sys.executable,'benchmark/analysis/sbc-functions.py','--runs','execution/statistical-v4',
                '--output','execution/statistical-v4/likelihood-ranks.json'],check=True,stdout=subprocess.DEVNULL)
after={str(p.relative_to(root)):digest(p) for p in watched}
assert before==after,'Rebuilt numerical summaries changed'
s=json.loads((analysis/'cpu-formal/formal-summary.json').read_text())
rows=json.loads((analysis/'cpu-formal/run-metrics.json').read_text())
pairs=json.loads((analysis/'cpu-formal/paired-speedups.json').read_text())
assert s['planned']==s['observed']==1920 and s['pending']==0
assert len(s['groups'])==80 and all(g['attempted']==24 for g in s['groups'])
assert s['failed']==sum(r['status']!='completed' for r in rows)
assert np.isclose(sum(g['all_attempt_cost_seconds'] for g in s['groups']),sum(r['t_total'] for r in rows))
index={(r['model'],r['retained_draws'],r['replicate'],r['method']):r for r in rows}
for pair in pairs:
 key=(pair['model'],pair['retained_draws'],pair['replicate'])
 parallel=index[(*key,pair['method'])]
 sequential=index[(*key,pair['method'].split('/')[0]+'/sequential')]
 assert pair['complete_speedup']==sequential['t_total']/parallel['t_total']
 assert pair['cached_speedup']==sequential['t_cached']/parallel['t_cached']
for g in s['groups']:
 if not g['reference_usable']:
  assert all(x['status']=='not_assessable' for x in g['precision_assessment'])
stats=json.loads(Path('execution/statistical-v4/summary.json').read_text())
assert len(stats['methods'])==5 and sum(m['attempted'] for m in stats['methods'])==320
for m in stats['methods']:
 receipts=[json.loads(p.read_text()) for p in Path('execution/statistical-v4').glob('*-'+m['method'].replace('/','-')+'.json')]
 assert len(receipts)==64
 valid=[r for r in receipts if r['status']=='completed']
 assert m['failed']==64-len(valid)
 if valid:assert m['coverage']==sum(r['covered'] for r in valid)/len(valid)
 assert m['divergences']==sum(r.get('divergences',0) for r in receipts)
companion=json.loads(Path('execution/statistical-v4/likelihood-ranks.json').read_text())
assert len(companion['rows'])==320
for row in companion['rows']:
 if row['status']=='completed':assert 0<=row['rank']<=row['rank_draws']==64
report=dict(status='passed',scope='Exact numerical summary rebuild, frozen task grid, all paired ratios, cost sums, unavailable-reference decisions, and SBC receipt arithmetic',
 formal_tasks=len(rows),groups=len(s['groups']),paired_comparisons=len(pairs),sbc_fits=320,
 rebuilt_hashes=after,gpu='Historical CPU evidence only; Windows has a separate source version and protocol')
Path('execution/final-evidence-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
