"""Post-freeze evidence review; never changes frozen source, inputs or attempts.

Run after the frozen analyzer and modern_diagnostics.R. Cross-device checks
read actual arrays, not seeds or posterior means. All summary inputs are hashed.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'execution/windows-native/windows-native-v1'
ANALYSIS = ROOT / 'benchmark/analysis/outputs/windows-native-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def main():
    summary = read(ANALYSIS / 'summary.json')
    rows = read(ANALYSIS / 'run-metrics.json')
    diagnostics = read(RUN / 'modern-diagnostics.json')
    protocol = read(RUN / 'protocol.json')
    assert len(rows) == len(protocol['tasks']) == len(diagnostics) == 512
    by_id = {r['task_id']: r for r in rows}
    pairs = []
    originals = {}
    acceptance = []
    for row in rows:
        folder = RUN / 'tasks' / row['task_id'][:20]
        state = read(folder / 'state.json')
        folder = folder / state['attempt']
        for name, expected in state['checksums'].items():
            assert sha(folder / name) == expected
        result = read(folder / 'result.json')
        assert row['status'] == 'completed' and result['audit']['passed']
        assert result['normal_replay_identical']
        assert not result['fallback']
        originals[row['task_id']] = (folder, state, result)
        with np.load(folder/'raw.npz') as raw:
            acceptance.append(dict(task_id=row['task_id'],model=row['model'],kernel=row['kernel'],
                device=row['device'],executor=row['executor'],draws=row['draws'],
                accepted=int(raw['accept'].sum()),transitions=raw['accept'].size,
                retained_all_parameters_constant=bool(np.all(np.ptp(raw['draws'][:,state['task']['discard']:],axis=(0,1))==0))))
    for cpu in rows:
        if cpu['device'] != 'cpu':
            continue
        matches = [r for r in rows if r['device'] == 'cuda' and all(
            r[k] == cpu[k] for k in ('model','replicate','kernel','executor','draws','chains','window'))]
        assert len(matches) == 1
        gpu = matches[0]
        cp, cs, cr = originals[cpu['task_id']]
        gp, gs, gr = originals[gpu['task_id']]
        assert cs['tape_sha256'] == gs['tape_sha256']
        record = {k: cpu[k] for k in ('model','replicate','kernel','executor','draws')}
        record.update(cpu_task=cpu['task_id'], cuda_task=gpu['task_id'])
        with np.load(cp/'raw.npz') as x, np.load(gp/'raw.npz') as y:
            for k in ('tape__noise','tape__log_uniform','tape__directions'):
                assert np.array_equal(x[k], y[k]), k
            mismatches = int(np.count_nonzero(x['accept'] != y['accept']))
            assert mismatches == 0
            record['acceptance_mismatches'] = mismatches
            for key in ('unconstrained','draws'):
                assert x[key].shape == y[key].shape
                assert np.isfinite(x[key]).all() and np.isfinite(y[key]).all()
                error = float(np.max(np.abs(x[key]-y[key])))
                record[key+'_max_abs_difference'] = error
                # Review bound is the sum of the two independently checked
                # oracle errors, with a floating subtraction rounding allowance.
                audit_key = 'max_abs_path_error' if key == 'unconstrained' else 'max_abs_constrained_error'
                allowance = max(cr['audit'][audit_key])+max(gr['audit'][audit_key])
                rounding = 8*np.finfo(float).eps*max(1., float(np.max(np.abs(x[key]))))
                assert error <= allowance + rounding
            record['nonfinite_values'] = 0
        record['cpu_vs_cuda_warmed_ratio'] = cpu['warmed_seconds']/gpu['warmed_seconds']
        pairs.append(record)
    assert len(pairs) == 256
    write(ANALYSIS/'cross-device-checks.json', pairs)

    diagnostic_rows = []
    for path, item in diagnostics.items():
        tid = path.replace('\\','/').split('/')[-1]
        row = by_id[tid]
        constants = [s for s in item['summary'] if s['state'] == 'undefined_no_variation']
        values = [s['rhat'] for s in item['summary'] if s['rhat'] is not None]
        diagnostic_rows.append(dict(task_id=tid,model=row['model'],kernel=row['kernel'],
            max_finite_rhat=max(values) if values else None,
            finite_rhat_over_1_01=any(v>1.01 for v in values),
            constant_variables=[s['variable'] for s in constants],
            diagnostic_seconds=item['elapsed']))
    write(ANALYSIS/'diagnostic-overview.json', diagnostic_rows)
    write(ANALYSIS/'acceptance-overview.json', acceptance)

    speed = []
    for device in ('cpu','cuda'):
        for kernel in ('mala','rwm'):
            groups = [g for g in summary['groups'] if g['device']==device and g['kernel']==kernel]
            s = dict(device=device, kernel=kernel, groups=len(groups))
            for metric in ('warmed_speed_ratio','normal_speed_ratio','audit_api_speed_ratio'):
                medians = [g[metric]['median'] for g in groups]
                s[metric] = dict(group_median_min=min(medians), group_median_max=max(medians),
                    group_medians_over_one=sum(m>1 for m in medians),
                    groups_ci95_low_over_one=sum(g[metric]['ci95'][0]>1 for g in groups))
            speed.append(s)
    flat = [s for d in diagnostics.values() for s in d['summary']]
    cuda = [r for r in rows if r['device']=='cuda']
    report = dict(scope='Windows native development evidence, not a convergence certificate',
        source_commit=summary['source_commit'], protocol_sha256=summary['protocol_sha256'],
        counts=dict(formal=512,completed=summary['completed'],failed=summary['failed'],
            cuda=256,cpu=256,cross_device_pairs=len(pairs),modern_diagnostic_fits=len(diagnostics)),
        numerical=dict(oracle_max_path_error=max(r['max_path_error'] for r in rows),
            acceptance_mismatches=sum(r['acceptance_mismatches'] for r in rows),
            cross_device_max_path_error=max(r['unconstrained_max_abs_difference'] for r in pairs),
            cross_device_max_constrained_error=max(r['draws_max_abs_difference'] for r in pairs),
            cross_device_nonfinite_values=sum(r['nonfinite_values'] for r in pairs),
            normal_replays_identical=512, terminal_attempt_count=sum(len(list((RUN/'tasks'/r['task_id'][:20]).glob('attempt-*'))) for r in rows)),
        no_movement=dict(zero_acceptance_fits=sum(r['accepted']==0 for r in acceptance),
            zero_acceptance_models_kernels=dict(Counter(r['model']+'/'+r['kernel'] for r in acceptance if r['accepted']==0)),
            retained_all_parameters_constant=sum(r['retained_all_parameters_constant'] for r in acceptance)),
        speed=speed,
        diagnostics=dict(max_finite_rhat=max(s['rhat'] for s in flat if s['rhat'] is not None),
            min_finite_bulk_ess=min(s['ess_bulk'] for s in flat if s['ess_bulk'] is not None),
            min_finite_tail_ess=min(s['ess_tail'] for s in flat if s['ess_tail'] is not None),
            fits_with_finite_rhat_over_1_01=sum(r['finite_rhat_over_1_01'] for r in diagnostic_rows),
            constant_variable_count=sum(s['state']=='undefined_no_variation' for s in flat),
            constant_fits=sum(bool(r['constant_variables']) for r in diagnostic_rows),
            constant_models=dict(Counter(r['model'] for r in diagnostic_rows if r['constant_variables'])),
            elapsed_seconds=sum(r['diagnostic_seconds'] for r in diagnostic_rows)),
        resources=dict(cuda_peak_allocated_bytes=max(r['memory']['peak_allocated_bytes'] for r in cuda),
            cuda_peak_reserved_bytes=max(r['memory']['peak_reserved_bytes'] for r in cuda),
            host_scalar_reads=sum(r['host_scalar_reads'] for r in rows),
            host_scalar_wait_seconds=sum(r['host_scalar_wait_seconds'] for r in rows),
            all_attempt_seconds=summary['all_attempt_seconds'],
            cpu_peak_rss='not measured per formal fit; array estimate only'),
        notes=['Speed ratios compare sequential to time executor on the same device and kernel.',
            'n=4 independent tapes per cell; bootstrap intervals are exploratory and pointwise.',
            'Warmed repeats are technical repetitions, not new independent tapes.',
            'Finite Rhat >1.01 count is a descriptive post-run diagnostic, not a frozen pass rule.',
            'diagnostic-input q labels contain constrained model parameters, followed by f estimands.',
            'Constant diagnostics and unresolved L1/L2 finite references are not accuracy passes.',
            'Host scalar wait includes device waiting; it is not isolated Python interpreter cost.'],
        input_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in (
            ANALYSIS/'summary.json',ANALYSIS/'run-metrics.json',RUN/'modern-diagnostics.json',
            RUN/'protocol.json',Path(__file__))})
    write(ANALYSIS/'delivery-review.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
