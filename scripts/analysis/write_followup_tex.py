"""Render reviewed Windows follow-up evidence; saved records, no sampler calls.

This is a fixed evidence edition, not a generic new-study report. Input pins
bind it to the independently checked returns. A different return requires an
explicit new review, not replacing hashes to obtain a passing report.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

INPUTS = {'benchmark/protocols/mechanism-windows-pilot-v1.json': 'd8b3a6090148f1ea7d3d49c20bb01d2349b345e5c1fab5d0c209021fb0f17e4e', 'benchmark/analysis/outputs/windows-followup-intake-v1/comparison-summary.json': 'c99b15bf200d78d57b25faf668de37d7fb0c04cfd9c2729640fb6798859f1772', 'benchmark/analysis/outputs/windows-followup-intake-v1/numpy-summary.json': '8b89658b151fa4a0852038f497e6838edaf18da3409b56b7f199b86827f87a37', 'benchmark/analysis/outputs/windows-followup-intake-v1/runtime/SUMMARY.json': 'd4b9ce12c23ecdbff615bc6566e2a5a61e43cf073aeadbb7f193bd82db670f86', 'manuscript/software/intake.generated.tex': '1d3576fe927db1433c2712f5caaff45c24aacaf6401527068754323feeda0ffa', 'manuscript/software/followup.template.tex': '749f6f6710211b9cde823f13f051db57e45ad6b9a1c59d5cb3f9766b9f449f9e', 'figures/windows-mechanism-pilot-v1/work-and-cached-cost.pdf': 'cb5bc9c51a9735d5e7f7a10de697c141ecac47093c26c6de5d505042a7b29329', 'benchmark/analysis/outputs/mechanism-windows-pilot-v1/windows-20261006/analysis-cpu/workflows.csv': '04d86adde990daa6809994ed97b0cbd3fb81a940771a5f0e6a54101b02134c7f', 'benchmark/analysis/outputs/mechanism-windows-pilot-v1/windows-20261006/analysis-cuda/workflows.csv': '9e2fd3b87f61bbb453aac19b038c42bbe11710d5d2ff455239b5ffafe48c4b8b'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render(root):
    data = {}
    for name, expected in INPUTS.items():
        p = root / name
        if p.is_symlink() or not p.is_file():
            raise ValueError('Missing/nonregular evidence input: ' + name)
        data[name] = p.read_bytes()
        if sha(data[name]) != expected:
            raise ValueError('Changed reviewed input: ' + name)
    intake = 'benchmark/analysis/outputs/windows-followup-intake-v1/'
    mechanism = 'benchmark/analysis/outputs/mechanism-windows-pilot-v1/windows-20261006/'
    comparison = json.loads(data[intake + 'comparison-summary.json'])
    reference = json.loads(data[intake + 'numpy-summary.json'])['groups']['mechanism']
    runtime = json.loads(data[intake + 'runtime/SUMMARY.json'])
    protocol = json.loads(data['benchmark/protocols/mechanism-windows-pilot-v1.json'])
    tables, work, allocation = [], {}, []
    for device in ['cpu', 'cuda']:
        rows = list(csv.DictReader(io.StringIO(data[mechanism + f'analysis-{device}/workflows.csv'].decode())))
        if len(rows) != 96 or any(r['status'] != 'completed' for r in rows):
            raise ValueError('Unexpected workflow population/status')
        grouped = {}
        for row in rows:
            if row['role'] == 'equal_512_output_chain_allocation':
                grouped.setdefault((row['model'], row['replicate']), []).append(row)
        if len(grouped) != 4:
            raise ValueError('Incomplete allocation comparison')
        for key, group in sorted(grouped.items()):
            short = [r for r in group if r['label'] == 'sequential' and int(r['chains']) == 16]
            long = [r for r in group if r['label'] == 'online_picard-w16' and int(r['chains']) == 1]
            if len(short) != 1 or len(long) != 1 or len(group) != 3:
                raise ValueError('Ambiguous allocation pairing')
            if any(int(r['total_transitions']) != 512 for r in group):
                raise ValueError('Unequal output budgets')
            allocation.append(dict(device=device, model=key[0], input=key[1],
                picard_seconds=float(long[0]['cached_sample_seconds']),
                sequential_16_seconds=float(short[0]['cached_sample_seconds']),
                ratio=float(long[0]['cached_sample_seconds']) / float(short[0]['cached_sample_seconds'])))
        for kernel in ['mala', 'rwm']:
            selected = [r for r in rows if r['kernel'] == kernel and r['label'] != 'sequential']
            ratios = [float(r['paired_cached_ratio']) for r in selected]
            checked = comparison['mechanism'][f'{device}-{kernel}']
            if len(ratios) != checked['pairs'] or sum(x > 1 for x in ratios) != checked['over_one']:
                raise ValueError('Pair population differs from independent intake')
            for x, y in [(min(ratios), checked['minimum']), (max(ratios), checked['maximum'])]:
                if not math.isclose(x, y, rel_tol=1e-14):
                    raise ValueError('Independent ratio comparison differs')
            tables.append(f"{device.upper()} / {'quasi-DEER' if kernel == 'mala' else 'Picard'} & {len(ratios)} & {checked['over_one']} & {min(ratios):.3f}--{max(ratios):.3f} " + r'\\')
            work[f'{device}-{kernel}'] = {
                column: [min(float(r[column]) for r in selected), max(float(r[column]) for r in selected)]
                for column in ['forward_maps_per_transition','JVPs_per_transition']
            }
    values = {
        'TABLE': '\n'.join(tables),
        'TAPES': str(protocol['independent_tapes_per_model']),
        'REPLAYS': str(protocol['technical_replays']),
        'PATH_ERROR': (lambda m, e: m + r"\times10^{" + str(int(e)) + "}")(*f"{reference['maximum_path_error']:.2e}".split("e")),
        'ALLOCATION_MIN': f"{min(r['ratio'] for r in allocation):.2f}",
        'ALLOCATION_MAX': f"{max(r['ratio'] for r in allocation):.2f}",
        'FORWARD_MALA': '--'.join(f'{v:g}' for v in work['cpu-mala']['forward_maps_per_transition']),
        'JVP_MALA': '--'.join(f'{v:g}' for v in work['cpu-mala']['JVPs_per_transition']),
        'FORWARD_RWM': '--'.join(f'{v:g}' for v in work['cpu-rwm']['forward_maps_per_transition']),
        'MAIN_TASKS': str(runtime['main_planned']),
        'CACHE_TASKS': str(runtime['cache_planned']),
        'CACHE_CALLS': str(runtime['cached_calls']),
        'BAD_RHAT': str(comparison['runtime']['rhat_over_1_01']),
        'DIAG_ROWS': str(comparison['runtime']['diagnostic_rows']),
        'TAIL_NULL': str(comparison['runtime']['tail_ess_null']),
    }
    old = data['manuscript/software/intake.generated.tex'].decode()
    prefix = old.split('实际数组传递同样是复现契约的一部分。')[0]
    template = data['manuscript/software/followup.template.tex'].decode()
    for key, value in values.items():
        template = template.replace('@@' + key + '@@', value)
    if '@@' in template:
        raise ValueError('Unfilled manuscript placeholder')
    provenance = ''.join(f'% Reviewed input SHA256 {value} {name}\n' for name, value in INPUTS.items())
    report = dict(scope='Saved reviewed records to manuscript; no new sampling or device timing',
        source_inputs=INPUTS, windows_workflows=192, independent_inputs_per_model=2,
        work_ranges=work, allocation_comparisons=allocation,
        formal_inference_repetitions_added=0, figures_regenerated=False)
    return provenance + prefix + template, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    text, report = render(args.root.resolve())
    outputs = [args.output] + ([args.report] if args.report else [])
    if any(p.exists() for p in outputs):
        raise FileExistsError('Use new output paths; reviewed results are not overwritten')
    for p in outputs:
        p.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding='utf-8')
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='passed', workflows=192, new_sampler_calls=0)))


if __name__ == '__main__':
    main()
