"""Three complementary local archives; no private authoring tools or environments."""
from pathlib import Path
import hashlib,json,tarfile,io,time
root=Path.cwd();out=root/'output/reproduction';out.mkdir(exist_ok=True)
bundle='parallelbayes-cpu-review-v1';prefix='parallelbayes-reproduction'
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def collect(paths):
 files={}
 for name in paths:
  p=root/name
  if not p.exists():raise FileNotFoundError(p)
  for f in ([p] if p.is_file() else p.rglob('*')):
   rel=f.relative_to(root)
   if not f.is_file() or f.is_symlink():continue
   if any(x in {'__pycache__','.pytest_cache','figure-qa','archived-source'} or x.endswith('.egg-info') for x in rel.parts):continue
   if f.suffix in {'.pyc','.so','.dylib','.o','.hpp','.aux','.log','.out','.synctex','.xdv'}:continue
   files[str(rel)]=f
 return files
software=collect(['r-package','pyproject.toml','LICENSE','models/stan','examples','tests/python','tests/safety','environment/locks','software/parallel-mcmc-upstream','execution/source-snapshots/formal-v1-source.tar.gz','execution/source-snapshots/release-0.1.0-to-0.1.1.patch','execution/source-snapshots/release-0.1.1-source.tar.gz','execution/source-snapshots/release-0.1.1.json','output/release/parallelbayes_0.1.1.tar.gz'])
analysis=collect(['reproduce.py','docs/CAPABILITIES.md','docs/CPU-REVIEW-REVISION.md','docs/PORTABLE-REPRODUCTION.md','docs/COMPUTATION-CONTRACT.md','docs/INSTALL-AND-USE.md','docs/EXTENDING-TARGETS.md','docs/REBUILD-RESULTS.md','docs/VERSION-BRIDGE.md','docs/THIRD-PARTY.md','docs/RELEASE-NOTES.md','benchmark/protocols','scripts/install-r.R','scripts/setup-bridgestan.py','scripts/statistical-validation.py','scripts/write-results-tex.py','scripts/audit-final-evidence.py','scripts/verify-statistical-evidence.py','scripts/revision/mechanism.py','scripts/revision/version-replay.py','scripts/revision/modern-diagnostics.R','scripts/revision/write-revision-tex.py','scripts/revision/build-reproduction.py'])
analysis.update({k:v for k,v in collect(['benchmark/analysis']).items() if '/outputs/' not in k});analysis['README.md']=root/'docs/PORTABLE-REPRODUCTION.md'
evidence=collect(['benchmark/runs/cpu-formal-v1','benchmark/runs/cpu-reference-v1','execution/statistical-v4','execution/cpu-revision-v1/cpu-mechanism-v1','execution/cpu-revision-v1/cpu-mechanism-development','execution/cpu-revision-v1/mechanism-development-code.py','execution/cpu-revision-v1/version-replay','output/cpu-revision','benchmark/analysis/outputs','manuscript/software','execution/custom-target-example.json','execution/custom-target-R-example.json','figures/software','output/software-paper/软件与基准研究.pdf','output/software-paper/qa-cpu-review/QA.md','execution/logs/r-reviewed-check.txt','execution/logs/python-reviewed-release.xml','execution/logs/r-stan-end-to-end.json'])
# Keep all review attempt logs, including failure and explicit integration evidence.
for f in (root/'execution/cpu-revision-v1').glob('*'):
 if f.is_file() and f.suffix in ['.log','.json','.xml'] and not f.name.startswith('archive-'):evidence[str(f.relative_to(root))]=f
for name in ['validation-attempt1.xml','validation-repair.xml']:
 f=root/'execution/cpu-revision-v1/relocated-checkout'/name;evidence[str(f.relative_to(root))]=f
# Include QA log results but never private QA implementation.
for f in (root/'figures/software/qa-cpu-review').glob('*.log'):evidence[str(f.relative_to(root))]=f
plans=[('software',software,'software-0.1.1-cpu-review-v1.tar.gz'),('experiments',analysis,'experiments-cpu-review-v1.tar.gz'),('evidence-paper',evidence,'evidence-paper-cpu-review-v1.tar')]
seen=set();index=[]
for kind,files,name in plans:
 assert not seen.intersection(files),'Components overlap';seen.update(files)
 manifest=dict(bundle_id=bundle,component=kind,core_version='0.1.1',formal_source_version='0.1.0',files={n:sha(p) for n,p in sorted(files.items())})
 payload=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();path=out/name
 with tarfile.open(path,'w:gz' if name.endswith('.gz') else 'w',format=tarfile.PAX_FORMAT) as tar:
  for rel,p in sorted(files.items()):tar.add(p,arcname=prefix+'/'+rel,recursive=False)
  info=tarfile.TarInfo(prefix+'/reproduction-manifests/'+kind+'.json');info.size=len(payload);info.mtime=0;tar.addfile(info,io.BytesIO(payload))
 row=dict(component=kind,path=name,files=len(files),bytes=path.stat().st_size,sha256=sha(path));index.append(row);print(row,flush=True)
(out/'index.json').write_text(json.dumps(dict(bundle_id=bundle,archives=index,core_source_sha256='d8cb2fc2bf950fbe6b47841f3feb449d553e5f2a7c78d140811c6b2f2ba51ec7',scope='Local CPU research candidate; no GPU support, no public publication',instructions='Extract all three in one parent directory, cd parallelbayes-reproduction; python reproduce.py verify before rebuilding'),ensure_ascii=False,indent=2)+'\n')
(out/'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in index))
(out/'README.md').write_text((root/'docs/PORTABLE-REPRODUCTION.md').read_text())
