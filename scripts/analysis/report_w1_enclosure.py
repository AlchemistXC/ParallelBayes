#!/usr/bin/env python3
"""Render W1 reference tables only from completed, independently audited evidence.

This report never evaluates the target or creates a reference from progress files.
Decimal bounds are rounded outward from exact rational endpoints.
"""
from __future__ import annotations
import argparse
import csv
from fractions import Fraction as F
import hashlib
import io
import json
from pathlib import Path

NAMES = ['alpha', 'beta', 'alpha_squared', 'beta_squared',
         'p_switch_0m', 'p_switch_100m', 'beta_positive']
LABELS = [r'$\alpha$', r'$\beta$', r'$\alpha^2$', r'$\beta^2$',
          r'$p(0)$', r'$p(100)$', r'$\Pr(\beta>0)$']
PROTOCOL_SHA = '85506f871a4fedb6f1cb30da1d9509afa764d2621e40ee51c48a1a6b44a97d36'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def interval(record):
    lo, hi = (F(int(record[k][0]), int(record[k][1]))
              for k in ('lower_exact', 'upper_exact'))
    require(lo <= hi, 'reversed reported interval')
    return lo, hi


def ball(record):
    def value(pair):
        n, e = int(pair[0]), int(pair[1])
        require(abs(e) <= 100000, 'unreasonable exponent')
        return F(n * (1 << e)) if e >= 0 else F(n, 1 << -e)
    mid, radius = map(value, record['binary_ball'])
    require(radius >= 0, 'negative ball radius')
    return mid - radius, mid + radius


