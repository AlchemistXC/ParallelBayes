#!/usr/bin/env python3
"""Read-only v5 companion: pinned phase records, cache subsets and L1 ties.

No formal samples, outcomes, reference values or bootstrap intervals are changed.
Supply an already verified formal delivery and receiver index. Each raw member
read below is checked again against that index before use.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics

import numpy as np


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(project, delivery, index, statistics_dir, output):
    project, delivery, index, statistics_dir, out = map(Path,
        (project, delivery, index, statistics_dir, output))
    out.mkdir(parents=True, exist_ok=False)
    db = sqlite3.connect((index/'files.sqlite3').resolve().as_uri()+'?mode=ro', uri=True)
    sources = {}
    manifest_path = statistics_dir/'SHA256.json'
    if sha(manifest_path) != 'd928a497889e11f6aaf5829bf1ffd807a647a880a5d4ae7cef4acf3046c34bfb':
        raise ValueError('Verified Mac statistics manifest differs')
    statistics_manifest = json.loads(manifest_path.read_text())
    sources['statistics/SHA256.json'] = sha(manifest_path)

    def bound(relative):
        p = delivery/relative
        record = db.execute('SELECT bytes,sha256 FROM files WHERE path=?', (relative,)).fetchone()
        if record is None or p.stat().st_size != record[0] or sha(p) != record[1]:
            raise ValueError('Raw member failed index binding: '+relative)
        sources['delivery/'+relative] = record[1]
        return p

    def saved(name):
        p = statistics_dir/name
        if sha(p) != statistics_manifest[name]:
            raise ValueError('Saved statistics member differs: '+name)
        sources['statistics/'+name] = sha(p)
        return json.loads(p.read_text())

    rows = saved('W1/task-frame.json')
    rows = [r for r in rows if r['phase']=='main' and r['task']['budget']==4096]
    assert len(rows)==216 and all(r['outcome']=='valid' for r in rows)
    decomposed = []
    for r in rows:
        t = r['task']
        prefix = f"formal-runs/batch-{t['batch']:02}/main/tasks/{t['id']}/attempt-0001/"
        phases = json.loads(bound(prefix+'ordinary-phases.json').read_text())['phases']
        assert all(p['status']=='completed' and p['synchronization_included'] for p in phases)
        expected = ('source_environment_input_target', 'ordinary_sampling_including_transfer_transform',
                    'ordinary_full_array_output', 'ordinary_functions_and_R_diagnostics')
        assert tuple(p['name'] for p in phases)==expected
        ordinary = r['costs']['phases']['ordinary_workflow']['complete_seconds']
        audit = r['costs']['phases']['research_execution']['complete_seconds']
        gap = ordinary-sum(p['wall_seconds'] for p in phases)
        assert gap >= 0 and audit >= ordinary
        decomposed.append(dict(id=t['id'],workflow=t['workflow'],replicate=t['replicate'],
            ordinary=ordinary, startup_gaps_exit=gap, target=phases[0]['wall_seconds'],
            sampling_transfer_transform=phases[1]['wall_seconds'], output=phases[2]['wall_seconds'],
            functions_R_diagnostics=phases[3]['wall_seconds'], additional_audit=audit-ordinary))
    summary = []
    for w in sorted({r['workflow'] for r in decomposed}):
        group = [r for r in decomposed if r['workflow']==w]
        assert len(group)==24
        summary.append(dict(workflow=w,n=24,**{k:statistics.mean(r[k] for r in group)
            for k in group[0] if k not in ('id','workflow','replicate')}))
    cache_rows = list(csv.DictReader((project/'execution/windows-compact/formal-results/W1/cache.csv').open()))
    sources['project/execution/windows-compact/formal-results/W1/cache.csv'] = sha(project/'execution/windows-compact/formal-results/W1/cache.csv')
    boundaries = []
    for device in ('cpu','cuda'):
        for kernel, executor in (('rwm','online_picard'),('mala','quasi_deer')):
            left, right = device+'-'+kernel+'-sequential', device+'-'+kernel+'-'+executor
            cache = {w:json.loads(next(r['per_input_seconds'] for r in cache_rows
                if r['workflow']==w and int(r['budget'])==4096)) for w in (left,right)}
            reps = sorted(set(cache[left]) & set(cache[right]),key=int)
            assert list(map(int,reps))==[0,8,16,23]
            def gm(values): return math.exp(statistics.mean(math.log(x) for x in values))
            item = dict(device=device,kernel=kernel,n=4,replicates=list(map(int,reps)),
                prepared=gm(cache[left][r]/cache[right][r] for r in reps))
            for phase in ('ordinary_workflow','research_execution'):
                values={w:{r['task']['replicate']:r['costs']['phases'][phase]['complete_seconds']
                    for r in rows if r['task']['workflow']==w} for w in (left,right)}
                item[phase]=gm(values[left][int(r)]/values[right][int(r)] for r in reps)
            boundaries.append(item)

    l1 = saved('L1/task-frame.json')
    selected = {r['task']['workflow']:r for r in l1 if r['phase']=='main' and
        r['task']['replicate']==21 and r['task']['budget']==4096 and r['task']['workflow'] in
        ('cpu-mala-sequential','cpu-mala-quasi_deer')}
    assert len(selected)==2
    arrays, tie_rows = {}, []
    for label,w in (('seq','cpu-mala-sequential'),('deer','cpu-mala-quasi_deer')):
        r = selected[w]; t = r['task']
        prefix = f"formal-runs/batch-{t['batch']:02}/main/tasks/{t['id']}/attempt-0001/"
        with np.load(bound(prefix+'fit.npz'),allow_pickle=False) as a:
            q = a['draws'][:,512:,0].copy(); accept = a['accept'][:,512:].copy()
        arrays[label] = (q,accept)
        q.astype('<f8').tofile(out/(label+'.bin'))
        p05=np.quantile(q,.05)
        runs=[]
        for chain in accept:
            current=longest=0
            for move in chain:
                current=0 if move else current+1
                longest=max(longest,current)
            runs.append(longest)
        tie_rows.append(dict(workflow=w,id=t['id'],replicate=21,retained=4096,
            saved_diagnostics=r['diagnostics'][0],acceptances=accept.sum(1).tolist(),
            longest_rejection_run=runs,unique_per_chain=[len(np.unique(c)) for c in q],
            q05=float(p05),q05_le_counts=(q<=p05).sum(1).tolist(),q05_ties=(q==p05).sum(1).tolist()))
    assert np.array_equal(arrays['seq'][1],arrays['deer'][1])
    delta=float(np.max(np.abs(arrays['seq'][0]-arrays['deer'][0])))
    assert delta<1e-8

    result=dict(schema='manuscript-review5-companion-v1',new_formal_sampler_calls=0,
        historical_outcomes_unchanged=True,source_files=sources,w1_phase_means=summary,
        w1_cost_boundaries_same_four_inputs=boundaries,l1_tie_case=tie_rows,
        l1_max_abs_parameter_difference=delta,l1_acceptance_mismatches=0,
        phase_scope='Inclusive sampler phase contains discard/warmup, transfer and transform. Residual contains startup/import, gaps, journal and exit; it is not a separately measured pure initialization cost.',
        cache_scope='Prepared per-input means from four replays; paired geometric ratios on the SAME four original inputs. Descriptive, no BCa, no new independent posterior repetitions.')
    (out/'SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for name,data in (('w1-phase-records.csv',decomposed),('w1-phase-means.csv',summary),('w1-three-boundaries.csv',boundaries)):
        with (out/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    db.close()
    print(json.dumps(dict(w1_phase_records=len(decomposed),l1_fixed_fits=len(tie_rows),
        new_formal_sampler_calls=0,output=str(out))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in ('project','delivery','index','statistics-dir','output'):p.add_argument('--'+a,required=True)
    build(**vars(p.parse_args()))
