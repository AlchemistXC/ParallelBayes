"""Generate the resource amendment and byte ledger, never RNG inputs or samples.

This is a design artifact, deliberately not the accepted formal-study schema.
The old freezer/controller must not consume it. Reuses checked storage formulas.
"""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys


def build(root):
    root = Path(root).resolve()
    sys.path[:0] = [str(root/'scripts/completion'), str(root/'scripts/analysis')]
    from formal_study_plan import create_study_plan
    from batch_contract import create_tasks, WORKFLOWS
    from formal_runtime import fingerprint, file_hash
    from audit_formal_storage import main_array_bytes, cache_array_bytes
    catalog_path = root/'benchmark/protocols/inference-budget-pilot-mac-v1.json'
    reference_path = root/'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis/reference-contract.json'
    old = create_study_plan('windows-formal-inference-v1', json.loads(catalog_path.read_text()))
    assert old['design_sha256'] == '68a1cba1b9309216d237ac4613531216f167ff344dfdfcb72dc3aaca0ca0baa5'
    identity = 'windows-compact-inference-v1'
    models = [t['name'] for t in old['targets']]
    budgets = [1024, 4096]
    groups = [dict(models=models, replicates=list(range(24)), budgets=budgets, workflows=list(WORKFLOWS))]
    tasks = create_tasks(identity, groups, batch_size=8)
    cache_models, cache_reps = ['G1', 'G2', 'L2', 'W1'], [0, 8, 16, 23]
    probes = []
    for t in tasks:
        if t['kernel'] != 'nuts' and t['model'] in cache_models and t['replicate'] in cache_reps:
            probe = dict(t, initial_calls=1, prepared_replays=3, primary_task_id=t['id'])
            probe['id'] = fingerprint(dict(identity=identity, role='compact-cache-v1', primary=t['id']))[:24]
            probes.append(probe)
    inputs = {f'{m}-rep{r:04d}.npz': dict(model=m, replicate=r, chains=4,
        dimension=next(t['dimension'] for t in old['targets'] if t['name']==m), steps=4608,
        roles=['initial', 'noise', 'log_uniform', 'directions', 'nuts_seeds'])
        for m in models for r in range(24)}
    batches = [dict(batch=b, replicates=list(range(8*b,8*(b+1))),
        main_tasks=sum(t['batch']==b for t in tasks), cache_probes=sum(t['batch']==b for t in probes)) for b in range(3)]
    spec = dict(schema='compact-study-design-v1', identity=identity, date='2026-10-08',
        status='design_only_native_adapter_not_implemented',
        amendment=dict(supersedes_design_sha256=old['design_sha256'],
            old_sampling_started='user_confirmed_progress_not_independently_received',
            reason='User hardware/storage constraint; approximately 50–80 GiB additional storage',
            old_pause_verified=False, old_outputs_preservation_required=True, old_outputs_preservation_verified=False,
            new_identity_and_fresh_actual_random_arrays_required=True,
            reuse_old_successful_subset=False, fully_prospective_preregistration=False),
        targets=copy.deepcopy(old['targets']), groups=groups, batches=batches,
        counts=dict(main=len(tasks), main_MH=sum(t['kernel']!='nuts' for t in tasks),
            main_NUTS=sum(t['kernel']=='nuts' for t in tasks), cache=len(probes),
            cache_numerical_calls=4*len(probes), inputs=len(inputs)),
        independent_repetitions_per_target=24, batch_size=8, chains=4,
        controls=old['controls'], initial_policy=old['initial_policy'],
        trajectory_policy=old['trajectory_policy'], analysis_policy=old['analysis_policy'],
        execution_policy=old['execution_policy'], cost_policy=old['cost_policy'],
        input_requirements=inputs,
        cache_policy=dict(models=cache_models, original_replicates=cache_reps, budgets=budgets,
            workflows=[w for w,v in WORKFLOWS.items() if v['kernel']!='nuts'],
            initial_calls=1, prepared_replays=3, inference_samples=False,
            summary='Per-input median of 3 prepared calls only when initial and all 3 replays pass full path/events and have complete timings; otherwise median and ratio undefined; retain every call and failure; no BCa at n=4',
            replace_failed_inputs=False),
        primary_task_table_sha256=fingerprint(tasks), cache_table_sha256=fingerprint(probes),
        sources=dict(catalog_sha256=file_hash(catalog_path), reference_sha256=file_hash(reference_path)),
        sampler_calls_generated=0, actual_random_inputs_generated=0, sampling_allowed=False,
        native_environment_frozen=False, formal_inference_complete=False)
    spec['design_sha256'] = fingerprint(spec)
    ctrl=spec['controls']; c=ctrl['chains']; dims={t['name']:t['dimension'] for t in spec['targets']}
    ref=json.loads(reference_path.read_text()); functions={m:len(ref[m]['names']) for m in models}
    costs=Counter(); receiver=0
    for r in inputs.values():
        costs['master_inputs'] += 8*(c*r['dimension']+c*r['steps']*(2*r['dimension']+1)+c)
    for t in tasks:
        costs.update(main_array_bytes(t,dims[t['model']],ctrl,5056))
        one=t['budget']*c*functions[t['model']]*8
        costs['original_two_function_binaries']+=2*one; receiver+=3*one
    for p in probes:
        costs['cache_four_calls_arrays']+=cache_array_bytes(p,dims[p['model']],ctrl)
    reserve=(len(tasks)+len(probes))*1024**2; base=sum(costs.values())+reserve
    old_ids={t['id'] for t in old['tasks']}
    assert not old_ids.intersection(t['id'] for t in tasks)
    assert len(tasks)==3888 and len(probes)==256 and len(inputs)==216
    assert sum(functions.values())==36
    assert [b['main_tasks'] for b in batches]==[1296]*3
    assert [b['cache_probes'] for b in batches]==[64,64,128]
    # Inference repetitions and cache calls are different units.
    result=dict(schema='compact-storage-ledger-v1', design_sha256=spec['design_sha256'],
        named_arrays_bytes=dict(costs), named_arrays_total_bytes=sum(costs.values()),
        retained_success_attempt_reserves_bytes=reserve, receiver_function_binaries_bytes=receiver,
        scenarios_bytes=dict(one_Windows_original=base, one_Mac_original_and_receiver=base+receiver,
            two_machine_originals_and_receiver=2*base+receiver,
            three_full_copies_and_receiver=3*base+receiver),
        zero_failures_n24_pointwise_two_sided_95_percent_upper=1-0.025**(1/24),
        reductions=dict(main_fraction=1-len(tasks)/len(old['tasks']),
            cache_fraction=1-len(probes)/len(old['cache_allocation']['probes']),
            main_retained_steps_fraction=1-sum(t['budget']*c for t in tasks)/sum(t['budget']*c for t in old['tasks'])),
        assumptions=['all tasks succeed once; no retries', 'native NUTS RNG state length 5056 bytes as in finite v2',
            'unchanged saved array roles and float64; actual tape shape includes discarded draws',
            'no full tar plus duplicate extracted tree on the same machine'],
        exclusions=['JSON, observation logs, SQLite and metadata', 'failed and partial retries',
            'NPY/ZIP/TAR headers and filesystem allocation', 'transfer buffers and extra analysis outputs',
            'old already-started study; environments and history'],
        capacity_guarantee=False, compression_forecast=False, runtime_forecast=False,
        sampler_calls=0, actual_inputs_generated=0)
    result['planning_script_sha256']=file_hash(Path(__file__))
    return spec,result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Preserve existing design outputs')
    spec,result=build(args.root)
    args.output.mkdir(parents=True)
    for name,value in [('design.json',spec),('storage.json',result)]:
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(counts=spec['counts'],design_sha256=spec['design_sha256'],
        scenario_GiB={k:v/1024**3 for k,v in result['scenarios_bytes'].items()},sampler_calls=0)))
