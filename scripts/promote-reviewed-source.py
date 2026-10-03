"""Promote reviewed boundary repairs only after the frozen CPU v1 run ends."""
from pathlib import Path
import shutil,json,difflib,tarfile
from parallelbayes.experiment import source_hash,freeze,file_hash,write_json
root=Path.cwd();runs=root/'benchmark/runs/cpu-formal-v1'
if (runs/'.runner.lock').exists():raise RuntimeError('Frozen v1 computation is still running')
registry=json.loads((runs/'registry.json').read_text())
if len(registry['tasks'])!=1920 or any(x['status'] not in ('completed','failed') for x in registry['tasks']):
 raise RuntimeError('Keep the frozen source until all original tasks end')
old=json.loads(Path('benchmark/protocols/protocol-v1.json').read_text())
completion=Path('execution/source-snapshots/release-0.1.1.json')
if completion.exists() and source_hash(root)==json.loads(completion.read_text())['source_sha256']:
 print('Reviewed source already promoted; preserving its protocols');raise SystemExit(0)
if source_hash(root)!=old['source_sha256']:raise RuntimeError('Source changed before controlled promotion')
import xml.etree.ElementTree as ET
suites=ET.parse('execution/logs/safety-stage.xml').getroot().findall('testsuite')
if not suites or any(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites):raise RuntimeError('Safety regression checks incomplete')
stage=Path('software/release-safety-stage');changes=[]
for p in sorted(list(stage.glob('r-package/inst/python/parallelbayes/*.py'))+list(stage.glob('r-package/R/*.R'))):
 dest=p.relative_to(stage);before=dest.read_text() if dest.exists() else ''
 changes.extend(difflib.unified_diff(before.splitlines(True),p.read_text().splitlines(True),fromfile=str(dest),tofile=str(dest)))
 shutil.copy2(p,dest)
Path('execution/source-snapshots/release-0.1.0-to-0.1.1.patch').write_text(''.join(changes))
for path,oldversion,newversion in [('pyproject.toml','version = "0.1.0"','version = "0.1.1"'),('r-package/DESCRIPTION','Version: 0.1.0','Version: 0.1.1')]:
 p=Path(path);p.write_text(p.read_text().replace(oldversion,newversion))
# Already frozen against the separately reviewed source. Never refreeze in place.
from parallelbayes.models import fingerprint
for name in ['protocol-v3','pilot-v4','reference-v3','statistical-v4']:
 p=json.loads(Path(f'benchmark/protocols/{name}.json').read_text());digest=p.pop('protocol_sha256')
 if fingerprint(p)!=digest or p['source_sha256']!=source_hash(root):raise RuntimeError('Reviewed protocol/source mismatch')
with tarfile.open('execution/source-snapshots/release-0.1.1-source.tar.gz','w:gz') as archive:
 for pattern in ['r-package/inst/python/parallelbayes/*.py','r-package/R/*.R','models/stan/*.stan']:
  for p in sorted(Path('.').glob(pattern)):archive.add(p,arcname=str(p))
write_json('execution/source-snapshots/release-0.1.1.json',dict(source_sha256=source_hash(root),previous_source_sha256=old['source_sha256'],
 patch_sha256=file_hash('execution/source-snapshots/release-0.1.0-to-0.1.1.patch'),
 cpu_formal='Historical frozen 0.1.0 / protocol-v1; no silent replacement',gpu_formal='0.1.1 / protocol-v3, not yet executed',
 comparison='Within-machine paired methods. No pure cross-version hardware speedup attribution.'))
print('Promoted source 0.1.1; preserved frozen 0.1.0 results and source')
