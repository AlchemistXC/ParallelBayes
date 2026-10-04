"""Rebuild frozen MH tuning scores from arrays and diagnose all valid candidates.

No fresh MCMC, no modification of candidate choice using post hoc diagnostics.
The historical estimand functions are evaluated on original model outputs.
"""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'r-package/inst/python'),str(ROOT/'examples'),str(ROOT/'scripts/completion')]
from parallelbayes.reference import make_reference
from affine_target import affine_model
from external_wells import load_wells,make_wells
from inference_estimands import evaluate
from inference_tuning_stats import select_candidate
from mechanism_runner import identity,sha,actual_hash,write


def csv_write(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def analyze(run,inputs,protocol,source,output,rscript):
    run,inputs,output=Path(run).resolve(),Path(inputs).resolve(),Path(output).resolve()
    if output.exists() or run in output.parents or inputs in output.parents:
        raise ValueError('Analysis requires a new directory outside frozen evidence')
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if identity(unsigned)!=digest:raise ValueError('Protocol identity mismatch')
    for name,h in p['source_files'].items():
        if sha(ROOT/name)!=h:raise ValueError('Frozen source mismatch: '+name)
    for name,row in p['master_inputs'].items():
        if sha(inputs/name)!=row['sha256']:raise ValueError('Input file mismatch')
        with np.load(inputs/name,allow_pickle=False) as z:
            if actual_hash(dict(z))!=row['actual_sha256']:raise ValueError('Actual input arrays differ')
    saved_summary=json.loads((run/'summary.json').read_text())
    if saved_summary['protocol_sha256']!=digest:raise ValueError('Summary protocol mismatch')
    old=json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())
    models={};setup_seconds=0.
    for item in p['targets']:
        name=item['name'];setup=json.loads((run/name/'setup.json').read_text())
        unsigned=dict(setup);sh=unsigned.pop('setup_sha256')
        if identity(unsigned)!=sh or setup['protocol_sha256']!=digest:raise ValueError('Geometry identity mismatch')
        base=make_wells(load_wells(source)) if name=='W1' else make_reference(old['models'][name])
        if base.target_id!=setup['base_target_id']:raise ValueError('Base target mismatch')
        g=setup['geometry'];model=affine_model(base,g['center'],g['factor'])
        models[name]=(model,sh);setup_seconds+=setup['initial_setup_seconds']
    output.mkdir(parents=True)
    rows=[];transports=[];max_score_difference=0.;checked_assets=0
    for case in p['cases']:
        folder=run/case['model']/case['id'];statefile=folder/'state.json'
        state=json.loads(statefile.read_text());model,sh=models[case['model']]
        if state['case']!=case or state['protocol_sha256']!=digest or state['setup_sha256']!=sh:
            raise ValueError('Case state identity mismatch')
        if state['target_id']!=model.target_id:raise ValueError('Coordinate target mismatch')
        for name,h in state['assets'].items():
            if sha(folder/name)!=h:raise ValueError('Task asset changed')
            checked_assets+=1
        if state['status'] not in ('completed','failed'):raise ValueError('Nonterminal task')
        with np.load(inputs/case['input'],allow_pickle=False) as z:payload={k:z[k].copy() for k in z.files}
        initial=payload.pop('initial')
        if actual_hash(payload)!=state['actual_tape_sha256']:raise ValueError('Tape identity mismatch')
        attempt=folder/state['attempt'];meta=json.loads((attempt/'fit.json').read_text())
        config=meta['config']
        for key,value in [('kernel',case['kernel']),('executor','sequential'),('step_size',case['step']),
                          ('draws',p['warmup']+p['retained']),('chains',p['chains'])]:
            if config[key]!=value:raise ValueError('Recorded numerical configuration differs')
        if not np.array_equal(config['initial'],initial):raise ValueError('Initial state mismatch')
        row=dict(id=case['id'],model=case['model'],kernel=case['kernel'],multiplier=case['multiplier'],
            step=case['step'],replicate=case['replicate'],status=state['status'],selected=False,
            score=None,acceptance_rate=None,retained_transitions=p['chains']*p['retained'],
            max_rhat=None,min_bulk_ess=None,min_tail_ess=None,undefined_rhat=None,
            whole_case_seconds=state['wall_seconds_including_archive'],
            sample_seconds_including_discarded_phase=meta['timing']['sample'],
            independent_audit_seconds=meta['timing']['audit'],
            raw_sha256=sha(attempt/'fit.npz'),state_sha256=sha(statefile))
        with np.load(attempt/'fit.npz',allow_pickle=False) as z:
            if state['status']=='completed':
                if not meta['audit']['passed'] or any(meta['audit']['acceptance_mismatches']):
                    raise ValueError('Completed task lacks fixed-path audit')
                path=z['unconstrained'];draws=z['draws'];accept=z['accept']
                shape=(p['chains'],p['warmup']+p['retained'],model.dimension)
                if path.shape!=shape or draws.shape!=shape or accept.shape!=shape[:2]:raise ValueError('Shape differs')
                if not np.isfinite(path).all() or not np.isfinite(draws).all():raise ValueError('Nonfinite valid trajectory')
                previous=np.concatenate((initial[:,None,:],path[:,:-1,:]),axis=1)
                if not np.array_equal(path[~accept],previous[~accept]):raise ValueError('Rejection self-transition changed')
                np.testing.assert_allclose(draws,model.constrain(path),rtol=1e-10,atol=1e-12)
                # Direct independent array reconstruction; not the sampling-time score function.
                delta=path[:,p['warmup']:,:]-previous[:,p['warmup']:,:]
                squared=np.sum(delta*delta,axis=2)/model.dimension
                score=float(np.mean(squared));chain_scores=np.mean(squared,axis=1)
                scored=json.loads((attempt/'score.json').read_text())
                np.testing.assert_allclose(score,scored['mean_squared_jump_per_dimension'],rtol=1e-12,atol=1e-15)
                np.testing.assert_allclose(chain_scores,scored['chain_scores'],rtol=1e-12,atol=1e-15)
                np.testing.assert_allclose(score,state['score'],rtol=1e-12,atol=1e-15)
                rate=float(accept[:,p['warmup']:].mean())
                if rate!=state['acceptance_rate'] or rate!=scored['acceptance_rate']:raise ValueError('Acceptance rate changed')
                if scored['transitions']!=row['retained_transitions']:raise ValueError('Scored transition count changed')
                max_score_difference=max(max_score_difference,abs(score-state['score']))
                row.update(score=score,acceptance_rate=rate)
                functions=evaluate(model.spec,draws[:,p['warmup']:,:])
                values=functions['values'].transpose(1,0,2)
                binary=case['id']+'.bin';np.asarray(values,dtype='<f8').ravel(order='F').tofile(output/binary)
                transports.append(dict(id=case['id'],input=binary,shape=list(values.shape),names=functions['names'],
                    input_sha256=sha(output/binary),source_raw_sha256=row['raw_sha256'],
                    discarded_draws_per_chain=p['warmup'],parameter_scope=functions['parameter_scope']))
            else:
                if 'draws' in z or 'unconstrained' in z or state['score'] is not None:
                    raise ValueError('Failed output was promoted to ordinary samples or score')
        rows.append(row)
    selections=[];selection_rows=[]
    for item in p['targets']:
        for kernel in ('rwm','mala'):
            group=[r for r in rows if r['model']==item['name'] and r['kernel']==kernel]
            steps=sorted(set(r['step'] for r in group))
            selection=select_candidate(group,steps,p['replicates'])
            original=next(s for s in saved_summary['selections'] if s['model']==item['name'] and s['kernel']==kernel)
            if selection['selected_step']!=original['selected_step']:raise ValueError('Selected candidate changed')
            if [x['eligible'] for x in selection['candidates']]!=[x['eligible'] for x in original['candidates']]:
                raise ValueError('Candidate eligibility changed')
            selected=[r for r in group if r['step']==selection['selected_step']]
            for row in selected:row['selected']=True
            selection.update(model=item['name'],kernel=kernel,
                grid_boundary=selection['selected_step'] in (steps[0],steps[-1]))
            selections.append(selection)
            scores=[r['score'] for r in selected if r['score'] is not None]
            selection_rows.append(dict(model=item['name'],kernel=kernel,step=selection['selected_step'],
                multiplier=selected[0]['multiplier'] if selected else None,grid_boundary=selection['grid_boundary'],
                development_repetitions=len(selected),mean_score=float(np.mean(scores)) if scores else None,
                min_rep_score=min(scores) if scores else None,max_rep_score=max(scores) if scores else None,
                max_rhat=None,min_bulk_ess=None,min_tail_ess=None,undefined_rhat=None,
                mean_acceptance=float(np.mean([r['acceptance_rate'] for r in selected])) if selected else None,
                all_candidates_seconds=sum(r['whole_case_seconds'] for r in group)))
    scope='Post hoc diagnostics for every valid tuning candidate, using historical estimands. No change to frozen selection; no formal accuracy or convergence claim.'
    unit='Two independent four-chain development runs per candidate. Within each repetition, candidates and kernels share actual inputs. Chains, draws, and candidate settings do not add independent repetitions.'
    write(output/'transport.json',dict(fits=transports,failed_ids=[r['id'] for r in rows if r['status']=='failed'],scope=scope,independent_unit=unit))
    start=time.perf_counter()
    process=subprocess.run([str(rscript),'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(output)],text=True,capture_output=True)
    r_wall=time.perf_counter()-start;(output/'R.log').write_text(process.stdout+process.stderr)
    if process.returncode:raise RuntimeError('R diagnostics failed; inspect preserved R.log')
    diagnostics=json.loads((output/'posterior.json').read_text())
    for fit in transports:
        if sha(output/(fit['input']+'.roundtrip'))!=fit['input_sha256']:raise ValueError('Binary R roundtrip differs')
    for row in rows:
        if row['status']!='completed':continue
        stats=diagnostics['results'][row['id']]
        for key,field,op in [('max_rhat','rhat',max),('min_bulk_ess','ess_bulk',min),('min_tail_ess','ess_tail',min)]:
            values=[s[field] for s in stats if s.get(field) is not None and np.isfinite(s[field])]
            row[key]=op(values) if values else None
        row['undefined_rhat']=sum(s.get('rhat') is None for s in stats)
    for selected in selection_rows:
        pair=[r for r in rows if r['model']==selected['model'] and r['kernel']==selected['kernel'] and r['selected']]
        for key,op in [('max_rhat',max),('min_bulk_ess',min),('min_tail_ess',min)]:
            values=[r[key] for r in pair if r[key] is not None];selected[key]=op(values) if values else None
        selected['undefined_rhat']=sum(r['undefined_rhat'] or 0 for r in pair)
    csv_write(output/'all-candidates.csv',rows);csv_write(output/'selected-candidates.csv',selection_rows)
    write(output/'selections.json',dict(selections=selections,scope=p['scope'],original_protocol_sha256=digest))
    summary=dict(planned=len(p['cases']),completed=len(transports),failed=sum(r['status']=='failed' for r in rows),
        task_asset_hashes_verified=checked_assets,scores_reconstructed=len(transports),
        max_abs_score_reconstruction_difference=max_score_difference,binary_roundtrips_verified=len(transports),
        selected_target_kernel_groups=len(selection_rows),grid_boundary_groups=[dict(model=r['model'],kernel=r['kernel']) for r in selection_rows if r['grid_boundary']],
        valid_fits_some_finite_rhat_gt_1_01=sum(r['max_rhat'] is not None and r['max_rhat']>1.01 for r in rows),
        valid_fits_some_undefined_rhat=sum(r['undefined_rhat'] is not None and r['undefined_rhat']>0 for r in rows),
        selected_groups_some_finite_rhat_gt_1_01=sum(r['max_rhat'] is not None and r['max_rhat']>1.01 for r in selection_rows),
        selected_groups_some_undefined_rhat=sum(r['undefined_rhat'] is not None and r['undefined_rhat']>0 for r in selection_rows),
        setup_seconds=setup_seconds,all_case_seconds=sum(r['whole_case_seconds'] for r in rows),
        failed_case_seconds=sum(r['whole_case_seconds'] for r in rows if r['status']=='failed'),
        companion_R_process_seconds=r_wall,R=diagnostics['R'],posterior=diagnostics['posterior'],
        original_protocol_sha256=digest,original_source_commit=p['source_commit'],
        source_run_summary_sha256=sha(run/'summary.json'),
        analysis_sources={str(f.relative_to(ROOT)):sha(f) for f in [Path(__file__),ROOT/'scripts/completion/posterior_diagnostics.R',ROOT/'scripts/completion/inference_estimands.py']},
        scope=scope,independent_unit=unit,formal_inference_complete=False)
    if (summary['completed'],summary['failed'])!=(saved_summary['completed'],saved_summary['failed']):raise ValueError('Task counts differ')
    write(output/'summary.json',summary)
    write(output/'manifest.json',{f.name:sha(f) for f in sorted(output.iterdir()) if f.is_file()})
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['run','inputs','protocol','source','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--rscript',required=True);a=parser.parse_args()
    print(json.dumps(analyze(a.run,a.inputs,a.protocol,a.source,a.output,a.rscript),indent=2))
