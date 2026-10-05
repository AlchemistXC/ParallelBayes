"""Relocated, read-only technical batch evidence -> complete planned analysis.

This does not execute samplers, repair outcomes, regenerate random inputs, or
turn one technical repetition into a formal precision or speed estimate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from analyze_budget_pilot import references
from batch_contract import BatchPlan,mh_config
from formal_evidence import RuntimeEvidence,inside
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_runtime_analysis import extract_task
from formal_streaming import read_member
from formal_error_summary import summarize,paired_difference
from measured_coordinator import read_calls,summarize_calls


def verify_binding(plan,task,binding,root_binding):
    """Tie a worker request back to the full frozen declared grid."""
    c,h=plan.capsule(task['id']);request=binding['request']
    if binding['task']!=dict(task,protocol_sha256=plan.protocol_sha256) or request['capsule']!=c or request['capsule_sha256']!=h:
        raise ValueError('Archived capsule conflicts with the declared plan')
    if root_binding['protocol_sha256']!=plan.protocol_sha256 or any(request[k]!=root_binding[k] for k in ('inputs','rscript','r_library')):
        raise ValueError('Historical input/environment binding differs')
    if (binding['worker_sha256']!=c['source_files']['scripts/completion/batch_worker.py'] or
        binding['host_lock']!=root_binding['host_lock'] or binding['required_disk_bytes']!=c['required_disk_bytes_per_task'] or
        binding['max_tree_rss_bytes']!=c['process_tree_rss_limit_bytes']):
        raise ValueError('Worker/resource binding differs')
    return c,h


def audit(bundle,output,rscript,r_library):
    bundle=bundle.resolve();output=output.resolve()
    if output.exists() or output.is_relative_to(bundle) or bundle.is_relative_to(output):raise ValueError('New separate analysis output required')
    manifest=json.loads((bundle/'MANIFEST.json').read_text())
    actual={f.relative_to(bundle).as_posix() for f in bundle.rglob('*') if f.is_file()}
    if actual!=set(manifest)|{'MANIFEST.json'}:raise ValueError('Archive inventory differs')
    for name,h in manifest.items():
        if file_hash(inside(bundle,name))!=h:raise ValueError('Archive asset differs: '+name)
    p=json.loads((bundle/'profile.json').read_text());plan=BatchPlan(p)
    if p['scope_kind']!='technical_batch_validation':raise ValueError('This reader declares technical evidence only')
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Frozen scientific source differs: '+name)
    names=['scripts/completion/'+n for n in ('audit_batch_archive.py','analyze_budget_pilot.py','formal_evidence.py',
        'formal_runtime_analysis.py','formal_streaming.py','formal_error_summary.py','measured_coordinator.py','posterior_diagnostics.R')]
    names+=['benchmark/analysis/outputs/completion-f3/reference-reuse.json','benchmark/protocols/windows-native-v1.json',
        'benchmark/analysis/outputs/wells-quadrature-v1/R12-n96.json','benchmark/analysis/outputs/wells-quadrature-v1/result.json']
    sources={n:file_hash(ROOT/n) for n in names}
    for name,h in sources.items():
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:raise ValueError('Commit analysis source first: '+name)
    receipt=json.loads((bundle/'receipt.json').read_text());binding=json.loads((bundle/'run/binding.json').read_text())
    latest=inside(bundle,receipt['verification_invocation']);prior={}
    for path in sorted(latest.glob('task-*.json')):
        row=json.loads(path.read_text());prior[row['task']['id']]=row
    tasks=list(plan.tasks(receipt['batch']))
    if set(prior)!={t['id'] for t in tasks}:raise ValueError('Every planned task must be present, including interruptions')
    locations=receipt['locations'];models,refs=references(p,None);output.mkdir(parents=True)
    identity=dict(identity='batch-archive-analysis-mac-v1',protocol_sha256=plan.protocol_sha256,
        manifest_sha256=file_hash(bundle/'MANIFEST.json'),registry_sha256=manifest['registry/registry.sqlite3'],
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_files=sources,
        statistical_scope='One existing four-chain technical input per model; intervals unavailable; no repeated-run MSE claim')
    identity['analysis_sha256']=fingerprint(identity);atomic_json(output/'analysis-identity.json',identity)
    atomic_json(output/'reference-contract.json',refs)
    env=dict(os.environ);env['R_LIBS_USER']=str(r_library)
    rows=[];cost_rows=[];diagnostics=[];histories_exact=0;binary_exact=0;means_exact=0;start=time.perf_counter()
    with RuntimeEvidence(bundle/'registry/registry.sqlite3',identity['registry_sha256'],bundle,locations) as evidence:
        for task in tasks:
            previous=prior[task['id']];original=previous['costs']['history']['original']
            directory=inside(bundle,locations[original]);saved=json.loads((directory/'binding.json').read_text())
            c,h=verify_binding(plan,task,saved,binding);ctrl=c['controls'];item=p['inputs'][task['input']]
            inp=inside(bundle,'inputs/'+task['input'])
            if file_hash(inp)!=item['sha256']:raise ValueError('Input file differs')
            initial=read_member(inp,'initial',ctrl['maximum_member_bytes']).tolist()
            contract=dict(task=dict(task,protocol_sha256=plan.protocol_sha256),original=original,
                model=task['model'],workflow=task['workflow'],budget=task['budget'],replicate=str(task['replicate']),
                scientific_task=task,scientific_protocol_sha256=plan.protocol_sha256,science_directory='attempt-0001',
                target_id=models[task['model']].target_id,chains=ctrl['chains'],discard=0 if task['kernel']=='nuts' else ctrl['mh_discard'],
                nuts_warmup=ctrl['nuts_warmup'],expected_config={} if task['kernel']=='nuts' else mh_config(c,initial),
                input_relative='inputs/'+task['input'],input_sha256=item['sha256'],actual_input_sha256=item['actual_sha256'])
            destination=output/'tasks'/task['id'];row=extract_task(evidence,contract,models[task['model']],destination,ctrl['maximum_member_bytes'])
            history=row['history'];oldhistory=previous['costs']['history']
            if history['attempts']!=oldhistory['attempts'] or history['summary']!=oldhistory['summary']:raise ValueError('Recorded history changed')
            histories_exact+=1
            ledger=bundle/'run/call-costs'/fingerprint(original);costidentity,calls=read_calls(ledger)
            cost=summarize_calls(history,costidentity,calls)
            for key in ('calls','actual_attempts','verification_only_invocations','unfinished_invocations','complete_invocation_seconds'):
                if cost[key]!=previous['costs'][key]:raise ValueError('Invocation ledger differs: '+key)
            eligible=[x for x in calls if x['finished'] and (x.get('result') or {}).get('newly_executed') is True]
            verification=[x for x in calls if x['finished'] and (x.get('result') or {}).get('newly_executed') is False]
            primary_complete=(cost['unfinished_invocations']==0 and cost['attempts_missing_outer_measurement']==0 and len(eligible)==cost['actual_attempts'])
            costrow=dict(id=task['id'],model=task['model'],workflow=task['workflow'],budget=task['budget'],outcome=row['outcome'],
                actual_attempts=cost['actual_attempts'],all_invocations_seconds=cost['complete_invocation_seconds'],
                completed_execution_invocation_known_seconds=sum(x['seconds'] for x in eligible),
                execution_invocation_seconds=sum(x['seconds'] for x in eligible) if primary_complete else None,
                additional_verification_seconds=sum(x['seconds'] for x in verification),verification_invocations=len(verification),
                unfinished_invocations=cost['unfinished_invocations'],ordinary_process_seconds=None,cached_execution_seconds=None,
                recorded_sampled_peak_tree_rss_bytes=previous.get('sampled_peak_tree_rss_bytes'),
                unknown_time_imputed=False,nested_phase_times_added=False,all_calls_are_time_to_inference=False)
            if row['outcome']=='valid':
                oldattempt=Path(history['eligible_directory'])/'attempt-0001'
                worker=json.loads((oldattempt/'worker-result.json').read_text());ordinary=json.loads((oldattempt/'ordinary-output.json').read_text())
                if worker['capsule_sha256']!=h or ordinary['capsule_sha256']!=h or ordinary['task']!=task or ordinary['protocol_sha256']!=plan.protocol_sha256:
                    raise ValueError('Ordinary/final output capsule differs')
                costrow['ordinary_process_seconds']=worker['ordinary_process']['ordinary_process_wall_seconds']
                if task['kernel']=='nuts':
                    meta=json.loads((oldattempt/'fit.json').read_text())
                    if any(meta[k]!=v for k,v in {'workers_requested':ctrl['nuts_workers'],'workers_allocated':ctrl['nuts_workers'],
                        'threads_per_worker':ctrl['nuts_threads'],'process_start_method':'spawn'}.items()):raise ValueError('NUTS resource policy differs')
                    for child in meta['worker_records']:
                        cm=json.loads(inside(oldattempt,child['result_directory']+'/metadata.json').read_text())
                        expected=dict(full_mass=ctrl['nuts_full_mass'],target_accept_prob=ctrl['nuts_target_accept'],max_tree_depth=ctrl['nuts_tree_depth'],
                            warmup_per_chain=ctrl['nuts_warmup'],draws_per_chain=task['budget'])
                        if any(cm[k]!=v for k,v in expected.items()) or child['threads']!=ctrl['nuts_threads']:raise ValueError('NUTS adaptation policy differs')
                if row['function_status']!='completed':raise ValueError('Historical functions unavailable')
                estimates=json.loads((oldattempt/'diagnostics/estimates.json').read_text())
                if row['names']!=estimates['names'] or row['means']!=estimates['means']:raise ValueError('Function estimates differ')
                means_exact+=1
                if file_hash(destination/'functions.bin')!=file_hash(oldattempt/'diagnostics/functions.bin'):raise ValueError('Function transport differs')
                atomic_json(destination/'transport.json',dict(fits=[dict(id=task['id'],input='functions.bin',shape=row['extraction']['shape'],names=row['names'])],
                    scope=identity['statistical_scope'],independent_unit='one existing technical four-chain input'))
                proc=subprocess.run([str(rscript),'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(destination)],capture_output=True,text=True,env=env)
                (destination/'R.log').write_text(proc.stdout+proc.stderr)
                if proc.returncode:raise RuntimeError('R read-only reanalysis failed')
                if file_hash(destination/'functions.bin')!=file_hash(destination/'functions.bin.roundtrip'):raise ValueError('R roundtrip differs')
                post=json.loads((destination/'posterior.json').read_text());oldpost=json.loads((oldattempt/'diagnostics/posterior.json').read_text())
                if any(post[k]!=oldpost[k] for k in ('R','posterior','results')):raise ValueError('Saved modern diagnostics differ')
                binary_exact+=1
                diagnostics.extend(dict(task_id=task['id'],model=task['model'],workflow=task['workflow'],budget=task['budget'],**d) for d in post['results'][task['id']])
            rows.append(row);cost_rows.append(costrow)
    points=[];pairs=[];path_pairs=[]
    for name,ref in refs.items():
        selected=[r for r in rows if r['model']==name]
        for j,fn in enumerate(ref['names']):
            reference=dict(kind=ref['kinds'][j],value=ref['means'][j],mcse=ref['mcse'][j])
            for row in selected:
                estimate=None if row['means'] is None else row['means'][j]
                points.append(dict(model=name,workflow=row['workflow'],budget=row['budget'],function=fn,report=summarize([estimate],reference)))
            for kernel,executor in [('rwm','online_picard'),('mala','quasi_deer')]:
                a=next(r for r in selected if r['workflow']==f'cpu-{kernel}-sequential');b=next(r for r in selected if r['workflow']==f'cpu-{kernel}-{executor}')
                pairs.append(dict(model=name,kernel=kernel,function=fn,report=paired_difference(
                    [None if a['means'] is None else a['means'][j]],[None if b['means'] is None else b['means'][j]],reference)))
        for kernel,executor in [('rwm','online_picard'),('mala','quasi_deer')]:
            a=next(r for r in selected if r['workflow']==f'cpu-{kernel}-sequential');b=next(r for r in selected if r['workflow']==f'cpu-{kernel}-{executor}')
            pair=dict(model=name,kernel=kernel,budget=a['budget'],valid_pair=a['outcome']==b['outcome']=='valid',acceptance_mismatches=None,max_path_difference=None)
            if pair['valid_pair']:
                af=Path(a['history']['eligible_directory'])/'attempt-0001/fit.npz';bf=Path(b['history']['eligible_directory'])/'attempt-0001/fit.npz'
                pair['acceptance_mismatches']=int(np.count_nonzero(read_member(af,'accept')!=read_member(bf,'accept')))
                pair['max_path_difference']=float(np.max(np.abs(read_member(af,'unconstrained')-read_member(bf,'unconstrained'))))
            path_pairs.append(pair)
    atomic_json(output/'technical-points.json',dict(points=points,pairs=pairs,interpretation=identity['statistical_scope'],resampling_performed=False))
    for name,data in [('task-records',rows),('costs',cost_rows),('modern-diagnostics',diagnostics),('path-pairs',path_pairs)]:atomic_json(output/(name+'.json'),data)
    summary=dict(analysis_sha256=identity['analysis_sha256'],source_commit=identity['source_commit'],assets_checked=len(manifest),planned=len(tasks),
        valid=sum(r['outcome']=='valid' for r in rows),interrupted=sum(r['outcome']=='infrastructure_interruption' for r in rows),
        means_exact=means_exact,histories_exact=histories_exact,R_transports_exact=binary_exact,modern_diagnostic_rows_exact=len(diagnostics),
        finite_function_rhat_above_1_01=sum(d.get('rhat') is not None and d['rhat']>1.01 for d in diagnostics),
        undefined_function_rhat=sum(d.get('rhat') is None for d in diagnostics),paired_paths=len(path_pairs),
        paired_acceptance_mismatches=sum(x['acceptance_mismatches'] or 0 for x in path_pairs),
        primary_cost_available=sum(x['execution_invocation_seconds'] is not None for x in cost_rows),
        ordinary_cost_available=sum(x['ordinary_process_seconds'] is not None for x in cost_rows),
        technical_point_rows=len(points),technical_pair_rows=len(pairs),available_intervals=0,
        new_MCMC_fits=0,formal_scientific_repetitions=0,formal_inference_complete=False,native_Windows_validated=False,
        analysis_wall_seconds=time.perf_counter()-start,analysis_is_sampler_time=False)
    import resource
    summary.update(Python_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        largest_child_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        memory_scope='Separate Mac lifetime maxima, not summed process-tree peak')
    for name,h in sources.items():
        if file_hash(ROOT/name)!=h:raise ValueError('Analysis source changed')
    for name,h in manifest.items():
        if file_hash(inside(bundle,name))!=h:raise ValueError('Evidence changed during read-only analysis')
    atomic_json(output/'summary.json',summary)
    atomic_json(output/'manifest.json',{f.relative_to(output).as_posix():file_hash(f) for f in sorted(output.rglob('*')) if f.is_file()})
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bundle','output','rscript','r-library'):p.add_argument('--'+name,type=Path,required=True)
    print(json.dumps(audit(**vars(p.parse_args())),indent=2))
