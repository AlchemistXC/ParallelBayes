"""Freeze/run a finite full-schema Mac batch, including the largest shape.

Formal launch stays closed. The same declared-grid/capsule interfaces can be
used after native Windows and scientific gates are satisfied in a new identity.
"""
import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from batch_contract import BatchPlan,create_tasks
from formal_runtime import atomic_json,file_hash,fingerprint,disk_preflight


def freeze(protocol,inputs,rscript,r_library):
    import numpy as np
    from formal_inputs import build_payload,validate_addresses
    from mechanism_runner import actual_hash
    if protocol.exists() or inputs.exists():raise FileExistsError('New protocol/input directory required')
    if sys.platform!='darwin':raise ValueError('This technical freeze is native Mac only')
    scientific=json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    old=json.loads((ROOT/'benchmark/protocols/formal-runtime-technical-mac-v1.json').read_text())
    sources=dict(old['source_files'])
    for name in ('batch_contract','batch_worker','batch_runner','measured_workflow','measured_coordinator',
                 'formal_coordinator','formal_recovery','formal_outcomes','formal_streaming','formal_evidence',
                 'formal_runtime_analysis','formal_uncertainty','formal_error_summary','analyze_budget_pilot'):
        path='scripts/completion/'+name+'.py';sources[path]=file_hash(ROOT/path)
    for name,h in sources.items():
        if file_hash(ROOT/name)!=h or hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit and preserve all source before freezing: '+name)
    env=dict(os.environ);env['R_LIBS_USER']=str(r_library.resolve())
    code='cat(jsonlite::toJSON(list(R=R.version.string,posterior=as.character(packageVersion("posterior"))),auto_unbox=TRUE))'
    renv=json.loads(subprocess.check_output([str(rscript),'--vanilla','-e',code],text=True,env=env))
    workflows=['cpu-rwm-sequential','cpu-mala-sequential','cpu-rwm-online_picard','cpu-mala-quasi_deer','cpu-nuts-spawn_chains']
    groups=[dict(models=['G1','L1'],replicates=[0],budgets=[64],workflows=workflows),
            dict(models=['G2'],replicates=[0],budgets=[16384],workflows=workflows)]
    identity='batch-schema-maximum-mac-v1';tasks=create_tasks(identity,groups)
    targets=[copy.deepcopy(t) for t in scientific['targets'] if t['name'] in ('G1','L1','G2')]
    p=dict(schema=1,identity=identity,scope_kind='technical_batch_validation',required_platform='darwin',
        batch_size=32,groups=groups,tasks=tasks,targets=targets,inputs={},source_files=sources,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        required_versions={n:importlib.metadata.version(n) for n in ('numpy','scipy','torch','pyro-ppl','psutil')},
        required_R_version=renv['R'],required_R_posterior=renv['posterior'],
        controls=dict(chains=4,mh_discard=512,nuts_warmup=1024,nuts_tree_depth=8,nuts_target_accept=.8,
            nuts_full_mass=False,nuts_workers=4,nuts_threads=1,torch_threads=4,window=32,quasi_deer_max_iter=2048,
            atol=1e-10,rtol=1e-10,memory_limit_mb=2048,maximum_member_bytes=128*1024**2),
        process_tree_rss_limit_bytes=6*1024**3,required_disk_bytes_per_task=1024**3,
        cost_policy=dict(primary='Separate ordinary subprocess and post-exit audit; outer invocation ledger retains all calls',
            cached='No warmed probes hidden inside a primary fit. Existing cached-cost-v1 remains separate technical evidence; formal probe assignment is not frozen.',
            verification='Additional resume costs separate from original execution/recovery calls',
            report_walls_not_sums_of_nested_phases=True),
        scientific_scope='15 technical fits: G1/L1 small retained budgets plus all five CPU workflows at widest G2 dimension and largest retained budget; not every computational worst case or Windows validation',
        maximum_declared_dimension=64,maximum_retained_budget=16384,no_total_time_cutoff=True,
        resource_policy='Numerical iteration guards, 2GiB sampler workspace estimate, sampled 6GiB process tree guard, 1GiB free disk at each task; not strict allocator guarantees',
        recovery_policy='No automatic numerical retry; explicit infrastructure recovery at most once via the existing coordinator',
        formal_inference_complete=False,formal_scientific_repetitions=0,native_Windows_validated=False)
    p['addresses']=validate_addresses(identity,[t['name'] for t in targets],[0],4)
    inputs.mkdir(parents=True)
    for item in targets:
        n=max(t['budget'] for t in tasks if t['model']==item['name'])+p['controls']['mh_discard']
        # Read/check/write one input group at a time. This is not a global raw cache.
        disk_preflight(inputs,4*n*(2*item['dimension']+1)*8+1024**3)
        data=build_payload(identity,item['name'],0,item['dimension'],n,4);name=f"{item['name']}-rep0000.npz"
        np.savez_compressed(inputs/name,**data)
        p['inputs'][name]=dict(model=item['name'],replicate=0,dimension=item['dimension'],chains=4,steps=n,
            sha256=file_hash(inputs/name),actual_sha256=actual_hash(data));del data
    p['protocol_sha256']=fingerprint(p);BatchPlan(p);atomic_json(protocol,p)
    return dict(protocol_sha256=p['protocol_sha256'],tasks=len(tasks),inputs=len(p['inputs']),source_commit=p['source_commit'],formal_inference_complete=False)


