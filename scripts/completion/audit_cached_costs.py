"""Finite native Mac prepared-executor and recovery-inclusive cost validation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python')]
from formal_runtime import file_hash,fingerprint,atomic_json


def freeze(profile,scientific_protocol,measurement_profile):
    if profile.exists():raise FileExistsError('New immutable technical profile required')
    p=json.loads(scientific_protocol.read_text());m=json.loads(measurement_profile.read_text())
    for doc,key in ((p,'protocol_sha256'),(m,'measurement_sha256')):
        unsigned=dict(doc);digest=unsigned.pop(key)
        if fingerprint(unsigned)!=digest:raise ValueError('Dependency hash differs')
    names=['scripts/completion/'+n+'.py' for n in ('cached_execution','cached_cost_worker','measured_coordinator',
        'measured_recovery_fixture','audit_cached_costs','formal_coordinator','formal_outcomes','formal_recovery','formal_runtime')]
    sources={name:file_hash(ROOT/name) for name in names}
    for name,h in {**p['source_files'],**m['source_files'],**sources}.items():
        if file_hash(ROOT/name)!=h or hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit and preserve source before freeze: '+name)
    tasks=[t for t in p['tasks'] if t['model']=='G1' and t['kernel']!='nuts']
    if len(tasks)!=4:raise ValueError('Four existing G1 MH tasks required')
    profile_data=dict(identity='cached-cost-technical-mac-v1',required_platform='darwin',source_files=sources,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        scientific_protocol_sha256=p['protocol_sha256'],measurement_profile_sha256=m['measurement_sha256'],
        cached_tasks=tasks,warm_replays=3,recovery_task=next(t for t in tasks if t['kernel']=='mala' and t['executor']=='sequential'),
        recovery_execution_id='recovery-'+next(t['id'] for t in tasks if t['kernel']=='mala' and t['executor']=='sequential'),
        purpose='Finite timing/eligibility/recovery validation, no performance ranking or formal inference',
        recovery_injection='Exit code 7 after original audited worker completes; explicit retry preserves input and source',
        no_total_time_cutoff=True,actual_MH_executions_planned=18,new_independent_statistical_repetitions=0,
        cached_NUTS_measured=False,native_Windows_validated=False,formal_inference_complete=False)
    profile_data['protocol_sha256']=fingerprint(profile_data);atomic_json(profile,profile_data);return profile_data


def run(profile,scientific_protocol,measurement_profile,inputs,reference,output,host_lock,rscript,r_library):
    import numpy as np
    from measured_coordinator import MeasuredCoordinator
    from formal_streaming import read_member
    from formal_outcomes import read_attempt
    p=json.loads(scientific_protocol.read_text());m=json.loads(measurement_profile.read_text());c=json.loads(profile.read_text())
    for doc,key in ((p,'protocol_sha256'),(m,'measurement_sha256'),(c,'protocol_sha256')):
        unsigned=dict(doc);digest=unsigned.pop(key)
        if fingerprint(unsigned)!=digest:raise ValueError('Protocol hash differs')
    if sys.platform!='darwin' or c['identity']!='cached-cost-technical-mac-v1':raise ValueError('Native Mac technical profile only')
    if c['scientific_protocol_sha256']!=p['protocol_sha256'] or c['measurement_profile_sha256']!=m['measurement_sha256']:
        raise ValueError('Dependency differs')
    for source in (p['source_files'],m['source_files'],c['source_files']):
        for name,h in source.items():
            if file_hash(ROOT/name)!=h:raise ValueError('Frozen source differs: '+name)
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    measured=MeasuredCoordinator(host_lock,output/'call-costs');jobs=[];cached=[];snapshots={}
    for task in c['cached_tasks']:
        job=dict(task=dict(task,protocol_sha256=c['protocol_sha256']),request=dict(profile=str(profile.resolve()),
            scientific_protocol=str(scientific_protocol.resolve()),inputs=str(inputs.resolve()),reference=str(reference.resolve()),task_id=task['id']),
            worker=ROOT/'scripts/completion/cached_cost_worker.py',output=output/'cached'/task['id'],
            required_disk_bytes=p['required_disk_bytes_per_task'],max_tree_rss_bytes=p['process_tree_rss_limit_bytes'])
        print(json.dumps(dict(starting_cached=task)),flush=True)
        result=measured.run(**job);jobs.append(job)
        if result['status']!='completed':raise AssertionError('Cached measurement failed; inspect retained evidence')
        cached.append(result['worker_result'])
    task=c['recovery_task'];original=output/'injected-recovery'
    job=dict(task=dict(task,id=c['recovery_execution_id'],protocol_sha256=c['protocol_sha256'],role='intentional_recovery_fixture'),
        request=dict(measurement_protocol=str(measurement_profile.resolve()),scientific_request=dict(
            protocol=str(scientific_protocol.resolve()),inputs=str(inputs.resolve()),task_id=task['id'],
            rscript=str(rscript.resolve()),r_library=str(r_library.resolve()))),
        worker=ROOT/'scripts/completion/measured_recovery_fixture.py',output=original,
        required_disk_bytes=p['required_disk_bytes_per_task'],max_tree_rss_bytes=p['process_tree_rss_limit_bytes'])
    print(json.dumps(dict(starting_intentional_recovery=task)),flush=True)
    interrupted=measured.run(**job)
    if interrupted['status']!='interrupted' or interrupted['samples_eligible']:raise AssertionError('Injected original was not quarantined')
    original_hashes={str(f):file_hash(f) for f in original.rglob('*') if f.is_file()}
    recovered=measured.retry(original,reason='Predeclared technical exit-7 injection after real audited MALA; not a scientific failure retry')
    if recovered['status']!='completed':raise AssertionError('Explicit retry failed')
    retry=original.with_name(original.name+'.retry');matches={}
    for k in ('draws','unconstrained','accept'):
        matches[k]=bool(np.array_equal(read_member(original/'attempt-0001/fit.npz',k),read_member(retry/'attempt-0001/fit.npz',k)))
    if not all(matches.values()):raise AssertionError('Recovered numerical output differs')
    if any(file_hash(Path(f))!=h for f,h in original_hashes.items()):raise AssertionError('Recovery changed original evidence')
    before=measured.report(original)
    if before['actual_attempts']!=2 or before['complete_invocation_seconds'] is None:raise AssertionError('Recovery costs incomplete')
    if before['history']['attempts'][0]['outcome']!='infrastructure_interruption':raise AssertionError('Original outcome lost')
    # Task artifacts remain immutable; separately appended verification calls
    # retain their overhead without replacing original execution receipts.
    for location in [j['output'] for j in jobs]+[original,retry]:
        for f in location.rglob('*'):
            if f.is_file():snapshots[str(f)]=file_hash(f)
    for j in jobs+[job]:
        if measured.run(**j,resume=True)['newly_executed']:raise AssertionError('Resume launched new work')
    if any(file_hash(Path(f))!=h for f,h in snapshots.items()):raise AssertionError('Resume modified task evidence')
    costs=[measured.report(j['output']) for j in jobs];recovery=measured.report(original)
    for report in costs+[recovery]:
        if report['complete_invocation_seconds'] is None or report['unfinished_invocations']:raise AssertionError('Missing external cost')
    receipt=dict(protocol_sha256=c['protocol_sha256'],source_commit=c['source_commit'],cached_workflows=len(cached),
        initial_executor_calls=4,warm_executor_calls=12,independent_path_audits=16,
        cached_records=cached,cached_task_costs=costs,recovery_cost_before_verification=before,recovery_cost_after_verification=recovery,
        original_retry_arrays_identical=matches,original_files_preserved=len(original_hashes),
        resume_new_tasks=0,terminal_files_preserved=len(snapshots),actual_MH_executions=18,
        new_independent_statistical_repetitions=0,cached_NUTS_measured=False,native_Windows_validated=False,formal_inference_complete=False,
        registry=str(measured.coordinator.registry_path),
        scope='Four frozen MH inputs, initial plus 3 prepared replays; two actual MALA executions in an explicit infrastructure-failure fixture. No new independent repeats or performance ranking.')
    atomic_json(output/'receipt.json',receipt)
    atomic_json(output/'manifest.json',{f.relative_to(output).as_posix():file_hash(f) for f in sorted(output.rglob('*')) if f.is_file()})
    return {k:v for k,v in receipt.items() if k not in ('cached_records','cached_task_costs','recovery_cost_before_verification','recovery_cost_after_verification')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');r=sub.add_parser('run')
    for child in (f,r):
        for name in ('profile','scientific-protocol','measurement-profile'):child.add_argument('--'+name,type=Path,required=True)
    for name in ('inputs','reference','output','host-lock','rscript','r-library'):r.add_argument('--'+name,type=Path,required=True)
    args=vars(parser.parse_args());action=args.pop('action');print(json.dumps((freeze if action=='freeze' else run)(**args),indent=2))
