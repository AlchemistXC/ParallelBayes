"""Build an auditable, standalone source transfer; excludes papers and local envs."""
from pathlib import Path
import shutil,tarfile,hashlib,json
from parallelbayes.experiment import file_hash,source_hash,write_json
out=Path('handoff/gpu');stage=out/'bundle-0.1.1-rc2';stage.mkdir(parents=True,exist_ok=True)
import difflib,xml.etree.ElementTree as ET
archive=out/'parallelbayes-gpu-handoff-0.1.1-rc2.tar.gz'
if archive.exists():raise FileExistsError('A released archive is immutable; choose a new release candidate name')
suites=ET.parse('execution/logs/python-reviewed-stage.xml').getroot().findall('testsuite')
if not suites or any(int(x.get('failures',0))+int(x.get('errors',0)) for x in suites):raise RuntimeError('Reviewed Python checks not passed')
if 'Status: OK' not in Path('execution/logs/r-reviewed-check.txt').read_text():raise RuntimeError('Reviewed R package check not passed')
patterns=['LICENSE','pyproject.toml','r-package/DESCRIPTION','r-package/NAMESPACE','r-package/LICENSE','r-package/.Rbuildignore',
 'examples/*.R','r-package/R/*.R','r-package/man/*.Rd','r-package/inst/python/parallelbayes/*.py','r-package/tests/*.R','r-package/tests/testthat/*.R',
 'models/stan/*.stan','tests/python/*.py','tests/safety/*.py','scripts/*.py','scripts/*.R','scripts/figure-qa/*.py','environment/locks/*',
 'software/parallel-mcmc-upstream/*','benchmark/protocols/*.json','benchmark/analysis/*.py',
 'benchmark/analysis/outputs/reference-summary.json','benchmark/analysis/outputs/reference-summary.provenance.json','execution/source-snapshots/release-0.1.0-to-0.1.1.patch','execution/source-snapshots/formal-v1-source.tar.gz','execution/source-snapshots/release-0.1.1.json','docs/*.md','execution/WORK-PACKAGES.md',
 'execution/logs/python-reviewed-stage.xml','execution/logs/python-reviewed-release.xml','execution/logs/r-reviewed-check.txt','execution/logs/r-release-quickstart.txt','execution/logs/r-release-logistic-paired.txt','execution/final-evidence-audit.json','handoff/gpu/*.md','handoff/gpu/*.sh','handoff/gpu/*.ps1','handoff/gpu/*.py',
 'environment/bridgestan-2.7.0.tar.gz','environment/stanc-linux-2.37.0','environment/macos.json']
files=set()
for pattern in patterns:
 for p in Path('.').glob(pattern):
  if p.is_file() and '__pycache__' not in p.parts:files.add(p)
for p in sorted(files):
 dest=stage/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
# The reviewed release is now promoted and independently checked. Copy its
# preserved historical patch verbatim; do not replace it with an empty diff.
expected=json.loads((stage/'benchmark/protocols/protocol-v3.json').read_text())['source_sha256']
if source_hash(stage)!=expected:raise RuntimeError('Packaged source differs from reviewed protocol')
write_json(stage/'RELEASE.json',dict(version='0.1.1-rc2',source_sha256=source_hash(stage),
 cpu_validation='58 Python tests and R CMD check passed for reviewed 0.1.1; 1920 CPU formal v1 tasks and 320 fresh SBC fits completed; installed R examples passed',
 gpu_support='unverified until returned evidence',changes_from_rc1='Documentation/examples and analysis companions; identical source hash and GPU protocol-v3. Existing rc1 sampling may continue',data='synthetic benchmark models only; no literature PDFs'))
manifest='\n'.join(f'{file_hash(p)}  {p.relative_to(stage)}' for p in sorted(stage.rglob('*')) if p.is_file() and p.name!='SHA256SUMS')+'\n'
(stage/'SHA256SUMS').write_text(manifest)
archive=out/'parallelbayes-gpu-handoff-0.1.1-rc2.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in sorted(stage.rglob('*')):
  if p.is_file():tar.add(p,arcname=str(p.relative_to(stage)))
(out/(archive.name+'.sha256')).write_text(file_hash(archive)+'  '+archive.name+'\n')
print(archive.resolve(),archive.stat().st_size)
