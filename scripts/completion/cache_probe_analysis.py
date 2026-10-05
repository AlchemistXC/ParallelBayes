"""Paired cache-cost analysis on the prespecified original-input subset.

Callers verify frozen bindings, array manifests and independent numerical audits
before this statistical interface. This module does not execute samplers or
convert replay output into new inference samples. All missing planned probes
and execution slots must be explicit; primary-run success is never an input.
"""
import math
import re

from formal_measurement_plan import validate_measurement_plan,summarize_probe
from formal_outcomes import OUTCOMES
from formal_runtime import fingerprint
from formal_uncertainty import create_plan,analyze_costs

POLICY='cached-input-companion-v1'
AVAILABILITY=('available','failed','interrupted','not_run','incomplete_record')
FAILURES={'numerical_failure','resource_failure','output_failure_unclassified'}


def create_cache_plan(allocation,primary_tasks,model):
    """Separate archived resampling frame; same rows for all budgets/workflows."""
    validate_measurement_plan(allocation,primary_tasks)
    ids=tuple(str(r) for r in sorted({p['replicate'] for p in allocation['probes'] if p['model']==model}))
    return create_plan(POLICY+'::'+allocation['allocation_sha256'],model,ids)


def _validate_bindings(probes,bindings):
    inputs={};tapes={};initials={};targets=set();paired={}
    for p in probes:
        b=bindings[p['id']];c=b['config'];r=p['replicate'];budget=p['budget']
        if set(b)!={'input_file_sha256','tape_sha256','target_id','config'}:
            raise ValueError('Complete input/configuration binding required')
        for key in ('input_file_sha256','tape_sha256','target_id'):
            if not isinstance(b[key],str) or not re.fullmatch('[0-9a-f]{64}',b[key]):
                raise ValueError('Explicit input/target/tape SHA256 required')
        required={'kernel','executor','device','chains','draws','step_size','initial','atol','rtol','audit','on_failure'}
        if (not isinstance(c,dict) or not required<=set(c) or
            any(c[k]!=p[k] for k in ('kernel','executor','device')) or type(c['chains']) is not int or c['chains']!=4 or
            type(c['draws']) is not int or c['draws']<budget or c['audit'] is not False or c['on_failure']!='error'):
            raise ValueError('Probe configuration differs from declared task')
        if any(type(c[k]) not in (int,float) or not math.isfinite(c[k]) or c[k]<=0 for k in ('step_size','atol','rtol')):
            raise ValueError('Positive finite kernel/output controls required')
        if r in inputs and inputs[r]!=b['input_file_sha256']:raise ValueError('Shared actual input file differs')
        inputs[r]=b['input_file_sha256']
        address=(r,budget)
        if address in tapes and tapes[address]!=b['tape_sha256']:raise ValueError('Shared actual tape differs')
        tapes[address]=b['tape_sha256']
        initial=fingerprint(c['initial'])
        if r in initials and initials[r]!=initial:raise ValueError('Shared initial coordinates differ')
        initials[r]=initial;targets.add(b['target_id'])
        key=(r,budget,p['device'],p['kernel'])
        comparable={k:v for k,v in c.items() if k not in ('executor','max_iter')}
        if key in paired and paired[key]!=comparable:raise ValueError('Same-kernel paired configuration differs')
        paired[key]=comparable
    if len(targets)!=1:raise ValueError('One model target identity required')


