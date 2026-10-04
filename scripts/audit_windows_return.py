"""Read-only Mac reanalysis of frozen Windows evidence; no torch/CUDA required."""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json, sys, time
import numpy as np
from scipy.special import expit
from scipy.stats import norm

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def fp(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def tape_hash(tape):
    h = hashlib.sha256()
    for k in sorted(tape):
        a = np.ascontiguousarray(tape[k], dtype='<f8')
        h.update(k.encode())
        h.update(str(a.shape).encode())
        h.update(a.tobytes())
    return h.hexdigest()

def check_files(folder, checks):
    for name, h in checks.items():
        assert sha(folder / name) == h, (folder, name)

def values(spec, x):
    kind = spec['kind']
    if kind == 'gaussian':
        z = (x[..., 0] - spec['mean'][0]) / np.sqrt(spec['covariance'][0][0])
        return (np.stack([z, z * z, z > 1], -1), np.array([0.0, 1.0, norm.sf(1)]))
    if kind in ('funnel', 'funnel_noncentered'):
        v = x[..., 0]
        return (np.stack([v / 3, np.tanh(v / 3), x[..., 1] > 0, np.cos(x[..., 1] * np.exp(-v / 2))], -1), np.array([0.0, 0.0, 0.5, np.exp(-0.5)]))
    if kind == 'mixture':
        return (np.stack([x[..., 0] / np.sqrt(1 + spec['separation'] ** 2), x[..., 0] > 0, x[..., 1], x[..., 1] ** 2], -1), np.array([0.0, 0.5, 0.0, 1.0]))
    if kind == 'logistic':
        return (np.stack([x[..., 0], x[..., 1], expit(x[..., 0]), x[..., 0] > 0], -1), None)
    raise ValueError(kind)

def ci(x, stat=np.median):
    x = np.asarray(x)
    ix = np.random.Generator(np.random.Philox(555124)).integers(0, len(x), (2000, len(x)))
    return np.quantile(stat(x[ix], axis=1), [0.025, 0.975])

def main(evidence, source, out):
    if evidence == out or evidence in out.parents or out in evidence.parents:
        raise ValueError("Output and original evidence must be separate directories")
    sys.dont_write_bytecode = True
    start = time.perf_counter()
    out.mkdir(parents=True, exist_ok=False)
    run = evidence / 'execution/windows-native/windows-native-v1'
    p = read(run / 'protocol.json')
    unsigned = dict(p)
    digest = unsigned.pop('protocol_sha256')
    assert fp(unsigned) == digest
    assert p == read(source / 'benchmark/protocols/windows-native-v1.json')
    frozen = evidence / 'execution/windows-native/frozen-source'
    sources = []
    for name, h in p['source_files'].items():
        archived = (frozen / name).read_bytes()
        assert hashlib.sha256(archived).hexdigest() == h, name
        checked = (source / name).read_bytes()
        if checked != archived:
            assert checked.replace(b'\r\n', b'\n') == archived.replace(b'\r\n', b'\n'), name
            sources.append({'path': name, 'difference': 'CRLF/LF only', 'frozen_sha256': h, 'checkout_sha256': hashlib.sha256(checked).hexdigest()})
    for field in ['dependency_lock', 'r_dependency_lock']:
        assert sha(evidence / p[field]) == p[field + '_sha256']
    spec = importlib.util.spec_from_file_location('received_numpy_reference', frozen / 'r-package/inst/python/parallelbayes/reference.py')
    ref = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ref
    spec.loader.exec_module(ref)
    saved = read(evidence / 'benchmark/analysis/outputs/windows-native-v1/summary.json')
    saved_rows = {r['task_id']: r for r in read(evidence / 'benchmark/analysis/outputs/windows-native-v1/run-metrics.json')}
    assert len(p['tasks']) == 512 and len(saved_rows) == 512
    tasks = {fp(t): t for t in p['tasks']}
    assert len(tasks) == 512
    assert len(list((run / 'tasks').glob('*/state.json'))) == 512
    tapes = {}
    oracle = {}
    rows = []
    raw_pairs = {}
    attempts = 0
    max_error = 0.0
    max_constrained = 0.0
    mismatches = 0
    zero = []
    max_group = {}
    for n, (tid, t) in enumerate(sorted(tasks.items())):
        c = t['config']
        shape = (c['chains'], c['draws'], p['models'][t['model']]['dimension'])
        folder = run / 'tasks' / tid[:20]
        s = read(folder / 'state.json')
        assert s['task'] == t and s['protocol_sha256'] == digest
        attempts += len(list(folder.glob('attempt-*')))
        folder = folder / s['attempt']
        check_files(folder, s['checksums'])
        r = read(folder / 'result.json')
        check_files(folder / 'normal', r['normal']['checksums'])
        assert s['status'] == r['status'] == 'completed' and r['audit']['passed'] and (not r['fallback']) and (r['config'] == c)
        assert r['diagnostics']['status'] == 0 and r['diagnostics']['confirmed'] == c['chains'] * c['draws']
        tapeid = t['tape_sha256']
        inp = run / 'inputs' / (tapeid + '.npz')
        assert sha(inp) == t['tape_file_sha256']
        if tapeid not in tapes:
            with np.load(inp, allow_pickle=False) as z:
                tapes[tapeid] = {k: z[k] for k in z.files}
            assert tape_hash(tapes[tapeid]) == tapeid
        tape = tapes[tapeid]
        key = (t['model'], c['draws'], t['replicate'], c['kernel'])
        if key not in oracle:
            m = ref.make_reference(p['models'][t['model']])
            pp = []
            aa = []
            for chain in range(c['chains']):
                path, accept = ref.numpy_reference(m, c['kernel'], np.zeros(shape[-1]), tape['noise'][chain], tape['log_uniform'][chain], c['step_size'])
                pp.append(path)
                aa.append(accept)
            path = np.asarray(pp)
            oracle[key] = (path, np.asarray(aa), m.constrain(path), m.target_id)
        expected, acc, theta, targetid = oracle[key]
        assert r['target_id'] == targetid
        with np.load(folder / 'raw.npz', allow_pickle=False) as z:
            for k, v in tape.items():
                np.testing.assert_array_equal(z['tape__' + k], v)
            path = z['unconstrained']
            draws = z['draws']
            accept = z['accept']
            assert path.shape == draws.shape == shape and accept.shape == shape[:2]
            assert np.isfinite(path).all() and np.isfinite(draws).all()
            error = np.max(np.abs(path - expected), axis=(1, 2))
            limit = 100 * (c['atol'] + c['rtol'] * np.maximum(1, np.max(np.abs(path), axis=(1, 2))))
            assert np.all(error <= limit), (tid, error, limit)
            mismatch = int(np.count_nonzero(accept != acc))
            assert mismatch == 0
            max_error = max(max_error, float(error.max()))
            mismatches += mismatch
            constrained = float(np.max(np.abs(draws - theta)))
            max_constrained = max(max_constrained, constrained)
            with np.load(folder / 'normal/raw.npz', allow_pickle=False) as normal:
                np.testing.assert_array_equal(path, normal['unconstrained'])
                np.testing.assert_array_equal(accept, normal['accept'])
            if not accept.any():
                zero.append({'task_id': tid, 'model': t['model'], 'kernel': c['kernel']})
            f, truth = values(p['models'][t['model']], draws[:, t['discard']:])
            estimate = f.mean((0, 1))
            se = None if truth is None else (estimate - truth) ** 2
            old = saved_rows[tid]
            np.testing.assert_allclose(estimate, old['estimate'], atol=1e-12, rtol=1e-12)
            if se is not None:
                np.testing.assert_allclose(se, old['squared_error'], atol=1e-12, rtol=1e-12)
            else:
                assert old['reference_state'] == 'unresolved_finite_reference'
            pairkey = key + (c['executor'],)
            if pairkey in raw_pairs:
                other = raw_pairs.pop(pairkey)
                np.testing.assert_array_equal(accept, other[1])
                np.testing.assert_allclose(path, other[0], atol=1e-10, rtol=1e-10)
                np.testing.assert_allclose(draws, other[2], atol=1e-09, rtol=1e-09)
            else:
                raw_pairs[pairkey] = (path.copy(), accept.copy(), draws.copy())
        warmed = float(np.median([v['timing']['sample'] for v in r['warmed_eager_replays']]))
        assert len(r['warmed_eager_replays']) == 2 and all((v['status'] == 'completed' for v in r['warmed_eager_replays']))
        row = {'task_id': tid, 'model': t['model'], 'draws': c['draws'], 'replicate': t['replicate'], 'device': c['device'], 'kernel': c['kernel'], 'executor': c['executor'], 'warmed_seconds': warmed, 'normal_seconds': r['normal']['wall_seconds'], 'audit_api_seconds': r['timing']['total'], 'estimate': estimate.tolist(), 'squared_error': None if se is None else se.tolist()}
        for k in ['warmed_seconds', 'normal_seconds', 'audit_api_seconds']:
            assert row[k] == old[k]
        rows.append(row)
        if (n + 1) % 64 == 0:
            print('Audited actual arrays and NumPy reference:', n + 1, '/512', flush=True)
    assert not raw_pairs and len(tapes) == 64 and (len(oracle) == 128) and (attempts == 512)
    groups = collections.defaultdict(list)
    index = {(r['model'], r['draws'], r['replicate'], r['device'], r['kernel'], r['executor']): r for r in rows}
    for r in rows:
        if r['executor'] == 'sequential':
            continue
        seq = index[r['model'], r['draws'], r['replicate'], r['device'], r['kernel'], 'sequential']
        g = {k: r[k] for k in ['model', 'draws', 'device', 'kernel']}
        g.update({k.replace('_seconds', '_speed_ratio'): seq[k] / r[k] for k in ['warmed_seconds', 'normal_seconds', 'audit_api_seconds']})
        groups[r['model'], r['device'], r['kernel'], r['draws']].append(g)
    paired = []
    for old in saved['groups']:
        key = tuple((old[k] for k in ['model', 'device', 'kernel', 'draws']))
        rr = groups[key]
        assert len(rr) == 4
        row = {k: old[k] for k in ['model', 'device', 'kernel', 'draws']}
        for metric in ['warmed_speed_ratio', 'normal_speed_ratio', 'audit_api_speed_ratio']:
            x = [r[metric] for r in rr]
            med = float(np.median(x))
            bounds = ci(x)
            np.testing.assert_allclose(med, old[metric]['median'], atol=1e-14)
            np.testing.assert_allclose(bounds, old[metric]['ci95'], atol=1e-14)
            row[metric] = {'median': med, 'ci95': bounds.tolist()}
        paired.append(row)
    for old in saved['accuracy']:
        rr = [r for r in rows if all((r[k] == old[k] for k in ['model', 'device', 'kernel', 'executor', 'draws']))]
        assert len(rr) == 4
        if rr[0]['squared_error'] is None:
            continue
        errors = np.array([r['squared_error'] for r in rr])
        np.testing.assert_allclose(errors.mean(0), old['function_mse'], atol=1e-12, rtol=1e-12)
        np.testing.assert_allclose([ci(errors[:, i], np.mean) for i in range(errors.shape[1])], old['function_mse_ci95'], atol=1e-12, rtol=1e-12)
    sbc = evidence / 'execution/windows-native/sbc-01'
    ss = read(sbc / 'summary.json')
    sr = read(sbc / 'paired-analytic-summary.json')
    datasets = ss['design']['datasets']
    rng = np.random.Generator(np.random.Philox(11043007))
    covered = 0
    for d in datasets:
        truth = float(rng.normal())
        y = rng.normal(truth, 1, 8)
        assert truth == d['truth']
        np.testing.assert_array_equal(y, d['y'])
        interval = norm.ppf([0.05, 0.95], loc=y.sum() / 9, scale=1 / 3)
        np.testing.assert_allclose(interval, d['interval'])
        covered += bool(interval[0] <= truth <= interval[1])
    for r in ss['rows']:
        kernel, executor = r['workflow'].split('/')
        folder = sbc / f"{r['dataset']:02d}-{kernel}-{executor}"
        check_files(folder, r['checksums'])
        d = datasets[r['dataset']]
        with np.load(folder / 'raw.npz', allow_pickle=False) as z:
            draws = z['draws'][:, 0 if kernel == 'nuts' else 256:, 0]
        interval = np.quantile(draws, [0.05, 0.95])
        np.testing.assert_allclose(interval, r['interval'], atol=1e-12)
        np.testing.assert_allclose(draws.mean(), r['mean'], atol=1e-12)
        assert bool(interval[0] <= d['truth'] <= interval[1]) == r['covered'] == r['analytic_covered']
    assert covered == sr['analytic_covered'] == 9 and len(ss['rows']) == 60
    result = {'status': 'passed', 'scope': 'Mac read-only NumPy replay and arithmetic reanalysis, not a new GPU timing experiment', 'protocol_sha256': digest, 'source_files_exact_in_frozen_snapshot': len(p['source_files']), 'git_checkout_newline_differences': sources, 'formal_tasks': 512, 'independent_oracle_replays': 128, 'actual_tapes_verified': 64, 'acceptance_mismatches': mismatches, 'max_path_error_vs_mac_numpy': max_error, 'max_constrained_error_vs_mac_numpy': max_constrained, 'cpu_cuda_pairs': 256, 'terminal_attempts': attempts, 'normal_replays_verified_from_arrays': 512, 'zero_acceptance_fits': len(zero), 'zero_acceptance_models_kernels': dict(collections.Counter((r['model'] + '/' + r['kernel'] for r in zero))), 'paired_speed_groups_recomputed': len(paired), 'accuracy_groups_recomputed': len(saved['accuracy']), 'sbc_fits_recomputed': 60, 'sbc_independent_data_sets': 12, 'analytic_and_each_workflow_coverage': '9/12', 'elapsed_mac_audit_seconds': time.perf_counter() - start, 'numpy': np.__version__}
    for device in ['cpu', 'cuda']:
        for kernel in ['mala', 'rwm']:
            gs = [g['warmed_speed_ratio']['median'] for g in paired if g['device'] == device and g['kernel'] == kernel]
            result[f'{device}_{kernel}_warmed_range'] = [min(gs), max(gs)]
    (out / 'paired-recomputed.json').write_text(json.dumps(paired, indent=2) + '\n')
    (out / 'mac-independent-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('Do not run this audit with Python -O; integrity assertions are required')
    a = argparse.ArgumentParser()
    a.add_argument('--evidence', type=Path, required=True)
    a.add_argument('--source', type=Path, required=True)
    a.add_argument('--output', type=Path, required=True)
    p = a.parse_args()
    main(p.evidence.resolve(), p.source.resolve(), p.output.resolve())
