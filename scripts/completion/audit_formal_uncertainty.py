"""Exercise new uncertainty/reporting contracts on frozen pilot summaries.

This reads hashed scalar estimates, not new trajectories. The pilot has four
repetitions; it must not acquire a formal-size confidence claim by bootstrap.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from formal_uncertainty import create_plan,save_plan,load_plan,analyze_function,analyze_costs

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def table(name):
    with (SOURCE/name).open(newline='') as stream:return list(csv.DictReader(stream))


def save_report(path,report):
    arrays=report.pop('bootstrap_statistics')
    if arrays:raise ValueError('Four-repeat pilot must not produce a bootstrap interval distribution')
    report['bootstrap_statistics_saved']=False
    write(path,report)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve()
    if out.exists():raise FileExistsError('Use a new companion output directory')
    manifest=json.loads((SOURCE/'manifest.json').read_text())
    files=['function-estimates.json','reference-contract.json','tasks.csv','function-errors.csv']
    source_hashes={name:sha(SOURCE/name) for name in files}
    if any(manifest.get(name)!=h for name,h in source_hashes.items()):raise ValueError('Frozen summary input changed')
    tasks=table('tasks.csv');old=table('function-errors.csv')
    estimates=json.loads((SOURCE/'function-estimates.json').read_text())
    refs=json.loads((SOURCE/'reference-contract.json').read_text())
    ids=tuple(str(i) for i in range(4));budgets=(256,1024,4096);workflows=('rwm','mala','nuts')
    index={(x['model'],x['workflow'],int(x['budget']),x['replicate']):x for x in tasks}
    if len(index)!=324 or len(tasks)!=324:raise ValueError('Unexpected pilot task identity/count')
    original={(x['model'],x['workflow'],int(x['budget']),x['function']):x for x in old}
    if len(original)!=324:raise ValueError('Unexpected pilot function group count')
    code=['scripts/completion/formal_uncertainty.py','scripts/completion/formal_error_summary.py',
          'scripts/completion/audit_formal_uncertainty.py']
    if subprocess.check_output(['git','status','--porcelain','--',*code],cwd=ROOT,text=True):
        raise ValueError('Commit analysis code before durable evidence')
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    out.mkdir(parents=True)
    summary=dict(identity='formal-uncertainty-pilot-companion-v1',source_commit=source_commit,
        input_hashes=source_hashes,input_manifest_sha256=sha(SOURCE/'manifest.json'),
        new_mcmc_fits=0,pilot_independent_repetitions=4,bootstrap_resamples=9999,
        minimum_valid_repetitions_for_bca=20,formal_sampling=False,
        workflow_function_rows=0,paired_function_rows=0,cost_workflow_rows=0,cost_pair_rows=0,
        loss_interval_status_counts=Counter(),pair_interval_status_counts=Counter(),
        legacy_eligible_point_comparisons=0,legacy_point_max_abs_difference=0.,
        unresolved_reference_rows=0,available_bca_intervals=0,resampling_plans_reloaded=0,
        saved_scalar_summary_scope='Hashes and grouped scalar reconstruction, not a new full trajectory/R audit. All four original repetitions and the failed fit are retained.',
        costs_scope='Existing recorded task wall excludes some archive/hash/terminal/R work; not a complete ordinary or audit workflow.',
        paired_scope='CPU NUTS versus CPU sequential RWM/MALA; paired repetition identity is not same transition path.')
    for model,ref in refs.items():
        folder=out/model;folder.mkdir()
        plan=create_plan('formal-uncertainty-pilot-companion-v1',model,ids)
        save_plan(plan,folder/'resampling-plan');restored=load_plan(folder/'resampling-plan')
        assert restored.sha256==plan.sha256
        summary['resampling_plans_reloaded']+=1
        pairs=[(f'nuts@{b}',f'{w}@{b}') for b in budgets for w in ('rwm','mala')]
        for j,fn in enumerate(ref['names']):
            data={}
            for w in workflows:
                for b in budgets:
                    group={}
                    for rep in ids:
                        t=index[(model,w,b,rep)]
                        group[rep]=estimates[t['id']][j] if t['function_status']=='completed' else None
                    data[f'{w}@{b}']=group
            report=analyze_function(restored,data,dict(kind=ref['kinds'][j],value=ref['means'][j],mcse=ref['mcse'][j]),pairs)
            for name,row in report['workflows'].items():
                w,b=name.split('@');prior=original[(model,w,int(b),fn)]
                summary['workflow_function_rows']+=1
                summary['loss_interval_status_counts'][row['interval_status']]+=1
                summary['available_bca_intervals']+=row['confidence_interval'] is not None
                assert row['planned']==4 and row['valid']==int(prior['valid'])
                if row['reference_eligible']:
                    previous=float(prior['conditional_squared_discrepancy'])
                    current=row['conditional_squared_discrepancy']
                    np.testing.assert_allclose(current,previous,rtol=5e-13,atol=1e-15)
                    summary['legacy_eligible_point_comparisons']+=1
                    summary['legacy_point_max_abs_difference']=max(summary['legacy_point_max_abs_difference'],abs(current-previous))
                else:
                    assert row['conditional_squared_discrepancy'] is None
                    summary['unresolved_reference_rows']+=1
            for row in report['pairs']:
                summary['paired_function_rows']+=1
                summary['pair_interval_status_counts'][row['interval_status']]+=1
                summary['available_bca_intervals']+=row['confidence_interval'] is not None
                if model=='H1' and row['workflow_b']=='mala@4096':
                    assert row['validity_table']==dict(n11=3,n10=1,n01=0,n00=0)
                    assert row['unconditional_mean_loss_difference'] is None
            report.update(model=model,function=fn)
            save_report(folder/f'function-{j}.json',report)
        costs={};states={}
        for w in workflows:
            for b in budgets:
                cost={};state={}
                for rep in ids:
                    t=index[(model,w,b,rep)]
                    if t['status'] not in ('completed','failed'):raise ValueError('Pilot task is not terminal')
                    cost[rep]=float(t['whole_task_seconds']) if t['whole_task_seconds'] else None
                    state[rep]='valid' if t['status']=='completed' else 'numerical_failure'
                costs[f'{w}@{b}']=cost;states[f'{w}@{b}']=state
        report=analyze_costs(restored,costs,states,pairs,phase='historical_recorded_task_wall')
        for row in report['workflows'].values():
            summary['cost_workflow_rows']+=1
            summary['available_bca_intervals']+=row['confidence_interval'] is not None
        summary['cost_pair_rows']+=len(report['pairs'])
        for row in report['pairs']:summary['available_bca_intervals']+=row['ratio_confidence_interval'] is not None
        if model=='H1':
            failure=report['workflows']['mala@4096']
            assert failure['outcome_counts']['numerical_failure']==1
            assert failure['unusable_output_cost_seconds']>0
            summary['preserved_failed_fit_cost_seconds']=failure['unusable_output_cost_seconds']
            summary['failed_group_total_recorded_seconds']=failure['total_recorded_seconds']
        save_report(folder/'cost.json',report)
    assert summary['available_bca_intervals']==0 and summary['unresolved_reference_rows']==9
    assert summary['legacy_eligible_point_comparisons']==315
    assert source_hashes=={name:sha(SOURCE/name) for name in files}
    write(out/'summary.json',summary)
    write(out/'manifest.json',{p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
