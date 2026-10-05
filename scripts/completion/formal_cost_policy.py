"""Explicit task cost scopes from verified attempt and invocation evidence.

Callers first validate archive identities and receipts. This module reduces
one declared logical task, never treats attempts as repetitions, and preserves
unknown durations. It neither measures clocks nor decides output eligibility.
"""
import math
from formal_outcomes import OUTCOMES,summarize_attempts
from measured_coordinator import summarize_calls

POLICY='four-chain-runtime-costs-v1'
SCOPES=dict(
    ordinary_workflow='Sum ordinary subprocess creation-through-exit wall over every registered actual attempt; includes ordinary output/diagnostics, excludes outer audit and inter-call waiting',
    research_execution='Sum all coordinator run/retry calls except completed verification-only returns; includes recorded refusals/recovery/audit/sealing; excludes ledger writes, report observations and inter-call waiting',
    additional_verification='Completed coordinator calls returning newly_executed=false; kept outside primary execution cost',
    all_invocations='All coordinator calls, including additional verification; operational consumption, not standardized time-to-inference')


def _duration(value):
    if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0):
        raise ValueError('Durations must be nonnegative finite seconds or explicit None')


def _phase(values,scope,*,empty_known=False,missing_attempts=0,prior_known=0.):
    values=list(values)
    for value in values:_duration(value)
    unknown=sum(v is None for v in values);known=math.fsum(v for v in values if v is not None)
    complete=not unknown and not missing_attempts and (bool(values) or empty_known)
    return dict(complete_seconds=known if complete else None,known_seconds=known,
        recorded_measurements=sum(v is not None for v in values),unknown_measurements=unknown,
        attempts_missing_call_return=missing_attempts,prior_interruption_known_seconds=prior_known,
        cost_scope=scope,unknown_time_imputed=False)


def summarize_task_costs(history,identity,calls,ordinary):
    """Reduce verified ledgers; ordinary maps every actual attempt to seconds/None.

    A receipt missing before/during subprocess execution remains None even if
    a later retry succeeded. No attempt is zero only because its receipt is
    absent. Verification-only calls may be added without altering primaries.
    """
    reduced=summarize_attempts(history['attempts'])
    if history['summary']!=reduced:raise ValueError('Attempt summary conflicts with history')
    if len(history['attempts'])>2:raise ValueError('At most one explicit infrastructure retry')
    ids=[a['attempt_id'] for a in history['attempts']]
    if set(ordinary)!=set(ids):raise ValueError('Every ordinary attempt needs an explicit measured or unknown value')
    for index,c in enumerate(calls):
        if c['index']!=index or type(c['finished']) is not bool or c['finished']!=(c['seconds'] is not None):
            raise ValueError('Invocation order/completion differs')
        _duration(c['seconds'])
        if not c['finished'] and (c['result'] is not None or c['error'] is not None):raise ValueError('Unfinished call has a terminal result')
        if c['result'] is not None:
            if type(c['result']['newly_executed']) is not bool or c['result']['attempt_id'] not in ids or c['error'] is not None:
                raise ValueError('Invocation result identity/completion differs')
    measured=summarize_calls(history,identity,calls)
    previous={a['attempt_id'] for a in history['attempts'][:-1]}
    verification=[c for c in calls if c['result'] is not None and c['result']['newly_executed'] is False]
    primary=[c for c in calls if c not in verification]
    prior=math.fsum(c['seconds'] for c in primary if c['result'] is not None and c['result']['attempt_id'] in previous)
    ordinary_prior=math.fsum(ordinary[a] for a in previous if ordinary[a] is not None)
    phases=dict(
        ordinary_workflow=_phase([ordinary[a] for a in ids],SCOPES['ordinary_workflow'],prior_known=ordinary_prior),
        research_execution=_phase([c['seconds'] for c in primary],SCOPES['research_execution'],
            missing_attempts=measured['attempts_missing_outer_measurement'],prior_known=prior),
        additional_verification=_phase([c['seconds'] for c in verification],SCOPES['additional_verification'],empty_known=True),
        all_invocations=_phase([c['seconds'] for c in calls],SCOPES['all_invocations'],missing_attempts=measured['attempts_missing_outer_measurement']))
    return dict(policy=POLICY,task=history['task'],original=history['original'],outcome=reduced['outcome'],
        actual_attempts=len(ids),invocations=len(calls),verification_only_invocations=len(verification),
        recorded_refusals_or_exceptions=sum(c['finished'] and c['result'] is None for c in primary),
        phases=phases,cached_execution_seconds=None,cached_scope='Requires a separately declared prepared-execution measurement; never inferred from ordinary wall',
        attempts_are_statistical_repetitions=False,phase_totals_are_additive=False)


