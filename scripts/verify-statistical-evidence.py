"""Verify frozen SBC inputs and raw receipts before resuming or accepting a run.

This is an outer evidence gate; it does not change the frozen sampling program.
"""
import argparse
import json
from pathlib import Path
from parallelbayes.experiment import file_hash, load_protocol


def verify(folder, protocol, platform, require_complete=False):
    folder = Path(folder)
    frozen = load_protocol(protocol, '.')
    if not (folder / 'manifest.json').exists():
        if require_complete:
            raise ValueError('Missing SBC manifest')
        return dict(verified=0, complete=False)
    manifest = json.loads((folder / 'manifest.json').read_text())
    expected = dict(replicates=frozen['replicates'], source_sha256=frozen['source_sha256'],
                    platform=platform, seed=frozen['seed'], sampling_seed=frozen['sampling_seed'])
    if any(manifest.get(k) != v for k, v in expected.items()):
        raise ValueError('SBC manifest differs from frozen protocol/platform')
    methods = ['mala/sequential', 'mala/quasi_deer', 'rwm/sequential',
               'rwm/online_picard', 'nuts/sequential']
    verified = 0
    for r in range(frozen['replicates']):
        for method in methods:
            kernel, executor = method.split('/')
            path = folder / f'{r:03d}-{kernel}-{executor}.json'
            if not path.exists():
                if require_complete:
                    raise ValueError(f'Missing SBC receipt: {path.name}')
                continue
            record = json.loads(path.read_text())
            config = record['config']
            if (record['replicate'] != r or config['seed'] != frozen['sampling_seed'] + r
                or config['kernel'] != kernel or config['executor'] != executor
                or config['platform'] != platform):
                raise ValueError(f'SBC receipt has different identity: {path.name}')
            if record['status'] not in ('completed', 'failed'):
                raise ValueError(f'Unfinished SBC receipt: {path.name}')
            if record['status'] == 'completed':
                raw = path.with_suffix('.npz')
                if not raw.exists() or file_hash(raw) != record.get('raw_sha256'):
                    raise ValueError(f'SBC raw checksum mismatch: {raw.name}')
            verified += 1
    if require_complete:
        summary = json.loads((folder / 'summary.json').read_text())
        if summary['manifest'] != manifest or {x['method'] for x in summary['methods']} != set(methods):
            raise ValueError('SBC summary identity differs')
        for row in summary['methods']:
            if row['attempted'] != frozen['replicates']:
                raise ValueError('SBC summary does not include all frozen repetitions')
            if row['failed']:
                raise ValueError('SBC failures require a documented scientific decision')
    return dict(verified=verified, complete=verified == frozen['replicates'] * len(methods))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--protocol', default='benchmark/protocols/statistical-v4.json')
    p.add_argument('--platform', default='cpu')
    p.add_argument('--require-complete', action='store_true')
    a = p.parse_args()
    print(json.dumps(verify(a.output, a.protocol, a.platform, a.require_complete)))
