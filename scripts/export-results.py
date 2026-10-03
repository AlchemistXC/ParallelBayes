"""Export raw results, all statuses, frozen protocols, source and environment."""
import argparse,hashlib,json,subprocess,tarfile,time
from pathlib import Path
from parallelbayes.experiment import write_json,environment,source_hash,file_hash
p=argparse.ArgumentParser();p.add_argument('--platform',choices=['cpu','gpu'],required=True);a=p.parse_args()
out=Path('handoff')/'returns';out.mkdir(parents=True,exist_ok=True)
name=f'parallelbayes-{a.platform}-return-{time.strftime("%Y%m%d-%H%M%S")}'
files=[]
patterns=['r-package/**/*.py','r-package/R/*.R','r-package/DESCRIPTION','r-package/NAMESPACE','models/stan/*.stan',
 'scripts/*.py','scripts/*.R','benchmark/protocols/*.json','benchmark/analysis/*.py',f'benchmark/runs/{a.platform}-*/**/*',
 f'execution/{a.platform}/**/*','environment/locks/*','handoff/gpu/*','software/parallel-mcmc-upstream/*',
 'pyproject.toml','tests/python/*.py','tests/safety/*.py','execution/source-snapshots/*.patch','execution/source-snapshots/*.json','benchmark/analysis/outputs/**/*.json','benchmark/analysis/outputs/**/*.csv']
for pattern in patterns:
 files.extend(p for p in Path('.').glob(pattern) if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.pyc','.tar.gz')) and 'bundle-0.1.1-rc1' not in p.parts)
write_json(out/(name+'.json'),dict(environment=environment(),source_sha256=source_hash('.'),platform=a.platform,
    run_manifests=[str(p) for p in Path('benchmark/runs').glob(f'{a.platform}-*/manifest.json')],
    note='Includes incomplete and failed tasks; inspect registries and logs before claiming completion'))
files.append(out/(name+'.json'))
freeze=out/(name+'-pip-freeze.txt');freeze.write_text(subprocess.check_output([__import__('sys').executable,'-m','pip','freeze'],text=True));files.append(freeze)
checks='\n'.join(f'{file_hash(p)}  {p}' for p in sorted(set(files)))+'\n'
checkfile=out/(name+'-SHA256SUMS');checkfile.write_text(checks)
archive=out/(name+'.tar.gz')
with tarfile.open(archive,'w:gz') as tar:
 for path in sorted(set(files)):tar.add(path,arcname=str(path))
 tar.add(checkfile,arcname='RETURN-SHA256SUMS')
(out/(archive.name+'.sha256')).write_text(file_hash(archive)+'  '+archive.name+'\n')
print(archive.resolve())
