#!/usr/bin/env python3
"""Retrospective sign-boundary check of original M1 paths, not a new experiment.

One fit at a time; no sampler, diagnostic recomputation or selection of runs.
Failed complete fits retain their outcomes and do not contribute partial chains.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/completion'))
from formal_streaming import read_member
from formal_runtime import fingerprint


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verified(root, members, name, provenance):
    expected = members[name]
    path = root / name
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    if path.stat().st_size != expected['bytes'] or digest.hexdigest() != expected['sha256']:
        raise ValueError('Original member differs: ' + name)
    provenance[name] = expected['sha256']
    return path


def path_metrics(initial, states, discard, saved_event):
    """Count observed q1=0 crossings; zero is nonpositive as in the estimand."""
    initial = np.asarray(initial)
    states = np.asarray(states)
    if (initial.shape != (4,) or states.ndim != 2 or states.shape[0] != 4 or
            not 0 <= discard < states.shape[1] or
            not np.isfinite(initial).all() or not np.isfinite(states).all()):
        raise ValueError('Invalid original-coordinate path')
    retained = states[:, discard:] > 0
    if not np.array_equal(retained, saved_event):
        raise ValueError('Original path and archived sign estimand differ')
    whole = np.column_stack((initial > 0, states > 0))
    return dict(initial_positive_chains=int(np.count_nonzero(initial > 0)),
        all_saved_sign_crossings=np.count_nonzero(np.diff(whole, axis=1), axis=1).tolist(),
        retained_sign_crossings=np.count_nonzero(np.diff(retained, axis=1), axis=1).tolist(),
        retained_positive_fraction=retained.mean(axis=1).tolist(),
        pooled_positive_fraction=float(retained.mean()),
        pooled_squared_error=float((retained.mean() - .5)**2))


def review(delivery, manifest, manifest_sha256, tasks, output):
    root, out = Path(delivery), Path(output)
    if out.exists():
        raise FileExistsError(out)
    raw = Path(manifest).read_bytes()
    if sha(raw) != manifest_sha256:
        raise ValueError('External manifest identity differs')
    members = json.loads(raw)['files']; provenance = {}
    task_raw = Path(tasks).read_bytes()
    plan = [r for r in csv.DictReader(task_raw.decode().splitlines())
            if r['model'] == 'M1' and r['phase'] == 'main']
    if len(plan) != 432 or len({r['id'] for r in plan}) != 432:
        raise ValueError('Complete M1 frame of 432 tasks required')
    rows = []
    def read(name):
        return json.loads(verified(root, members, name, provenance).read_bytes())
    for task in plan:
        prefix = f"formal-runs/batch-{int(task['batch']):02d}/main/tasks/{task['id']}/attempt-0001/"
        state = read(prefix + 'state.json'); end = read(prefix + 'completion.json')
        req = read(prefix + 'request.json'); c = req['capsule']; t = c['task']
        if (end['state_sha256'] != members[prefix + 'state.json']['sha256'] or
                req['capsule_sha256'] != fingerprint(c) or
                state['outcome'] != task['outcome'] or
                any(state['task'][k] != t[k] for k in t) or
                any(t[k] != task[k] for k in ('id', 'model', 'workflow')) or
                t['budget'] != int(task['budget']) or t['replicate'] != int(task['replicate'])):
            raise ValueError('Original task identity differs')
        row = dict(id=t['id'], workflow=t['workflow'], budget=t['budget'],
                   replicate=t['replicate'], outcome=state['outcome'], path_available=False)
        if state['outcome'] != 'valid':
            rows.append(row)
            continue
        target = c['target']; geometry = target['geometry']; dimension = target['dimension']
        if (target['base_target_id'] != '160bef01e246c8de94b78de748a60270560b5adee43332345dd0bd289dc7c95f' or
                not np.array_equal(geometry['center'], np.zeros(dimension)) or
                not np.array_equal(geometry['factor'], np.eye(dimension))):
            raise ValueError('M1 original/initial coordinate identity differs')
        inp = verified(root, members, 'inputs/' + t['input'], provenance)
        if members['inputs/' + t['input']]['sha256'] != c['input']['sha256']:
            raise ValueError('Actual initial input identity differs')
        initial = read_member(inp, 'initial')
        if initial.shape != (4, dimension):
            raise ValueError('Actual start shape differs')
        meta = read(prefix + 'fit.json')
        raw_path = verified(root, members, prefix + 'fit.npz', provenance)
        if (meta['status'] != 'completed' or
                meta['ordinary_candidate_arrays_sha256'] != members[prefix + 'fit.npz']['sha256']):
            raise ValueError('Ordinary and archived arrays differ')
        discard = 0 if t['kernel'] == 'nuts' else c['controls']['mh_discard']
        draws = read_member(raw_path, 'draws', c['controls']['maximum_member_bytes'])
        if draws.shape != (4, t['budget'] + discard, dimension) or draws.dtype != np.float64:
            raise ValueError('Original path shape/type differs')
        q1 = draws[:, :, 0].copy(); del draws
        if t['kernel'] == 'nuts':
            warm = read_member(raw_path, 'warmup_states', c['controls']['maximum_member_bytes'])
            if warm.shape != (4, c['controls']['nuts_warmup'], dimension):
                raise ValueError('Warmup shape differs')
            q1 = np.concatenate((warm[:, :, 0], q1), axis=1)
            discard = c['controls']['nuts_warmup']; del warm
        transport = read(prefix + 'diagnostics/transport.json')
        desc = transport['fits']
        names = ['standard_q1', 'q1_positive', 'q2', 'q2_squared']
        if desc != [dict(id=t['id'], input='functions.bin', names=names, shape=[t['budget'], 4, 4])]:
            raise ValueError('Original estimand transport differs')
        binary = verified(root, members, prefix + 'diagnostics/functions.bin', provenance)
        if binary.stat().st_size != t['budget'] * 4 * 4 * 8:
            raise ValueError('Original estimand byte length differs')
        functions = np.fromfile(binary, dtype='<f8').reshape((t['budget'], 4, 4), order='F')
        metrics = path_metrics(initial[:, 0], q1, discard, functions[:, :, 1].T)
        estimates = read(prefix + 'diagnostics/estimates.json')
        if estimates['names'] != names or estimates['means'][1] != metrics['pooled_positive_fraction']:
            raise ValueError('Pooled archived estimator differs')
        row.update(path_available=True, checked_saved_steps_per_chain=q1.shape[1], **metrics)
        rows.append(row)
    groups = []
    for workflow, budget in sorted({(r['workflow'], r['budget']) for r in rows}):
        group = [r for r in rows if (r['workflow'], r['budget']) == (workflow, budget)]
        paths = [r for r in group if r['path_available']]
        groups.append(dict(workflow=workflow, budget=budget, planned=len(group),
            valid_fits=len(paths), outcomes=dict(Counter(r['outcome'] for r in group)),
            checked_chains=4*len(paths),
            sign_crossings_including_warmup_and_initial=sum(sum(r['all_saved_sign_crossings']) for r in paths),
            retained_sign_crossings=sum(sum(r['retained_sign_crossings']) for r in paths),
            fits_with_pooled_probability_exactly_half=sum(r['pooled_positive_fraction'] == .5 for r in paths)))
    summary = dict(schema='compact-mixture-path-companion-v1', complete=True, planned_tasks=432,
        outcome_counts=dict(Counter(r['outcome'] for r in rows)), groups=groups,
        manifest_sha256=manifest_sha256, task_table_sha256=sha(task_raw), source_assets_sha256=provenance,
        scope='Retrospective descriptive companion after seeing M1 summaries; no changed inferential rule',
        crossing_definition='Change of the indicator q1 > 0 between consecutive saved states; first comparison uses the actual start',
        independent_unit='Original four-chain input; budgets, workflows and returned chains are not extra independent repetitions',
        failed_fit_partial_chains_not_used=True, new_sampler_calls=0, new_R_diagnostic_calls=0,
        new_formal_repetitions=0, full_formal_reconstruction_completed=False)
    out.mkdir(parents=True)
    with (out/'tasks.json').open('w') as f:
        json.dump(rows, f, indent=2, allow_nan=False); f.write('\n')
    (out/'SUMMARY.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('delivery', 'manifest', 'manifest-sha256', 'tasks', 'output'):
        p.add_argument('--'+name, required=True)
    result = review(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in result.items() if k not in ('groups','source_assets_sha256')}, indent=2))
