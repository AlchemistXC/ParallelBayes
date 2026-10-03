"""Replay representative frozen raw inputs under an explicitly selected old/new core."""
import argparse,json,os,sys,tarfile,subprocess
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--worker',choices=['old','new']);a=p.parse_args()
root=Path.cwd();out=root/'execution/cpu-revision-v1/version-replay';out.mkdir(parents=True,exist_ok=True)
protocol=json.loads((root/'benchmark/protocols/protocol-v1.json').read_text())
if a.worker:
 from parallelbayes import sample
 from parallelbayes.experiment import write_json,file_hash
 from parallelbayes.models import fingerprint
 import parallelbayes,jax
 for task in protocol['tasks']:
  if task['replicate']!=0 or task['retained_draws']!=256:continue
  tid=fingerprint(task)[:20];dest=out/a.worker/(tid+'.json')
  if dest.exists():continue
  saved=root/'benchmark/runs/cpu-formal-v1/tasks'/tid
  state=json.loads((saved/'state.json').read_text());raw_path=saved/state['attempt']/'raw.npz'
  c=dict(protocol['defaults'],**task['config']);c['timing_repeats']=1
  # Keep sampling parameters and the actual saved random tape; only skip timing replays.
  with np.load(raw_path) as raw:
   tape={k.removeprefix('tape__'):raw[k] for k in raw.files if k.startswith('tape__')}
   r=sample(protocol['models'][task['model']],c,tape=tape or None)
   delta=float(np.max(np.abs(raw['draws']-r['draws']))) if r['draws'] is not None else None
  dest.parent.mkdir(exist_ok=True);np.savez_compressed(dest.with_suffix('.npz'),draws=r['draws'],accept=r['diagnostics'].get('accept',[]))
  write_json(dest,dict(model=task['model'],method=c['kernel']+'/'+c['executor'],source_module=parallelbayes.__file__,status=r['status'],historical_raw_sha256=file_hash(raw_path),max_difference_from_historical=delta,
    audit=r.get('audit'),timing=r['timing'],output_sha256=file_hash(dest.with_suffix('.npz'))))
  print(a.worker,task['model'],c['kernel'],c['executor'],delta,flush=True);jax.clear_caches()
else:
 old=out/'archived-source';old.mkdir(exist_ok=True)
 if not (old/'r-package').exists():
  with tarfile.open('execution/source-snapshots/formal-v1-source.tar.gz') as tar:tar.extractall(old,filter='data')
 for version,source in [('old',old),('new',root)]:
  env=dict(os.environ,PYTHONPATH=str(source/'r-package/inst/python'))
  subprocess.run([sys.executable,__file__,'--worker',version],env=env,check=True)
 rows=[]
 for p in sorted((out/'old').glob('*.json')):
  q=out/'new'/p.name;oldr=json.loads(p.read_text());newr=json.loads(q.read_text())
  with np.load(p.with_suffix('.npz')) as x,np.load(q.with_suffix('.npz')) as y:
   diff=float(np.max(np.abs(x['draws']-y['draws'])));mismatch=int(np.sum(x['accept']!=y['accept']))
  rows.append(dict(model=oldr['model'],method=oldr['method'],old_status=oldr['status'],new_status=newr['status'],path_difference=diff,acceptance_mismatch=mismatch,
   old_against_historical=oldr['max_difference_from_historical'],new_against_historical=newr['max_difference_from_historical']))
 from parallelbayes.experiment import write_json
 write_json(out/'summary.json',dict(rows=rows,scope='One original repeat, shorter retained budget, all 8 models x 5 workflows. MH actual tape; NUTS original seed/keys. No speed-equivalence claim; paired caches and timing are not controlled.'))
