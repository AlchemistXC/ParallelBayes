"""Task outcomes and all-attempt cost accounting for declared recoveries.

References and statistics in the historical uncertainty module stay unchanged.
Output-contract failures include resource failures but never hide their class.
"""
import json
import math
from pathlib import Path

from formal_uncertainty import analyze_costs
from formal_runtime import file_hash, fingerprint, task_artifact_kind, validate_worker_eligibility

OUTCOMES=('valid','measurement_available','numerical_failure','resource_failure','output_failure_unclassified',
          'infrastructure_interruption','not_run')


def read_attempt(directory):
    """Verify sealed state or a recovery snapshot before classifying evidence."""
    directory=Path(directory).resolve()
    statefile=directory/'state.json';completion=directory/'completion.json'
    recovery=directory.with_name(directory.name+'.recovery')/'recovery.json'
    cost=None
    if recovery.exists():
        record=json.loads(recovery.read_text());unsigned=dict(record);digest=unsigned.pop('recovery_sha256')
        if fingerprint(unsigned)!=digest:raise ValueError('Recovery checksum differs')
        assets={p.relative_to(directory).as_posix():file_hash(p) for p in directory.rglob('*') if p.is_file()}
        if assets!=record['original_assets']:raise ValueError('Recovery original asset checksum differs')
        binding=json.loads((directory/'binding.json').read_text())
        if fingerprint(binding)!=record['binding_sha256']:raise ValueError('Recovery binding checksum differs')
        worker_result=directory/'attempt-0001/worker-result.json'
        if worker_result.exists() and json.loads(worker_result.read_text()).get('status')=='failed':
            raise ValueError('Recovery classification conflicts with known failed output')
        if statefile.exists() and json.loads(statefile.read_text())['status']!='interrupted':
            raise ValueError('Recovery conflicts with an existing final output classification')
        if record.get('outcome')!='infrastructure_interruption' or record.get('samples_eligible') is not False:
            raise ValueError('Recovery outcome classification is inconsistent')
        outcome='infrastructure_interruption';cost=record['cost_seconds'];digest=file_hash(recovery)
    else:
        state=json.loads(statefile.read_text());receipt=json.loads(completion.read_text())
        if receipt['state_sha256']!=file_hash(statefile):raise ValueError('Terminal state checksum differs')
        binding=json.loads((directory/'binding.json').read_text())
        if fingerprint(binding)!=state['binding_sha256']:raise ValueError('Terminal binding checksum differs')
        for name,h in state['assets'].items():
            path=directory/name
            if not path.resolve().is_relative_to(directory) or path.is_symlink() or file_hash(path)!=h:
                raise ValueError('Terminal asset checksum differs')
        kind=task_artifact_kind(binding['task'])
        if state.get('artifact_kind','posterior')!=kind:raise ValueError('Terminal artifact kind differs')
        if kind=='cache_measurement' and state['samples_eligible'] is not False:
            raise ValueError('Measurement terminal cannot contain eligible posterior samples')
        if state['status']=='completed':
            validate_worker_eligibility(binding['task'],state['worker_result'])
            if kind=='posterior':
                if state['samples_eligible'] is not True:raise ValueError('Completed output eligibility differs')
                outcome='valid'
            else:
                if state.get('measurement_available') is not True:raise ValueError('Completed measurement unavailable')
                outcome='measurement_available'
        elif state['status']=='interrupted':outcome='infrastructure_interruption'
        elif state['status']=='failed':
            if state['samples_eligible'] is not False:raise ValueError('Failed output eligibility differs')
            if state['failure_kind']=='process_tree_memory_guard':outcome='resource_failure'
            else:
                outcome=(state.get('worker_result') or {}).get('failure_category','output_failure_unclassified')
                if outcome not in ('numerical_failure','resource_failure','output_failure_unclassified'):
                    raise ValueError('Unsupported explicit worker failure category')
        else:raise ValueError('Unknown terminal status')
        cost=receipt['inclusive_preflight_through_terminal_seconds'];digest=file_hash(statefile)
    return dict(attempt_id=str(directory),binding_sha256=fingerprint(binding),outcome=outcome,seconds=cost,
                evidence_sha256=digest,cost_scope='runtime_v1_preflight_through_terminal',
                fixed_task=binding['task'],artifact_kind=task_artifact_kind(binding['task']),unknown_time_imputed=False)


