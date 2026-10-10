#!/usr/bin/env python3
"""Original NUTS child-metadata audit; no sampling, reruns or causal classification.

Child durations overlap. This tool never subtracts them from parent wall time.
A missing worker has an unknown failure stage, not an assumed zero duration.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(root, members, name, provenance):
    expected=members[name]
    path=root/name
    data=path.read_bytes()
    if len(data)!=expected['bytes'] or digest(data)!=expected['sha256']:
        raise ValueError('Original member differs: '+name)
    provenance[name]=expected['sha256']
    return json.loads(data)


def metadata_member(prefix,candidate,worker,members):
    expected='worker-'+str(worker['chain'])
    if worker['result_directory']!=expected:raise ValueError('Child path differs')
    if candidate['status'] not in ('completed','failed'):raise ValueError('Unfinished candidate')
    name=prefix+expected+('/metadata.json' if candidate['status']=='completed' else '/partial-fit.json')
    if name not in members:raise ValueError('Declared child evidence absent from original manifest')
    return name


def extract_worker(task,candidate,worker,metadata):
    chain=worker['chain']
    if (chain not in range(4) or metadata['chain_seeds']!=[candidate['chain_seeds'][chain]] or
        metadata['target_id']!=candidate['target_id'] or metadata['draws_per_chain']!=int(task['budget'])):
        raise ValueError('Child identity/seed/budget differs')
    if metadata['warmup_per_chain']!=1024 or metadata['provider']!='pyro_cpu_nuts':
        raise ValueError('Unexpected formal NUTS child contract')
    timing=metadata['timing']
    for key in ('warmup','sample','finalization_diagnostics','transform','total'):
        if type(timing[key]) not in (int,float) or not math.isfinite(timing[key]) or timing[key]<0:
            raise ValueError('Invalid saved child duration')
    completed=metadata['status']=='completed'
    if completed and (timing['total']<=0 or
        sum(timing[k] for k in ('warmup','sample','finalization_diagnostics','transform'))>timing['total']+1e-6):
        raise ValueError('Nested child durations exceed inclusive total')
    records=metadata['chain_records']
    diag=records[0]['diagnostics'].get('q',{}) if len(records)==1 else {}
    ess=diag.get('n_eff')
    if ess is not None and (not isinstance(ess,list) or len(ess)!=len(metadata['names'])):
        raise ValueError('Legacy ESS shape differs')
    nonfinite=0 if ess is None else sum(v is None for v in ess)
    for value in ess or []:
        if value is not None and (type(value) not in (float,int) or not math.isfinite(value)):
            raise ValueError('Invalid serialized ESS')
    return dict(task_id=task['id'],model=task['model'],batch=int(task['batch']),
        replicate=int(task['replicate']),budget=int(task['budget']),task_outcome=task['outcome'],
        chain=chain,child_status=metadata['status'],dimension=len(metadata['names']),
        warmup_seconds=timing['warmup'],sample_seconds=timing['sample'],
        post_final_hook_seconds=timing['finalization_diagnostics'],transform_seconds=timing['transform'],
        child_total_seconds=timing['total'],worker_wall_seconds=worker['worker_wall'],
        post_final_hook_fraction=timing['finalization_diagnostics']/timing['total'] if completed else None,
        legacy_ess_present=ess is not None,legacy_ess_null=nonfinite,
        legacy_ess_all_null=ess is not None and nonfinite==len(ess),
        pyro_version=metadata['pyro_version'],torch_version=metadata['torch_version'])


def review(delivery,manifest,manifest_sha256,tasks,output,partial=False):
    root=Path(delivery);out=Path(output)
    if out.exists():raise FileExistsError(out)
    raw=Path(manifest).read_bytes()
    if digest(raw)!=manifest_sha256:raise ValueError('Transfer manifest checksum differs')
    members=json.loads(raw)['files'];provenance={}
    raw_tasks=Path(tasks).read_bytes()
    plan=[r for r in csv.DictReader(raw_tasks.decode().splitlines()) if r['phase']=='main' and r['workflow']=='cpu-nuts-spawn_chains']
    if len(plan)!=432 or len({r['id'] for r in plan})!=432:raise ValueError('All 432 NUTS tasks required')
    rows=[];task_rows=[];pending=[]
    for task in plan:
        prefix=f"formal-runs/batch-{int(task['batch']):02d}/main/tasks/{task['id']}/attempt-0001/"
        required=[prefix+n for n in ['state.json','completion.json','candidate.json']]
        if not all((root/n).is_file() for n in required):pending.append(task['id']);continue
        state,completion,candidate=[checked(root,members,n,provenance) for n in required]
        if (completion['state_sha256']!=members[prefix+'state.json']['sha256'] or
            state['outcome']!=task['outcome'] or any(state['task'][k]!=task[k] for k in ['id','model','workflow']) or
            state['task']['budget']!=int(task['budget'])):
            raise ValueError('Terminal task identity differs')
        workers=candidate['worker_records'];ids=[w['chain'] for w in workers]
        if len(set(ids))!=len(ids) or not set(ids)<=set(range(4)):raise ValueError('Aliased child')
        if candidate['workers_requested']!=4 or candidate['workers_allocated']!=4:
            raise ValueError('Unexpected NUTS process count')
        names=[]
        for w in workers:names.append(metadata_member(prefix,candidate,w,members))
        if not all((root/n).is_file() for n in names):pending.append(task['id']);continue
        children=[extract_worker(task,candidate,w,checked(root,members,n,provenance)) for w,n in zip(workers,names)]
        missing=set(range(4))-set(ids)
        if set(map(int,candidate['worker_errors']))!=missing:
            raise ValueError('Missing children do not match unresolved futures')
        if task['outcome']=='valid' and (missing or not all(r['child_status']=='completed' for r in children)):
            raise ValueError('Valid task lacks four complete children')
        rows+=children
        fractions=[r['post_final_hook_fraction'] for r in children if r['post_final_hook_fraction'] is not None]
        task_rows.append(dict(task_id=task['id'],model=task['model'],budget=int(task['budget']),
            outcome=task['outcome'],returned_workers=len(children),unreturned_workers=len(missing),
            median_returned_child_post_hook_fraction=statistics.median(fractions) if fractions else None,
            child_legacy_ess_all_null=sum(r['legacy_ess_all_null'] for r in children),
            failure_stage_of_unreturned_workers='unknown' if missing else 'not_applicable'))
    if pending and not partial:raise ValueError(f'Full review requires {len(pending)} further original task records')
    groups=[]
    for model,budget,outcome in sorted({(r['model'],r['budget'],r['outcome']) for r in task_rows}):
        group=[r for r in task_rows if (r['model'],r['budget'],r['outcome'])==(model,budget,outcome)]
        child=[r for r in rows if (r['model'],r['budget'],r['task_outcome'])==(model,budget,outcome)]
        fractions=[r['median_returned_child_post_hook_fraction'] for r in group if r['median_returned_child_post_hook_fraction'] is not None]
        groups.append(dict(model=model,budget=budget,outcome=outcome,tasks=len(group),
            returned_workers=len(child),unreturned_workers=sum(r['unreturned_workers'] for r in group),
            legacy_ess_all_null_workers=sum(r['legacy_ess_all_null'] for r in child),
            median_of_task_child_median_post_hook_fraction=statistics.median(fractions) if fractions else None,
            range_of_task_child_median_post_hook_fraction=[min(fractions),max(fractions)] if fractions else None))
    summary=dict(schema='compact-nuts-worker-review-v1',complete=not pending,partial_mode=partial,
        planned_tasks=432,inspected_tasks=len(task_rows),pending_task_ids=pending,
        task_outcome_counts=dict(Counter(r['outcome'] for r in task_rows)),returned_worker_records=len(rows),
        unreturned_workers=sum(r['unreturned_workers'] for r in task_rows),groups=groups,
        manifest_sha256=manifest_sha256,task_display_table_sha256=digest(raw_tasks),source_assets_sha256=provenance,
        interpretation=['Post-final-hook interval includes MCMC finalization, sample extraction/hook comparison and legacy diagnostics; it is not isolated ESS timing',
            'Child durations overlap and are not subtracted from parent wall time or summed as latency',
            'Returned children of failed tasks remain partial evidence, never complete-fit samples',
            'No stage or cause is imputed for unreturned workers',
            'Group fractions are descriptive medians of per-task child medians, not independent child confidence intervals'],
        new_sampler_calls=0,new_diagnostic_calls=0,new_formal_repetitions=0)
    out.mkdir(parents=True)
    for name,values in [('workers',rows),('tasks',task_rows)]:
        with (out/(name+'.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(values[0]) if values else ['task_id'],lineterminator='\n');w.writeheader();w.writerows(values)
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['delivery','manifest','manifest-sha256','tasks','output']:p.add_argument('--'+name,required=True)
    p.add_argument('--partial',action='store_true')
    summary=review(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in summary.items() if k not in ['source_assets_sha256','pending_task_ids','groups']},indent=2))
