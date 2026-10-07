"""Verified statistics -> complete source tables and bounded manuscript inputs.

No sampler, raw-array replay, R diagnostics or new interval estimator runs here.
Fixtures require explicit marking and can never become manuscript evidence.
"""
import argparse
from collections import Counter,defaultdict
import csv
import json
import math
from pathlib import Path
import re
import statistics
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'scripts/completion')]
from formal_runtime import atomic_json,file_hash
from formal_freeze import relative_file
from formal_analyze import output_inventory
from batch_contract import WORKFLOWS,create_tasks
from formal_measurement_plan import create_measurement_plan

MODELS=('G1','G2','A1','L1','L2','H1','H2','M1','W1')
BUDGETS=(256,1024,4096,16384)
SCOPES=('ordinary_workflow','research_execution')
DISPLAY={
    'cpu-rwm-sequential':'CPU RWM seq', 'cuda-rwm-sequential':'CUDA RWM seq',
    'cpu-rwm-online_picard':'CPU Picard', 'cuda-rwm-online_picard':'CUDA Picard',
    'cpu-mala-sequential':'CPU MALA seq', 'cuda-mala-sequential':'CUDA MALA seq',
    'cpu-mala-quasi_deer':'CPU quasi-DEER', 'cuda-mala-quasi_deer':'CUDA quasi-DEER',
    'cpu-nuts-spawn_chains':'CPU NUTS'}


def json_read(path):
    def unique(pairs):
        value={}
        for k,v in pairs:
            if k in value:raise ValueError('Duplicate JSON field')
            value[k]=v
        return value
    def invalid(value):raise ValueError('Nonfinite JSON value: '+value)
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,parse_constant=invalid)


def label_parts(label):
    workflow,budget=label.rsplit('@',1)
    if workflow not in WORKFLOWS or not budget.isdecimal():raise ValueError('Unknown workflow/budget label')
    return workflow,int(budget)


def interval(row,key='confidence_interval'):
    bounds=row.get(key)
    if bounds is None:return None,None
    if set(bounds)!={'low','high'} or not all(type(v) in (int,float) and math.isfinite(v) for v in bounds.values()) or bounds['low']>=bounds['high']:
        raise ValueError('Invalid saved interval; no zero-width substitute')
    return bounds['low'],bounds['high']


def csv_write(path,rows):
    columns=list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})


