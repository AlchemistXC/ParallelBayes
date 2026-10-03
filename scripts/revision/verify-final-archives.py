"""Verify final delivery, retaining the earlier full numerical rebuild evidence."""
from pathlib import Path
import json,hashlib,tarfile,subprocess,os
root=Path.cwd();out=root/'execution/cpu-revision-v1';candidate=json.loads((out/'archive-validation.json').read_text());assert all(s['exit_code']==0 for s in candidate['stages']) and len(candidate['stages'])==5
project=Path(candidate['relocated_path']);old={}
for p in (project/'reproduction-manifests').glob('*.json'):old.update(json.loads(p.read_text())['files'])
index=json.loads((root/'output/reproduction/index.json').read_text());new={}
for row in index['archives']:
 path=root/'output/reproduction'/row['path'];h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 assert h.hexdigest()==row['sha256']
 with tarfile.open(path) as tar:
  ms=[m for m in tar.getmembers() if '/reproduction-manifests/' in m.name]
  assert len(ms)==1;new.update(json.load(tar.extractfile(ms[0]))['files']);tar.extractall(project.parent,filter='data')
protected=['r-package/','models/','tests/','environment/locks/','benchmark/analysis/','benchmark/protocols/','benchmark/runs/','execution/statistical-v4/','execution/cpu-revision-v1/cpu-mechanism-v1/','output/cpu-revision/','scripts/revision/modern-diagnostics.R','scripts/revision/mechanism.py','reproduce.py']
keys={k for k in set(old)|set(new) if any(k.startswith(p) for p in protected)}
assert all(old.get(k)==new.get(k) for k in keys),'Scientific inputs changed since full clean-environment rebuild'
changed=[k for k in set(old)|set(new) if old.get(k)!=new.get(k)]
py=root/'execution/cpu-revision-v1/clean-python/bin/python';env=dict(os.environ,PB_TECTONIC='/Applications/ChatGPT.app/Contents/Resources/tectonic/tectonic')
for stage in ['verify','paper']:
 with (out/('final-archive-'+stage+'.log')).open('w') as log:subprocess.run([str(py),'reproduce.py',stage],cwd=project,env=env,check=True,stdout=log,stderr=subprocess.STDOUT)
import fitz
current=fitz.open(root/'output/software-paper/软件与基准研究.pdf');rebuilt=fitz.open(project/'output/software-paper/软件与基准研究.pdf')
assert len(current)==len(rebuilt)==17
assert [p.get_text() for p in current]==[p.get_text() for p in rebuilt]
report=dict(status='passed',bundle=index['bundle_id'],archives=index['archives'],files_verified=len(new),protected_scientific_files_unchanged=len(keys),changes_since_numerical_rebuild=sorted(changed),full_rebuild=candidate['stages'],final_archive_verification=True,final_paper_pages=17,final_paper_extracted_text_identical=True,scope='Fresh temporary extraction and independent locked Python environment; same Mac/R/compiler. Full analysis and 1928 modern diagnostics already rebuilt; only prose, packaging or validation metadata subsequently changed.')
for p in [out/'final-archive-validation.json',root/'output/reproduction/validation.json']:p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Final delivery verified',len(new),'files;',len(keys),'scientific files unchanged; final paper text identical')
