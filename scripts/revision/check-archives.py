"""Extract the delivered archives to a new temporary directory and use only them."""
from pathlib import Path
import tempfile,tarfile,subprocess,os,json,hashlib,time
root=Path.cwd();out=root/'execution/cpu-revision-v1';tmp=Path(tempfile.mkdtemp(prefix='parallelbayes-cpu-review-',dir='/private/tmp'))
(out/'archive-check-root.txt').write_text(str(tmp)+'\n')
index=json.loads((root/'output/reproduction/index.json').read_text());records=[]
for item in index['archives']:
 p=root/'output/reproduction'/item['path'];h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 assert h.hexdigest()==item['sha256']
 with tarfile.open(p) as t:t.extractall(tmp,filter='data')
project=tmp/'parallelbayes-reproduction';py=root/'execution/cpu-revision-v1/clean-python/bin/python'
env=dict(os.environ,R_LIBS_USER=str(root/'environment/R-library'),PB_TECTONIC='/Applications/ChatGPT.app/Contents/Resources/tectonic/tectonic')
for stage in ['verify','analysis','diagnostics','figures','paper']:
 start=time.time()
 with (out/('archive-'+stage+'.log')).open('w') as log:r=subprocess.run([str(py),'reproduce.py',stage],cwd=project,env=env,stdout=log,stderr=subprocess.STDOUT)
 records.append(dict(stage=stage,exit_code=r.returncode,elapsed=time.time()-start));(out/'archive-validation.json').write_text(json.dumps(dict(bundle=index['bundle_id'],archives=index['archives'],relocated_path=str(project),shared_environment='Independent locked Python environment; same macOS and existing R library/compiler',stages=records),indent=2)+'\n')
 print(stage,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
