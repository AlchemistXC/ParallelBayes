"""Portable explicit read-only adapter for Windows-owned-runtime-v1 evidence.

Reads relocated paths derived from the complete frozen plan, never old absolute
paths, a live registry, samplers, RNG reconstruction or Mac process groups.
"""
import argparse
import math
import shutil
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/windows'),str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from formal_runtime import atomic_json,file_hash,fingerprint
from batch_contract import BatchPlan,mh_config
from formal_streaming import read_member,extract_functions
from formal_outcomes import summarize_attempts
from formal_cost_policy import summarize_task_costs
from measured_coordinator import read_calls
from analyze_budget_pilot import references
from formal_error_summary import summarize
from technical_summary import cache_description


def manifest(root):
    return {p.relative_to(root).as_posix():file_hash(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name!='EVIDENCE-MANIFEST.json'}


def seal(bundle):
    bundle=Path(bundle).resolve();target=bundle/'EVIDENCE-MANIFEST.json'
    if target.exists():raise FileExistsError('Evidence already sealed')
    atomic_json(target,manifest(bundle))
    return len(json.loads(target.read_text()))


def verify_attempt(directory,attempt):
    if (directory/'state.json').exists():
        state=json.loads((directory/'state.json').read_text())
        if state['schema']!='windows-owned-runtime-v1' or state['outcome']!=attempt['outcome']:
            raise ValueError('Native attempt outcome/schema differs')
        if file_hash(directory/'state.json')!=json.loads((directory/'completion.json').read_text())['state_sha256']:
            raise ValueError('Attempt state checksum differs')
        actual={p.relative_to(directory).as_posix():file_hash(p) for p in directory.rglob('*') if p.is_file() and p.name not in ('state.json','completion.json')}
        if actual!=state['assets']:raise ValueError('Attempt assets differ')
        if state['job_final']['active_processes']!=0:raise ValueError('Sealed job has active processes')
        return state
    sidecar=directory.parent/'recovery'/attempt['recovery']
    record=json.loads(sidecar.read_text())
    actual={p.relative_to(directory).as_posix():file_hash(p) for p in directory.rglob('*') if p.is_file()}
    if record['original_assets']!=actual:raise ValueError('Interrupted original assets differ')
    if record['proof']['state']!='absent' and record['proof']['active_processes']!=0:raise ValueError('Recovery lacks Windows job end proof')
    return dict(outcome=record['outcome'],samples_eligible=False,measurement_available=False,invocation_seconds=None)


def numeric_comparison(left,right,atol,rtol):
    """Explicit receiver comparison; missing/constant diagnostics remain exact."""
    differences=[]
    def visit(a,b):
        if isinstance(a,dict) and isinstance(b,dict):return a.keys()==b.keys() and all(visit(a[k],b[k]) for k in a)
        if isinstance(a,list) and isinstance(b,list):return len(a)==len(b) and all(visit(x,y) for x,y in zip(a,b))
        if type(a) in (float,int) and type(b) in (float,int):
            if not math.isfinite(a) or not math.isfinite(b):return False
            differences.append(abs(a-b));return math.isclose(a,b,abs_tol=atol,rel_tol=rtol)
        return type(a) is type(b) and a==b
    passed=visit(left,right)
    return dict(exact=left==right,passed=passed,maximum_absolute_difference=max(differences,default=0),atol=atol,rtol=rtol)


def audit(bundle,output,rscript,r_library,cross_platform=False):
    bundle=Path(bundle).resolve();output=Path(output).resolve()
    if output.exists() or output.is_relative_to(bundle) or bundle.is_relative_to(output):raise ValueError('Fresh separate analysis directory required')
    if json.loads((bundle/'EVIDENCE-MANIFEST.json').read_text())!=manifest(bundle):raise ValueError('Sealed evidence inventory differs')
    p=json.loads((bundle/'protocol.json').read_text());plan=BatchPlan(p)
    cp=json.loads((bundle/'cache-protocol.json').read_text());cacheplan=BatchPlan(cp)
    marker=json.loads((bundle/'PARALLELBAYES-FROZEN.json').read_text())
    if marker['protocols']!=[p['protocol_sha256'],cp['protocol_sha256']] or marker['source_commit']!=p['source_commit'] or marker['dependency_sha256']!=file_hash(bundle/'pip-freeze.txt'):
        raise ValueError('Frozen source/protocol/full environment lock binding differs')
    if p['required_platform']!='win32' or len(list(plan.tasks()))!=27 or len(list(cacheplan.tasks()))!=24:
        raise ValueError('Wrong bounded Windows engineering grid')
    for name,row in p['inputs'].items():
        path=bundle/'inputs'/name
        if file_hash(path)!=row['sha256']:raise ValueError('Actual master file differs')
        from mechanism_runner import actual_hash
        payload={k:read_member(path,k) for k in ('initial','noise','log_uniform','directions','nuts_seeds')}
        if actual_hash(payload)!=row['actual_sha256']:raise ValueError('Actual master arrays differ')
        del payload
    # A frozen source copy is checked independently; no Windows APIs are imported.
    for name,h in p['source_files'].items():
        if file_hash(bundle/'source'/name)!=h:raise ValueError('Archived numerical/runtime source differs')
    # References are read from verified archived bytes, not the checkout's
    # mutable data catalog. Reader numerical helpers must match that identity.
    for name,h in p['source_files'].items():
        if name.startswith(('r-package/inst/python/','examples/')) and file_hash(ROOT/name)!=h:
            raise ValueError('Compatible numerical reader source required: '+name)
    import analyze_budget_pilot
    analyze_budget_pilot.ROOT=bundle/'source'
    models,refs=references(p,None);output.mkdir()
    atomic_json(output/'reference-contract.json',refs)
    rows=[];cache_rows=[];ownership=[];diagnostics=[];costs=[];fits={};cache_records={}
    for phase,current in (('main',plan),('cache',cacheplan)):
        snapshots=sorted((bundle/phase/'invocations').glob('call-*/registry-snapshot.json'))
        if not snapshots:raise ValueError('Quiescent native registry snapshot required')
        registry=json.loads(snapshots[-1].read_text());digest=registry.pop('sha256');flag=registry.pop('snapshot_is_live_registry')
        if flag is not False or fingerprint(registry)!=digest or registry['schema']!='windows-owned-runtime-v1':raise ValueError('Static registry checksum/schema differs')
        for task in current.tasks():
            key=fingerprint(dict(protocol=current.protocol_sha256,id=task['id']));entry=registry['tasks'].get(key)
            capsule,h=current.capsule(task['id']);kind='posterior' if phase=='main' else 'cache_measurement'
            expected=dict(task,protocol_sha256=current.protocol_sha256,artifact_kind=kind)
            row=dict(task=task,outcome='not_run',samples_eligible=False,measurement_available=False,means=None,function_status='unavailable')
            attempts=[];ordinary={};latest=None;folder=None
            if entry:
                binding=entry['binding'];request=binding['request']
                if binding['task']!=expected or request['capsule']!=capsule or request['capsule_sha256']!=h:
                    raise ValueError('Native task/config/source/plan binding differs')
                if binding['worker_sha256']!=capsule['source_files']['scripts/windows/'+('batch_worker.py' if phase=='main' else 'cache_worker.py')]:raise ValueError('Worker hash differs')
                for attempt in entry['attempts']:
                    folder=bundle/phase/'tasks'/task['id']/attempt['id']
                    latest=verify_attempt(folder,attempt)
                    if latest.get('artifact_kind',kind)!=kind:
                        raise ValueError('Native artifact kind contradicts the planned task')
                    if kind=='cache_measurement' and latest['samples_eligible']:
                        raise ValueError('Cache measurement cannot become posterior samples')
                    if bool(latest['measurement_available'])!=(attempt['outcome']=='measurement_available') or bool(latest['samples_eligible'])!=(attempt['outcome']=='valid'):
                        raise ValueError('Native task outcome contradicts eligibility')
                    binding_sha=latest.get('binding_sha256',fingerprint(binding))
                    attempts.append(dict(attempt_id=attempt['id'],binding_sha256=binding_sha,outcome=attempt['outcome'],seconds=latest.get('invocation_seconds'),artifact_kind=kind))
                    timing=folder/'ordinary-process.json'
                    ordinary[attempt['id']]=json.loads(timing.read_text())['ordinary_process_wall_seconds'] if timing.exists() else None
                    if (folder/'ownership.ndjson').exists():
                        samples=[json.loads(v) for v in (folder/'ownership.ndjson').read_text().splitlines()]
                        members={x['pid']:x for sample in samples for x in sample['members']}
                        if any(not x['member_of_owned_job'] for x in members.values()):raise ValueError('Non-member in owned process observation')
                        ownership.append(dict(task_id=task['id'],phase=phase,members=list(members.values()),
                            sampled_rss_peak=max((s['sampled_rss_bytes'] for s in samples),default=0),
                            raw_PeakJobMemoryUsed_bytes=max((s['kernel_peak_job_commit_bytes'] for s in samples),default=0),
                            kernel_peak_counter_scope='Raw Windows PeakJobMemoryUsed. Bounded denial fixture shows this counter can exceed the allocation limit after a denied request; not a proven maximum of successfully committed memory. Frozen input field name preserved.',
                            completed_kernel_job_proof=latest.get('job_final'),quiescent_registry=True,
                            process_cpu_seconds=latest.get('job_final',{}).get('job_cpu_seconds'),
                            process_cpu_scope='Kernel cumulative user+kernel CPU of owned processes; may exceed wall seconds with multiple threads/processes',
                            RSS_is_not_VRAM=True,polling_peak_is_not_hard_RSS_limit=True))
                reduced=summarize_attempts(attempts)
                row.update(outcome=reduced['outcome'],samples_eligible=bool(latest and latest['samples_eligible']),measurement_available=bool(latest and latest['measurement_available']))
                ledger=bundle/phase/'call-costs'/task['id']
                if attempts and ledger.exists():
                    identity,calls=read_calls(ledger)
                    history=dict(task=expected,original=entry['output'],attempts=attempts,summary=reduced)
                    cost=summarize_task_costs(history,identity,calls,ordinary);costs.append(dict(phase=phase,**cost))
            if phase=='cache':
                cache=folder/'cache' if folder else None
                if cache and (cache/'MANIFEST.json').exists():
                    from cache_probe_execution import read_cached_probe
                    report=read_cached_probe(cache)
                    for execution in report['observation']['records']:
                        if execution is not None and execution['technical_output_valid']:
                            d=execution['diagnostics']
                            if not d['tensor_device'].startswith(task['device']) or d['tensor_dtype']!='torch.float64':
                                raise ValueError('Actual cached device/precision contradicts the plan')
                    row['description']=cache_description(report,row['outcome'])
                    row['binding']=report['binding'];cache_records[task['id']]=report
                else:row['description']=None
                cache_rows.append(row);continue
            if row['samples_eligible']:
                if row['outcome']!='valid':raise ValueError('Posterior eligibility contradicts native outcome')
                item=capsule['target'];meta=json.loads((folder/'fit.json').read_text())
                raw=folder/'fit.npz';q=read_member(raw,'unconstrained');a=read_member(raw,'accept') if task['kernel']!='nuts' else None
                total=task['budget']+(512 if task['kernel']!='nuts' else 0)
                if q.shape!=(4,total,item['dimension']) or meta['target_id']!=models[task['model']].target_id:raise ValueError('Fit target/shape differs')
                if task['kernel']!='nuts':
                    initial=read_member(bundle/'inputs'/task['input'],'initial')
                    from parallelbayes.torch_backend.sampling import settings,tape_hash
                    expected_config=settings(mh_config(capsule,initial.tolist()))
                    tape={k:read_member(bundle/'inputs'/task['input'],k)[:,:total] for k in ('noise','log_uniform','directions')}
                    if meta['config']!=expected_config or meta['tape_sha256']!=tape_hash(tape) or not meta['audit']['passed'] or any(meta['audit']['acceptance_mismatches']):raise ValueError('Saved MH audit/config/actual tape conflicts')
                    row['acceptance_rate']=float(a[:,512:].mean());row['tape_sha256']=meta['tape_sha256'];del tape
                    row['mechanism']=meta.get('diagnostics')
                    if not row['mechanism']['tensor_device'].startswith(task['device']) or row['mechanism']['tensor_dtype']!='torch.float64':
                        raise ValueError('Actual MH device/precision contradicts the plan')
                    row['nested_sampler_timing']=meta.get('timing')
                    row['cuda_memory']=json.loads((folder/'cuda-after.json').read_text()) if task['device']=='cuda' else None
                else:
                    if len(meta['worker_records'])!=4 or len(set(meta['observed_worker_pids']))!=4:raise ValueError('Four actual NUTS spawn workers required')
                    seen={p['pid'] for o in ownership if o['task_id']==task['id'] for p in o['members']}
                    if not set(meta['observed_worker_pids'])<=seen:raise ValueError('NUTS workers not observed in the owned Windows job')
                    row['nuts_worker_pids']=meta['observed_worker_pids']
                    master=bundle/'inputs'/task['input']
                    if not np.array_equal(read_member(raw,'initial'),read_member(master,'initial')) or meta['chain_seeds']!=read_member(master,'nuts_seeds').tolist():
                        raise ValueError('NUTS actual initial/seeds differ')
                    warm=read_member(raw,'warmup_states');rng=read_member(raw,'initial_torch_rng_states')
                    if warm.shape!=(4,1024,item['dimension']) or rng.shape[0]!=4 or not np.isfinite(warm).all():
                        raise ValueError('NUTS warmup/random-state evidence missing')
                    del warm,rng
                fits[task['id']]=(task,raw)
                saved_worker=json.loads((folder/'worker-result.json').read_text())
                if saved_worker['diagnostics_status']=='function_failure':
                    row.update(function_status='function_failure',function_error=json.loads((folder/'function-failure.json').read_text()))
                    rows.append(row);del q,a;continue
                destination=output/'tasks'/task['id']
                extracted=extract_functions(raw,file_hash(raw),models[task['model']],q.shape,512 if task['kernel']!='nuts' else 0,destination)
                old=folder/'diagnostics'
                exact_binary=file_hash(destination/'functions.bin')==file_hash(old/'functions.bin')
                original_values=np.fromfile(old/'functions.bin',dtype='<f8');rebuilt_values=np.fromfile(destination/'functions.bin',dtype='<f8')
                if original_values.shape!=rebuilt_values.shape:raise ValueError('Function transport shape differs')
                function_compare=dict(exact=exact_binary,passed=bool(np.allclose(original_values,rebuilt_values,atol=p['controls']['atol'],rtol=p['controls']['rtol'])),
                    maximum_absolute_difference=float(np.max(np.abs(original_values-rebuilt_values))),atol=p['controls']['atol'],rtol=p['controls']['rtol'])
                if not function_compare['passed'] or not cross_platform and not exact_binary:raise ValueError('Original function transport did not meet declared receiver comparison')
                if cross_platform:
                    # Preserve both the receiver computation and the archived
                    # Windows binary. R diagnostics consume the latter, never
                    # silently rewrite the underlying scientific arrays.
                    (destination/'functions.bin').rename(destination/'functions.receiver.bin')
                    shutil.copy2(old/'functions.bin',destination/'functions.bin')
                    atomic_json(destination/'receiver-extraction-binding.json',dict(receiver_binary='functions.receiver.bin',
                        receiver_sha256=extracted['input_sha256'],R_input='functions.bin',R_input_sha256=file_hash(destination/'functions.bin'),
                        comparison=function_compare,scientific_original_unchanged=True))
                del original_values,rebuilt_values
                estimates=json.loads((old/'estimates.json').read_text())
                means_compare=numeric_comparison(extracted['means'],estimates['means'],p['controls']['atol'],p['controls']['rtol'])
                if extracted['names']!=estimates['names'] or not means_compare['passed'] or not cross_platform and not means_compare['exact']:raise ValueError('Original estimates differ')
                atomic_json(destination/'transport.json',dict(fits=[dict(id=task['id'],input='functions.bin',shape=extracted['shape'],names=extracted['names'])],
                    scope='Read-only relocated Windows technical arrays',independent_unit='One existing four-chain technical input'))
                env=dict(os.environ,R_LIBS_USER=str(r_library))
                result=subprocess.run([str(rscript),'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(destination)],env=env,capture_output=True,text=True)
                (destination/'R.log').write_text(result.stdout+result.stderr)
                if result.returncode:raise RuntimeError('R reconstruction failed')
                post=json.loads((destination/'posterior.json').read_text());original=json.loads((old/'posterior.json').read_text())
                diagnostic_compare=numeric_comparison(post['results'],original['results'],p['controls']['atol'],p['controls']['rtol'])
                if not diagnostic_compare['passed'] or not cross_platform and not diagnostic_compare['exact']:raise ValueError('Modern diagnostics differ beyond declared receiver comparison')
                diagnostics.extend([dict(task_id=task['id'],**v) for v in post['results'][task['id']]])
                row.update(means=extracted['means'],names=extracted['names'],function_status='completed',binary_rebuilt_exact=exact_binary,diagnostics_rebuilt_exact=diagnostic_compare['exact'],
                    receiver_function_comparison=function_compare,receiver_estimate_comparison=means_compare,receiver_diagnostics_comparison=diagnostic_compare,
                    receiver_R=post['R'],original_R=original['R'],receiver_posterior=post['posterior'],original_posterior=original['posterior'],
                    R_input='Archived Windows function binary' if cross_platform else 'Exactly rebuilt function binary')
                row['reference_discrepancy']=[summarize([v],dict(kind=k,value=m,mcse=e)) for v,k,m,e in zip(row['means'],refs[task['model']]['kinds'],refs[task['model']]['means'],refs[task['model']]['mcse'])]
                del q,a
            rows.append(row)
    pairs=[]
    for model in ('G1','L1','G2'):
        for device in ('cpu','cuda'):
            for kernel,parallel in (('rwm','online_picard'),('mala','quasi_deer')):
                selected=[r for r in rows if r['task']['model']==model and r['task']['device']==device and r['task']['kernel']==kernel]
                both=all(r['outcome']=='valid' for r in selected) and len(selected)==2
                pair=dict(model=model,device=device,kernel=kernel,available=both,acceptance_mismatches=None,maximum_path_difference=None)
                if both:
                    first,second=selected
                    if first['tape_sha256']!=second['tape_sha256']:raise ValueError('Pair actual random arrays differ')
                    raw1,raw2=(fits[r['task']['id']][1] for r in selected)
                    q1,q2=(read_member(raw,'unconstrained') for raw in (raw1,raw2));a1,a2=(read_member(raw,'accept') for raw in (raw1,raw2))
                    mismatches=int(np.count_nonzero(a1!=a2));difference=float(np.max(np.abs(q1-q2)))
                    passed=bool(not mismatches and np.allclose(q1,q2,atol=p['pair_atol'],rtol=p['pair_rtol']))
                    pair.update(acceptance_mismatches=mismatches,maximum_path_difference=difference,passed=passed,tape_sha256=first['tape_sha256'])
                    del q1,q2,a1,a2
                pairs.append(pair)
    summary=dict(main_planned=27,main_counts={o:sum(r['outcome']==o for r in rows) for o in ('valid','numerical_failure','resource_failure','output_failure_unclassified','infrastructure_interruption','not_run')},
        cache_planned=24,cache_counts={o:sum(r['outcome']==o for r in cache_rows) for o in ('measurement_available','numerical_failure','resource_failure','output_failure_unclassified','infrastructure_interruption','not_run')},
        cached_calls=sum(sum(x is not None for x in r['observation']['records']) for r in cache_records.values()),
        sample_eligible_cache_tasks=sum(r['samples_eligible'] for r in cache_rows),pairs=pairs,
        function_rebuilds_available=sum(r['function_status']=='completed' for r in rows),
        exact_function_rebuilds=sum(bool(r.get('binary_rebuilt_exact')) for r in rows),diagnostic_function_rows=len(diagnostics),
        formal_repetitions=0,intervals=None,source_protocol=p['protocol_sha256'],cache_protocol=cp['protocol_sha256'],
        receiver_cross_platform_mode=cross_platform,analyzer_sha256=file_hash(__file__),
        receiver_rules='Default exact reconstruction. Explicit cross-platform mode preserves both binaries and uses frozen output atol/rtol for function/diagnostic comparisons; MH path/acceptance rules unchanged.')
    for name,data in (('SUMMARY',summary),('main',rows),('cache',cache_rows),('ownership',ownership),('costs',costs),('diagnostics',diagnostics)):
        atomic_json(output/(name+'.json'),data)
    atomic_json(output/'SHA256.json',{p.relative_to(output).as_posix():file_hash(p) for p in output.rglob('*') if p.is_file()})
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    v=s.add_parser('seal');v.add_argument('--bundle',type=Path,required=True)
    a=s.add_parser('audit');a.add_argument('--bundle',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--rscript',type=Path,required=True);a.add_argument('--r-library',type=Path,required=True);a.add_argument('--cross-platform',action='store_true')
    args=vars(p.parse_args());command=args.pop('command');print(json.dumps((seal if command=='seal' else audit)(**args)))