class StatisticsBundle:
    """Manifest-verified standalone scalar bundle; original inference stays fixed."""
    def __init__(self,root,manifest_sha256,*,fixture=False):
        self.root=Path(root).resolve();self.fixture=fixture
        if not re.fullmatch('[0-9a-f]{64}',manifest_sha256) or file_hash(self.root/'SHA256.json')!=manifest_sha256:
            raise ValueError('Statistics manifest identity differs')
        self.manifest=json_read(self.root/'SHA256.json');self.manifest_sha256=manifest_sha256
        for name,digest in self.manifest.items():
            if name=='SHA256.json' or file_hash(relative_file(self.root,name))!=digest:raise ValueError('Statistics file identity differs: '+name)
        actual=set()
        for p in self.root.rglob('*'):
            if p.is_symlink():raise ValueError('Symlinked statistics')
            if p.is_file() and p!=self.root/'SHA256.json':actual.add(p.relative_to(self.root).as_posix())
        if actual!=set(self.manifest):raise ValueError('Statistics inventory incomplete')
        self.summary=self.read('SUMMARY.json');self.frame=self.summary['frame'];self.references=self.read('reference-contract.json')
        if self.summary.get('artificial_data',False) is not False and not fixture:
            raise ValueError('Artificial statistics require --fixture, even at the full formal shape')
        self.models=[m['model'] for m in self.summary['models']]
        if len(set(self.models))!=len(self.models) or not set(self.models)<=set(MODELS) or set(self.references)!=set(self.models):
            raise ValueError('Model/reference frame differs')
        if self.frame['scope'] not in ('formal_inference','technical_batch_validation'):raise ValueError('Unknown statistical scope')
        if self.summary['formal_inference_complete'] is not False:raise ValueError('Unsupported automatic completion claim')
        self.full_formal_frame=(self.frame['scope']=='formal_inference' and set(self.models)==set(MODELS) and
            self.frame['main_planned']==41472 and self.frame['cache_planned']==9216 and
            self.frame['formal_scientific_repetitions_per_model']==128)
        if not fixture and self.frame['scope']=='formal_inference':
            if not self.full_formal_frame:
                raise ValueError('Complete formal design required; artificial data need --fixture')
        if not fixture and self.frame['scope']=='technical_batch_validation':
            if set(self.models)!={'G1','G2','W1'} or (self.frame['main_planned'],self.frame['cache_planned'])!=(27,24):
                raise ValueError('Finite technical design differs')
        if sum(m['main_planned'] for m in self.summary['models'])!=self.frame['main_planned'] or sum(m['cache_planned'] for m in self.summary['models'])!=self.frame['cache_planned']:
            raise ValueError('Model and whole-study task counts differ')

    def read(self,name):
        if name not in self.manifest:raise ValueError('Required statistics file absent: '+name)
        return json_read(relative_file(self.root,name))

    def model(self,name):
        summary=self.read(name+'/SUMMARY.json')
        if summary!=next(m for m in self.summary['models'] if m['model']==name) or summary['reference']!=self.references[name]:
            raise ValueError('Whole-study and model/reference summaries differ')
        rows=self.read(name+'/task-frame.json');ids=set()
        for row in rows:
            task=row['task']
            if task['id'] in ids or task['model']!=name or task['protocol_sha256']!=self.frame['protocol_sha256']:
                raise ValueError('Aliased or misbound task')
            ids.add(task['id'])
            if task['workflow'] not in WORKFLOWS or any(task[k]!=v for k,v in WORKFLOWS[task['workflow']].items()):
                raise ValueError('Task/workflow identity differs')
            if row['phase'] not in ('main','cache') or task['artifact_kind']!=('posterior' if row['phase']=='main' else 'cache_measurement'):
                raise ValueError('Main/cache qualification differs')
        for phase in ('main','cache'):
            part=[r for r in rows if r['phase']==phase]
            if (len(part)!=summary[phase+'_planned'] or dict(Counter(r['disposition'] for r in part))!=summary[phase+'_dispositions'] or
                    dict(Counter(r.get('outcome') or 'unknown_evidence' for r in part))!=summary[phase+'_outcomes']):
                raise ValueError('Projected outcomes/dispositions differ')
        # An artificial watermark does not waive full-design identity checks.
        if self.full_formal_frame:
            primary=create_tasks(self.frame['identity'],[dict(models=[name],replicates=list(range(128)),budgets=list(BUDGETS),workflows=list(WORKFLOWS))])
            allocation=create_measurement_plan(self.frame['identity'],primary)
            originals={t['id']:t for t in primary};expected={}
            for phase,items in [('main',primary),('cache',allocation['probes'])]:
                for item in items:
                    base=item if phase=='main' else originals[item['primary_task_id']]
                    expected[item['id']]=dict(base,id=item['id'],protocol_sha256=self.frame['protocol_sha256'],
                        artifact_kind='posterior' if phase=='main' else 'cache_measurement')
            if {r['task']['id']:r['task'] for r in rows}!=expected:raise ValueError('Formal task identities differ from the fixed design')
        return summary,rows


def diagnostic_rows(rows,names):
    groups=defaultdict(list)
    for row in rows:
        if row['phase']=='main':groups[(row['task']['workflow'],row['task']['budget'])].append(row)
    output=[]
    for (workflow,budget),group in sorted(groups.items()):
        for name in names:
            received=[]
            for row in group:
                diag=row.get('diagnostics')
                if diag is None:continue
                if row['disposition']!='analyzed' or row['outcome']!='valid' or row['function_status']!='completed':
                    raise ValueError('Diagnostics cannot promote an ineligible task')
                byname={d['variable']:d for d in diag}
                if len(byname)!=len(diag) or set(byname)!=set(names):raise ValueError('Diagnostic function frame differs')
                received.append(byname[name])
            record=dict(workflow=workflow,budget=budget,function=name,planned=len(group),received=len(received),missing=len(group)-len(received))
            for field in ('rhat','ess_bulk','ess_tail','mcse_mean'):
                values=[d[field] for d in received if d.get(field) is not None]
                if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values):raise ValueError('Invalid saved diagnostic')
                record.update({field+'_finite':len(values),field+'_undefined':len(received)-len(values),
                    field+'_minimum':min(values,default=None),field+'_maximum':max(values,default=None),
                    field+'_median':statistics.median(values) if values else None})
                if field=='rhat':record['rhat_above_1_01']=sum(v>1.01 for v in values)
            output.append(record)
    return output


