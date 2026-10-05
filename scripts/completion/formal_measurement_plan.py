"""Prespecified input-stratified cache probes, separate from primary inference.

This module allocates and validates work; it never runs an executor, generates
random inputs, examines outcomes, or grants a formal-launch authorization.
"""
from collections import defaultdict
import copy
import hashlib
from batch_contract import WORKFLOWS
from formal_inputs import MODEL_CODES
from formal_runtime import fingerprint

POLICY='paired-prepared-mh-probes-v1'


def create_measurement_plan(identity,primary_tasks,*,batch_size=32,selected_per_batch=8,replays=3):
    """Select input repetitions before results, retaining every matching MH slot.

Rank SHA256(identity, model, batch, replicate) within each model/batch, keep
min(quota, available) inputs, then use the same subset for every budget/device/
kernel. Scheduling has its own domain-separated rank; no sampler RNG is used.
A selected task is never replaced because its primary or probe output failed.
"""
    if not isinstance(identity,str) or not identity:raise ValueError('Explicit primary identity required')
    if any(type(v) is not int or v<1 for v in (batch_size,selected_per_batch,replays)) or selected_per_batch>batch_size:
        raise ValueError('Positive integer counts and quota no greater than batch size required')
    tasks=copy.deepcopy(list(primary_tasks));seen=set();slots=defaultdict(lambda:defaultdict(set))
    fields={'id','model','replicate','budget','workflow','device','kernel','executor','batch','input'}
    for t in tasks:
        if set(t)!=fields or t['model'] not in MODEL_CODES or t['workflow'] not in WORKFLOWS:
            raise ValueError('Task identity/schema differs')
        if type(t['replicate']) is not int or not 0<=t['replicate']<2**32 or type(t['budget']) is not int or t['budget']<4:
            raise ValueError('Task identity/shape differs')
        row={k:t[k] for k in ('model','replicate','budget','workflow','device','kernel','executor')}
        if (any(t[k]!=v for k,v in WORKFLOWS[t['workflow']].items()) or
            t['id']!=fingerprint(dict(experiment=identity,**row))[:24] or
            t['batch']!=t['replicate']//batch_size or t['input']!=f"{t['model']}-rep{t['replicate']:04d}.npz"):
            raise ValueError('Task identity/input mapping differs')
        if t['id'] in seen:raise ValueError('Duplicate task identity')
        seen.add(t['id'])
        slots[t['model']][t['replicate']].add((t['budget'],t['device'],t['kernel'],t['executor']))
    if not tasks:raise ValueError('Nonempty primary task grid required')
    for model,byrep in slots.items():
        reference=next(iter(byrep.values()))
        if any(s!=reference for s in byrep.values()):raise ValueError('Incomplete paired grid across repetitions')
        mh=[s for s in reference if s[2]!='nuts']
        if not mh:raise ValueError('Complete MH pairs required for cache probes')
        for budget,device,kernel,executor in mh:
            expected={'sequential','online_picard' if kernel=='rwm' else 'quasi_deer'}
            actual={s[3] for s in mh if s[:3]==(budget,device,kernel)}
            if actual!=expected:raise ValueError('Complete sequential/time pairs required')
    def rank(role,*parts):
        return fingerprint([POLICY,role,identity,*parts])
    strata=[];chosen=set()
    for model,byrep in sorted(slots.items()):
        batches=defaultdict(list)
        for rep in byrep:batches[rep//batch_size].append(rep)
        for batch,reps in sorted(batches.items()):
            ordered=sorted(reps,key=lambda rep:(rank('selection',model,batch,rep),rep))
            selected=sorted(ordered[:selected_per_batch]);chosen.update((model,rep) for rep in selected)
            strata.append(dict(model=model,batch=batch,available_replicates=sorted(reps),selected_replicates=selected))
    probes=[]
    for t in tasks:
        if t['kernel']=='nuts' or (t['model'],t['replicate']) not in chosen:continue
        probe=dict(t);probe['primary_task_id']=probe.pop('id')
        probe.update(initial_calls=1,prepared_replays=replays,samples_eligible=False,
            primary_outcome_is_selection_criterion=False)
        probe['id']=fingerprint(dict(policy=POLICY,identity=identity,probe=probe))[:24]
        probes.append(probe)
    probes.sort(key=lambda p:(p['batch'],rank('order',p['id']),p['id']))
    result=dict(schema=1,policy=POLICY,primary_identity=identity,batch_size=batch_size,
        selected_per_batch=selected_per_batch,replays=replays,
        primary_grid_sha256=fingerprint(sorted(tasks,key=lambda t:t['id'])),
        primary_task_count=len(tasks),strata=strata,probes=probes,
        total_executor_calls=len(probes)*(replays+1),statistical_repetitions_added=0,
        probe_phase='separate phase after the primary batch is terminal or explicitly retained interrupted; no concurrent primary timing',
        nuts_cached_measurement=False,independent_unit='selected original complete four-chain repetition',
        failed_selected_tasks_replaced=False,execution_authorized=False)
    result['allocation_sha256']=fingerprint(result)
    return result


def validate_measurement_plan(plan,primary_tasks):
    """Rebuild the allocation from the original grid; a self-checksum is insufficient."""
    expected=create_measurement_plan(plan['primary_identity'],primary_tasks,batch_size=plan['batch_size'],
                                    selected_per_batch=plan['selected_per_batch'],replays=plan['replays'])
    if expected!=plan:raise ValueError('Saved allocation differs from its complete primary grid')
    return plan


def summarize_probe(probe,records,*,expected_tape_sha256,expected_target_id,expected_config):
    """Reduce a verified prepared-execution record without cherry-picking timings.

The caller verifies raw arrays/independent audit and immutable file manifests.
This reducer checks the recorded input/config identities and complete ordered
frame. Any failed/missing initial or replay invalidates its cached-cost point;
all measured execution costs remain recorded. It never grants sample validity.
"""
    import math
    from statistics import median
    expected=probe['initial_calls']+probe['prepared_replays']
    if probe['initial_calls']!=1 or type(probe['prepared_replays']) is not int or probe['prepared_replays']<1 or len(records)!=expected:
        raise ValueError('Complete declared replay frame required; use None for missing calls')
    valid=0;known=0.;missing=0
    for i,r in enumerate(records):
        if r is None:missing+=1;continue
        if (r['execution_index']!=i or r['has_prior_execution'] is not (i>0) or
            r['tape_sha256']!=expected_tape_sha256 or r['target_id']!=expected_target_id or
            r['config']!=expected_config or r['samples_eligible'] is not False):
            raise ValueError('Replay input/configuration/ordinal identity differs')
        seconds=r['executor_wall_seconds']
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<=0:
            raise ValueError('A measured replay requires positive finite execution time')
        if r['status'] not in ('candidate','failed') or type(r['technical_output_valid']) is not bool:
            raise ValueError('Explicit replay numerical outcome required')
        if r['status']=='failed' and r['technical_output_valid']:raise ValueError('Failed execution cannot be numerically valid')
        known+=seconds;valid+=bool(r['technical_output_valid'])
    all_valid=valid==expected
    return dict(probe_id=probe['id'],primary_task_id=probe['primary_task_id'],
        expected_executions=expected,observed_executions=expected-missing,missing_executions=missing,
        valid_executions=valid,all_executions_valid=all_valid,
        cached_seconds=median(r['executor_wall_seconds'] for r in records[1:]) if all_valid else None,
        cached_summary='median of all declared prepared replays, available only if initial and all replays satisfy the numerical contract',
        known_executor_seconds=known,complete_executor_seconds=None if missing else known,
        samples_eligible=False,statistical_repetitions_added=0,
        scope='Executor wall only; preparation, transfer, audits and archives remain separate measured records')