def analyze_cache_probes(allocation,primary_tasks,plan,bindings,observations):
    """Reduce complete declared execution frames, then analyze input-level costs.

    bindings maps every selected probe ID for plan.model to its verified input
    file hash, tape hash, target ID and full configuration. observations maps
    the same IDs to execution_outcomes and records, each initial+replay ordered.
    None means a missing timing/record, never zero elapsed time. Explicit valid
    output without a timing receipt remains unavailable for cache measurement.
    """
    expected=create_cache_plan(allocation,primary_tasks,plan.model)
    plan.validate()
    if plan.receipt()!=expected.receipt():raise ValueError('Cache companion resampling frame differs')
    probes=[p for p in allocation['probes'] if p['model']==plan.model]
    ids={p['id'] for p in probes}
    if set(bindings)!=ids or set(observations)!=ids:raise ValueError('Every planned probe binding and observation required')
    _validate_bindings(probes,bindings)
    grouped={};reduced={}
    for probe in probes:
        pid=probe['id'];binding=bindings[pid];observation=observations[pid]
        states=observation['execution_outcomes'];records=observation['records']
        count=1+probe['prepared_replays']
        if len(states)!=count or len(records)!=count or any(s not in OUTCOMES for s in states):
            raise ValueError('Complete explicit execution frame required')
        for state,record in zip(states,records):
            if record is not None and (state=='not_run' or record['technical_output_valid']!=(state=='valid')):
                raise ValueError('Execution outcome conflicts with numerical record')
        summary=summarize_probe(probe,records,expected_tape_sha256=binding['tape_sha256'],
            expected_target_id=binding['target_id'],expected_config=binding['config'])
        if summary['all_executions_valid']:availability='available'
        elif any(s in FAILURES for s in states):availability='failed'
        elif 'infrastructure_interruption' in states:availability='interrupted'
        elif all(s=='not_run' for s in states):availability='not_run'
        else:availability='incomplete_record'
        summary.update(availability=availability,execution_outcomes=list(states),
                       execution_outcome_counts={s:states.count(s) for s in OUTCOMES})
        reduced[pid]=summary
        label=probe['workflow']+'@'+str(probe['budget'])
        grouped.setdefault(label,{})[str(probe['replicate'])]=summary
    pairs=[]
    for budget,device,kernel in sorted({(p['budget'],p['device'],p['kernel']) for p in probes}):
        prefix=device+'-'+kernel+'-';suffix='@'+str(budget)
        pairs.append((prefix+'sequential'+suffix,prefix+('online_picard' if kernel=='rwm' else 'quasi_deer')+suffix))
    costs={label:{r:row['cached_seconds'] for r,row in rows.items()} for label,rows in grouped.items()}
    masks={label:{r:'valid' if row['availability']=='available' else 'not_run' for r,row in rows.items()} for label,rows in grouped.items()}
    # The generic engine's failure fields do not describe cache-point availability
    # and are intentionally not exposed. All six actual call outcomes remain below.
    statistics=analyze_costs(plan,costs,masks,pairs,'prepared_executor_cache_median')
    workflows={}
    for label,rows in grouped.items():
        stats=statistics['workflows'][label];values=list(rows.values())
        known=math.fsum(v['known_executor_seconds'] for v in values)
        workflows[label]=dict(planned_inputs=len(plan.replicate_ids),
            available_cache_points=sum(v['availability']=='available' for v in values),
            availability_counts={s:sum(v['availability']==s for v in values) for s in AVAILABILITY},
            execution_outcome_counts={s:sum(v['execution_outcome_counts'][s] for v in values) for s in OUTCOMES},
            planned_executions=sum(v['expected_executions'] for v in values),
            recorded_executions=sum(v['observed_executions'] for v in values),
            known_executor_seconds=known,
            complete_executor_seconds=known if all(v['complete_executor_seconds'] is not None for v in values) else None,
            unavailable_probe_known_seconds=math.fsum(v['known_executor_seconds'] for v in values if v['availability']!='available'),
            mean_cached_seconds=stats['mean_recorded_seconds'],confidence_interval=stats['confidence_interval'],
            interval_status=stats['interval_status'],interval_coverage='pointwise_conditional_on_available_cache_points',
            interval_diagnostics={k:v for k,v in stats.items() if k.startswith(('bca_','bootstrap_','resampled_')) or k in
                ('undefined_bootstrap_replicates','resampling_plan_sha256','minimum_valid_repetitions')},
            conditioning='All initial and declared replays satisfy the output contract and have timing receipts',
            consumption_scope='Sum every recorded initial/replay executor time, including unsuccessful probes; excludes preparation, transfer, audits, and archives')
    for pair in statistics['pairs']:
        pair.update(conditioning='both_input_level_cache_points_available',
            interval_coverage='pointwise_conditional_on_both_cache_points_available',
            validity_table_definition='n11 both available; n10 sequential only; n01 time executor only; n00 neither',
            ratio_interpretation='Sequential / time executor; greater than one means lower cached executor cost, not faster reliable inference')
    return dict(policy=POLICY,allocation_sha256=allocation['allocation_sha256'],binding_frame_sha256=fingerprint(bindings),resampling=plan.receipt(),
        workflows=workflows,pairs=statistics['pairs'],probes=reduced,bootstrap_statistics=statistics['bootstrap_statistics'],
        samples_eligible=False,new_independent_repetitions=0,technical_replays_are_independent_units=False,
        source_scope='Input bindings and numerical audits must be verified by caller; no new numerical proof is provided here',
        scope='Conditional input-level prepared-execution costs, not an ordinary-inference error-cost curve or a convergence assessment')
