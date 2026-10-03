"""Recover development-stage source snapshots by matching recorded SHA256 only.

Pilot/validation ran before the first development commit. Known compatibility
edits can be reversed in-memory; a candidate is retained only on an exact match
to the source digest recorded at execution. No experiment record is rewritten.
"""
import hashlib
import json
import subprocess
from pathlib import Path
from evidence import ROOT,write_json,sha

reversals={
 'r-package/inst/python/parallelbayes/reference.py':[
  ('    dimension = spec.get("dimension", 8)\n    if isinstance(dimension, bool) or not np.isfinite(dimension) or int(dimension) != dimension:\n        raise ValueError("dimension must be an integer")\n    d = int(dimension)', '    d = int(spec.get("dimension", 8))'),
  ('        if d < 1 or x.shape[0] < 1:\n            raise ValueError("logistic data must have positive dimensions")\n','')],
 'r-package/inst/python/parallelbayes/models.py':[
  ('import jax\njax.config.update("jax_enable_x64", True)\n','')],
 'r-package/R/interface.R':[
  ('pb_environment <- function(backend = c("jax", "torch")) {\n  backend <- match.arg(backend)', 'pb_environment <- function() {'),
  ('  module <- if (backend == "torch") "parallelbayes.torch_backend.sampling" else "parallelbayes.sampling"\n  reticulate::import(module)$environment()', '  reticulate::import("parallelbayes.sampling")$environment()')],
 'scripts/windows/validate_r.R':[
  ('stopifnot(identical(pb_environment("torch")$provider,"native_torch"))\n',''),
  ('stopifnot(length(pb_capabilities(model)$combinations)==4L)\n','')],
 'scripts/windows/run_study.py':[
  ("            if state['task']!=t or state.get('protocol_sha256')!=p['protocol_sha256']:\n                raise ValueError('task/protocol identity changed')", "            if state['task']!=t:raise ValueError('task identity changed')"),
  ("            if result['status']!=state['status']:raise ValueError('result and state status differ')\n",'')]
}


def candidates(name):
    raw=(ROOT/name).read_bytes();yield raw
    text=raw.decode('utf-8').replace('\r\n','\n')
    if name.endswith('torch_backend/sampling.py'):
        text=text[:text.index('\n\n\ndef environment():')]+'\n'
        start=text.index('        validation_evidence=')
        stop=text.index('        arbitrary_stan_translation=',start)
        text=text[:start]+text[stop:]
    if name=='tests/windows/test_torch_backend.py':
        start=text.index('\n\ndef test_diagonal_clipping_and_real_final_window():')
        stop=text.index('\n\n@pytest.mark.parametrize("config"',start)
        text=text[:start]+text[stop:]
    for old,new in reversals.get(name,[]):text=text.replace(old,new)
    yield text.encode('utf-8');yield text.replace('\n','\r\n').encode('utf-8')
    process=subprocess.run(['git','show','a774d83:'+name],cwd=ROOT,capture_output=True)
    if process.returncode==0:
        yield process.stdout;yield process.stdout.replace(b'\n',b'\r\n')


receipts=[]
for phase,entry in [('pilot-01','design.json'),('sbc-01','design.json'),('validation-01','summary.json')]:
    record=ROOT/'execution/windows-native'/phase/entry
    data=json.loads(record.read_text(encoding='utf-8'));dest=ROOT/'execution/windows-native/source-drafts'/phase
    missing=[];matched=[]
    for name,h in data['source_files'].items():
        existing=dest/name
        if existing.is_file() and sha(existing)==h:
            matched.append(name);continue
        match=next((x for x in candidates(name) if hashlib.sha256(x).hexdigest()==h),None)
        if match is None:missing.append(name);continue
        path=dest/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(match);matched.append(name)
    receipt=dict(phase=phase,record_sha256=sha(record),source_files=data['source_files'],missing=missing,matched=len(matched),
        note='Development working tree; recorded source_commit is the Git base, exact executed files are identified by source_files SHA256. Recovered bytes independently matched to those pre-existing digests.')
    write_json(dest/'SNAPSHOT.json',receipt);receipts.append(receipt)
    print(phase,len(matched),'matched;',missing,'missing')
write_json(ROOT/'execution/windows-native/source-drafts/index.json',receipts)
if any(r['missing'] for r in receipts):raise SystemExit(1)
