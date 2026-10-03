#!/usr/bin/env python3
"""Portable CPU reproduction entry. Default operations never launch the formal grid."""
from pathlib import Path
import argparse,subprocess,sys,os,json,hashlib,shutil
root=Path(__file__).resolve().parent;os.chdir(root)
p=argparse.ArgumentParser();p.add_argument('stage',choices=['verify','example','tests','analysis','diagnostics','figures','paper']);a=p.parse_args()
def run(*args,env=None):subprocess.run(list(args),check=True,env=env)
def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(2**20),b''):h.update(block)
 return h.hexdigest()
if a.stage=='verify':
 manifests=sorted(Path('reproduction-manifests').glob('*.json'))
 if len(manifests)!=3:raise SystemExit('Extract all three components first: expected three manifests')
 count=0;ids=set()
 for path in manifests:
  m=json.loads(path.read_text());ids.add(m['bundle_id'])
  for name,h in m['files'].items():
   if not Path(name).is_file() or digest(name)!=h:raise RuntimeError('Missing/changed file: '+name)
   count+=1
 assert len(ids)==1
 print(json.dumps(dict(status='passed',files=count,bundle=next(iter(ids)))))
elif a.stage=='example':run(sys.executable,'examples/custom-poisson-target.py')
elif a.stage=='tests':
 run(sys.executable,'-m','pytest','tests/python','tests/safety','-q')
 env=dict(os.environ,RETICULATE_PYTHON=sys.executable,R_LIBS_USER=str(root/'environment/R-library'),PB_RUN_INTEGRATION='1')
 run('Rscript','--vanilla','-e','library(testthat); library(parallelbayes); test_dir("r-package/tests/testthat", reporter="summary")',env=env)
elif a.stage=='analysis':
 run(sys.executable,'scripts/audit-final-evidence.py')
 for script in ['benchmark/analysis/revision/existing-evidence.py','benchmark/analysis/revision/summarize.py','benchmark/analysis/revision/mechanism-summary.py','scripts/write-results-tex.py','scripts/revision/write-revision-tex.py']:run(sys.executable,script)
elif a.stage=='diagnostics':
 # A new directory forces recomputation, preserving original diagnostic timing.
 dest=root/'output/modern-recomputed';env=dict(os.environ,RETICULATE_PYTHON=sys.executable,PB_DIAGNOSTIC_OUTPUT=str(dest))
 run('Rscript','--vanilla','scripts/revision/modern-diagnostics.R',env=env)
 original=root/'output/cpu-revision/modern';count=0
 for q in sorted(original.glob('*.json')):
  if q.name=='manifest.json':continue
  x=json.loads(q.read_text());y=json.loads((dest/q.name).read_text());x.pop('diagnostic_seconds',None);y.pop('diagnostic_seconds',None)
  assert x==y, 'Modern numerical diagnostics differ: '+q.name
  count+=1
 print('Modern diagnostics compared, excluding elapsed time:',count)
elif a.stage=='figures':
 run(sys.executable,'benchmark/analysis/figures.py');run(sys.executable,'benchmark/analysis/revision/figures.py')
else:
 source=root/'manuscript/software/软件与基准研究.tex';out=root/'output/software-paper';out.mkdir(parents=True,exist_ok=True)
 engine=os.environ.get('PB_TECTONIC') or shutil.which('tectonic')
 if engine:
  subprocess.run([engine,'-X','compile','--outdir',str(out),source.name],cwd=source.parent,check=True)
 else:
  engine=shutil.which('xelatex')
  if not engine:raise SystemExit('Install/provide Tectonic or XeLaTeX (ctex/Fandol); PB_TECTONIC may name an existing executable')
  for _ in range(2):subprocess.run([engine,'-interaction=nonstopmode','-halt-on-error','-output-directory='+str(out),source.name],cwd=source.parent,check=True)
