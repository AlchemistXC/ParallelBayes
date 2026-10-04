"""Complete-run budget pilot reanalysis; no new sampling or formal-study claims."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'r-package/inst/python'),str(ROOT/'examples'),str(ROOT/'scripts/completion')]
from parallelbayes.reference import make_reference
from external_wells import load_wells,make_wells
from affine_target import affine_model
from inference_estimands import evaluate
from inference_error_summary import summarize_function
from mechanism_runner import sha,identity,actual_hash,write
from analyze_inference_tuning import csv_write


def references(p,source):
    old=json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())
    logistic=json.loads((ROOT/'benchmark/analysis/outputs/completion-f3/reference-reuse.json').read_text())
    qroot=ROOT/'benchmark/analysis/outputs/wells-quadrature-v1'
    quadrature=json.loads((qroot/'R12-n96.json').read_text());qmeta=json.loads((qroot/'result.json').read_text())
    models={};refs={}
    for item in p['targets']:
        name=item['name'];base=make_wells(load_wells(source)) if name=='W1' else make_reference(old['models'][name])
        if base.target_id!=item['base_target_id']:raise ValueError('Base target identity mismatch')
        model=affine_model(base,item['geometry']['center'],item['geometry']['factor']);models[name]=model
        spec=evaluate(model.spec,np.zeros((1,1,model.dimension)))
        if spec['analytic_reference'] is not None:
            means=spec['analytic_reference'];kinds=['analytic']*len(means);mcse=[0.]*len(means)
        elif name in ('L1','L2'):
            ref=logistic['models'][name]
            if ref['target_id']!=base.target_id:raise ValueError('Finite reference target differs')
            means=ref['mean'];mcse=ref['conservative_mcse']
            kinds=['finite_mcmc' if i in ref['usable_function_indices'] else 'unresolved' for i in range(len(means))]
        elif name=='W1':
            if qmeta['target_id']!=base.target_id or qmeta['functions']!=spec['names']:
                raise ValueError('Quadrature reference target/functions differ')
            means=quadrature['means'];kinds=['numerical_uncertified']*len(means);mcse=[None]*len(means)
        else:raise ValueError('Missing reference contract')
        refs[name]=dict(names=spec['names'],means=means,kinds=kinds,mcse=mcse,base_target_id=base.target_id)
    return models,refs


def analyze(run,inputs,protocol,source,output,rscript):
    run,inputs,output=Path(run).resolve(),Path(inputs).resolve(),Path(output).resolve()
    if output.exists() or run in output.parents or inputs in output.parents:raise ValueError('Fresh separate analysis output required')
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if identity(unsigned)!=digest:raise ValueError('Protocol identity differs')
    for name,h in p['source_files'].items():
        if sha(ROOT/name)!=h:raise ValueError('Frozen source changed: '+name)
    saved_summary=json.loads((run/'summary.json').read_text())
    if saved_summary['terminal']!=len(p['tasks']) or saved_summary['protocol_sha256']!=digest:
        raise ValueError('Only analyze the complete fixed task list with this entry')
    payloads={}
    for name,record in p['master_inputs'].items():
        if sha(inputs/name)!=record['sha256']:raise ValueError('Input file differs')
        with np.load(inputs/name,allow_pickle=False) as z:payload={k:z[k].copy() for k in z.files}
        if actual_hash(payload)!=record['actual_sha256']:raise ValueError('Actual input identity differs')
        payloads[name]=payload
    models,refs=references(p,source);output.mkdir(parents=True)
    rows=[];transports=[];asset_count=0;means={};prefixes={};prefix_rows=[]
    for task in p['tasks']:
        folder=run/task['model']/task['id'];statefile=folder/'state.json';state=json.loads(statefile.read_text())
        if state['task']!=task or state['protocol_sha256']!=digest:raise ValueError('Task identity differs')
        for name,h in state['assets'].items():
            if sha(folder/name)!=h:raise ValueError('Terminal asset checksum differs')
            asset_count+=1
        row=dict(id=task['id'],model=task['model'],workflow=task['workflow'],replicate=task['replicate'],budget=task['budget'],
            status=state['status'],function_status='unavailable',whole_task_seconds=state['whole_task_seconds_including_archive'],
            sampling_or_pool_seconds=None,independent_audit_seconds=None,observed_workers=state.get('observed_worker_count'),
            retained_acceptance_rate=None,divergences=None,max_rhat=None,min_bulk_ess=None,min_tail_ess=None,undefined_rhat=None,
            raw_sha256=None,state_sha256=sha(statefile))
        raw=folder/state['attempt']/'fit.npz';metadata=raw.with_suffix('.json')
        if raw.exists():row['raw_sha256']=sha(raw)
        if state['status']!='completed':
            rows.append(row);continue
        meta=json.loads(metadata.read_text());model=models[task['model']];payload=payloads[task['input']]
        if state['target_id']!=model.target_id or meta['target_id']!=model.target_id or meta['status']!='completed':
            raise ValueError('Completed model/output identity differs')
        with np.load(raw,allow_pickle=False) as z:
            if task['workflow']=='nuts':
                draws=z['draws'].copy();q=z['unconstrained'].copy();rng=z['initial_torch_rng_states'].copy()
                if not np.array_equal(z['initial'],payload['initial']) or meta['chain_seeds']!=payload['nuts_seeds'].tolist():
                    raise ValueError('NUTS initial state or seeds differ')
                if z['warmup_states'].shape!=(p['chains'],p['nuts_warmup'],model.dimension):raise ValueError('NUTS warmup shape differs')
                if len(meta['worker_records'])!=p['chains']:raise ValueError('Missing NUTS child')
                divergences=0
                for child in meta['worker_records']:
                    cmeta=json.loads((folder/state['attempt']/child['result_directory']/'metadata.json').read_text())
                    divergences+=sum(len(v) for c in cmeta['chain_records'] for v in c['diagnostics']['divergences'].values())
                row.update(divergences=divergences,sampling_or_pool_seconds=state['pool_wall_seconds'])
                prefix=q.copy();accept=None
            else:
                if not meta['audit']['passed'] or any(meta['audit']['acceptance_mismatches']):raise ValueError('MH audit missing')
                discard=p['mh_warmup'];total=discard+task['budget']
                tape={k:payload[k][:,:total] for k in ['noise','log_uniform','directions']}
                if actual_hash(tape)!=state['actual_tape_sha256']:raise ValueError('MH actual prefix differs')
                if not np.array_equal(meta['config']['initial'],payload['initial']):raise ValueError('MH initial state differs')
                if z['draws'].shape!=(p['chains'],total,model.dimension):raise ValueError('MH stored shape differs')
                draws=z['draws'][:,discard:].copy();q=z['unconstrained'][:,discard:].copy();rng=None
                prefix=z['unconstrained'].copy();accept=z['accept'].copy()
                row.update(retained_acceptance_rate=float(accept[:,discard:].mean()),
                    sampling_or_pool_seconds=meta['timing']['sample'],independent_audit_seconds=meta['timing']['audit'])
            if draws.shape!=(p['chains'],task['budget'],model.dimension) or not np.isfinite(draws).all() or not np.isfinite(q).all():
                raise ValueError('Completed retained shape/finiteness differs')
            np.testing.assert_allclose(draws,model.constrain(q),rtol=1e-10,atol=1e-12)
        key=(task['model'],task['workflow'],task['replicate'])
        if key in prefixes:
            prior=prefixes[key];short=prefix[:,:prior['path'].shape[1]]
            record=dict(model=key[0],workflow=key[1],replicate=key[2],previous_budget=prior['budget'],budget=task['budget'],
                bitwise_path_prefix_equal=bool(np.array_equal(short,prior['path'])),max_abs_prefix_difference=float(np.max(abs(short-prior['path']))),
                acceptance_prefix_mismatches=None,rng_initial_equal=None)
            if accept is not None:record['acceptance_prefix_mismatches']=int(np.sum(accept[:,:prior['accept'].shape[1]]!=prior['accept']))
            if rng is not None:record['rng_initial_equal']=bool(np.array_equal(rng,prior['rng']))
            prefix_rows.append(record)
        prefixes[key]=dict(path=prefix,accept=accept,rng=rng,budget=task['budget'])
        try:
            values=evaluate(model.spec,draws)
            if values['names']!=refs[task['model']]['names']:raise ValueError('Function identity differs')
            means[task['id']]=values['values'].mean(axis=(0,1)).tolist()
            a=values['values'].transpose(1,0,2);binary=task['id']+'.bin'
            np.asarray(a,dtype='<f8').ravel(order='F').tofile(output/binary)
            transports.append(dict(id=task['id'],input=binary,shape=list(a.shape),names=values['names'],input_sha256=sha(output/binary),source_raw_sha256=row['raw_sha256']))
            row['function_status']='completed'
        except (FloatingPointError,OverflowError) as exc:
            row['function_status']='failed';write(output/(task['id']+'-function-failure.json'),dict(error=str(exc)))
        rows.append(row)
    write(output/'reference-contract.json',refs)
    write(output/'function-estimates.json',means)
    write(output/'prefix-checks.json',prefix_rows)
    write(output/'transport.json',dict(fits=transports,
        scope='Independent budget pilot companion diagnostics; no adaptation of frozen tasks or formal inference certification.',
        independent_unit=p['independent_unit']))
    start=time.perf_counter();process=subprocess.run([str(rscript),'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(output)],text=True,capture_output=True)
    elapsed=time.perf_counter()-start;(output/'R.log').write_text(process.stdout+process.stderr)
    if process.returncode:raise RuntimeError('R diagnostics failed; preserve log')
    diagnostic=json.loads((output/'posterior.json').read_text())
    for fit in transports:
        if sha(output/(fit['input']+'.roundtrip'))!=fit['input_sha256']:raise ValueError('R binary roundtrip differs')
    for row in rows:
        if row['function_status']!='completed':continue
        stats=diagnostic['results'][row['id']]
        for key,column,op in [('max_rhat','rhat',max),('min_bulk_ess','ess_bulk',min),('min_tail_ess','ess_tail',min)]:
            a=[s[column] for s in stats if s.get(column) is not None and np.isfinite(s[column])];row[key]=op(a) if a else None
        row['undefined_rhat']=sum(s.get('rhat') is None for s in stats)
    functions=[];groups=[]
    for item in p['targets']:
        for workflow in ['rwm','mala','nuts']:
            for budget in p['budgets']:
                group=[r for r in rows if r['model']==item['name'] and r['workflow']==workflow and r['budget']==budget]
                if {r['replicate'] for r in group}!=set(p['replicates']) or len(group)!=len(p['replicates']):raise ValueError('Planned repetition set differs')
                ref=refs[item['name']];errors=[]
                for index,name in enumerate(ref['names']):
                    estimates=[means[r['id']][index] if r['id'] in means else None for r in group]
                    report=summarize_function(estimates,ref['means'][index],ref['kinds'][index],ref['mcse'][index])
                    record=dict(model=item['name'],workflow=workflow,budget=budget,function=name,**report)
                    functions.append(record);errors.append(report)
                finite=[e['conditional_squared_discrepancy'] for e in errors if e['conditional_squared_discrepancy'] is not None]
                groups.append(dict(model=item['name'],workflow=workflow,budget=budget,planned=len(group),
                    completed=sum(r['status']=='completed' for r in group),failed=sum(r['status']!='completed' for r in group),
                    estimand_failed=sum(r['status']=='completed' and r['function_status']!='completed' for r in group),
                    median_whole_task_seconds=float(np.median([r['whole_task_seconds'] for r in group])),
                    conditional_max_squared_discrepancy=max(finite) if finite else None,
                    unresolved_reference_functions=sum(k=='unresolved' for k in ref['kinds']),
                    numerical_uncertified_reference_functions=sum(k=='numerical_uncertified' for k in ref['kinds']),
                    runs_with_finite_rhat_gt_1_01=sum(r['max_rhat'] is not None and r['max_rhat']>1.01 for r in group),
                    runs_with_undefined_rhat=sum(r['undefined_rhat'] is not None and r['undefined_rhat']>0 for r in group),
                    max_finite_rhat=max([r['max_rhat'] for r in group if r['max_rhat'] is not None],default=None),
                    min_bulk_ess=min([r['min_bulk_ess'] for r in group if r['min_bulk_ess'] is not None],default=None),
                    divergences=sum(r['divergences'] or 0 for r in group) if workflow=='nuts' else None))
    csv_write(output/'tasks.csv',rows);csv_write(output/'groups.csv',groups);csv_write(output/'function-errors.csv',functions)
    summary=dict(planned=len(rows),completed=sum(r['status']=='completed' for r in rows),failed=sum(r['status']!='completed' for r in rows),
        task_asset_hashes_verified=asset_count,binary_roundtrips_verified=len(transports),groups=len(groups),
        runs_some_finite_rhat_gt_1_01=sum(r['max_rhat'] is not None and r['max_rhat']>1.01 for r in rows),
        runs_some_undefined_rhat=sum(r['undefined_rhat'] is not None and r['undefined_rhat']>0 for r in rows),
        nuts_divergences=sum(r['divergences'] or 0 for r in rows),NUTS_runs_with_divergences=sum(bool(r['divergences']) for r in rows),
        prefix_comparisons=len(prefix_rows),bitwise_equal_prefix_comparisons=sum(r['bitwise_path_prefix_equal'] for r in prefix_rows),
        R=diagnostic['R'],posterior=diagnostic['posterior'],R_process_seconds=elapsed,
        original_protocol_sha256=digest,original_source_commit=p['source_commit'],source_run_summary_sha256=sha(run/'summary.json'),
        analysis_sources={str(f.relative_to(ROOT)):sha(f) for f in [Path(__file__),ROOT/'scripts/completion/inference_error_summary.py',ROOT/'scripts/completion/posterior_diagnostics.R',ROOT/'scripts/completion/analyze_inference_tuning.py']},
        independent_unit=p['independent_unit'],formal_inference_complete=False,
        limitations='Four independent pilot repetitions. Squared discrepancy to finite/numerical references includes their uncertainty; two-MCSE shifts are sensitivity only. Failed fits remain in the planned denominator. No speed ranking, certified convergence or precise time-to-accuracy.')
    write(output/'summary.json',summary)
    write(output/'manifest.json',{f.name:sha(f) for f in sorted(output.iterdir()) if f.is_file()})
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['run','inputs','protocol','source','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--rscript',required=True);a=parser.parse_args()
    print(json.dumps(analyze(a.run,a.inputs,a.protocol,a.source,a.output,a.rscript),indent=2))
