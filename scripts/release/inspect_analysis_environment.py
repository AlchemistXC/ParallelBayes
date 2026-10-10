import hashlib,importlib.abc,importlib.metadata as metadata,json,platform,sys
from pathlib import Path
from packaging.requirements import Requirement
source=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve()
if out.exists():raise FileExistsError(out)
blocked={'torch','jax','jaxlib','pyro','blackjax','bridgestan'};attempts=[]
class NoProviders(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in blocked:
   attempts.append(fullname);raise RuntimeError('Disallowed sampler dependency: '+fullname)
sys.meta_path.insert(0,NoProviders());sys.dont_write_bytecode=True
sys.path.insert(0,str(source/'scripts/analysis'))
import formal_analyze,formal_science,formal_statistics,formal_report
modules=[formal_analyze,formal_science,formal_statistics,formal_report]
for module in modules:
 if not Path(module.__file__).resolve().is_relative_to(source):raise ValueError('Wrong source loaded')
pending=['numpy','scipy','matplotlib','PyMuPDF'];seen={}
while pending:
 d=metadata.distribution(pending.pop());name=d.metadata['Name']
 if name.lower() in seen:continue
 rs=[Requirement(r) for r in d.requires or []]
 active=[r for r in rs if r.marker is None or r.marker.evaluate({'extra':''})]
 seen[name.lower()]=dict(name=name,version=d.version,required_dependencies=[str(r) for r in active])
 for r in active:
  if r.specifier and metadata.version(r.name) not in r.specifier:raise ValueError('Unsatisfied dependency: '+str(r))
  pending.append(r.name)
packages=sorted(seen.values(),key=lambda r:r['name'].lower())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
result=dict(scope='Read-only source import and observed dependency closure, not a new clean installation or full replay',
 python=sys.version,platform=platform.platform(),source=str(source),
 imported_sources={str(Path(m.__file__).relative_to(source)):sha(m.__file__) for m in modules},
 blocked_provider_prefixes=sorted(blocked),attempted_provider_imports=attempts,packages=packages,
 inference_dependencies_required_for_this_check=False,new_sampler_calls=0,new_R_diagnostic_calls=0,
 new_independent_repetitions=0,script_sha256=sha(__file__))
out.mkdir(parents=True)
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'compact-analysis-observed-v1.txt').write_text('# Observed Python 3.12.14 analysis/plot/PDF-QA dependency closure on macOS arm64.\n# Exact versions; this file does not pin wheel bytes or guarantee other-platform equivalence.\n# No sampler backend, editable source path or private tool is required.\n'+'\n'.join(p['name']+'=='+p['version'] for p in packages)+'\n')
print(json.dumps(dict(provider_import_attempts=attempts,dependency_packages=len(packages),new_sampler_calls=0)))
