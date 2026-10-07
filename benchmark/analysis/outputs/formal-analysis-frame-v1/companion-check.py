"""Companion check of nine archived references and 50,688 artificial file slots.

No trajectories, OS execution histories, formal inputs, or MCMC are generated.
The measured times describe this metadata check, not inference performance.
"""
import argparse
import json
from pathlib import Path
import resource
import shutil
import sys
import time
from types import SimpleNamespace

p=argparse.ArgumentParser()
for key in ('project','wells-source','output'):p.add_argument('--'+key,type=Path,required=True)
a=p.parse_args();root=a.project.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
sys.path[:0]=[str(root/'scripts/analysis'),str(root/'scripts/completion'),str(root/'scripts/windows')]
from formal_archive import build_index,EvidenceIndex
from formal_statistics import reference_contract
from formal_study_plan import create_study_plan
from formal_runtime import atomic_json,file_hash
from prepare_formal_study import REFERENCE_FILES

catalog=json.loads((root/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
delivery=out/'references';bundle=delivery/'bundle';sources={}
for name in REFERENCE_FILES:
    target=bundle/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,target)
    sources[name]=file_hash(target)
external=json.loads((root/'models/external/wells/source-manifest.json').read_text())
for row in external['files']:
    original=a.wells_source/row['path']
    assert original.stat().st_size==row['bytes'] and file_hash(original)==row['sha256']
    target=bundle/'external'/row['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,target)
files={p.relative_to(delivery).as_posix():dict(bytes=p.stat().st_size,sha256=file_hash(p)) for p in delivery.rglob('*') if p.is_file()}
manifest=delivery/'WINDOWS-RETURN-MANIFEST.json';atomic_json(manifest,dict(scope='Reference reconstruction fixture, not experiment return',files=files))
build_index(delivery,'bundle',file_hash(manifest),out/'reference-index')
index=EvidenceIndex(delivery,out/'reference-index')
try:refs=reference_contract(index,SimpleNamespace(protocol=dict(targets=catalog['targets'],source_files=sources)))
finally:index.close()
assert len(refs)==9 and sum(len(r['names']) for r in refs.values())==36
atomic_json(out/'reference-rebuild.json',dict(models=9,functions=36,references=refs,
    matches_frozen_reference_contract=True,external_files_verified=len(external['files']),
    reference_uncertainty_propagated=False,new_sampler_calls=0))
print('Nine-model reference reconstruction passed',flush=True)

design=create_study_plan('windows-formal-metadata-index-fixture-v1',catalog)
owned=[];primary={t['id']:t for t in design['tasks']}
for phase,items in [('main',design['tasks']),('cache',design['cache_allocation']['probes'])]:
    for t in items:
        base=t if phase=='main' else primary[t['primary_task_id']]
        owned.append((phase,dict(base,id=t['id'],protocol_sha256='artificial-not-frozen',
                                artifact_kind='posterior' if phase=='main' else 'cache_measurement')))
assert len(owned)==50688
delivery=out/'scale-delivery';delivery.mkdir();manifest=delivery/'WINDOWS-RETURN-MANIFEST.json'
payload=b'{"scope":"artificial metadata only"}\n'
import hashlib
digest=hashlib.sha256(payload).hexdigest();record=dict(bytes=len(payload),sha256=digest)
begin=time.perf_counter()
with manifest.open('x') as stream:
    stream.write('{"scope":"50,688 artificial files; no native evidence","files":{')
    for n,(phase,t) in enumerate(owned):
        name=f'bundle/formal-runs/batch-{t["batch"]:02d}/{phase}/tasks/{t["id"]}/fixture.json'
        path=delivery/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
        stream.write((',' if n else '')+json.dumps(name)+':'+json.dumps(record))
    stream.write('}}\n')
written=time.perf_counter();receipt=build_index(delivery,'bundle',file_hash(manifest),out/'scale-index')
indexed=time.perf_counter();index=EvidenceIndex(delivery,out/'scale-index')
try:
    for phase,t in owned:
        report=index.task_evidence(t,phase,f'formal-runs/batch-{t["batch"]:02d}/{phase}')
        assert report['evidence_status']=='evidence_gap' and report['known_output_without_export'] is True
        assert report['history_exports']==0 and report['task_files']==1
finally:index.close()
finished=time.perf_counter()
atomic_json(out/'scale-check.json',dict(planned_artificial_slots=len(owned),files_indexed=receipt['delivered_files'],
    all_task_lookups_checked=True,missing_history_not_reclassified_as_not_run=True,
    histories=receipt['history_exports'],manifest_bytes=manifest.stat().st_size,
    database_bytes=(out/'scale-index/files.sqlite3').stat().st_size,
    write_fixture_seconds=written-begin,index_seconds=indexed-written,query_seconds=finished-indexed,
    ru_maxrss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,ru_maxrss_units='bytes on macOS, KiB on Linux',
    timings_scope='Artificial metadata check only; not MCMC or GPU/inference performance',
    source_files={p.relative_to(root).as_posix():file_hash(p) for p in (root/'scripts/analysis').glob('*.py')},
    new_sampler_calls=0,new_independent_repetitions=0,formal_raw_archive_verified=False))
print('All 50,688 artificial task file lookups passed',flush=True)
