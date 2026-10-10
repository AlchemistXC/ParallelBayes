#!/usr/bin/env python3
"""Summarize hash-bound cross-host checks without replacing frozen statistics.

A snapshot is explicitly incomplete. Final review requires the finished 4,144-row
reader and its actual zero-reanalysis resume proof. No sampler or R is called.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sqlite3

PROTOCOL = '91bbff0ec47f9f47b64ac4acfd328e2df8834a67b1d24a1c9e35c4fa0a980aeb'
METRICS = ('mean', 'sd', 'rhat', 'ess_bulk', 'ess_tail', 'mcse_mean')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def contained(root, name):
    path = root / name
    if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError('Unsafe receiver member')
    return path


def diagnostic_pairs(original, receiver):
    if len(original) != len(receiver):
        raise ValueError('Diagnostic rows differ')
    rows = []
    for left, right in zip(original, receiver):
        if left['variable'] != right['variable']:
            raise ValueError('Diagnostic variable order differs')
        for metric in METRICS:
            a, b = left[metric], right[metric]
            if (a is None) != (b is None):
                raise ValueError('Diagnostic undefined state changed')
            if a is not None and not (math.isfinite(a) and math.isfinite(b)):
                raise ValueError('Nonfinite diagnostic must remain explicit null')
            rows.append(dict(variable=left['variable'], metric=metric, undefined=a is None,
                exact=a == b, absolute_difference=None if a is None else abs(a-b),
                scaled_difference=None if a is None else abs(a-b)/max(1., abs(a), abs(b)),
                rhat_classification_changed=metric == 'rhat' and a is not None and ((a > 1.01) != (b > 1.01)),
                original=a, receiver=b))
    return rows


def review(analysis, output, *, snapshot=False, resume_proof=None):
    root, out = Path(analysis).resolve(), Path(output)
    if out.exists():
        raise FileExistsError('Preserve existing companion')
    identity = read(root/'identity.json')
    frame = identity['frame']
    if (frame['protocol_sha256'] != PROTOCOL or frame['identity'] != 'windows-compact-inference-v1' or
            frame['main_planned'] != 3888 or frame['cache_planned'] != 256 or identity['cross_platform'] is not True):
        raise ValueError('Wrong compact receiver identity')
    proof = None
    if not snapshot:
        if resume_proof is None:
            raise ValueError('Final review requires actual resume proof')
        summary, proof = read(root/'SUMMARY.json'), read(resume_proof)
        if (summary['visited'] != 4144 or summary['evidence_complete'] is not True or
                proof['passed'] is not True or proof['new_analyses'] != 0 or proof['reused_analyses'] != 4144):
            raise ValueError('Full reconstruction/resume has not finished')
    db = sqlite3.connect((root/'analysis.sqlite3').as_uri()+'?mode=ro', uri=True)
    try:
        saved = db.execute('SELECT id,task,disposition,receipt,sha256 FROM results ORDER BY id').fetchall()
    finally:
        db.close()
    if not snapshot and len(saved) != 4144:
        raise ValueError('Incomplete final row frame')
    outcomes = {'main': Counter(), 'cache': Counter()}
    dispositions, functions = Counter(), Counter()
    comparisons = {k: dict(fits=0, exact=0, maximum_absolute_difference=0.) for k in ('function', 'means', 'diagnostics')}
    metrics = {k: dict(entries=0, undefined=0, exact=0, maximum_absolute_difference=0., maximum_scaled_difference=0.) for k in METRICS}
    paths = {k: dict(calls=0, transitions=0, acceptance_mismatches=0, maximum_path_error=0., maximum_error_bound_ratio=0.) for k in ('main', 'cache')}
    task_rows, crossings, bindings = [], [], {}
    nuts = 0
    for identifier, task_json, disposition, receipt_name, digest in saved:
        receipt_path = contained(root, receipt_name)
        if sha(receipt_path) != digest:
            raise ValueError('Receipt digest changed: '+identifier)
        receipt = read(receipt_path)
        task = json.loads(task_json)
        if task['id'] != identifier or receipt['task'] != task or receipt['disposition'] != disposition:
            raise ValueError('Receipt identity differs')
        bindings[receipt_name] = digest
        folder = receipt_path.parent
        def checked(name):
            path = contained(folder, name)
            if name not in receipt['files'] or sha(path) != receipt['files'][name]:
                raise ValueError('Receiver output changed: '+name)
            return read(path)
        projected = checked(receipt['row'])
        if projected['task'] != task:
            raise ValueError('Projected task differs')
        phase = projected['phase']
        dispositions[disposition] += 1
        outcomes[phase][projected.get('outcome', 'unavailable')] += 1
        if disposition != 'analyzed':
            task_rows.append(dict(id=identifier, disposition=disposition, error=projected.get('error')))
            continue
        science = checked(projected['scientific_result'])
        if science['task'] != task or science['outcome'] != projected['outcome']:
            raise ValueError('Scientific result differs')
        if science['new_sampler_calls'] != 0 or science['new_independent_repetitions'] != 0:
            raise ValueError('Receiver must not add sampling')
        functions[science['function_status']] += 1
        row = dict(id=identifier, model=task['model'], workflow=task['workflow'], budget=task['budget'],
            replicate=task['replicate'], phase=phase, outcome=science['outcome'], disposition=disposition)
        replays = [science['independent_replay']] if 'independent_replay' in science else science.get('cache', {}).get('independent_replays', [])
        for replay in replays:
            if replay['passed'] is not True:
                raise ValueError('Eligible receiver replay failed')
            a = paths[phase]
            a['calls'] += 1
            a['transitions'] += replay['transitions']
            a['acceptance_mismatches'] += sum(replay['acceptance_mismatches'])
            a['maximum_path_error'] = max(a['maximum_path_error'], *replay['maximum_path_error'])
            a['maximum_error_bound_ratio'] = max(a['maximum_error_bound_ratio'], *(x/y for x,y in zip(replay['maximum_path_error'], replay['frozen_path_limits'])))
        if science.get('nuts') is not None:
            nuts += 1
        if science['function_status'] == 'completed':
            for kind, accumulator in comparisons.items():
                item = science['receiver_'+kind+'_comparison']
                if item['passed'] is not True or item['atol'] != 1e-10 or item['rtol'] != 1e-10:
                    raise ValueError('Original receiver tolerance/comparison differs')
                accumulator['fits'] += 1
                accumulator['exact'] += item['exact']
                accumulator['maximum_absolute_difference'] = max(accumulator['maximum_absolute_difference'], item['maximum_absolute_difference'])
                row[kind+'_exact'] = item['exact']
            post = checked('science/functions/posterior.json')
            for delta in diagnostic_pairs(science['diagnostics'], post['results'][identifier]):
                accumulator = metrics[delta['metric']]
                accumulator['entries'] += 1
                accumulator['undefined'] += delta['undefined']
                accumulator['exact'] += delta['exact']
                if not delta['undefined']:
                    accumulator['maximum_absolute_difference'] = max(accumulator['maximum_absolute_difference'], delta['absolute_difference'])
                    accumulator['maximum_scaled_difference'] = max(accumulator['maximum_scaled_difference'], delta['scaled_difference'])
                if delta['rhat_classification_changed']:
                    crossings.append(dict(id=identifier, **delta))
        task_rows.append(row)
    result = dict(schema='compact-reconstruction-review-v1', stage='partial_snapshot' if snapshot else 'complete_receiver_review',
        visited=len(saved), planned=4144, frame=frame, receiver_environment=identity['receiver_environment'],
        original_statistics_replaced=False, new_sampler_calls=0, new_independent_repetitions=0,
        dispositions=dict(dispositions), original_outcomes={k:dict(v) for k,v in outcomes.items()},
        function_status=dict(functions), replay=paths, NUTS_contracts=nuts, comparisons=comparisons,
        diagnostic_metrics=metrics, rhat_threshold=1.01, rhat_classification_changes=crossings,
        identity_sha256=sha(root/'identity.json'), receiver_receipts=bindings,
        resume_proof_sha256=sha(resume_proof) if proof is not None else None,
        note='Same archived binary is used for cross-host R diagnostics; regenerated functions are compared separately. No threshold or tolerance is changed.')
    out.mkdir(parents=True)
    for name, value in [('SUMMARY.json', result), ('tasks.json', task_rows)]:
        (out/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--snapshot', action='store_true')
    p.add_argument('--resume-proof')
    args = p.parse_args()
    result = review(**vars(args))
    print(json.dumps({k:v for k,v in result.items() if k != 'receiver_receipts'}, indent=2))
