"""Freeze and check separate ordinary/audited task walls on existing inputs.

This is a finite Mac timing-boundary validation, not a performance experiment.
Five technical executions reuse existing random arrays; statistical n is zero.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_runtime import atomic_json,file_hash,fingerprint

SOURCE_NAMES=['scripts/completion/'+name+'.py' for name in (
    'measured_workflow','measured_ordinary_worker','measured_audit_worker','audit_measured_workflow',
    'formal_coordinator','formal_recovery','formal_outcomes','formal_runtime','formal_streaming','selected_mh_readiness')]


def load_profile(profile,protocol):
    profile=json.loads(Path(profile).read_text());p=json.loads(Path(protocol).read_text())
    for obj,key in ((profile,'measurement_sha256'),(p,'protocol_sha256')):
        unsigned=dict(obj);digest=unsigned.pop(key)
        if fingerprint(unsigned)!=digest:raise ValueError('Protocol digest differs')
    if profile['identity']!='measured-workflow-technical-mac-v1' or sys.platform!='darwin':
        raise ValueError('Only the declared native Mac measurement profile is supported')
    if profile['dependency_protocol_sha256']!=p['protocol_sha256']:
        raise ValueError('Scientific dependency differs')
    for source in (profile['source_files'],p['source_files']):
        for name,h in source.items():
            if file_hash(ROOT/name)!=h:raise ValueError('Frozen source changed: '+name)
    return profile,p


def freeze(profile,protocol):
    if profile.exists():raise FileExistsError('A new immutable measurement profile is required')
    p=json.loads(protocol.read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if fingerprint(unsigned)!=digest or p['identity']!='formal-runtime-technical-mac-v1':
        raise ValueError('Expected frozen scientific technical dependency')
    sources={name:file_hash(ROOT/name) for name in SOURCE_NAMES}
    for name,h in {**p['source_files'],**sources}.items():
        if file_hash(ROOT/name)!=h or hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit unchanged source before freezing: '+name)
    tasks=[t for t in p['tasks'] if (t['model']=='G1' and t['kernel']!='nuts') or (t['model']=='L1' and t['kernel']=='nuts')]
    if len(tasks)!=5:raise ValueError('Expected four G1 MH workflows and L1 four-process NUTS')
    result=dict(identity='measured-workflow-technical-mac-v1',required_platform='darwin',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_files=sources,dependency_protocol_sha256=digest,tasks=tasks,actual_inputs=p['inputs'],
        no_total_time_cutoff=True,independent_statistical_repetitions_added=0,
        ordinary_scope='Standalone Python batch startup through exit, full retained paths and R diagnostics, before independent MH path audit',
        audit_scope='External coordinator.run wall including registration, owned process lifecycle, independent audit, sealing and verified history; excludes the outer measurement receipt write and companion validation',
        cached_execution_measured=False,formal_inference_complete=False,
        resume_policy='Keep initial execution-wall receipt unchanged; record resume verification as a separate invocation',
        numerical_standards='Unchanged dependency tolerances, fixed actual random arrays and independent NumPy oracle; no fallback')
    result['measurement_sha256']=fingerprint(result)
    atomic_json(profile,result);return result


def phase_checks(path):
    phases=json.loads(path.read_text())['phases'];previous=0.
    for row in phases:
        if row['status']!='completed' or not 0<=previous<=row['start_offset_seconds']<=row['end_offset_seconds']:
            raise AssertionError('Phases failed or overlap')
        previous=row['end_offset_seconds']
    return phases


def run(profile,protocol,inputs,output,rscript,r_library,host_lock,reference,resume=False):
    import numpy as np
    from formal_coordinator import TaskCoordinator
    from formal_outcomes import read_attempt
    from formal_streaming import read_member
    from selected_mh_readiness import compare
    m,p=load_profile(profile,protocol)
    output=output.resolve();output.mkdir(parents=True,exist_ok=resume)
    binding=dict(measurement_sha256=m['measurement_sha256'],protocol=str(protocol.resolve()),
        inputs=str(inputs.resolve()),rscript=str(rscript.resolve()),r_library=str(r_library.resolve()),
        host_lock=str(host_lock.resolve()),reference=str(reference.resolve()))
    if (output/'binding.json').exists():
        if json.loads((output/'binding.json').read_text())!=binding:raise ValueError('Driver binding differs')
    else:atomic_json(output/'binding.json',binding)
    coordinator=TaskCoordinator(host_lock);jobs=[];rows=[];new=0
    for task in m['tasks']:
        science=dict(protocol=binding['protocol'],inputs=binding['inputs'],task_id=task['id'],
            rscript=binding['rscript'],r_library=binding['r_library'])
        job=dict(task=dict(task,protocol_sha256=m['measurement_sha256']),
            request=dict(measurement_protocol=str(profile.resolve()),scientific_request=science),
            worker=ROOT/'scripts/completion/measured_audit_worker.py',output=output/'tasks'/task['id'],
            required_disk_bytes=p['required_disk_bytes_per_task'],max_tree_rss_bytes=p['process_tree_rss_limit_bytes'])
        jobs.append(job);receipt=output/(task['id']+'-measurement.json')
        # Losing the external timer cannot be repaired by timing a cached resume.
        if job['output'].exists() and not receipt.exists():
            raise ValueError('Prior execution has no external wall receipt; retain it as missing, do not substitute resume time')
        print(json.dumps(dict(starting=task)),flush=True)
        start=time.perf_counter();result=coordinator.run(**job,resume=resume);seconds=time.perf_counter()-start
        new+=result['newly_executed']
        if result['newly_executed']:
            if receipt.exists():raise ValueError('Refusing to replace original execution wall')
            atomic_json(receipt,dict(task=task,measurement_sha256=m['measurement_sha256'],
                audited_task_invocation_wall_seconds=seconds,boundary=m['audit_scope'],
                status=result['status'],nested_components_additive=False))
        rows.append(json.loads(receipt.read_text()))
        print(json.dumps(dict(done=task['id'],status=result['status'],newly_executed=result['newly_executed'])),flush=True)
    snapshots={};fits={};diagnostics=[];validation=[]
    for task,job,row in zip(m['tasks'],jobs,rows):
        directory=job['output'];attempt=directory/'attempt-0001'
        worker=json.loads((attempt/'worker-result.json').read_text())
        if worker['status']!='completed' or not worker['samples_eligible']:
            raise AssertionError('Technical output failed; retain evidence and inspect '+task['id'])
        ordinary=json.loads((attempt/'ordinary-output.json').read_text())
        if ordinary['samples_eligible'] is not False:raise AssertionError('Unaudited candidate was eligible')
        phases=phase_checks(attempt/'phases.json');phase_checks(attempt/'ordinary-phases.json')
        by_name={x['name']:x for x in phases}
        ordinary_wall=worker['ordinary_process']['ordinary_process_wall_seconds']
        audit_phase=by_name['independent_research_audit_after_ordinary_exit']['wall_seconds']
        if not 0<ordinary_wall<=by_name['ordinary_process_startup_through_exit']['wall_seconds']<row['audited_task_invocation_wall_seconds']:
            raise AssertionError('Inconsistent ordinary and outer measured walls')
        metadata=json.loads((attempt/'fit.json').read_text())
        if metadata['ordinary_candidate_arrays_sha256']!=file_hash(attempt/'fit.npz') or metadata['ordinary_candidate_metadata_sha256']!=file_hash(attempt/'candidate.json'):
            raise AssertionError('Candidate changed during audit')
        original=reference/task['id'];old=read_attempt(original)
        if old['outcome']!='valid' or old['fixed_task']!=dict(task,protocol_sha256=p['protocol_sha256']):
            raise AssertionError('Original comparison evidence is not eligible or task differs')
        oldpath=original/'attempt-0001';keys=['draws','unconstrained']+([] if task['kernel']=='nuts' else ['accept'])
        matched={k:bool(np.array_equal(read_member(attempt/'fit.npz',k),read_member(oldpath/'fit.npz',k))) for k in keys}
        if not all(matched.values()):raise AssertionError('Numerical output differs after moving audit: '+task['id'])
        for rel in ['diagnostics/functions.bin','diagnostics/functions.bin.roundtrip']:
            if file_hash(attempt/rel)!=file_hash(oldpath/rel):raise AssertionError('R input/transport changed')
        post=json.loads((attempt/'diagnostics/posterior.json').read_text())['results'][task['id']]
        if post!=json.loads((oldpath/'diagnostics/posterior.json').read_text())['results'][task['id']]:
            raise AssertionError('Modern diagnostics changed')
        diagnostics.extend(post)
        if task['kernel']!='nuts':
            if not worker['full_MH_audit']['passed']:raise AssertionError('Independent full audit failed')
            fits[(task['kernel'],task['executor'])]=dict(status='completed',**{k:read_member(attempt/'fit.npz',k) for k in keys})
        validation.append(dict(task=task,ordinary_process_wall_seconds=ordinary_wall,
            audited_task_invocation_wall_seconds=row['audited_task_invocation_wall_seconds'],
            independent_audit_phase_seconds=audit_phase,original_arrays_identical=matched,
            R_binary_and_diagnostics_identical=True,phases_nonoverlapping=True,
            candidate_ineligible_before_audit=True,raw_candidate_retained=True))
        for f in directory.rglob('*'):
            if f.is_file():snapshots[str(f)]=file_hash(f)
        snapshots[str(output/(task['id']+'-measurement.json'))]=file_hash(output/(task['id']+'-measurement.json'))
    pairs=[dict(kernel=k,**compare(fits[(k,'sequential')],fits[(k,e)],p)) for k,e in [('rwm','online_picard'),('mala','quasi_deer')]]
    if not all(x['passed'] for x in pairs):raise AssertionError('Paired paths differ')
    resume_rows=[]
    for job in jobs:
        start=time.perf_counter();r=coordinator.run(**job,resume=True);seconds=time.perf_counter()-start
        if r['newly_executed']:raise AssertionError('Resume unexpectedly ran new work')
        resume_rows.append(dict(task_id=job['task']['id'],verification_invocation_seconds=seconds,newly_executed=False))
    if any(file_hash(Path(f))!=h for f,h in snapshots.items()):raise AssertionError('Resume changed immutable evidence or original timing')
    receipt=dict(measurement_sha256=m['measurement_sha256'],source_commit=m['source_commit'],
        completed=len(validation),newly_executed_tasks=new,validation=validation,pairs=pairs,
        independent_MH_audits=4,R_binary_roundtrips=5,
        finite_function_rhat_above_1_01=sum(x.get('rhat') is not None and x['rhat']>1.01 for x in diagnostics),
        undefined_function_rhat=sum(x.get('rhat') is None for x in diagnostics),
        terminal_and_initial_measurement_files_unchanged=len(snapshots),resume_new_tasks=0,
        resume_verification=resume_rows,registry=str(coordinator.registry_path),
        histories=[coordinator.history(job['output']) for job in jobs],
        actual_technical_executions_total=5,new_independent_statistical_repetitions=0,
        cached_execution_measured=False,ordinary_workflow_measured_separately=True,
        native_Windows_validated=False,formal_inference_complete=False,
        scope='Finite cost-boundary validation. One measurement per task; no speed comparison, no cold filesystem cache claim. Audit wall excludes companion validation and own receipt write.')
    history=output/'invocations';history.mkdir(exist_ok=True)
    atomic_json(history/(str(time.time_ns())+'.json'),receipt)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');r=sub.add_parser('run')
    for child in (f,r):
        for name in ('profile','protocol'):child.add_argument('--'+name,type=Path,required=True)
    for name in ('inputs','output','rscript','r-library','host-lock','reference'):r.add_argument('--'+name,type=Path,required=True)
    r.add_argument('--resume',action='store_true');args=vars(parser.parse_args());action=args.pop('action')
    print(json.dumps((freeze if action=='freeze' else run)(**args),indent=2))
