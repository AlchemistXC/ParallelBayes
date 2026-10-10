#!/usr/bin/env python3
"""Describe all frozen R technical timings without treating them as new experiments."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def span(values):
    if len(values) != 4 or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Exactly four finite, nonnegative technical observations required')
    return dict(median=statistics.median(values), minimum=min(values), maximum=max(values), values=values)


def report(analysis, recovery, output):
    analysis, recovery, out = Path(analysis), Path(recovery), Path(output)
    if out.exists():
        raise FileExistsError('Use a new output directory')
    summary = json.loads((analysis/'SUMMARY.json').read_text())
    resume = json.loads(recovery.read_text())
    if not (summary['all_numerical_checks_passed'] and summary['rows'] == 64 and
            summary['missing_or_failed_processes'] == 0 and resume['passed'] and
            resume['new_processes'] == 0 and resume['reused_processes'] == 32):
        raise ValueError('Actual complete calls, independent checks and recovery required')
    with (analysis/'calls.csv').open(newline='') as f:
        calls = list(csv.DictReader(f))
    if len(calls) != 64 or len({r['task_id'] for r in calls}) != 32:
        raise ValueError('Unexpected timing frame')
    order = [('rwm','sequential'),('rwm','online_picard'),('mala','sequential'),('mala','quasi_deer')]
    rows = []
    for audit in (False, True):
        for kernel, executor in order:
            selected = [r for r in calls if r['audit'] == str(audit) and
                        r['kernel'] == kernel and r['executor'] == executor]
            first = sorted([r for r in selected if r['call'] == 'first'],key=lambda r:int(r['block']))
            later = sorted([r for r in selected if r['call'] == 'subsequent'],key=lambda r:int(r['block']))
            if len(first) != 4 or len(later) != 4 or len({r['block'] for r in first}) != 4 or any(r['status']!='completed' for r in selected):
                raise ValueError('Incomplete or failed technical cell')
            row = dict(audit=audit,kernel=kernel,executor=executor,technical_replays=4,
                first=span([float(r['cold_R_ready_seconds']) for r in first]),
                subsequent=span([float(r['call_seconds']) for r in later]),
                load=span([float(r['load_seconds']) for r in first]),
                target=span([float(r['target_seconds']) for r in first]))
            for phase in ('invoke','transfer_to_R','posterior_conversion','diagnostics','archive'):
                row[phase+'_first'] = span([float(r[phase+'_seconds']) for r in first])
                row[phase+'_subsequent'] = span([float(r[phase+'_seconds']) for r in later])
            rows.append(row)
    checks=summary['numerical_checks']
    evidence=dict(schema='r-frontend-cost-description-v1',rows=rows,
        input_blocks=1,formal_repetitions_added=0,technical_processes=32,calls=64,
        independent_acceptance_mismatches=sum(r['acceptance_mismatches'] for r in checks),
        max_path_difference=max(r['max_abs_error'] for r in checks),
        analysis_files={p.name:sha(p) for p in sorted(analysis.iterdir()) if p.is_file()},
        recovery_sha256=sha(recovery),intervals='None: four technical replays of one actual input.',
        cold_boundary='Actual R process launch to first results-ready notification, before evidence archive.',
        subsequent_boundary='In-process full invoke, R transfer, conversion and diagnostics; not warmed kernel alone.')
    def fmt(x):
        return f"{x['median']:.3f} [{x['minimum']:.3f}, {x['maximum']:.3f}]"
    names={('rwm','sequential'):'RWM / 顺序',('rwm','online_picard'):'RWM / Picard',('mala','sequential'):'MALA / 顺序',('mala','quasi_deer'):'MALA / quasi-DEER'}
    tex=[r'\begin{table}[htbp]\centering\small',r'\begin{tabular}{llrr}\toprule',r'模式 & 工作流 & R启动至首次结果/秒 & 会话内再次调用/秒\\\midrule']
    for r in rows:
        tex.append(('审计' if r['audit'] else '普通')+' & '+names[(r['kernel'],r['executor'])]+' & '+fmt(r['first'])+' & '+fmt(r['subsequent'])+r'\\')
    tex.extend([r'\bottomrule\end{tabular}',r'\caption{M4 CPU上的R前端技术计时。每格四次串行新进程，给出中位数及最小--最大值；同一实际Poisson输入，四链各128步。首次结果边界含启动和依赖载入，再次调用仍含采样、传输、转换和诊断；完整证据写盘另记。技术重复不增加正式研究的独立样本量，未构造统计区间。}',r'\label{tab:r-frontend}',r'\end{table}'])
    out.mkdir(parents=True)
    (out/'SUMMARY.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    (out/'r-frontend.generated.tex').write_text('\n'.join(tex)+'\n')
    manifest={p.name:sha(p) for p in out.iterdir() if p.is_file()}
    (out/'SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(rows=len(rows),calls=64,formal_repetitions_added=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in ('analysis','recovery','output'):p.add_argument('--'+a,required=True)
    report(**vars(p.parse_args()))
