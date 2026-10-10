#!/usr/bin/env python3
"""Project verified compact statistics into bounded Chinese manuscript inputs.

This preserves saved estimators/intervals and all declared comparisons. Preview
output cannot pass the final Mac reconstruction gate. No sampling is performed.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/analysis'))
from formal_report import StatisticsBundle, model_tables, MODELS, DISPLAY
from formal_runtime import file_hash
from plot_compact_overview import select_complete_contrasts

ORDER = ('cpu-rwm-sequential','cpu-rwm-online_picard','cuda-rwm-sequential','cuda-rwm-online_picard',
         'cpu-mala-sequential','cpu-mala-quasi_deer','cuda-mala-sequential','cuda-mala-quasi_deer','cpu-nuts-spawn_chains')


def final_gate(bundle, review, review_sha):
    if review is None or review_sha is None or file_hash(review) != review_sha:
        raise ValueError('Final manuscript requires a verified Mac review')
    value = json.loads(Path(review).read_text())
    if (value['stage'] != 'complete_receiver_review' or value['visited'] != 4144 or
            value['dispositions'] != {'analyzed':4144} or value['frame'] != bundle.frame or
            value['identity_sha256'] != bundle.summary['analysis_identity_sha256'] or
            not value['resume_proof_sha256']):
        raise ValueError('Statistics are not bound to the complete Mac review')
    return value


def number(value, digits=2):
    return '--' if value is None else f'{value:.{digits}f}'


def squared_error(row):
    center = number(None if row['point'] is None else row['point']*1e6)
    if row['low'] is None:
        return center + ' [--]'
    return center+' ['+number(row['low']*1e6)+', '+number(row['high']*1e6)+']'


def build(statistics_directory, manifest_sha256, output, *, review=None, review_sha256=None, preview=False):
    out = Path(output)
    if out.exists():
        raise FileExistsError('Use a fresh manuscript projection directory')
    bundle = StatisticsBundle(statistics_directory, manifest_sha256)
    if not bundle.compact_frame or set(bundle.models) != set(MODELS) or bundle.frame['scope'] != 'formal_inference':
        raise ValueError('Complete compact research frame required')
    evidence = None if preview else final_gate(bundle, review, review_sha256)
    summaries, tables = {}, {}
    for name in MODELS:
        summaries[name], tables[name] = model_tables(bundle, name)
    selected = select_complete_contrasts(tables)
    costs = []
    for device, kernel in [('cpu','rwm'),('cuda','rwm'),('cpu','mala'),('cuda','mala')]:
        rows = [r for r in selected if r['device'] == device and r['kernel'] == kernel]
        points = [r['point'] for r in rows if r['point'] is not None]
        costs.append(dict(device=device, kernel=kernel, planned_contrasts=len(rows), available_points=len(points),
            minimum=min(points, default=None), maximum=max(points, default=None), points_above_one=sum(p>1 for p in points),
            intervals_available=sum(r['low'] is not None for r in rows),
            minimum_paired=min(r['paired'] for r in rows), maximum_paired=max(r['paired'] for r in rows), source_rows=rows))
    outcomes, diagnostics, nuts = Counter(), [], []
    for name in MODELS:
        s, t = summaries[name], tables[name]
        outcomes.update(s['main_outcomes'])
        diagnostic = dict(model=name, function_rows=sum(r['received'] for r in t['diagnostics']),
            rhat_above=sum(r['rhat_above_1_01'] for r in t['diagnostics']),
            rhat_undefined=sum(r['rhat_undefined'] for r in t['diagnostics']))
        diagnostic['rhat_at_most_1_01'] = diagnostic['function_rows']-diagnostic['rhat_above']-diagnostic['rhat_undefined']
        diagnostics.append(diagnostic)
        nuts.extend(dict(model=name, **r) for r in t['nuts'])
    wells = []
    for workflow in ORDER:
        rows = [r for r in tables['W1']['errors'] if r['workflow'] == workflow and r['budget'] == 4096 and r['phase'] == 'ordinary_workflow']
        if len(rows) != 7 or len({r['function'] for r in rows}) != 7:
            raise ValueError('Incomplete W1 function/workflow frame')
        pair = {name:next(r for r in rows if r['function'] == name) for name in ('alpha','beta')}
        if any(r['available'] != 24 or r['reference_kind'] != 'numerical_uncertified' for r in pair.values()):
            raise ValueError('W1 table denominator/reference changed; update the manuscript explicitly')
        if pair['alpha']['mean_seconds'] != pair['beta']['mean_seconds']:
            raise ValueError('W1 functions have different cost sets')
        wells.append(dict(workflow=workflow, n=24, ordinary_mean_seconds=pair['alpha']['mean_seconds'], **pair))
    claims = dict(schema='compact-manuscript-projection-v1', preview_reconstruction_pending=preview,
        frame=bundle.frame, statistics_manifest_sha256=manifest_sha256,
        reconstruction_review_sha256=None if preview else review_sha256,
        main_outcomes=dict(outcomes), ordinary_costs=costs, diagnostics=diagnostics,
        nuts_diagnostics=nuts, wells_4096=wells,
        selection='All 72 ordinary same-kernel contrasts; all models in outcome/diagnostic table. W1 alpha/beta at longer measured budget are main-text estimands; full 36-function/two-budget report remains available.',
        reference_uncertainty_in_BCa=False, intervals='Saved pointwise 95% BCa with 9999 resamples; conditional on available original complete four-chain repetitions.',
        new_sampler_calls=0, new_statistical_estimates=0)
    macros = {'PBCompactValid':outcomes['valid'], 'PBCompactNumerical':outcomes['numerical_failure'],
        'PBCompactUnclassified':outcomes['output_failure_unclassified'],
        'PBCompactFunctionRows':sum(d['function_rows'] for d in diagnostics),
        'PBCompactHighRhat':sum(d['rhat_above'] for d in diagnostics),
        'PBCompactUndefinedRhat':sum(d['rhat_undefined'] for d in diagnostics)}
    for prefix, row in zip(('PBCPURWM','PBCUDARWM','PBCPUMALA','PBCUDAMALA'), costs):
        macros[prefix+'Min'] = f"{row['minimum']:.3f}"
        macros[prefix+'Max'] = f"{row['maximum']:.3f}"
        macros[prefix+'Above'] = row['points_above_one']
    scalar = '% Generated from a verified scalar bundle; do not edit numbers by hand.\n'
    if preview:
        scalar += '% PREVIEW: Mac full reconstruction gate has not been passed.\n'
    scalar += '\n'.join('\\newcommand{\\'+k+'}{'+str(v)+'}' for k,v in macros.items())+'\n'
    table = [r'\begin{table}[htbp]\centering\small',r'\begin{tabular}{lrrr}\toprule',
        r'工作流 & 普通耗时（秒） & $\alpha$参考平方差（$10^{-6}$） & $\beta$参考平方差（$10^{-6}$）\\\midrule']
    for row in wells:
        table.append(DISPLAY[row['workflow']]+' & '+number(row['ordinary_mean_seconds'])+' & '+squared_error(row['alpha'])+' & '+squared_error(row['beta'])+r'\\')
    table += [r'\bottomrule\end{tabular}',
        r'\caption{水井W1在每链4096次保留转移下的普通工作流耗时均值和参考平方差。每行24份原始四链重复；方括号为条件95\% BCa区间。表中沿用冻结求积参考点；BCa区间不传播参考误差，后续数值包络分析另列。耗时包含普通进程与R诊断，不含最外层R前端。其余五函数和1024步结果见完整结果附录图R39--R45。}',
        r'\label{tab:compact-wells}',r'\end{table}']
    outcome_table = [r'\begin{table}[htbp]\centering\small',r'\begin{tabular}{lrrrrrr}\toprule',
        r'目标 & 有效 & 数值失败 & 未分类失败 & 函数行 & $\hat R>1.01$ & $\hat R$未定\\\midrule']
    for name, diag in zip(MODELS, diagnostics):
        counts = summaries[name]['main_outcomes']
        outcome_table.append(name+' & '+' & '.join(str(v) for v in (counts.get('valid',0),counts.get('numerical_failure',0),counts.get('output_failure_unclassified',0),diag['function_rows'],diag['rhat_above'],diag['rhat_undefined']))+r'\\')
    outcome_table += [r'\bottomrule\end{tabular}',
        r'\caption{紧凑研究各目标的全部432项主任务状态，以及有效拟合的所选函数诊断。函数行按拟合与函数计数，不是独立重复；未分类失败保持原状态。缓存探测不进入这些后验计数。}',r'\label{tab:compact-outcomes}',r'\end{table}']
    out.mkdir(parents=True)
    (out/'claims.json').write_text(json.dumps(claims, indent=2, allow_nan=False)+'\n')
    for name, content in [('compact-scalars.generated.tex',scalar), ('compact-wells.generated.tex','\n'.join(table)+'\n'), ('compact-outcomes.generated.tex','\n'.join(outcome_table)+'\n')]:
        (out/name).write_text(content)
    manifest = {p.name:file_hash(p) for p in out.iterdir() if p.is_file()}
    (out/'SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(preview=preview, outcomes=dict(outcomes), ordinary_contrasts=len(selected), wells_workflows=len(wells))))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('statistics-directory','manifest-sha256','output'):
        p.add_argument('--'+name, required=True)
    p.add_argument('--review')
    p.add_argument('--review-sha256')
    p.add_argument('--preview',action='store_true')
    build(**vars(p.parse_args()))