def nuts_rows(rows):
    groups=defaultdict(list)
    for row in rows:
        if row['phase']=='main' and row['task']['kernel']=='nuts':groups[row['task']['budget']].append(row)
    output=[]
    for budget,group in sorted(groups.items()):
        divs=hits=known_chains=hit_chains=0;received=0
        for row in group:
            saved=row.get('nuts')
            if saved is None:continue
            if row['disposition']!='analyzed' or row['outcome']!='valid':raise ValueError('NUTS diagnostics in ineligible task')
            received+=1;children=saved['chain_diagnostics']
            if sorted(c['chain'] for c in children)!=list(range(4)):raise ValueError('Exactly four NUTS children required')
            for child in children:
                records=child['records']
                if len(records)!=1:raise ValueError('One per-child chain record required')
                divergence=records[0]['diagnostics'].get('divergences')
                if divergence is not None:
                    if len(divergence)!=1:raise ValueError('Unexpected child divergence frame')
                    positions=next(iter(divergence.values()))
                    if len(set(positions))!=len(positions) or any(type(x) is not int or not 0<=x<budget for x in positions):
                        raise ValueError('Invalid post-warmup divergence positions')
                    divs+=len(positions);known_chains+=1
                hit=child['tree_depth_hit_count']
                if hit is not None:
                    if type(hit) is not int or not 0<=hit<=budget:raise ValueError('Invalid tree-depth count')
                    hits+=hit;hit_chains+=1
        output.append(dict(budget=budget,planned_tasks=len(group),received_tasks=received,missing_tasks=len(group)-received,
            known_divergence_chains=known_chains,unknown_divergence_chains=4*len(group)-known_chains,
            known_divergences=divs,complete_divergences=divs if known_chains==4*len(group) else None,
            divergence_fraction_among_recorded_chain_draws=divs/(known_chains*budget) if known_chains else None,
            known_tree_depth_chains=hit_chains,unknown_tree_depth_chains=4*len(group)-hit_chains,
            known_tree_depth_hits=hits,complete_tree_depth_hits=hits if hit_chains==4*len(group) else None,
            diagnostic_counts_are_not_independent_repetitions=True))
    return output


def ratio_row(pair,*,phase,kind):
    a,b=label_parts(pair['workflow_a']),label_parts(pair['workflow_b'])
    if a[1]!=b[1]:raise ValueError('Paired budgets differ')
    saved=pair.get('ratio_confidence_interval');status=pair['interval_status']
    collapsed=(isinstance(saved,dict) and set(saved)=={'low','high'} and
        all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in saved.values()) and saved['low']==saved['high'])
    if collapsed:
        # A strictly ordered log interval can lose its width under exp in
        # floating point. Preserve that source, but do not draw a zero CI or
        # widen it with nextafter/pseudocounts. This is a display qualification.
        if interval(pair)==(None,None):raise ValueError('Collapsed ratio interval lacks its ordered log source')
        lo=hi=None;status='unrepresentable_width_on_saved_ratio_scale'
    else:lo,hi=interval(pair,'ratio_confidence_interval')
    point=pair['geometric_mean_ratio']
    if point is not None and (not math.isfinite(point) or point<=0):raise ValueError('Cost ratio must be positive or unavailable')
    return dict(phase=phase,kind=kind,workflow_a=a[0],workflow_b=b[0],budget=a[1],
        planned=pair['planned'],paired=pair['validity_table']['n11'],validity_table=pair['validity_table'],
        point=point,low=lo,high=hi,interval_status=status,source_interval_status=pair['interval_status'],
        ratio_interval_collapsed_under_transform=collapsed,
        missing_cost_pairs=pair['jointly_valid_pairs_missing_cost'],zero_cost_pairs=pair['jointly_valid_pairs_zero_cost'],
        definition='geometric mean of A/B cost; interval on ratio scale',source_record=pair)


