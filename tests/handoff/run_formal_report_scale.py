"""Full approved scalar shape, explicitly artificial; NEVER invokes a sampler.

This is a companion scale check, not part of the fast pytest suite. It uses
original task identities/reference names but invented scalar values/times.
Neither its protocol-shaped dictionaries nor its plots authorize execution.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import shutil
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'scripts/completion')]
from formal_study_plan import create_study_plan,MODELS,BUDGETS
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_outcomes import summarize_attempts
from formal_cost_policy import summarize_task_costs
from formal_statistics import summarize_model
from formal_report import StatisticsBundle,build
from formal_analyze import output_inventory


def peak_rss():
    try:
        import resource
        value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform=='darwin' else 1024*value)
    except ImportError:return None


def artificial_main(task,reference):
    rep=task['replicate'];kernel=task['kernel'];executor=task['executor'];budget=task['budget']
    outcome=('numerical_failure' if rep==0 and executor!='sequential' and kernel!='nuts' else
             'resource_failure' if rep==7 and kernel=='nuts' else 'valid')
    missing_function=rep==1 and executor=='sequential'
    aid=task['id']+'-artificial-attempt';seconds=(budget/256)*(1+rep/256)*(1.2 if kernel=='nuts' else 1.)
    if task['device']=='cuda':seconds*=.45
    if executor in ('online_picard','quasi_deer'):seconds*=.8 if executor=='online_picard' else 2.
    ordinary=None if rep==2 and task['device']=='cuda' and executor=='sequential' else seconds
    if rep==9 and executor=='sequential' and task['device']=='cpu':ordinary=0.
    attempt=dict(attempt_id=aid,binding_sha256=fingerprint(task),outcome=outcome,seconds=seconds+1.)
    history=dict(task=task,original=aid,attempts=[attempt],summary=summarize_attempts([attempt]))
    call=dict(index=0,action='run',finished=True,seconds=seconds+1.,error=None,
        result=dict(task=task,attempt_id=aid,newly_executed=True))
    cost=summarize_task_costs(history,dict(task=task,original=aid),[call],{aid:ordinary})
    means=diagnostics=None
    if outcome=='valid' and not missing_function:
        means=[];diagnostics=[]
        for j,name in enumerate(reference['names']):
            constant=(task['model']=='L2' and name=='q1_positive') or (task['model']=='M1' and name=='q1_positive')
            value=0. if constant else reference['means'][j]+.02*math.sin((rep+1)*(j+1))*math.sqrt(256/budget)*(1.2 if kernel=='nuts' else 1.)
            if any(x in name for x in ('positive','gt1','sigmoid','p_switch')):value=max(0.,min(1.,value))
            means.append(value)
            diagnostics.append(dict(variable=name,mean=value,sd=0. if constant else 1.,
                rhat=None if constant else 1.+rep/10000,ess_bulk=None if constant else budget/2,
                ess_tail=None if constant else budget/4,mcse_mean=None if constant else 1/math.sqrt(budget)))
    row=dict(task=task,phase='main',disposition='analyzed',outcome=outcome,means=means,
        names=reference['names'] if means is not None else None,diagnostics=diagnostics,
        function_status='completed' if means is not None else 'failed' if outcome=='valid' else 'unavailable',
        costs=cost,cache=None)
    if kernel=='nuts' and outcome=='valid':
        row['nuts']=dict(chain_diagnostics=[dict(chain=i,records=[dict(diagnostics=dict(divergences={'chain 0':[0] if rep%8==0 and i==0 else []}))],
            tree_depth_hit_count=None,tree_depth_note='artificial missing observation',max_tree_depth=8) for i in range(4)])
    return row


def artificial_cache(probe,primary,protocol_hash,reference,first_selected,dimension):
    task=dict(primary,id=probe['id'],protocol_sha256=protocol_hash,artifact_kind='cache_measurement')
    config=dict(kernel=probe['kernel'],executor=probe['executor'],device=probe['device'],chains=4,
        draws=probe['budget']+512,step_size=.1,initial=[[0.]*dimension for _ in range(4)],atol=1e-10,rtol=1e-10,
        window=32,max_iter=2048,audit=False,on_failure='error')
    binding=dict(input_file_sha256=fingerprint(['artificial-input',probe['model'],probe['replicate']]),
        tape_sha256=fingerprint(['artificial-tape',probe['model'],probe['replicate'],probe['budget']]),
        target_id=reference['base_target_id'],config=config)
    median=(probe['budget']/256)*(1.+probe['replicate']/128)
    if probe['device']=='cuda':median*=.5
    if probe['executor']=='online_picard':median*=.7
    if probe['executor']=='quasi_deer':median*=2.
    records=[dict(execution_index=i,has_prior_execution=i>0,status='candidate',samples_eligible=False,
        technical_output_valid=True,executor_wall_seconds=seconds,tape_sha256=binding['tape_sha256'],
        target_id=binding['target_id'],config=copy.deepcopy(config)) for i,seconds in enumerate([median+1.,median*.9,median,median*1.1])]
    states=['valid']*4;outcome='measurement_available'
    if probe['replicate']==first_selected and probe['executor']!='sequential':
        records[0].update(status='failed',technical_output_valid=False);states[0]='numerical_failure';outcome='numerical_failure'
    return dict(task=task,phase='cache',disposition='analyzed',outcome=outcome,means=None,names=None,
        function_status='unavailable',diagnostics=None,costs=None,
        cache=dict(binding=binding,observation=dict(records=records,execution_outcomes=states)))


def run(output):
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('Fresh artificial scale directory required')
    if shutil.disk_usage(output.parent).free<2*1024**3:raise RuntimeError('At least 2 GiB free required for artificial output')
    output.mkdir();start=time.perf_counter()
    identity='windows-formal-artificial-report-scale-v1'
    catalog=json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    plan=create_study_plan(identity,catalog)
    reference_path=ROOT/'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis/reference-contract.json'
    refs=json.loads(reference_path.read_text());protocol=dict(identity=identity,scope_kind='formal_inference',
        protocol_sha256=fingerprint(['artificial-scalars-not-a-protocol',identity]),tasks=plan['tasks'])
    statistics=output/'statistics';statistics.mkdir();reports=[];timings=[]
    for name in MODELS:
        began=time.perf_counter();primary={t['id']:t for t in plan['tasks'] if t['model']==name}
        probes=[p for p in plan['cache_allocation']['probes'] if p['model']==name]
        selected=sorted({p['replicate'] for p in probes})
        rows=[artificial_main(dict(t,protocol_sha256=protocol['protocol_sha256'],artifact_kind='posterior'),refs[name]) for t in primary.values()]
        rows.extend(artificial_cache(p,primary[p['primary_task_id']],protocol['protocol_sha256'],refs[name],selected[0],next(t['dimension'] for t in plan['targets'] if t['name']==name)) for p in probes)
        report=summarize_model(rows,refs[name],name=name,protocol=protocol,allocation=plan['cache_allocation'],output=statistics/name)
        reports.append(report);timings.append(dict(model=name,seconds=time.perf_counter()-began,process_peak_rss_bytes=peak_rss()))
        print(json.dumps(dict(phase='artificial-statistics',**timings[-1])),flush=True)
        del rows
    frame=dict(identity=identity,scope='formal_inference',protocol_sha256=protocol['protocol_sha256'],
        main_planned=41472,cache_planned=9216,formal_scientific_repetitions_per_model=128,analysis_can_authorize_sampling=False)
    atomic_json(statistics/'SUMMARY.json',dict(frame=frame,models=reports,artificial_data=True,
        formal_inference_complete=False,new_independent_repetitions=0))
    atomic_json(statistics/'reference-contract.json',refs)
    atomic_json(statistics/'SHA256.json',output_inventory(statistics));digest=file_hash(statistics/'SHA256.json')
    try:StatisticsBundle(statistics,digest)
    except ValueError as exc:
        if 'Artificial statistics require --fixture' not in str(exc):raise
    else:raise AssertionError('Artificial source was not guarded')
    source=StatisticsBundle(statistics,digest,fixture=True)
    assert source.full_formal_frame
    for name in MODELS:source.model(name)
    original_read=source.read;bad=copy.deepcopy(original_read('G1/task-frame.json'));bad[0]['task']['id']='a'*24
    with patch.object(source,'read',side_effect=lambda n:bad if n=='G1/task-frame.json' else original_read(n)):
        try:source.model('G1')
        except ValueError as exc:
            if 'Formal task identities differ' not in str(exc):raise
        else:raise AssertionError('Fixture label waived full task identity')
    report_start=time.perf_counter();result=build(statistics,digest,output/'report',fixture=True,render=True)
    assert result['fixture'] and not result['scientific_results'] and result['new_sampler_calls']==0
    assert len(result['source_models'])==9 and len(result['figures'])==45
    assert sum(f['panels'] for f in result['figures'])==99
    for model in result['source_models']:
        tables=json.loads((output/'report'/model['model']/'tables.json').read_text())
        assert sum(r['planned'] for r in tables['tasks'] if r['phase']=='main')==4608
        assert sum(r['planned'] for r in tables['tasks'] if r['phase']=='cache')==1024
        assert any(r['outcomes'].get('numerical_failure',0) for r in tables['tasks'])
        assert all(r['complete_tree_depth_hits'] is None for r in tables['nuts'])
    l2=json.loads((output/'report/L2/tables.json').read_text())
    assert all(r['point'] is None and not r['plot_point'] for r in l2['errors'] if r['function']=='q1_positive')
    receipt=dict(artificial_data=True,source_commit=__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in [Path(__file__),ROOT/'scripts/analysis/formal_statistics.py',ROOT/'scripts/analysis/formal_report.py',ROOT/'scripts/analysis/formal_plots.py',ROOT/'scripts/analysis/formal_report_text.py']},
        reference_contract_sha256=file_hash(reference_path),statistics_manifest_sha256=digest,report_manifest_sha256=file_hash(output/'report/SHA256.json'),
        main_slots=41472,cache_slots=9216,models=9,functions=sum(len(r['names']) for r in refs.values()),figures=45,panels=99,
        per_model=timings,report_seconds=time.perf_counter()-report_start,total_seconds=time.perf_counter()-start,
        process_peak_rss_bytes=peak_rss(),output_bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
        false_scientific_promotion_rejected=True,wrong_full_frame_task_rejected=True,new_sampler_calls=0,new_formal_repetitions=0,
        scope='Invented scalar pipeline stress check, not native runtime/raw-array reconstruction or scientific results')
    atomic_json(output/'RECEIPT.json',receipt);print(json.dumps(receipt,indent=2),flush=True)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
