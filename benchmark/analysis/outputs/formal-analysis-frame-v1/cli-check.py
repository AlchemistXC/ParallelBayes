"""CLI integration fixture with real input/source files but NO native results.

Every task must remain an evidence gap. This is not Windows acceptance and
must not be used to authorize sampling or estimate posterior accuracy.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

p=argparse.ArgumentParser()
for key in ('project','wells-source','output','rscript','r-library'):p.add_argument('--'+key,type=Path,required=True)
a=p.parse_args();root=a.project.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
sys.path[:0]=[str(root/'scripts/analysis'),str(root/'scripts/completion'),str(root/'scripts/windows')]
from formal_analyze import analysis_environment
from formal_validation import validation_design,seal_validation,TEST_FILES
from formal_freeze import InputArchive
from formal_execution import VALIDATION_ID
from formal_runtime import atomic_json,file_hash
from prepare_formal_study import sources,LIMITS

catalog=json.loads((root/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text());design=validation_design(catalog)
source_files=sources();extra=json.loads((root/'models/external/wells/source-manifest.json').read_text())
external={r['path']:r['sha256'] for r in extra['files']}
lock='\n'.join(sorted(d.metadata['Name']+'=='+d.version for d in importlib.metadata.distributions()))+'\n'
import hashlib
env=analysis_environment(a.rscript,a.r_library)
env.update(fixture_only=True,platform=sys.platform,pip_freeze_sha256=hashlib.sha256(lock.encode()).hexdigest(),
    lock_collection='importlib.metadata in receiver test fixture; not native pip freeze')
binding=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
    source_branch='fixture-no-native-execution',source_files=source_files,
    validation_test_sources={n:file_hash(root/n) for n in TEST_FILES},external_files=external,environment=env,
    required_versions=env['packages'],required_R_version=env['R']['R'],required_R_posterior=env['R']['posterior'],
    windows_limits=LIMITS,minimum_available_ram_bytes=12*1024**3,shared_host_lock='D:\\fixture-only-no-execution\\lock')
delivery=out/'delivery';bundle=delivery/'bundle'
archive=InputArchive(bundle,VALIDATION_ID,design['input_requirements'],binding)
for name,value in {'catalog.json':catalog,'validation-design.json':design,'environment.json':env,
    'address-check.json':dict(fixture_only=True,no_native_or_sampler_execution=True)}.items():atomic_json(bundle/name,value)
(bundle/'pip-freeze.txt').write_text(lock);(bundle/'pip-check.txt').write_text('Fixture setup; not a Windows pip check\n')
for prefix,origin,inventory in [('source',root,dict(source_files,**binding['validation_test_sources'])),('external',a.wells_source,external)]:
    for name,digest in inventory.items():
        assert file_hash(origin/name)==digest
        dest=bundle/prefix/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(origin/name,dest)
for name in design['input_requirements']:archive.prepare(name)
seal_validation(bundle,archive,catalog,binding)
files={p.relative_to(delivery).as_posix():dict(bytes=p.stat().st_size,sha256=file_hash(p)) for p in delivery.rglob('*') if p.is_file()}
manifest=delivery/'WINDOWS-RETURN-MANIFEST.json';atomic_json(manifest,dict(scope=__doc__,files=files))

def call(label,script,args):
    command=[sys.executable,str(root/script),*map(str,args)]
    result=subprocess.run(command,cwd=root,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
    (out/(label+'.stdout')).write_text(result.stdout);(out/(label+'.stderr')).write_text(result.stderr)
    atomic_json(out/(label+'.command.json'),dict(command=command,returncode=result.returncode))
    if result.returncode:raise RuntimeError('CLI check failed; retained '+label)
    return json.loads(result.stdout)

index=out/'index';analysis=out/'analysis';statistics=out/'statistics'
indexed=call('index','scripts/analysis/formal_analyze.py',
    ['index','--delivery',delivery,'--bundle-relative','bundle','--manifest-sha256',file_hash(manifest),'--output',index])
args=['run','--delivery',delivery,'--index',index,'--output',analysis,'--rscript',a.rscript,'--r-library',a.r_library,'--cross-platform']
first=call('run','scripts/analysis/formal_analyze.py',args)
assert first['counts']==dict(main=dict(evidence_gap=27),cache=dict(evidence_gap=24))
assert first['visited']==first['new_analyses']==51 and not first['evidence_complete']
resume=call('resume','scripts/analysis/formal_analyze.py',args+['--resume'])
assert resume['new_analyses']==0 and resume['reused_analyses']==51
stats=call('statistics','scripts/analysis/formal_statistics.py',
    ['--delivery',delivery,'--index',index,'--analysis',analysis,'--output',statistics])
assert len(stats['models'])==3 and all(m['main_statistics']==m['cache_statistics']=='technical_descriptive_only' for m in stats['models'])
assert all(file_hash(delivery/n)==r['sha256'] for n,r in files.items())
atomic_json(out/'CLI-RECEIPT.json',dict(scope=__doc__,source_commit=binding['source_commit'],
    files=indexed['delivered_files'],input_files=3,planned_tasks=51,evidence_gaps=51,
    first_analysis=first,resume=resume,summary_model_count=3,source_and_input_files_unchanged=True,
    new_sampler_calls=0,new_formal_repetitions=0,native_windows_executed=False,
    artificial_OS_metadata=True,real_numpy_inputs_and_source_snapshots=True))
print('CLI index -> 51 explicit evidence gaps -> zero-replay resume -> technical-only summaries passed')
