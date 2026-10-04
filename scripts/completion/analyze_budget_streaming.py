"""Rebuild the frozen budget pilot from raw evidence, one fit at a time.

This adapter accepts the historical pilot schema only. It cannot launch or
certify formal inference. No all-study input or trajectory cache is retained.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from analyze_budget_pilot import references
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_streaming import read_member,array_hash,extract_functions,aggregate_model
from mechanism_runner import actual_hash


def inside(root,name):
    path=root/name
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Evidence path escapes its owned directory')
    return path


def analyze(run,inputs,protocol,source,output,rscript,r_library,maximum_member_bytes=128*1024**2):
    run,inputs,output=map(lambda x:Path(x).resolve(),[run,inputs,output])
    if output.exists() or any(root==output or root in output.parents or output in root.parents for root in [run,inputs]):
        raise ValueError('Fresh separate analysis output required')
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if fingerprint(unsigned)!=digest:raise ValueError('Protocol checksum differs')
    if p['identity']!='inference-budget-pilot-mac-v1' or not p['pilot_not_formal']:
        raise ValueError('Only the archived pilot schema is accepted; formal adapter is separate')
    for name,h in p['source_files'].items():
        if file_hash(inside(ROOT,name))!=h:raise ValueError('Frozen source changed: '+name)
    original=ROOT/'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis'
    original_manifest=json.loads((original/'manifest.json').read_text())
    for name in ['tasks.csv','function-estimates.json','reference-contract.json']:
        if file_hash(original/name)!=original_manifest[name]:raise ValueError('Original companion changed: '+name)
    with (original/'tasks.csv').open(newline='') as stream:old_tasks={r['id']:r for r in csv.DictReader(stream)}
    if set(old_tasks)!={t['id'] for t in p['tasks']}:raise ValueError('Original task frame differs')
    models,refs=references(p,source)
    if refs!=json.loads((original/'reference-contract.json').read_text()):raise ValueError('Reference contract changed')
    output.mkdir(parents=True)
    atomic_json(output/'reference-contract.json',refs)
    sources=[Path(__file__),ROOT/'scripts/completion/formal_streaming.py',ROOT/'scripts/completion/formal_uncertainty.py',
             ROOT/'scripts/completion/formal_error_summary.py',ROOT/'scripts/completion/posterior_diagnostics.R']
    source_hashes={str(f.relative_to(ROOT)):file_hash(f) for f in sources}
    atomic_json(output/'analysis-identity.json',dict(protocol_sha256=digest,sources=source_hashes,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_state_manifest_sha256=file_hash(original/'tasks.csv'),maximum_member_bytes=maximum_member_bytes,
        scope='Saved pilot raw-array reanalysis, not formal inference or new MCMC',
        memory='At most one input/fit and one model of scalars; prefix comparisons retain hashes only'))
    env=dict(os.environ)
    if r_library:env['R_LIBS_USER']=str(r_library)
    summary=dict(planned=len(p['tasks']),completed=0,failed=0,function_failed=0,
        task_asset_hashes_verified=0,R_binary_roundtrips=0,scalar_estimates_exact=0,
        prefix_comparisons=0,equal_path_prefixes=0,equal_acceptance_prefixes=0,
        finite_rhat_gt_1_01_fits=0,undefined_rhat_fits=0,nuts_divergences=0,
        available_bca_intervals=0,new_MCMC_fits=0,formal_inference_complete=False,
        maximum_member_bytes=maximum_member_bytes,maximum_observed_raw_file_bytes=0,
        model_reports=[],reference_uncertainty_propagated=False,
        cost_scope='Original task wall excludes later diagnostics and parts of terminal hashing; not full ordinary/audit cost')
    # These are scalar reference values only, never trajectories or input arrays.
    old_means=json.loads((original/'function-estimates.json').read_text())
    def record_task(row):
        with (output/'tasks.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(row,allow_nan=False)+'\n')
    start=time.perf_counter()
    for item in p['targets']:
        name=item['name'];model=models[name];records=[];prior={}
        tasks=sorted([t for t in p['tasks'] if t['model']==name],key=lambda t:(t['workflow'],t['replicate'],t['budget']))
        for task in tasks:
            folder=inside(run,name+'/'+task['id']);statefile=folder/'state.json'
            if file_hash(statefile)!=old_tasks[task['id']]['state_sha256']:raise ValueError('Archived task state changed')
            state=json.loads(statefile.read_text())
            if state['task']!=task or state['protocol_sha256']!=digest:raise ValueError('Task/protocol identity differs')
            if state['status'] not in ('completed','failed'):raise ValueError('Pilot task not terminal')
            for asset,h in state['assets'].items():
                if file_hash(inside(folder,asset))!=h:raise ValueError('Task asset checksum differs: '+asset)
                summary['task_asset_hashes_verified']+=1
            row=dict(id=task['id'],model=name,workflow=task['workflow'],budget=task['budget'],
                replicate=str(task['replicate']),status=state['status'],
                outcome='valid' if state['status']=='completed' else 'numerical_failure',
                seconds=state['whole_task_seconds_including_archive'],function_status='unavailable',means=None,
                state_sha256=file_hash(statefile),raw_sha256=None,divergences=None,
                max_rhat=None,undefined_rhat=None,min_bulk_ess=None,min_tail_ess=None)
            raw=inside(folder,state['attempt']+'/fit.npz')
            if raw.exists():row['raw_sha256']=file_hash(raw)
            if state['status']=='failed':
                # The known pilot failure is a numerical output failure. This
                # adapter must not relabel future memory/interruption outcomes.
                if state['audit'].get('passed') is not False:raise ValueError('Unknown pilot failure class')
                summary['failed']+=1;records.append(row);record_task(row)
                continue
            summary['completed']+=1
            if raw.relative_to(folder).as_posix() not in state['assets']:raise ValueError('Unsealed raw payload')
            meta=json.loads(raw.with_suffix('.json').read_text())
            if state['target_id']!=model.target_id or meta['target_id']!=model.target_id or meta['status']!='completed':
                raise ValueError('Model or output identity differs')
            input_file=inside(inputs,task['input']);expected=p['master_inputs'][task['input']]
            if file_hash(input_file)!=expected['sha256']:raise ValueError('Input file changed')
            with zipfile.ZipFile(input_file) as z:input_keys=[n[:-4] for n in z.namelist() if n.endswith('.npy')]
            if set(input_keys)!={'initial','noise','log_uniform','directions','nuts_seeds'}:raise ValueError('Input roles differ')
            payload={k:read_member(input_file,k,maximum_member_bytes) for k in input_keys}
            if actual_hash(payload)!=expected['actual_sha256']:raise ValueError('Actual input arrays differ')
            rng_hash=None
            if task['workflow']=='nuts':
                initial=read_member(raw,'initial',maximum_member_bytes)
                if not np.array_equal(initial,payload['initial']) or meta['chain_seeds']!=payload['nuts_seeds'].tolist():
                    raise ValueError('NUTS initialization or actual seed list differs')
                warmup=read_member(raw,'warmup_states',maximum_member_bytes)
                if warmup.shape!=(p['chains'],p['nuts_warmup'],model.dimension):raise ValueError('Warmup shape differs')
                del initial,warmup
                rng_hash=array_hash(read_member(raw,'initial_torch_rng_states',maximum_member_bytes))
                if len(meta['worker_records'])!=p['chains']:raise ValueError('Missing NUTS worker')
                divergences=0
                for child in meta['worker_records']:
                    childfile=inside(folder,state['attempt']+'/'+child['result_directory']+'/metadata.json')
                    if childfile.relative_to(folder).as_posix() not in state['assets']:raise ValueError('Unsealed worker metadata')
                    data=json.loads(childfile.read_text())
                    divergences+=sum(len(v) for c in data['chain_records'] for v in c['diagnostics']['divergences'].values())
                row['divergences']=divergences;summary['nuts_divergences']+=divergences
                discard=0
            else:
                discard=p['mh_warmup'];total=discard+task['budget']
                tape={k:payload[k][:,:total] for k in ['noise','log_uniform','directions']}
                if actual_hash(tape)!=state['actual_tape_sha256']:raise ValueError('Actual tape prefix differs')
                if not np.array_equal(meta['config']['initial'],payload['initial']):raise ValueError('MH initial differs')
                if not meta['audit']['passed'] or any(meta['audit']['acceptance_mismatches']):raise ValueError('MH audit not passed')
                del tape
            del payload
            destination=output/'tasks'/task['id']
            lengths=[discard+b for b in p['budgets'] if b<=task['budget']]
            try:
                extracted=extract_functions(raw,row['raw_sha256'],model,
                    (p['chains'],discard+task['budget'],model.dimension),discard,destination,
                    maximum_member_bytes=maximum_member_bytes,prefix_lengths=lengths)
            except (FloatingPointError,OverflowError) as exc:
                destination.mkdir(parents=True,exist_ok=True)
                atomic_json(destination/'function-failure.json',dict(error=repr(exc)))
                row['function_status']='failed';summary['function_failed']+=1
                records.append(row);record_task(row);continue
            if extracted['names']!=refs[name]['names']:raise ValueError('Function definitions differ')
            row['means']=extracted['means'];row['function_status']='completed'
            if row['means']!=old_means[task['id']]:raise ValueError('Raw-rebuilt estimates differ from original companion')
            summary['scalar_estimates_exact']+=1
            key=(task['workflow'],task['replicate'])
            if key in prior:
                previous=prior[key];length=str(previous['length'])
                equal=previous['path']==extracted['path_prefix_sha256'][length]
                acceptance=None if task['workflow']=='nuts' else previous['accept']==extracted['acceptance_prefix_sha256'][length]
                prefix=dict(model=name,workflow=key[0],replicate=key[1],previous_budget=previous['budget'],
                    budget=task['budget'],bitwise_path_prefix_equal=equal,bitwise_acceptance_prefix_equal=acceptance,
                    initial_rng_equal=None if rng_hash is None else rng_hash==previous['rng'],
                    max_abs_difference=None,comparison_method='C-order actual array SHA256; numeric discrepancy not estimated')
                with (output/'prefix-checks.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(prefix)+'\n')
                summary['prefix_comparisons']+=1;summary['equal_path_prefixes']+=equal
                summary['equal_acceptance_prefixes']+=acceptance is True
            total=discard+task['budget']
            prior[key]=dict(path=extracted['path_prefix_sha256'][str(total)],
                accept=extracted['acceptance_prefix_sha256'].get(str(total)),rng=rng_hash,length=total,budget=task['budget'])
            transport=dict(fits=[dict(id=task['id'],input='functions.bin',shape=extracted['shape'],names=extracted['names'])],
                scope='Streaming saved budget-pilot companion',independent_unit=p['independent_unit'])
            atomic_json(destination/'transport.json',transport)
            r=subprocess.run([str(rscript),'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(destination)],
                             capture_output=True,text=True,env=env)
            (destination/'R.log').write_text(r.stdout+r.stderr,encoding='utf-8')
            if r.returncode:raise RuntimeError('R diagnostics failed; original arrays and failure log preserved')
            if file_hash(destination/'functions.bin.roundtrip')!=extracted['input_sha256']:raise ValueError('R roundtrip differs')
            post=json.loads((destination/'posterior.json').read_text())
            summary['R_binary_roundtrips']+=1;summary['R']=post['R'];summary['posterior']=post['posterior']
            stats=post['results'][task['id']]
            for key,field,op in [('max_rhat','rhat',max),('min_bulk_ess','ess_bulk',min),('min_tail_ess','ess_tail',min)]:
                vals=[x[field] for x in stats if x.get(field) is not None]
                row[key]=op(vals) if vals else None
            row['undefined_rhat']=sum(x.get('rhat') is None for x in stats)
            summary['finite_rhat_gt_1_01_fits']+=row['max_rhat'] is not None and row['max_rhat']>1.01
            summary['undefined_rhat_fits']+=row['undefined_rhat']>0
            summary['maximum_observed_raw_file_bytes']=max(summary['maximum_observed_raw_file_bytes'],raw.stat().st_size)
            records.append(row);record_task(row)
            atomic_json(destination/'task-summary.json',row)
            print(json.dumps(dict(task=task['id'],model=name,verified=sum([summary['completed'],summary['failed']]))),flush=True)
        # Only one model's small scalar frame enters uncertainty calculations.
        report=aggregate_model(records,model_name=name,replicate_ids=p['replicates'],
            workflow_names=['rwm','mala','nuts'],budgets=p['budgets'],reference=refs[name],
            namespace='formal-uncertainty-pilot-companion-v1',output=output/'models'/name,
            pairs=[('nuts','rwm'),('nuts','mala')],cost_phase='historical_recorded_task_wall')
        summary['model_reports'].append(report)
        summary['available_bca_intervals']+=report['available_bca_intervals']
        atomic_json(output/'progress.json',summary)
    summary['analysis_wall_seconds']=time.perf_counter()-start
    if sys.platform!='win32':
        import resource
        summary['process_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
        summary['largest_child_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
        summary['peak_rss_scope']='Separate process lifetime peaks, not simultaneous process-tree RSS or a Windows resource check'
    for name,h in source_hashes.items():
        if file_hash(ROOT/name)!=h:raise ValueError('Analysis source changed while running')
    atomic_json(output/'summary.json',summary)
    atomic_json(output/'manifest.json',{f.relative_to(output).as_posix():file_hash(f) for f in sorted(output.rglob('*')) if f.is_file()})
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['run','inputs','protocol','source','output','rscript','r-library']:
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    print(json.dumps(analyze(a.run,a.inputs,a.protocol,a.source,a.output,a.rscript,a.r_library),indent=2))
