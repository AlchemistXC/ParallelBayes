#!/usr/bin/env python3
"""Build the L2 companion report from immutable outputs and independent audit."""
import argparse
import csv
import json
from pathlib import Path
import shutil


def build(source,audit,output):
    if output.exists():raise FileExistsError('Fresh report directory required')
    output.mkdir(parents=True)
    summary=json.loads((source/'SUMMARY.json').read_text());check=json.loads((audit/'audit.json').read_text())
    if not check['passed']:raise ValueError('Independent reaggregation required')
    estimates=summary['reference_estimates'];selected=json.loads((source/'SELECTION.json').read_text())
    lines=['# L2稀有事件独立参考结果','',
        '2026-10-10。按冻结的l2-rare-reference-is-v1完成两套提议各8批、每批131072点；正式参考共2097152点，另16384个试探点全部排除。两套提议均达到预设权重和相对MCSE门槛，相差不超过3倍合并MCSE。结果是带近似蒙特卡洛误差的自归一化重要性估计，不是确定误差认证。','',
        '| 提议标准差倍数（t，事件正态） | P(θ1>0) | MCSE | 相对MCSE | 事件ESS | 分母ESS | 最大事件权重 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for e in estimates:
        lines.append(f"| {tuple(e['scale_pair'])} | {e['probability']:.9g} | {e['mcse']:.6g} | {100*e['relative_mcse']:.3f}% | {e['numerator_ess']:.2f} | {e['denominator_ess']:.2f} | {e['maximum_numerator_weight']:.6g} |")
    lines += ['',
        'MCSE按每套提议8个独立批次的分子/分母联合协方差计算；没有把重要性ESS当独立批次数，也没有平均16个批次比率。第二套提议的事件权重集中度更高，误差更大；两套结果均保留，没有事后只呈现更精确的一套。8批MCSE仍可能不稳定，质量门槛通过不保证名义覆盖率。','',
        '## 对既有研究的影响','',
        '原262144个相关参考样本的符号事件恒零，仍不能据此把概率定为0。新增独立参考把该事件定位到约10⁻⁹量级。原正式L2主任务432项中414项有效、18项失败；全部414项有效输出的事件均值均为0。若只看此事件的原尺度平均平方误差，两套新参考给出的数值分别为'+', '.join(f"{e['probability']**2:.6g}" for e in estimates)+'。这个绝对误差很小，但全零估计对非零小概率的相对误差仍为100%。','',
        '因此，本补充说明了原绝对误差尺度对极稀有事件的敏感性限制；它没有证明链已经探索到事件域。原常量事件的Rhat/ESS继续不可判定，原18项失败、全部诊断、正式参考文件及全函数判据不回写。新增事件参考及其不确定性单独列示；既有前三个连续函数的参考误差仍按原分析处理。','',
        '## 核验与复现','',
        f"独立程序逐项核对{check['checked_source_assets']}件资产，从保存权重以补偿求和重算比率、ESS和MCSE；另核对{check['scalar_log_weight_checks']}个预定/极值点的原目标和完整混合密度，最大log权重差{check['maximum_independent_log_weight_difference']:.6g}。没有调用被核验的比率/MCSE汇总函数。恢复运行复用全部2113536个提议点和260个权重块，新增随机点与权重计算均为0。",
        '',f"冻结采样源码为`{summary['source_commit']}`，协议SHA256为`{summary['protocol_sha256']}`。实际目标身份`{summary['target_sha256']}`与旧协议相同。冻结前6个确定目标点通过128-bit Arb标量对照。",
        '', '四组试探按预先规定的相对影响量方差排序，固定选择'+str(selected['selected'])+'，选择及提议参数在正式点生成前保存。实际随机点、组件、PCG64初末状态、所有权重块与校验和保留；分析只读复用，不改变旧结果。',
        '', '完整结果见SUMMARY.json；各批次见batch-results.csv；原18组方法—预算的事件伴随误差见old-L2-event-sensitivity.json。安装锁、原目标、源码和再分析入口随本地归档提供，未自动公开原始证据。']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    rows=[]
    for e in estimates:
        for i,b in enumerate(e['batches']):rows.append(dict(candidate=e['candidate'],batch=i,**b))
    with (output/'batch-results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    for name in ('SUMMARY.json','SELECTION.json'):shutil.copyfile(source/name,output/name)
    for name in ('audit.json','batches-reaggregated.json','old-L2-event-sensitivity.json'):shutil.copyfile(audit/name,output/name)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source','audit','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();build(a.source.resolve(),a.audit.resolve(),a.output.resolve())