def decimal_bound(value, places, upper=False):
    """Fixed decimal outward rounding, including negative values and exact zero."""
    scale = 10 ** places
    scaled = F(value) * scale
    integer = (-((-scaled.numerator) // scaled.denominator) if upper
               else scaled.numerator // scaled.denominator)
    sign = '-' if integer < 0 else ''
    digits = str(abs(integer)).zfill(places + 1)
    return sign + (digits[:-places] + '.' + digits[-places:] if places else digits)


def meets(bounds, event=False):
    lo, hi = bounds
    half = (hi - lo) / 2
    return ((lo > 0 and half <= F('1e-13') and half <= abs((hi + lo)/2)/100)
            if event else half <= F('1e-8'))


def csv_text(rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def read_checked(directory, names):
    manifest = json.loads((directory/'checksums.json').read_text())
    require(set(names) <= set(manifest), 'required report input absent from manifest')
    result = {}
    for name in names:
        require(sha(directory/name) == manifest[name], 'report input checksum differs: ' + name)
        result[name] = json.loads((directory/name).read_text())
    return result


def render(source, audit):
    require((source/'SUMMARY.json').is_file(), 'completed W1 summary required')
    summary = read_checked(source, ['SUMMARY.json'])['SUMMARY.json']
    evidence = read_checked(audit, ['audit.json', 'reference-sensitivity.json'])
    check, sensitivity = evidence['audit.json'], evidence['reference-sensitivity.json']
    require(check['passed'] and check['both_methods_present'], 'both completed audited methods required')
    require(check['source_summary_sha256'] == sha(source/'SUMMARY.json'), 'audit summary binding differs')
    require(check['protocol_sha256'] == summary['protocol_sha256'] == PROTOCOL_SHA, 'reference protocol differs')
    require(check['numerical_source_commit'] == summary['source_commit'], 'numerical source differs')
    require(check['new_mcmc_calls'] == check['new_integrand_evaluations'] == summary['new_mcmc_fits'] == 0
            and summary['preserved_old_references'], 'reference scope changed')
    require([r['method'] for r in check['methods']] == [r['method'] for r in summary['methods']]
            == ['gauss2', 'simpson'], 'method identity differs')
    require(set(check['combined']) == set(summary['intersection']) == set(NAMES), 'incomplete reference functions')
    combined = {name: interval(check['combined'][name]) for name in NAMES}
    for name, bounds in combined.items():
        require(bounds == ball(summary['intersection'][name]), 'reference interval projection differs')
    method_bounds = {}
    method_rows = []
    for verified, saved in zip(check['methods'], summary['methods']):
        method = verified['method']
        require(set(verified['function_intervals']) == set(NAMES), 'incomplete method functions')
        method_bounds[method] = {name: interval(verified['function_intervals'][name]) for name in NAMES}
        require(interval(verified['denominator']) == ball(saved['posterior']['normalizer'])
                and interval(verified['denominator'])[0] > 0, 'positive normalizer not verified')
        for name, bounds in method_bounds[method].items():
            require(bounds == ball(saved['posterior']['functions'][name]), 'method interval projection differs')
            require(verified['functions_meeting_targets'][name] == meets(bounds, name == 'beta_positive'),
                    'method accuracy status differs')
        require(verified['stop_reason'] == saved['stop_reason'], 'method stopping status differs')
        require(verified['charged'] == saved['charged_evaluations_upper_bound']
                and verified['callbacks'] == saved['completed_external_callbacks'], 'work accounting differs')
        method_rows.append(dict(method=method, stop_reason=verified['stop_reason'],
            active_cells=saved['active_cells'], charged_adaptive=verified['charged'],
            charged_probes=saved['probe_charged_evaluations'], callbacks=verified['callbacks'],
            functions_meeting_target=sum(verified['functions_meeting_targets'].values())))
    for name in NAMES:
        exact_lo = max(method_bounds[m][name][0] for m in method_bounds)
        exact_hi = min(method_bounds[m][name][1] for m in method_bounds)
        require(combined[name][0] <= exact_lo <= exact_hi <= combined[name][1],
                'combined reference does not enclose exact intersection')
    require(check['charged_evaluations'] == summary['charged_evaluations_upper_bound'] <= 4000000,
            'global work accounting differs')
    all_met = all(r['functions_meeting_target'] == 7 for r in method_rows)
    require(all_met == check['all_method_targets_met'] == summary['all_method_targets_met'],
            'overall accuracy status differs')
    require(sum(sensitivity['old_outcomes'].values()) == 432, 'old task denominator changed')
    singles, pairs = sensitivity['individual'], sensitivity['paired']
    require(len(singles) == 126 and len(pairs) == 504, 'incomplete reference sensitivity')
    require(len({(r['function'], r['budget'], r['workflow']) for r in singles}) == 126,
            'duplicate individual row')
    require(len({(r['function'], r['budget'], r['workflow_a'], r['workflow_b']) for r in pairs}) == 504,
            'duplicate paired row')
    rows, stability = [], []
    for name, label in zip(NAMES, LABELS):
        one = [r for r in singles if r['function'] == name]
        paired = [r for r in pairs if r['function'] == name]
        require(len(one) == 18 and len(paired) == 72, 'missing function sensitivity')
        require(all(r['budget'] in (1024, 4096) and r['planned'] == 24 and 0 <= r['valid'] <= 24 for r in one),
                'individual count differs')
        membership = {r['old_reference_in_enclosure'] for r in one}
        require(len(membership) == 1, 'inconsistent reference membership')
        counts = dict(stable_sign=0, exact_tie=0, unresolved=0, opposite_old_sign=0, missing_pairs=0)
        for row in paired:
            require(row['planned'] == 24 and row['budget'] in (1024, 4096)
                    and 0 <= row['paired_valid'] <= 24 and len(set(row['paired_replicates'])) == row['paired_valid'],
                    'paired count differs')
            if row['paired_valid'] == 0:
                require(row['loss_difference_range'] is None, 'missing pair assigned a loss')
                counts['missing_pairs'] += 1
                continue
            lo, hi = interval(row['loss_difference_range'])
            old_lo, old_hi = interval(row['old_reference_loss_difference'])
            require(old_lo == old_hi, 'old fixed-reference difference is not a point')
            stable = hi < 0 or lo > 0
            require(row['reference_sign_stable'] == stable, 'sensitivity sign projection differs')
            expected_direction = 'a_lower_loss' if hi < 0 else 'b_lower_loss' if lo > 0 else 'unresolved'
            require(row['direction'] == expected_direction, 'sensitivity direction differs')
            if stable:
                counts['stable_sign'] += 1
                counts['opposite_old_sign'] += int((old_lo > 0 and hi < 0) or (old_lo < 0 and lo > 0))
            elif lo == hi == 0:
                counts['exact_tie'] += 1
            else:
                counts['unresolved'] += 1
        stability.append(dict(function=name, **counts))
        lo, hi = combined[name]
        places = 18 if name == 'beta_positive' else 12
        rows.append(dict(function=name, lower=decimal_bound(lo, places), upper=decimal_bound(hi, places, True),
            halfwidth_upper=decimal_bound((hi-lo)/2, 20, True),
            gauss2_met=meets(method_bounds['gauss2'][name], name == 'beta_positive'),
            simpson_met=meets(method_bounds['simpson'][name], name == 'beta_positive'),
            intersection_met=meets((lo, hi), name == 'beta_positive'), old_reference_inside=membership.pop()))
    totals = {k: sum(r[k] for r in stability) for k in stability[0] if k != 'function'}
    lines = ['# W1参考区间与原结果敏感性', '',
        '两种有限域求积及矩尾界已完成独立端点、分区和汇总检查。区间有效性依赖固定实现的球算术、四阶导数余项与凹性尾界；有限测试不是一般软件正确性证明。', '',
        '| 函数 | 区间下界 | 区间上界 | Gauss达标 | Simpson达标 | 原参考在交集内 |',
        '|---|---:|---:|---|---|---|']
    yes = lambda x: '是' if x else '否'
    tex_rows = []
    for label, row in zip(LABELS, rows):
        lines.append('| '+label+' | '+' | '.join([row['lower'],row['upper'],yes(row['gauss2_met']),yes(row['simpson_met']),yes(row['old_reference_inside'])])+' |')
        tex_rows.append(label+' & $['+row['lower']+', '+row['upper']+']$ & '+yes(row['gauss2_met'])+'/'+yes(row['simpson_met'])+r'\\')
    status = '两种规则的七函数均达到预设目标。' if all_met else '存在未达到预设精度的函数，逐项结果按原标准保留。'
    lines += ['',status, '', '表中区间为两规则区间的交集，十进制端点向外舍入。连续函数使用12位小数，事件使用18位；精度判断使用未缩写的二进制区间。两规则共享目标、导数与尾界代码，一致性不等于两套完全独立数学实现。', '',
        '在全部504个预定函数—预算—方法对中，参考区间内损失差符号固定的有'+str(totals['stable_sign'])+'个，始终相等的有'+str(totals['exact_tie'])+'个，跨越或接触零且非恒等的有'+str(totals['unresolved'])+'个，缺少有效配对的有'+str(totals['missing_pairs'])+'个；相对旧参考点符号反转的有'+str(totals['opposite_old_sign'])+'个。', '',
        '此处比较同一有效配对集合的经验平方差。参考区间传播不新增重复，也不代替重复实验置信区间、探索诊断或效应大小解释。原参考及达标率不覆盖。', '',
        '全局预留评价次数为'+str(check['charged_evaluations'])+'；新MCMC拟合为0。每种规则的停止原因、实际回调数和单元数见method-costs.csv。全部126行单方法及504行配对范围保留在reference-sensitivity.json。']
    tex = [r'\begin{table}[htbp]\centering\small',r'\begin{tabular}{lrl}\toprule',
        r'函数 & 后验期望区间 & Gauss/Simpson达标\\\midrule',*tex_rows,
        r'\bottomrule\end{tabular}',
        r'\caption{W1后验函数的数值包络交集。端点向外舍入；各规则的精度状态由未舍入区间判断。连续函数半宽目标为$10^{-8}$，事件半宽目标为$10^{-13}$且相对半宽不超过1\%。}',
        r'\label{tab:w1-enclosure}\end{table}',status]
    provenance = dict(identity='w1-reference-report-v1',
        source_summary_sha256=sha(source/'SUMMARY.json'), audit_sha256=sha(audit/'audit.json'),
        sensitivity_sha256=sha(audit/'reference-sensitivity.json'),
        source_checksums_sha256=sha(source/'checksums.json'), audit_checksums_sha256=sha(audit/'checksums.json'),
        generator_sha256=sha(Path(__file__)), protocol_sha256=PROTOCOL_SHA,
        numerical_source_commit=summary['source_commit'], old_outcomes=sensitivity['old_outcomes'],
        old_references_preserved=True, new_mcmc_calls=0, all_method_targets_met=all_met,
        reference_sensitivity_counts=totals,
        scope='Completed audited reference only; numerical reference sensitivity is not sampling uncertainty.')
    return {'REPORT.md':'\n'.join(lines)+'\n', 'w1-reference-table.generated.tex':'\n'.join(tex)+'\n',
        'reference-intervals.csv':csv_text(rows), 'method-costs.csv':csv_text(method_rows),
        'reference-sign-sensitivity.csv':csv_text(stability),
        'reference-sensitivity.json':(audit/'reference-sensitivity.json').read_text(),
        'report.provenance.json':json.dumps(provenance,ensure_ascii=False,indent=2)+'\n'}


def build(source, audit, output):
    require(not output.exists(), 'fresh report output required')
    rendered = render(source, audit)
    output.mkdir(parents=True)
    for name, contents in rendered.items():
        (output/name).write_text(contents, encoding='utf-8')
    (output/'checksums.json').write_text(json.dumps({name:sha(output/name) for name in rendered},indent=2)+'\n')
    return list(rendered)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('source','audit','output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({'files':build(args.source,args.audit,args.output), 'new_mcmc_calls':0}))
