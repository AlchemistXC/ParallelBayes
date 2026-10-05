"""Finite Mac technical cache execution, costs and portable statistical intake.

Two targets, two new technical inputs each, four CPU MH workflows, short paths.
No primary posterior fit is required or executed. No formal research is launched.
The direct small validation uses a cooperative lease and sampler workspace guard;
it does not certify OS-cohort recovery or enforce the capsule's supervisor limit.
"""
import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from batch_contract import BatchPlan,create_tasks,mh_config
from batch_cost_ledger import BatchCostLedger,read_batch_costs
from cache_probe_execution import execute_cached_probe,read_cached_probe
from cache_probe_analysis import create_cache_plan,analyze_cache_probes
from formal_inputs import build_payload
from formal_measurement_plan import create_measurement_plan,validate_measurement_plan
from formal_runtime import atomic_json,file_hash,fingerprint,host_lease
from formal_uncertainty import save_plan,load_plan


def stats(allocation,tasks,model,reports,output=None,stored=None):
    selected={pid:r for pid,r in reports.items() if r['probe']['model']==model}
    plan=create_cache_plan(allocation,tasks,model) if stored is None else load_plan(stored/'resampling')
    report=analyze_cache_probes(allocation,tasks,plan,{p:r['binding'] for p,r in selected.items()},
                              {p:r['observation'] for p,r in selected.items()})
    arrays=report.pop('bootstrap_statistics')
    if output is not None:
        output.mkdir();save_plan(plan,output/'resampling');atomic_json(output/'analysis.json',report)
        np.savez_compressed(output/'bootstrap-statistics.npz',**arrays)
    if stored is not None:
        if report!=json.loads((stored/'analysis.json').read_text()):raise ValueError('Saved cache statistics differ')
        with np.load(stored/'bootstrap-statistics.npz',allow_pickle=False) as z:
            if set(z.files)!=set(arrays) or any(not np.array_equal(z[k],arrays[k],equal_nan=True) for k in arrays):
                raise ValueError('Saved cache bootstrap differs')
    return report


