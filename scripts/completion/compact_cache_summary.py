"""Descriptive input-level cache reduction, always retaining the four-call frame.

No bootstrap is performed at n=4. Missing elapsed times remain None. An outer
interruption cannot become an available point even if all inner calls passed.
"""
from collections import Counter,defaultdict
import math
from statistics import median
from formal_runtime import fingerprint


def summarize_probe(probe,records,*,expected_tape_sha256,expected_target_id,expected_config):
    if probe['initial_calls']!=1 or probe['prepared_replays']!=3 or len(records)!=4:
        raise ValueError('The prescribed initial plus three prepared calls are required')
    known=[];valid=0;missing=0;unknown_time=0
    for i,r in enumerate(records):
        if r is None:missing+=1;continue
        if (r['execution_index']!=i or r['has_prior_execution'] is not (i>0) or
            r['tape_sha256']!=expected_tape_sha256 or r['target_id']!=expected_target_id or
            r['config']!=expected_config or r['samples_eligible'] is not False or
            r['status'] not in ('candidate','failed') or type(r['technical_output_valid']) is not bool or
            (r['status']=='failed' and r['technical_output_valid'])):
            raise ValueError('Cache call identity/eligibility conflicts')
        seconds=r.get('executor_wall_seconds')
        if seconds is None:unknown_time+=1
        elif type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<=0:
            raise ValueError('Invalid elapsed time is not a usable measurement')
        else:known.append(seconds)
        valid+=bool(r['technical_output_valid'] and seconds is not None)
    all_valid=valid==4
    return dict(probe_id=probe['id'],primary_task_id=probe['primary_task_id'],expected_executions=4,
        observed_executions=4-missing,missing_executions=missing,missing_elapsed_times=unknown_time,
        valid_executions=valid,all_executions_valid=all_valid,
        cached_seconds=median(r['executor_wall_seconds'] for r in records[1:]) if all_valid else None,
        cached_summary='Median of all three prepared calls only when the initial and all replays pass and have timing receipts',
        known_executor_seconds=math.fsum(known),complete_executor_seconds=None if missing or unknown_time else math.fsum(known),
        samples_eligible=False,statistical_repetitions_added=0,
        scope='Executor wall only; preparation/transfer/audit/output/outer costs are separate')


def analyze(allocation,primary_tasks,model,bindings,observations):
    probes=[p for p in allocation['probes'] if p['model']==model]
    if set(bindings)!=set(observations) or set(bindings)!={p['id'] for p in probes}:
        raise ValueError('Complete prescribed compact cache input frame required')
    reduced=[];groups=defaultdict(dict)
    for p in probes:
        b=bindings[p['id']];o=observations[p['id']]
        if 'task_outcome' not in o:raise ValueError('Owned cache outer outcome is mandatory')
        summary=summarize_probe(p,o['records'],expected_tape_sha256=b['tape_sha256'],
            expected_target_id=b['target_id'],expected_config=b['config'])
        available=o['task_outcome']=='measurement_available' and summary['all_executions_valid']
        row=dict(summary,task_outcome=o['task_outcome'],available=available,
            cached_seconds=summary['cached_seconds'] if available else None,
            candidate_cached_seconds=summary['cached_seconds'],original_replicate=p['replicate'],
            execution_outcome_counts=dict(Counter(o['execution_outcomes'])),binding=b)
        reduced.append(row);groups[p['workflow']+'@'+str(p['budget'])][p['replicate']]=row
    workflows={}
    for label,items in groups.items():
        values=[r['cached_seconds'] for r in items.values() if r['available']]
        workflows[label]=dict(planned_inputs=len(items),available_cache_points=len(values),
            per_input_seconds={str(k):r['cached_seconds'] for k,r in sorted(items.items())},
            available_range=[min(values),max(values)] if values else None,
            mean_cached_seconds=math.fsum(values)/len(values) if values else None,
            confidence_interval=None,interval_status='descriptive_four_inputs_no_interval',
            known_executor_seconds=math.fsum(r['known_executor_seconds'] for r in items.values()),
            complete_executor_seconds=None if any(r['complete_executor_seconds'] is None for r in items.values()) else
                math.fsum(r['complete_executor_seconds'] for r in items.values()),
            execution_outcome_counts=dict(sum((Counter(r['execution_outcome_counts']) for r in items.values()),Counter())),
            task_outcome_counts=dict(Counter(r['task_outcome'] for r in items.values())),samples_eligible=False)
    pairs=[]
    for budget,device,kernel in sorted({(p['budget'],p['device'],p['kernel']) for p in probes}):
        a=f'{device}-{kernel}-sequential@{budget}'
        b=f'{device}-{kernel}-'+('online_picard' if kernel=='rwm' else 'quasi_deer')+f'@{budget}'
        left,right=groups[a],groups[b]
        if set(left)!=set(right):raise ValueError('Incomplete paired cache inputs')
        table=dict(n11=0,n10=0,n01=0,n00=0);ratios={}
        for r in sorted(left):
            x,y=left[r],right[r]
            for k in ('input_file_sha256','tape_sha256','target_id'):
                if x['binding'][k]!=y['binding'][k]:raise ValueError('Cache paired actual input/target differs')
            cfg=lambda z:{k:v for k,v in z['binding']['config'].items() if k not in ('executor','max_iter')}
            if cfg(x)!=cfg(y):raise ValueError('Cache same-kernel configurations differ')
            table['n'+str(int(x['available']))+str(int(y['available']))]+=1
            ratios[str(r)]=x['cached_seconds']/y['cached_seconds'] if x['available'] and y['available'] else None
        values=[v for v in ratios.values() if v is not None]
        pairs.append(dict(workflow_a=a,workflow_b=b,planned=len(left),validity_table=table,
            per_input_ratios=ratios,ratio_range=[min(values),max(values)] if values else None,
            geometric_mean_ratio=math.exp(math.fsum(math.log(v) for v in values)/len(values)) if values else None,
            ratio_confidence_interval=None,confidence_interval=None,interval_status='descriptive_four_inputs_no_interval',
            jointly_valid_pairs_missing_cost=0,jointly_valid_pairs_zero_cost=0,
            conditioning='Both outer tasks and all four calls valid and timed; no success-subcall median',
            ratio_interpretation='Sequential/time executor cached cost only, not ordinary posterior inference speed'))
    return dict(policy='compact-cache-descriptive-v1',allocation_sha256=allocation['allocation_sha256'],
        binding_frame_sha256=fingerprint(bindings),workflows=workflows,pairs=pairs,probes=reduced,
        resampling=None,bootstrap_statistics={},samples_eligible=False,new_independent_repetitions=0,
        technical_replays_are_independent_units=False,confidence_intervals_generated=False)
