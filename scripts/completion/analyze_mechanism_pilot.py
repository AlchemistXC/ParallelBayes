"""Rebuild descriptive pilot tables, retaining unsuccessful and pending cells."""
import argparse
import csv
import json
from pathlib import Path
import statistics
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from mechanism_runner import read_plan,sha,write,actual_hash,master_tape
from parallelbayes.reference import make_reference


def analyze(plan_path,run,output):
    if output.exists():raise FileExistsError('Preserve prior pilot analysis')
    if output==run or run in output.parents:raise ValueError('Do not write into raw evidence')
    plan=read_plan(plan_path);manifest=json.loads((run/'run.json').read_text())
    if manifest['protocol_sha256']!=plan['protocol_sha256']:raise ValueError('Run/protocol identity differs')
    rows=[];probes=[];statuses=[];states={};master={}
    target_ids={name:make_reference(spec).target_id for name,spec in plan['models'].items()}
    for g in plan['groups']:
        folder=run/'groups'/g['id'];path=folder/'state.json'
        labels=['sequential']+[('quasi_deer' if g['kernel']=='mala' else 'online_picard')+f'-w{w}' for w in g['windows']]
        if not path.exists():
            statuses.append('pending')
            for label in labels:rows.append(dict(group=g['id'],model=g['model'],kernel=g['kernel'],label=label,status='pending'))
            continue
        state=json.loads(path.read_text());states[g['id']]=sha(path)
        if state['group']!=g or state['device']!=manifest['device']:raise ValueError('Task identity differs')
        for name,digest in state['assets'].items():
            if sha(folder/name)!=digest:raise ValueError('Raw asset checksum mismatch: '+name)
        attempt=folder/state['attempt']
        key=(g['model'],g['replicate'])
        if key not in master:master[key]=master_tape(plan,*key)
        expected={k:a[:g['chains'],:g['draws']] for k,a in master[key].items()}
        with np.load(attempt/'inputs.npz',allow_pickle=False) as z:tape={k:z[k].copy() for k in z.files}
        if actual_hash(tape)!=actual_hash(expected):raise ValueError('Saved actual input is not the frozen prefix')
        statuses.append(state['status'])
        records={label:[] for label in labels}
        for record in state['records']:
            data=json.loads((attempt/record['record']).read_text())
            if data['status']=='completed':
                if data['target_id']!=target_ids[g['model']] or data['tape_sha256']!=actual_hash(expected):
                    raise ValueError('Recorded target or actual tape identity differs')
                expected_config=dict(chains=g['chains'],draws=g['draws'],kernel=g['kernel'],step_size=g['step_size'])
                if any(data['config'][k]!=v for k,v in expected_config.items()):
                    raise ValueError('Recorded transition configuration differs')
            records[record['label']].append((record,data))
        local=[]
        for label in labels:
            rr=records[label]
            first=next((x for _,x in rr if x['measurement']['phase']=='audited_first_call'),None)
            warmed=[x for _,x in rr if x['measurement']['phase']=='warmed_replay']
            post=[x for _,x in rr if x['measurement']['phase']=='post_probe_replay']
            valid=bool(first and first['status']=='completed' and first.get('audit',{}).get('passed') and
                       len(warmed)==plan['technical_replays'] and len(post)==1 and all(x['status']=='completed' for x in warmed+post))
            if valid:
                initial_record=next(r for r,x in rr if x is first)
                with np.load(attempt/initial_record['raw'],allow_pickle=False) as a:
                    reference_path=a['unconstrained'].copy();reference_accept=a['accept'].copy()
                for record,_ in rr:
                    with np.load(attempt/record['raw'],allow_pickle=False) as a:
                        if not np.array_equal(a['unconstrained'],reference_path) or not np.array_equal(a['accept'],reference_accept):
                            raise ValueError('A completed replay changed actual paths/events')
            status='completed' if valid else ('failed' if rr else 'not_executed')
            row=dict(group=g['id'],model=g['model'],kernel=g['kernel'],replicate=g['replicate'],
                label=label,device=manifest['device'],chains=g['chains'],draws=g['draws'],
                total_transitions=g['chains']*g['draws'],step_size=g['step_size'],role=g['role'],status=status,
                group_status=state['status'],cached_sample_seconds=None,paired_cached_ratio=None)
            if first and first['status']=='completed':
                meta=next(r for r,x in rr if x is first)
                with np.load(attempt/meta['raw'],allow_pickle=False) as a:
                    row['acceptance_fraction']=float(a['accept'].mean())
                d=first['diagnostics'];n=row['total_transitions']
                row.update(first_audit_seconds=first['timing']['audit'],forward_maps_per_transition=d['forward_evals']/n,
                           JVPs_per_transition=d['jvp_evals']/n,solver_iterations=d['iterations'],
                           confirmed=d['confirmed'],state_repairs=first['state_repairs'],fallback=first['fallback'])
                if g['kernel']=='rwm' and label!='sequential':
                    row['mean_confirmed_prefix_per_round']=statistics.mean(x['confirmed_prefix'] for x in d['rounds'])
            if valid:
                row.update(cached_sample_seconds=statistics.median(x['timing']['sample'] for x in warmed),
                    api_wall_seconds=statistics.median(x['measurement']['wall_seconds'] for x in warmed),
                    process_cpu_percent=statistics.median(x['measurement']['process_cpu_percent'] for x in warmed),
                    host_scalar_wait_seconds=statistics.median(x['diagnostics']['host_scalar_wait_seconds'] for x in warmed),
                    post_probe_sample_seconds=post[0]['timing']['sample'])
                row['post_probe_over_preprobe']=row['post_probe_sample_seconds']/row['cached_sample_seconds']
                row['seconds_per_confirmed_transition']=row['cached_sample_seconds']/row['total_transitions']
            local.append(row)
        baseline=local[0]
        pairs=json.loads((attempt/'comparison.json').read_text())['pairs'] if (attempt/'comparison.json').exists() else []
        for row in local:
            paired=next((p['passed'] for p in pairs if p['label']==row['label']),row['label']=='sequential')
            if baseline['status']==row['status']=='completed' and paired:
                row['paired_cached_ratio']=baseline['cached_sample_seconds']/row['cached_sample_seconds']
            rows.append(row)
        for probe in attempt.glob('probe-w*/result.json'):
            p=json.loads(probe.read_text())
            if p['status']!='passed':
                probes.append(dict(group=g['id'],model=g['model'],kernel=g['kernel'],status=p['status'],error=p.get('error')))
                continue
            for operation,timings in p['measurements'].items():
                probes.append(dict(group=g['id'],model=g['model'],kernel=g['kernel'],device=manifest['device'],
                    chains=p['shape'][0],width=p['shape'][1],dimension=p['shape'][2],operation=operation,
                    seconds_per_call=statistics.median(x['seconds_per_call'] for x in timings),
                    process_cpu_percent=statistics.median(x['process_cpu_percent'] for x in timings),
                    status='passed',components_are_additive=False))
    output.mkdir(parents=True)
    for name,data in [('workflows',rows),('probes',probes)]:
        fields=sorted(set().union(*(set(r) for r in data))) if data else ['status']
        with (output/(name+'.csv')).open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(data)
    summary=dict(protocol_sha256=plan['protocol_sha256'],source_commit=plan['source_commit'],
        run_manifest_sha256=sha(run/'run.json'),state_sha256=states,analyzer_sha256=sha(Path(__file__)),
        device=manifest['device'],groups_planned=len(plan['groups']),
        groups_completed=statuses.count('completed'),groups_failed=statuses.count('failed'),groups_pending=statuses.count('pending'),
        workflows_planned=sum(1+len(g['windows']) for g in plan['groups']),
        workflows_completed=sum(r['status']=='completed' for r in rows),
        workflow_status_counts={s:sum(r['status']==s for r in rows) for s in sorted(set(r['status'] for r in rows))},
        independent_tapes_per_model=plan['independent_tapes_per_model'],technical_replays=plan['technical_replays'],
        scope='Descriptive pilot tables; no confidence intervals, inference convergence or general speedup claim',
        cost_note='Fixed-state probe operations overlap in real execution and must not be added. Post-probe timing is a sensitivity check, not causal overhead subtraction.')
    write(output/'summary.json',summary)
    write(output/'checksums.json',{p.name:sha(p) for p in output.iterdir() if p.is_file() and p.name!='checksums.json'})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analyze(a.plan.resolve(),a.run.resolve(),a.output.resolve())
