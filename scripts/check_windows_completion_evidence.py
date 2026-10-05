"""Preserve failed input reconstruction and verify terminal resume invariance.

This companion never changes a protocol, sampler, or existing evidence file.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def terminal_files(run):
    states = sorted(run.glob('*/state.json')) + sorted(run.glob('groups/*/state.json'))
    if not states:
        raise ValueError('No terminal states found')
    files = {}
    for state in states:
        metadata = json.loads(state.read_text())
        if metadata['status'] not in ('completed', 'failed'):
            raise ValueError('Not terminal: ' + str(state))
        for path in sorted(state.parent.rglob('*')):
            if path.is_file():
                files[path.relative_to(run).as_posix()] = sha(path)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['mechanism-inputs', 'snapshot', 'verify-resume'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--snapshot', type=Path)
    args = parser.parse_args()
    if args.action == 'mechanism-inputs':
        import numpy as np
        sys.path.insert(0, str(ROOT / 'scripts/completion'))
        from mechanism_runner import read_plan, master_tape, actual_hash
        plan = read_plan(ROOT / 'benchmark/protocols/mechanism-windows-pilot-v1.json')
        args.output.mkdir(parents=True, exist_ok=False)
        rows = []
        for name in sorted(plan['models']):
            for rep in range(plan['independent_tapes_per_model']):
                key = f'{name}-r{rep}'
                tape = master_tape(plan, name, rep)
                path = args.output / (key + '.npz')
                np.savez_compressed(path, **tape)
                rows.append(dict(key=key, expected=plan['inputs'][key],
                    actual_sha256=actual_hash(tape), file_sha256=sha(path),
                    actual_matches=actual_hash(tape)==plan['inputs'][key]['actual_sha256'],
                    array_sha256={k:hashlib.sha256(np.ascontiguousarray(v,dtype='<f8').tobytes()).hexdigest() for k,v in tape.items()}))
        result = dict(status='blocked_before_sampling' if not all(r['actual_matches'] for r in rows) else 'matched',
            protocol_sha256=plan['protocol_sha256'], numpy=np.__version__, rows=rows,
            sampler_tasks_executed=0, pending_workflows=192,
            required_resolution='Obtain the six original frozen NPZ files and verify both file and actual-array hashes. These rejected reconstructions are not experiment inputs.',
            cause='Combined actual-array hashes differ; absent original arrays prevent assigning a specific component or numerical-library cause.')
        write_new(args.output/'verification.json', result)
    elif args.action == 'snapshot':
        result = dict(run=str(args.run.resolve()), summary=json.loads((args.run/'summary.json').read_text()),
            summary_sha256=sha(args.run/'summary.json'), files=terminal_files(args.run))
        write_new(args.output, result)
    else:
        before=json.loads(args.snapshot.read_text())
        if str(args.run.resolve()) != before['run']:
            raise ValueError('Run path differs')
        after=terminal_files(args.run)
        summary=json.loads((args.run/'summary.json').read_text())
        new=summary.get('newly_executed_targets', summary.get('newly_executed_groups'))
        changed=[name for name in sorted(set(before['files'])|set(after)) if before['files'].get(name)!=after.get(name)]
        result=dict(passed=not changed and new==0, terminal_files=len(after), changed_files=changed,
            newly_executed=new, before_summary_sha256=before['summary_sha256'], after_summary_sha256=sha(args.run/'summary.json'))
        write_new(args.output,result)
        if not result['passed']:
            raise ValueError('Resume modified terminal evidence or executed tasks')
    print(json.dumps({k:v for k,v in result.items() if k not in ('files','rows')}, indent=2))


if __name__ == '__main__':
    main()