def model_tables(bundle,name):
    summary,rows=bundle.model(name);names=summary['reference']['names'];main=[r for r in rows if r['phase']=='main']
    frames=defaultdict(list)
    for row in rows:frames[(row['phase'],row['task']['workflow'],row['task']['budget'])].append(row)
    tasks=[dict(phase=p,workflow=w,budget=b,planned=len(g),dispositions=dict(Counter(r['disposition'] for r in g)),
                outcomes=dict(Counter(r.get('outcome') or 'unknown_evidence' for r in g)),
                functions_available=sum(r.get('means') is not None for r in g)) for (p,w,b),g in sorted(frames.items())]
    tables=dict(tasks=tasks,diagnostics=diagnostic_rows(rows,names),nuts=nuts_rows(rows),ratios=[],errors=[],paired_errors=[],costs=[],cache=[])
    taskcost=[]
    for row in rows:
        for phase in ('ordinary_workflow','research_execution','additional_verification','all_invocations'):
            cost=row.get('costs');value=None if cost is None else cost['phases'][phase]
            taskcost.append(dict(id=row['task']['id'],artifact_kind=row['task']['artifact_kind'],workflow=row['task']['workflow'],
                budget=row['task']['budget'],replicate=row['task']['replicate'],phase=phase,disposition=row['disposition'],
                outcome=row.get('outcome'),known_original_outcome=row.get('recorded_outcome'),
                complete_seconds=None if value is None else value['complete_seconds'],
                known_seconds=None if value is None else value['known_seconds'],measurement=value))
    tables['task_costs']=taskcost
    pairs=[]
    if summary['main_statistics']=='completed':
        pairs=bundle.read(name+'/comparisons.json')['pairs']
        kinds={(p['left'],p['right']):p['kind'] for p in pairs}
        if len(kinds)!=len(pairs):raise ValueError('Duplicate comparison')
        for j,function in enumerate(names):
            report=bundle.read(name+f'/function-{j}.json')
            expected=dict(kind=summary['reference']['kinds'][j],value=summary['reference']['means'][j],mcse=summary['reference']['mcse'][j])
            if report['function']!=function or report['reference']!=expected or report['comparison_kinds']!=pairs:
                raise ValueError('Function/reference/contrast identity differs')
            actual={(r['task']['workflow'],r['task']['budget']) for r in main}
            if {label_parts(k) for k in report['error']['workflows']}!=actual:raise ValueError('Missing error workflow')
            for label,error in report['error']['workflows'].items():
                w,b=label_parts(label);group=frames[('main',w,b)];lo,hi=interval(error)
                available=sum(r.get('means') is not None for r in group)
                if error['planned']!=len(group) or error['valid']!=available:raise ValueError('Error denominator differs')
                for scope in SCOPES:
                    cost=None if report['costs'] is None else report['costs'][scope]['workflows'][label]
                    if cost is not None and (cost['function_available']!=available or
                            cost['plot_error_cost_point'] and (error['conditional_squared_discrepancy'] is None or cost['mean_seconds'] is None)):
                        raise ValueError('Error/cost availability differs')
                    clo,chi=(None,None) if cost is None else interval(cost)
                    tables['errors'].append(dict(function=function,workflow=w,budget=b,phase=scope,
                        planned=len(group),available=available,reference_kind=expected['kind'],reference_value=expected['value'],reference_mcse=expected['mcse'],
                        point=error['conditional_squared_discrepancy'],low=lo,high=hi,interval_status=error['interval_status'],
                        mean_seconds=None if cost is None else cost['mean_seconds'],cost_low=clo,cost_high=chi,
                        cost_interval_status='unavailable_call_ledger' if cost is None else cost['interval_status'],
                        plot_point=False if cost is None else cost['plot_error_cost_point'],
                        error_record=error,cost_record=cost))
            if [(p['workflow_a'],p['workflow_b']) for p in report['error']['pairs']]!=list(kinds):raise ValueError('Error contrast frame differs')
            for pair in report['error']['pairs']:
                a,b=label_parts(pair['workflow_a']),label_parts(pair['workflow_b']);lo,hi=interval(pair)
                tables['paired_errors'].append(dict(function=function,kind=kinds[(pair['workflow_a'],pair['workflow_b'])],
                    workflow_a=a[0],workflow_b=b[0],budget=a[1],reference_kind=expected['kind'],reference_mcse=expected['mcse'],
                    planned=pair['planned'],paired=pair['validity_table']['n11'],validity_table=pair['validity_table'],
                    point=pair['conditional_mean_loss_difference'],low=lo,high=hi,interval_status=pair['interval_status'],source_record=pair))
        if summary['cost_statistics']=='completed':
            cost=bundle.read(name+'/costs.json')
            for scope in SCOPES:
                for label,row in cost['phases'][scope]['workflows'].items():
                    w,b=label_parts(label);tables['costs'].append(dict(row,workflow=w,budget=b,phase=scope))
                for pair in cost['phases'][scope]['pairs']:
                    tables['ratios'].append(ratio_row(pair,phase=scope,kind=kinds[(pair['workflow_a'],pair['workflow_b'])]))
    if summary['cache_statistics']=='completed':
        cache=bundle.read(name+'/cache-costs.json')
        if cache['samples_eligible'] is not False or cache['new_independent_repetitions']!=0:raise ValueError('Cache eligibility differs')
        for label,row in cache['workflows'].items():
            w,b=label_parts(label);tables['cache'].append(dict(workflow=w,budget=b,**row))
        for pair in cache['pairs']:tables['ratios'].append(ratio_row(pair,phase='cached_executor',kind='same_kernel_execution'))
    return summary,tables