def analyze_task_costs(plan,records,pairs=()):
    """Use the shared whole-repetition plan for the two primary wall scopes.

    records[workflow_budget_label][repetition] contains the above reduction of
    verified source records. Missing planned tasks must appear as not_run;
    unavailable timings cannot be removed from jointly valid cost comparisons.
    """
    from formal_uncertainty import analyze_costs
    plan.validate()
    if not records:raise ValueError('Nonempty planned cost frame required')
    observed=set();outcomes={};operation={}
    for label,rows in records.items():
        if set(rows)!=set(plan.replicate_ids):raise ValueError('Every planned repetition required')
        for rep,row in rows.items():
            task=row['task'];key=(task['protocol_sha256'],task['id'])
            if key in observed:raise ValueError('One actual task cannot supply multiple statistical units')
            observed.add(key)
            if row['policy']!=POLICY or row['outcome'] not in OUTCOMES or task['model']!=plan.model or str(task['replicate'])!=rep:
                raise ValueError('Cost policy, model or repetition identity differs')
        outcomes[label]={r:('numerical_failure' if v['outcome'] in ('resource_failure','output_failure_unclassified') else v['outcome']) for r,v in rows.items()}
        operation[label]=dict(actual_attempts=sum(v['actual_attempts'] for v in rows.values()),
            verification_only_invocations=sum(v['verification_only_invocations'] for v in rows.values()),
            recorded_refusals_or_exceptions=sum(v['recorded_refusals_or_exceptions'] for v in rows.values()),
            additional_verification_known_seconds=math.fsum(v['phases']['additional_verification']['known_seconds'] for v in rows.values()),
            all_invocations_known_seconds=math.fsum(v['phases']['all_invocations']['known_seconds'] for v in rows.values()),
            tasks_with_incomplete_all_invocation_cost=sum(v['phases']['all_invocations']['complete_seconds'] is None for v in rows.values()),
            all_calls_are_time_to_inference=False)
    reports={}
    for phase in ('ordinary_workflow','research_execution'):
        costs={label:{r:v['phases'][phase]['complete_seconds'] for r,v in rows.items()} for label,rows in records.items()}
        report=analyze_costs(plan,costs,outcomes,pairs,phase)
        for label,row in report['workflows'].items():
            values=list(records[label].values());measurements=[v['phases'][phase] for v in values]
            row['outcome_counts']={k:sum(v['outcome']==k for v in values) for k in OUTCOMES}
            row['total_recorded_seconds']=math.fsum(v['known_seconds'] for v in measurements)
            row['known_partial_task_seconds']=math.fsum(v['known_seconds'] for v in measurements if v['complete_seconds'] is None)
            row['unusable_output_cost_seconds']=math.fsum(v['phases'][phase]['known_seconds'] for v in values if v['outcome']!='valid')
            row['prior_interruption_known_seconds']=math.fsum(v['prior_interruption_known_seconds'] for v in measurements)
            row['unknown_measurements']=sum(v['unknown_measurements'] for v in measurements)
            row['attempts_missing_call_return']=sum(v['attempts_missing_call_return'] for v in measurements)
            row['cost_scope']=SCOPES[phase]
            row['cost_estimator_condition']='Means/intervals use complete per-task phase totals; total_recorded_seconds also retains known portions of incomplete totals'
            row['failure_rate_definition']='Output-contract failures including numerical, resource and unclassified output failure; interval unavailable while infrastructure/not-run outcomes remain; not posterior convergence'
            row['unknown_time_imputed']=False
        reports[phase]=report
    return dict(policy=POLICY,phases=reports,operational_consumption=operation,
        primary_scopes_are_additive=False,attempts_are_statistical_repetitions=False,new_independent_repetitions=0,
        cached_execution_measured=False,scope='Shared whole-four-chain resampling; pointwise cost ratios condition on both outputs valid and require every such pair to have positive complete costs')
