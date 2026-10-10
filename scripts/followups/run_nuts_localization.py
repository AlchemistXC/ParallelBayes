#!/usr/bin/env python3
"""Bounded native Windows CPU localization, separate from every formal grid.

Commands are deliberately staged. The frozen protocol is produced only after
native kernel tests and four same-version MCMC qualification calls pass.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import numpy as np
from nuts_events import atomic_json,sha
from nuts_instrumented_worker import require_windows,prepare_rng_states
from nuts_registry import Registry,fingerprint,schedule,MODELS,CONDITIONS
from nuts_runtime import host_lease,execute,recover,verify
from nuts_evidence import qualification_check,failure_stage,paired_prefixes
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples'),str(ROOT/'scripts/windows')]
from inference_parallel_nuts import restore_model
IDENTITY='windows-nuts-localization-v1'
PREPARED_INPUT_MANIFEST_SHA256='d92824d78f352295449d80556368fd9ee3bed1e9b7af2d0443c3ffb7bfbc7504'


def read(path):return json.loads(Path(path).read_text())

def verify_files(root,hashes):
    for name,digest in hashes.items():
        path=root/name
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink() or sha(path)!=digest:
            raise ValueError('Input/source checksum differs: '+name)


def source_paths():
    paths=set()
    for prefix in ('scripts/followups','scripts/completion','r-package/inst/python/parallelbayes'):
        paths.update(p for p in (ROOT/prefix).rglob('*.py'))
    paths.update(ROOT/p for p in ('examples/external_wells.py','examples/affine_target.py',
        'scripts/windows/job_objects.py','scripts/completion/posterior_diagnostics.R',
        'tests/windows/test_nuts_localization_job.py','tests/windows/test_job_objects.py'))
    return sorted(str(p.relative_to(ROOT)) for p in paths)


def binding(study):
    require_windows();files={name:sha(ROOT/name) for name in source_paths()}
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    import hashlib
    for name,digest in files.items():
        committed=subprocess.run(['git','show',f'{commit}:{name}'],cwd=ROOT,capture_output=True)
        if committed.returncode or hashlib.sha256(committed.stdout).hexdigest()!=digest:
            raise ValueError('Commit each changed numerical/qualification file before running: '+name)
    versions={key:importlib.metadata.version(key) for key in ('numpy','psutil','pyro-ppl','scipy','torch')}
    env=dict(os.environ);env['R_LIBS_USER']=study['r_library']
    probe=subprocess.run([study['rscript'],'--vanilla','-e',
        'cat(jsonlite::toJSON(list(R=R.version.string,posterior=as.character(packageVersion("posterior"))),auto_unbox=TRUE))'],
        env=env,text=True,capture_output=True,check=True)
    r=json.loads(probe.stdout)
    differences={k:dict(required=v,actual=versions.get(k)) for k,v in study['required_versions'].items() if versions.get(k)!=v}
    if r['R']!=study['required_R_version'] or r['posterior']!=study['required_R_posterior']:
        differences['R']=dict(required=[study['required_R_version'],study['required_R_posterior']],actual=r)
    if differences:raise ValueError('Frozen native environment differs; select the original environment, do not silently upgrade: '+json.dumps(differences))
    identity=dict(source_files=files,versions=versions,R=r,python=platform.python_version(),
        executable_sha256=sha(sys.executable),system=platform.system(),machine=platform.machine(),
        processor=platform.processor(),host=platform.node(),rscript_sha256=sha(study['rscript']))
    return dict(identity=identity,binding_sha256=fingerprint(identity),source_commit=commit)


def baseline_files(case):
    names=['scripts/completion/inference_nuts.py','scripts/completion/inference_parallel_nuts.py',
        'examples/affine_target.py','examples/external_wells.py']
    names.extend(str(p.relative_to(ROOT)) for p in (ROOT/'r-package/inst/python/parallelbayes').rglob('*.py'))
    old=case['source_capsule']['source_files']
    for name in names:
        if name not in old or sha(ROOT/name)!=old[name]:raise ValueError('Frozen baseline implementation changed: '+name)


def prepare(inputs,root,rscript,r_library):
    require_windows();inputs=inputs.resolve();root.mkdir(parents=True,exist_ok=False)
    if sha(inputs/'checksums.json')!=PREPARED_INPUT_MANIFEST_SHA256:raise ValueError('Use the independently prepared fixed input package')
    hashes=read(inputs/'checksums.json');verify_files(inputs,hashes)
    summary=read(inputs/'SUMMARY.json')
    if len(summary['case_ids'])!=9 or len(summary['diagnostic_ids'])!=3:raise ValueError('Unexpected prepared selection')
    first=read(inputs/'G1-case.json');capsule=first['source_capsule']
    study=dict(identity=IDENTITY,input_manifest_sha256=sha(inputs/'checksums.json'),
        selection_sha256=summary['selection_sha256'],original_source=summary['original_source_commit'],
        rscript=str(rscript.resolve()),r_library=str(r_library.resolve()),
        required_versions=capsule['required_versions'],required_R_version=capsule['required_R_version'],
        required_R_posterior=capsule['required_R_posterior'],maximum_registered_calls=48,
        maximum_qualification_rounds=3,working_limit_bytes=6*1024**3,per_host_incremental_limit_bytes=20*1024**3,
        schedule_seed=20261010,posterior_samples_eligible=False)
    current=binding(study);atomic_json(root/'STUDY.json',study)
    environment=root/'environment';environment.mkdir()
    for label,command in [('pip-freeze',[sys.executable,'-m','pip','freeze','--all']),('pip-check',[sys.executable,'-m','pip','check'])]:
        result=subprocess.run(command,text=True,capture_output=True)
        (environment/(label+'.txt')).write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError(label+' failed; preparation evidence retained')
    import psutil
    atomic_json(environment/'host.json',dict(python=sys.version,executable=sys.executable,
        platform=platform.platform(),processor=platform.processor(),logical_cpus=psutil.cpu_count(),
        physical_cpus=psutil.cpu_count(logical=False),total_ram_bytes=psutil.virtual_memory().total,
        scientific_device='CPU only; CUDA is not exercised by this study'))
    shutil.copytree(inputs,root/'inputs')
    (root/'rng').mkdir();(root/'prepared-cases').mkdir();(root/'bindings').mkdir();(root/'calls').mkdir()
    for model in MODELS:
        case=read(root/'inputs'/f'{model}-case.json');baseline_files(case)
        native=restore_model(case['target_spec'])
        if native.target_id!=case['target_id']:raise ValueError('Restored native target differs: '+model)
        case['names']=native.names;atomic_json(root/'prepared-cases'/f'{model}.json',case)
        prepare_rng_states(case['chain_seeds'],root/'rng'/f'{model}.json')
    native=restore_model(dict(kind='gaussian',dimension=2,mean=[0.,0.],covariance=[[1.,0.],[0.,1.]],coordinate_id='identity'))
    fixture=dict(target_spec=native.spec,target_id=native.target_id,names=native.names,
        initial=[[-2.,-1.],[-1.,2.],[1.,-2.],[2.,1.]],chain_seeds=[161803,271828,314159,141421],
        fixture='independent standard Gaussian qualification, not formal G1')
    atomic_json(root/'prepared-cases'/'Q2.json',fixture);prepare_rng_states(fixture['chain_seeds'],root/'rng'/'Q2.json')
    atomic_json(root/'bindings'/f"{current['binding_sha256']}.json",current)
    atomic_json(root/'schedule.json',schedule(study['schedule_seed']))
    prepared={str(p.relative_to(root)):sha(p) for prefix in ('inputs','rng','prepared-cases','environment') for p in (root/prefix).rglob('*') if p.is_file()}
    prepared['schedule.json']=sha(root/'schedule.json');atomic_json(root/'prepared-checksums.json',prepared)
    r=Registry(root/'calls.sqlite',study);r.close()
    print(json.dumps(dict(status='prepared',new_sampler_calls=0,cases=9,rng_streams=40)),flush=True)


def load(root):
    study=read(root/'STUDY.json')
    if not (root/'calls.sqlite').exists():raise ValueError('Existing study call registry is missing; never reset quota')
    if sha(root/'inputs'/'checksums.json')!=PREPARED_INPUT_MANIFEST_SHA256 or study['input_manifest_sha256']!=PREPARED_INPUT_MANIFEST_SHA256:
        raise ValueError('Original fixed input manifest differs')
    verify_files(root/'inputs',read(root/'inputs'/'checksums.json'))
    verify_files(root,read(root/'prepared-checksums.json'))
    current=binding(study);path=root/'bindings'/f"{current['binding_sha256']}.json"
    if not path.exists():atomic_json(path,current)
    registry=Registry(root/'calls.sqlite',study)
    registered={r['id'] for r in registry.records()}
    directories={p.name for p in (root/'calls').iterdir() if p.is_dir()}
    if directories-registered:raise ValueError('Call directories absent from registry; do not reset accounting')
    return study,current,registry


def base_request(study,current):return dict(binding_sha256=current['binding_sha256'],
    source_commit=current['source_commit'],rscript=study['rscript'],r_library=study['r_library'],posterior_samples_eligible=False)


def sampling_request(root,study,current,item):
    model=item['model'];case=read(root/'prepared-cases'/f'{model}.json')
    if model=='Q2':config=dict(draws=64,warmup=64,max_tree_depth=8,target_accept_prob=.8,full_mass=False,memory_limit_mb=2048)
    else:
        c=case['source_capsule']['controls'];task=case['original_task']
        config=dict(draws=task['budget'],warmup=c['nuts_warmup'],max_tree_depth=c['nuts_tree_depth'],
            target_accept_prob=c['nuts_target_accept'],full_mass=c['nuts_full_mass'],memory_limit_mb=c['memory_limit_mb'])
        if config!=dict(draws=4096,warmup=1024,max_tree_depth=8,target_accept_prob=.8,full_mass=False,memory_limit_mb=2048):
            raise ValueError('Planned original configuration differs')
    rng=root/'rng'/f'{model}.json'
    return dict(**base_request(study,current),**item,case=case,config=config,rng_file=str(rng),rng_sha256=sha(rng))


def restore_all(root,registry):
    for record in registry.records():recover(root/'calls'/record['id'],record,registry)


def native_check(root,study,current):
    directory=root/'native-checks'/current['binding_sha256']
    if directory.exists():
        result=read(directory/'result.json') if (directory/'result.json').exists() else dict(passed=False)
        if result.get('passed'):
            verify_files(directory,read(directory/'checksums.json'));return result
        raise RuntimeError('This source binding has a failed/interrupted native gate; preserve it and commit a compatibility repair')
    directory.mkdir(parents=True)
    command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',
        'tests/windows/test_job_objects.py','tests/windows/test_nuts_localization_job.py',f'--junitxml={directory/"tests.xml"}']
    environment=dict(os.environ);environment.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    with (directory/'stdout.log').open('xb') as out,(directory/'stderr.log').open('xb') as err:
        proc=subprocess.run(command,cwd=ROOT,env=environment,stdout=out,stderr=err,check=False)
    tests=ET.parse(directory/'tests.xml').findall('.//testcase') if (directory/'tests.xml').exists() else []
    failed=sum(t.find('failure') is not None or t.find('error') is not None for t in tests)
    skipped=sum(t.find('skipped') is not None for t in tests)
    result=dict(passed=proc.returncode==0 and len(tests)==3 and failed==skipped==0,
        tests=len(tests),failed=failed,skipped=skipped,exit_code=proc.returncode,command=command,new_sampler_calls=0,
        binding_sha256=current['binding_sha256'])
    atomic_json(directory/'result.json',result)
    atomic_json(directory/'checksums.json',{p.name:sha(p) for p in directory.iterdir() if p.is_file()})
    if not result['passed']:raise RuntimeError('Native owned-process gate failed; no sampler qualification started')
    return result


def diagnostics(root,study,current,registry):
    native_check(root,study,current)
    for model in ('G1','G2','W1'):
        for kind,workers in (('legacy',1),('legacy',4),('modern',1)):
            case=read(root/'inputs'/f'{model}-diagnostic.json')
            names=restore_model(case['target_spec']).names
            request=dict(**base_request(study,current),id=f'diagnostic-{model}-{kind}-w{workers}',phase='diagnostic',
                model=model,diagnostic_kind=kind,workers=workers,names=names,
                diagnostic_input=str(root/'inputs'/f'{model}-diagnostic.npz'),
                diagnostic_input_sha256=case['diagnostic_arrays_sha256'])
            old=next((r for r in registry.records() if r['id']==request['id']),None)
            if old:verify(root/'calls'/old['id'],old['outcome']);continue
            execute(root/'calls'/request['id'],root,request,registry)


def qualify(root,study,current,registry):
    native_check(root,study,current)
    if len([r for r in registry.records() if r['phase']=='diagnostic' and r['outcome']])!=9:
        raise RuntimeError('Complete or record terminal failures for nine saved-trajectory diagnostics first')
    previous=[r for r in registry.records() if r['phase']=='qualification']
    rounds=sorted({r['request']['round'] for r in previous})
    if rounds:
        rows=[r for r in previous if r['request']['round']==rounds[-1]]
        assessment=qualification_check(root,rows)
        same=all(r['request']['binding_sha256']==current['binding_sha256'] for r in rows)
        if assessment['passed'] and same:
            print('Existing qualification passed; zero new calls',flush=True);return
        # An interrupted round can finish its as-yet unregistered conditions if
        # the binding is identical. Recorded failures are never retried.
        number=rounds[-1] if len(rows)<4 and same else rounds[-1]+1
    else:number=0
    if number>=3:raise RuntimeError('All three qualification rounds consumed; deliver incomplete evidence')
    for workers,enabled in CONDITIONS:
        item=dict(id=f'qualification-r{number}-w{workers}-d{int(enabled)}',phase='qualification',round=number,
            model='Q2',workers=workers,diagnostics_enabled=enabled)
        request=sampling_request(root,study,current,item)
        old=next((r for r in registry.records() if r['id']==item['id']),None)
        if old:verify(root/'calls'/old['id'],old['outcome']);continue
        execute(root/'calls'/item['id'],root,request,registry)
    rows=[r for r in registry.records() if r['phase']=='qualification' and r['request']['round']==number]
    assessment=qualification_check(root,rows);directory=root/'qualifications';directory.mkdir(exist_ok=True)
    path=directory/f'round-{number}.json'
    if path.exists():raise FileExistsError('Qualification assessment is immutable')
    atomic_json(path,assessment)
    if not assessment['passed']:raise RuntimeError('Qualification failed; preserve all calls and repair before the next round')


def freeze(root,study,current,registry):
    destination=root/'protocol.json'
    if destination.exists():
        protocol=read(destination)
        if protocol['binding_sha256']!=current['binding_sha256']:raise ValueError('Frozen source/environment differs')
        print('Existing protocol unchanged; zero new calls',flush=True);return
    rounds=[r['request']['round'] for r in registry.records() if r['phase']=='qualification']
    if not rounds:raise RuntimeError('No native MCMC qualification')
    rows=[r for r in registry.records() if r['phase']=='qualification' and r['request']['round']==max(rounds)]
    assessment=qualification_check(root,rows)
    if not assessment['passed'] or any(r['request']['binding_sha256']!=current['binding_sha256'] for r in rows):
        raise RuntimeError('Four conditions under the current source/environment must pass')
    protocol=dict(identity=IDENTITY,binding_sha256=current['binding_sha256'],source_commit=current['source_commit'],
        study_sha256=sha(root/'STUDY.json'),prepared_sha256=sha(root/'prepared-checksums.json'),
        qualification_ids=[r['id'] for r in rows],qualification_registered=len(rounds),
        maximum_registered_calls=48,main_calls=36,maximum_confirmation_calls=min(8,48-len(rounds)-36),
        schedule=read(root/'schedule.json'),confirmation_model_order=list(MODELS),
        confirmation_pair_order=[[[4,True],[4,False]],[[1,True],[1,False]],[[1,True],[4,True]],[[1,False],[4,False]]],
        scope='Technical localization only, preserves all original failures; instrumentation costs are not original benchmark timing',
        require_same_initial_actual_rng_states=True,posterior_samples_eligible=False)
    atomic_json(destination,protocol);atomic_json(root/'protocol.sha256.json',dict(sha256=sha(destination)))


def formal(root,study,current,registry):
    protocol=read(root/'protocol.json')
    if sha(root/'protocol.json')!=read(root/'protocol.sha256.json')['sha256']:raise ValueError('Frozen protocol changed')
    if current['binding_sha256']!=protocol['binding_sha256']:raise ValueError('Source/environment changed after qualification')
    if sha(root/'STUDY.json')!=protocol['study_sha256'] or sha(root/'prepared-checksums.json')!=protocol['prepared_sha256']:
        raise ValueError('Frozen inputs differ')
    qualified=[r for r in registry.records() if r['id'] in protocol['qualification_ids']]
    if not qualification_check(root,qualified)['passed'] or any(r['request']['binding_sha256']!=current['binding_sha256'] for r in qualified):
        raise ValueError('Frozen native qualification evidence is missing or differs')
    if protocol['schedule']!=schedule(study['schedule_seed']):raise ValueError('Frozen schedule differs from finite plan')
    for item in protocol['schedule']:
        old=next((r for r in registry.records() if r['id']==item['id']),None)
        if old:verify(root/'calls'/old['id'],old['outcome']);continue
        request=sampling_request(root,study,current,item);execute(root/'calls'/item['id'],root,request,registry)
    selection=root/'confirmation-selection.json'
    if not selection.exists():
        chosen=[];records={r['id']:r for r in registry.records()}
        def signature(r):
            if r['outcome']['status']=='completed':return ['completed']
            return [r['outcome']['status']]+[x['observed_stage'] for x in failure_stage(root/'calls'/r['id'])]
        for model in MODELS:
            if len(chosen)>=protocol['maximum_confirmation_calls']:break
            for a,b in protocol['confirmation_pair_order']:
                ids=[f'main-{model}-w{w}-d{int(d)}' for w,d in (a,b)]
                if signature(records[ids[0]])!=signature(records[ids[1]]):
                    for old_id,(workers,enabled) in zip(ids,(a,b)):
                        chosen.append(dict(id=f'confirmation-{model}-w{workers}-d{int(enabled)}',phase='confirmation',
                            model=model,workers=workers,diagnostics_enabled=enabled,confirms=old_id))
                    break
        atomic_json(selection,chosen)
    for item in read(selection):
        old=next((r for r in registry.records() if r['id']==item['id']),None)
        if old:verify(root/'calls'/old['id'],old['outcome']);continue
        request=sampling_request(root,study,current,item);execute(root/'calls'/item['id'],root,request,registry)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['prepare','check','diagnostics','qualify','freeze','run','verify'])
    p.add_argument('--output',required=True,type=Path);p.add_argument('--host-lock',required=True,type=Path)
    p.add_argument('--inputs',type=Path);p.add_argument('--rscript',type=Path);p.add_argument('--r-library',type=Path)
    a=p.parse_args();require_windows();root=a.output.resolve()
    with host_lease(a.host_lock.resolve(),IDENTITY+' '+a.command):
        if a.command=='prepare':
            if any(v is None for v in (a.inputs,a.rscript,a.r_library)):p.error('prepare needs --inputs --rscript --r-library')
            prepare(a.inputs,root,a.rscript,a.r_library);return
        study,current,registry=load(root)
        try:
            restore_all(root,registry)
            if a.command=='check':native_check(root,study,current)
            elif a.command=='diagnostics':diagnostics(root,study,current,registry)
            elif a.command=='qualify':qualify(root,study,current,registry)
            elif a.command=='freeze':freeze(root,study,current,registry)
            elif a.command=='run':formal(root,study,current,registry)
            else:
                records=registry.records();print(json.dumps(dict(registered_calls=sum(r['phase']!='diagnostic' for r in records),
                    diagnostics=sum(r['phase']=='diagnostic' for r in records),new_executions=0,
                    managed_active_processes=0,verified_assets=sum(verify(root/'calls'/r['id'],r['outcome']) for r in records))))
        finally:registry.close()

if __name__=='__main__':main()