def summarize_attempts(attempts):
    """Reduce one ordered history without losing partial measured consumption."""
    if not attempts:
        return dict(outcome='not_run',total_seconds=None,known_seconds=0.,unknown_cost_attempts=0,
                    prior_interruption_known_seconds=0.,attempt_count=0)
    if len({x['attempt_id'] for x in attempts})!=len(attempts):raise ValueError('Duplicate attempt identities')
    if len({x['binding_sha256'] for x in attempts})!=1:raise ValueError('Retry request/environment binding changed')
    if len({x.get('cost_scope','unspecified') for x in attempts})!=1:raise ValueError('Attempt timing scopes differ')
    kinds={x.get('artifact_kind','posterior') for x in attempts}
    if len(kinds)!=1:raise ValueError('Mixed posterior and measurement histories')
    for i,row in enumerate(attempts):
        if row['outcome']=='measurement_available' and row.get('artifact_kind','posterior')!='cache_measurement':
            raise ValueError('Measurement outcome requires measurement artifact kind')
        if row['outcome']=='valid' and row.get('artifact_kind','posterior')!='posterior':
            raise ValueError('Measurement cannot have a valid posterior outcome')
        if row['outcome'] not in OUTCOMES or row['outcome']=='not_run':raise ValueError('Unknown executed attempt outcome')
        if i<len(attempts)-1 and row['outcome']!='infrastructure_interruption':
            raise ValueError('Only infrastructure interruptions may precede an explicit retry')
        value=row['seconds']
        if value is not None and (not math.isfinite(value) or value<0):raise ValueError('Invalid attempt duration')
    unknown=sum(x['seconds'] is None for x in attempts)
    known=math.fsum(x['seconds'] for x in attempts if x['seconds'] is not None)
    return dict(outcome=attempts[-1]['outcome'],total_seconds=None if unknown else known,
        known_seconds=known,unknown_cost_attempts=unknown,
        prior_interruption_known_seconds=math.fsum(x['seconds'] for x in attempts[:-1] if x['seconds'] is not None),
        attempt_count=len(attempts))


def analyze_attempt_costs(plan,executions,pairs=(),phase='unspecified'):
    """Pointwise cost inference from complete task totals; all known parts kept.

    executions[workflow][repetition] is the ordered, verified attempt history.
    Missing old cost makes the full task total unknown even if a retry succeeds.
    Failure rates refer to output availability after permitted infrastructure
    recovery, not convergence or a pure numerical-algorithm failure probability.
    """
    if any(row.get("artifact_kind","posterior")!="posterior" for tasks in executions.values() for attempts in tasks.values() for row in attempts):
        raise ValueError("Measurement histories are not posterior inference costs")
    reduced={}
    for workflow,rows in executions.items():
        if set(rows)!=set(plan.replicate_ids):raise ValueError('Every planned repetition required')
        reduced[workflow]={rep:summarize_attempts(rows[rep]) for rep in plan.replicate_ids}
    costs={w:{r:x['total_seconds'] for r,x in rows.items()} for w,rows in reduced.items()}
    # The established BCa/CP machinery only needs valid vs terminal output
    # failure for its arithmetic. Its internal failure label is replaced by
    # the actual explicit categories below before any report is returned.
    binary={w:{r:('numerical_failure' if x['outcome'] in ('resource_failure','output_failure_unclassified') else x['outcome'])
               for r,x in rows.items()} for w,rows in reduced.items()}
    report=analyze_costs(plan,costs,binary,pairs,phase)
    for w,row in report['workflows'].items():
        values=list(reduced[w].values())
        row['outcome_counts']={k:sum(x['outcome']==k for x in values) for k in OUTCOMES}
        row['total_recorded_seconds']=math.fsum(x['known_seconds'] for x in values)
        row['known_partial_task_seconds']=math.fsum(x['known_seconds'] for x in values if x['total_seconds'] is None)
        row['unusable_output_cost_seconds']=math.fsum(x['known_seconds'] for x in values if x['outcome']!='valid')
        row['prior_interruption_known_seconds']=math.fsum(x['prior_interruption_known_seconds'] for x in values)
        row['attempts_with_unknown_cost']=sum(x['unknown_cost_attempts'] for x in values)
        row['executed_attempts']=sum(x['attempt_count'] for x in values)
        row['failure_rate_definition']='Probability of no eligible output after declared infrastructure recovery under the fixed resource/output contract; not convergence or numerical failure alone'
        row['cost_estimator_condition']='Means and BCa use complete per-task totals; total_recorded_seconds also retains known parts of incomplete histories'
        row['unobserved_attempt_cost_is_zero']=False
    report['attempts_are_statistical_replicates']=False
    report['scope']='Explicit outcome categories and all known attempt consumption. Unknown attempt cost makes paired total-cost ratios unavailable; finite tests do not establish recovery safety on every platform.'
    return report