def build(statistics_directory,manifest_sha256,output,*,fixture=False,render=True):
    source=StatisticsBundle(statistics_directory,manifest_sha256,fixture=fixture);output=Path(output).resolve()
    if output.exists() or output.is_relative_to(source.root) or source.root.is_relative_to(output):raise ValueError('Fresh report separate from statistics required')
    output.mkdir(parents=True);models=[];figures=[]
    for name in source.models:
        summary,tables=model_tables(source,name);dest=output/name;dest.mkdir()
        for table,rows in tables.items():csv_write(dest/(table+'.csv'),rows)
        atomic_json(dest/'tables.json',tables)
        atomic_json(dest/'SUMMARY.json',summary)
        if render:
            from formal_plots import render_model
            figures.extend(render_model(name,summary,tables,dest,fixture=fixture,technical=source.frame['scope']!='formal_inference'))
        models.append(dict(model=name,table_rows={k:len(v) for k,v in tables.items()},summary=summary))
    receipt=dict(schema='formal-results-report-v1',statistics_manifest_sha256=manifest_sha256,frame=source.frame,
        fixture=fixture,scientific_results=not fixture and source.frame['scope']=='formal_inference',
        all_main_statistics_available=all(m['summary']['main_statistics']=='completed' for m in models),
        all_cache_statistics_available=all(m['summary']['cache_statistics']=='completed' for m in models),
        producer_analysis_identity_sha256=source.summary.get('analysis_identity_sha256'),
        source_models=models,figures=figures,code_sha256={n:file_hash(Path(__file__).parent/n) for n in
            ('formal_report.py','formal_plots.py','formal_report_text.py')},
        new_sampler_calls=0,new_statistical_repetitions=0,raw_arrays_replayed=False,diagnostics_recomputed=False,
        complete_research_or_convergence_claim=False,
        source_integrity_scope='Verified supplied statistics manifest; original raw validation belongs to the recorded producer')
    atomic_json(output/'REPORT.json',receipt)
    from formal_report_text import write_report
    write_report(output,receipt)
    atomic_json(output/'SHA256.json',output_inventory(output))
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--statistics-directory',type=Path,required=True);p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture',action='store_true');p.add_argument('--no-render',action='store_true')
    args=vars(p.parse_args());args['render']=not args.pop('no_render')
    print(json.dumps(build(**args),indent=2))