def run(output,host_lock):
    from mechanism_runner import actual_hash
    if sys.platform!='darwin':raise ValueError('Native Mac technical validation only')
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    p=json.loads((ROOT/'benchmark/protocols/batch-schema-maximum-mac-v1.json').read_text());p.pop('protocol_sha256')
    p.update(identity='cache-probe-capsule-mac-v1',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    p['targets']=[t for t in p['targets'] if t['name'] in ('G1','L1')]
    workflows=['cpu-rwm-sequential','cpu-rwm-online_picard','cpu-mala-sequential','cpu-mala-quasi_deer']
    p['groups']=[dict(models=['G1','L1'],replicates=[0,1],budgets=[8],workflows=workflows)]
    p['tasks']=create_tasks(p['identity'],p['groups']);p['inputs']={}
    p['controls'].update(mh_discard=8,window=4,memory_limit_mb=128)
    for name in ('cache_probe_execution','cache_probe_analysis','formal_measurement_plan','batch_cost_ledger','validate_cache_execution'):
        key='scripts/completion/'+name+'.py';p['source_files'][key]=file_hash(ROOT/key)
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h or hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit matching source before technical execution: '+name)
    p['required_versions']={n:importlib.metadata.version(n) for n in p['required_versions']}
    # Replace inherited descriptive fields: their old maximum-task meanings do
    # not describe this new, deliberately small measurement-only experiment.
    p.pop('addresses',None)
    p.update(maximum_declared_dimension=max(t['dimension'] for t in p['targets']),maximum_retained_budget=8,
        scientific_scope='16 cache probes, 64 actual executor calls on four new technical inputs; no primary fits and no formal inference repetitions',
        resource_policy='128MiB estimated sampler workspace guard and cooperative host lease. This small direct validation does not enforce the inherited OS-supervisor RSS threshold or prove process-cohort recovery.',
        recovery_policy='No reexecution into existing output; unexpected interruption is retained and re-raised; no retry is launched',
        cost_policy=dict(primary='No primary posterior workflow in this validation',cached='Each probe has one initial plus three prepared executor calls; independently audited and never samples-eligible',batch='Input preparation, local archive and verification recorded separately; no per-fit allocation'))
    allocation=create_measurement_plan(p['identity'],p['tasks'])
    p['cache_allocation_sha256']=allocation['allocation_sha256']
    design=copy.deepcopy(p);design_sha=fingerprint(design);p['measurement_design_sha256']=design_sha
    atomic_json(output/'design.json',design)
    ledger=BatchCostLedger(output/'batch-costs',dict(study_identity=p['identity'],design_sha256=design_sha,
        operations=[dict(id='inputs',stage='input_preparation'),dict(id='archive',stage='archive'),dict(id='verify',stage='verification')]),host_lock)
    inputs=output/'inputs';inputs.mkdir()
    def prepare():
        rows={}
        for target in p['targets']:
            for rep in (0,1):
                name=f"{target['name']}-rep{rep:04d}.npz"
                data=build_payload(p['identity'],target['name'],rep,target['dimension'],16,4)
                np.savez_compressed(inputs/name,**data)
                rows[name]=dict(model=target['name'],replicate=rep,dimension=target['dimension'],chains=4,steps=16,
                    sha256=file_hash(inputs/name),actual_sha256=actual_hash(data))
        return rows
    p['inputs']=ledger.run('inputs',prepare)['result'];p['protocol_sha256']=fingerprint(p)
    plan=BatchPlan(p);atomic_json(output/'protocol.json',p);atomic_json(output/'allocation.json',allocation)
    reports={};started=time.perf_counter()
    # No nested lease: input/archive ledger operations occur outside this block.
    with host_lease(host_lock,p['identity']+' finite technical execution'):
        for i,probe in enumerate(allocation['probes']):
            capsule,digest=plan.capsule(probe['primary_task_id'])
            print(json.dumps(dict(index=i+1,total=len(allocation['probes']),probe=probe['id'],workflow=probe['workflow'])),flush=True)
            reports[probe['id']]=execute_cached_probe(capsule,digest,probe,inputs,output/'probes'/probe['id'])
    loop_wall=time.perf_counter()-started
    analysis=output/'analysis';analysis.mkdir()
    comparisons={m:stats(allocation,p['tasks'],m,reports,output=analysis/m) for m in ('G1','L1')}
    records=[r for report in reports.values() for r in report['observation']['records'] if r is not None]
    summary=dict(identity=p['identity'],protocol_sha256=plan.protocol_sha256,source_commit=p['source_commit'],
        measurement_design_sha256=design_sha,cache_probes=len(reports),available_probes=sum(r['measurement_available'] for r in reports.values()),
        actual_executor_records=len(records),new_technical_input_sets=len(p['inputs']),formal_inference_repetitions=0,
        samples_eligible_probes=sum(r['samples_eligible'] for r in reports.values()),
        independent_audits_passed=sum(bool(r['audit'] and r['audit']['passed']) for r in records),
        acceptance_mismatches=sum(sum(r['audit']['acceptance_mismatches']) for r in records if r['audit'] and 'acceptance_mismatches' in r['audit']),
        max_abs_path_error=max((max(r['audit']['max_abs_path_error']) for r in records if r['audit'] and r['audit'].get('max_abs_path_error')),default=None),
        cache_pairs=sum(len(a['pairs']) for a in comparisons.values()),ratio_intervals_available=sum(pair['ratio_confidence_interval'] is not None for a in comparisons.values() for pair in a['pairs']),
        known_executor_seconds=sum(r['executor_wall_seconds'] for r in records),driver_loop_wall_seconds=loop_wall,
        loop_scope='Lease acquisition, target/source/input setup, prepared executions, transfer, independent audits, archives and journals inside loop; excludes initial protocol/input preparation, subsequent statistical analysis, batch archive and final report',
        primitive_times_not_additive_to_loop_wall=True,process_supervision_validated=False,native_Windows_validated=False,
        scope='Short actual CPU execution/intake validation on new technical inputs, not formal speed, convergence or uncertainty evidence')
    atomic_json(output/'run-summary.json',summary)
    roots=['design.json','protocol.json','allocation.json','inputs','probes','analysis','run-summary.json']
    files=[]
    for name in roots:
        item=output/name
        files.extend([item] if item.is_file() else [f for f in item.rglob('*') if f.is_file()])
    manifest={f.relative_to(output).as_posix():file_hash(f) for f in sorted(files)}
    atomic_json(output/'payload-manifest.json',manifest)
    archive=output/'probe-evidence.tar'
    def pack():
        with tarfile.open(archive,'w') as tar:
            for f in sorted(files)+[output/'payload-manifest.json']:
                tar.add(f,arcname=f.relative_to(output).as_posix(),recursive=False)
        return dict(sha256=file_hash(archive),bytes=archive.stat().st_size,members=len(files)+1)
    packed=ledger.run('archive',pack)
    def verify():
        if file_hash(archive)!=packed['result']['sha256']:raise ValueError('Archive checksum differs')
        with tarfile.open(archive) as tar:
            names=tar.getnames()
            if len(names)!=len(set(names)) or set(names)!=set(manifest)|{'payload-manifest.json'}:raise ValueError('Archive inventory differs')
            for name,h in manifest.items():
                if hashlib.sha256(tar.extractfile(name).read()).hexdigest()!=h:raise ValueError('Archive member differs')
        return dict(verified_members=len(names),sha256=file_hash(archive))
    ledger.run('verify',verify);atomic_json(output/'batch-cost-summary.json',read_batch_costs(output/'batch-costs'))
    atomic_json(output/'MANIFEST.json',{f.relative_to(output).as_posix():file_hash(f) for f in sorted(output.rglob('*')) if f.is_file()})
    return summary


def audit(bundle):
    from batch_worker import payload
    from inference_targets import build_target
    from parallelbayes.torch_backend.sampling import settings,tape_hash
    bundle=Path(bundle);manifest=json.loads((bundle/'MANIFEST.json').read_text())
    actual={f.relative_to(bundle).as_posix() for f in bundle.rglob('*') if f.is_file()}
    if actual!=set(manifest)|{'MANIFEST.json'}:raise ValueError('Bundle inventory differs')
    for name,h in manifest.items():
        f=bundle/name
        if f.is_symlink() or not f.resolve().is_relative_to(bundle.resolve()) or file_hash(f)!=h:raise ValueError('Bundle checksum/path differs')
    p=json.loads((bundle/'protocol.json').read_text());plan=BatchPlan(p)
    allocation=json.loads((bundle/'allocation.json').read_text());validate_measurement_plan(allocation,p['tasks'])
    if allocation['allocation_sha256']!=p['cache_allocation_sha256']:raise ValueError('Allocation binding differs')
    reports={}
    for probe in allocation['probes']:
        directory=bundle/'probes'/probe['id'];capsule,digest=plan.capsule(probe['primary_task_id'])
        expected=dict(capsule=capsule,capsule_sha256=digest,probe=probe)
        if json.loads((directory/'request.json').read_text())!=expected:raise ValueError('Probe capsule differs')
        report=read_cached_probe(directory);values=payload(dict(inputs=str(bundle/'inputs')),capsule)
        config=settings(mh_config(capsule,values['initial'].tolist()))
        tape={k:values[k][:,:config['draws']] for k in ('noise','log_uniform','directions')}
        model=build_target(capsule['target'],None,'cpu')
        binding=dict(input_file_sha256=capsule['input']['sha256'],tape_sha256=tape_hash(tape),target_id=model.target_id,config=config)
        if binding!=report['binding']:raise ValueError('Actual input/target/config binding differs')
        reports[probe['id']]=report
    for model in ('G1','L1'):stats(allocation,p['tasks'],model,reports,stored=bundle/'analysis'/model)
    costs=read_batch_costs(bundle/'batch-costs')
    if costs!=json.loads((bundle/'batch-cost-summary.json').read_text()):raise ValueError('Batch costs differ')
    return dict(verified_manifest_files=len(manifest),probe_artifacts=len(reports),actual_inputs_verified=len(p['inputs']),
        actual_executor_records=sum(r['summary']['observed_executions'] for r in reports.values()),
        samples_eligible_probes=sum(r['samples_eligible'] for r in reports.values()),
        target_statistics_rebuilt=2,batch_costs_exact=True,new_executor_calls=0,new_independent_audits=0,
        formal_inference_complete=False,native_Windows_validated=False,
        scope='Moved read-only asset/input/binding/statistics reconstruction; prior independent path audits checked as sealed evidence, not re-executed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    r=sub.add_parser('run');r.add_argument('--output',type=Path,required=True);r.add_argument('--host-lock',type=Path,required=True)
    a=sub.add_parser('audit');a.add_argument('--bundle',type=Path,required=True)
    args=vars(parser.parse_args());action=args.pop('action');print(json.dumps((run if action=='run' else audit)(**args),indent=2),flush=True)