def run(protocol,inputs,output,rscript,r_library,host_lock,batch=0,resume=False):
    from measured_coordinator import MeasuredCoordinator
    p=json.loads(protocol.read_text());plan=BatchPlan(p)
    if p['required_platform']!=sys.platform or p['scope_kind']!='technical_batch_validation':
        raise ValueError('Formal/native-Windows launch gates remain open')
    if sys.platform!='darwin':raise ValueError('Native Mac technical coordinator only')
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Frozen source changed: '+name)
    for name,row in p['inputs'].items():
        if file_hash(inputs/name)!=row['sha256']:raise ValueError('Input file changed: '+name)
    selected=list(plan.tasks(batch))
    if not selected:raise ValueError('Declared batch contains no tasks')
    output=output.resolve();output.mkdir(parents=True,exist_ok=resume)
    binding=dict(protocol_sha256=plan.protocol_sha256,inputs=str(inputs.resolve()),
        rscript=str(rscript.resolve()),r_library=str(r_library.resolve()),host_lock=str(host_lock.resolve()))
    if (output/'binding.json').exists():
        if json.loads((output/'binding.json').read_text())!=binding:raise ValueError('Batch binding changed')
    else:atomic_json(output/'binding.json',binding)
    c=MeasuredCoordinator(host_lock,output/'call-costs');reports=[];new=0;began=time.perf_counter()
    for index,task in enumerate(selected):
        capsule,digest=plan.capsule(task['id'])
        job=dict(task=dict(task,protocol_sha256=plan.protocol_sha256),request=dict(capsule=capsule,capsule_sha256=digest,
            inputs=binding['inputs'],rscript=binding['rscript'],r_library=binding['r_library']),
            worker=ROOT/'scripts/completion/batch_worker.py',output=output/'tasks'/task['id'],
            required_disk_bytes=p['required_disk_bytes_per_task'],max_tree_rss_bytes=p['process_tree_rss_limit_bytes'])
        print(json.dumps(dict(index=index+1,total=len(selected),starting=task)),flush=True)
        result=c.run(**job,resume=resume);new+=result['newly_executed']
        reports.append(dict(task=task,status=result['status'],samples_eligible=result['samples_eligible'],
            sampled_peak_tree_rss_bytes=result['memory']['sampled_peak_tree_rss_bytes'],
            ordinary_process=(result.get('worker_result') or {}).get('ordinary_process'),
            diagnostics_status=(result.get('worker_result') or {}).get('diagnostics_status'),
            costs=c.report(job['output'])))
        print(json.dumps(dict(done=task['id'],status=result['status'],newly_executed=result['newly_executed'])),flush=True)
    report=dict(protocol_sha256=plan.protocol_sha256,source_commit=p['source_commit'],batch=batch,
        planned=len(selected),newly_executed=new,rows=reports,
        completed=sum(r['status']=='completed' for r in reports),failed=sum(r['status']=='failed' for r in reports),
        interrupted=sum(r['status']=='interrupted' for r in reports),
        driver_loop_wall_seconds=time.perf_counter()-began,driver_time_includes_report_and_log_overhead=True,
        driver_time_excludes_initial_plan_source_input_checks_and_own_summary_write=True,
        registry=str(c.coordinator.registry_path),formal_scientific_repetitions=0,formal_inference_complete=False)
    inv=output/'invocations';inv.mkdir(exist_ok=True);atomic_json(inv/(str(time.time_ns())+'.json'),report)
    return {k:v for k,v in report.items() if k!='rows'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');r=sub.add_parser('run')
    for child in (f,r):
        for name in ('protocol','inputs','rscript','r-library'):child.add_argument('--'+name,type=Path,required=True)
    for name in ('output','host-lock'):r.add_argument('--'+name,type=Path,required=True)
    r.add_argument('--batch',type=int,default=0);r.add_argument('--resume',action='store_true')
    args=vars(parser.parse_args());action=args.pop('action');print(json.dumps((freeze if action=='freeze' else run)(**args),indent=2))
