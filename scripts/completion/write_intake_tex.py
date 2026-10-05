"""Render bounded cross-host findings; do not reinterpret original pass flags."""
import argparse
import hashlib
import json
from pathlib import Path


def render(root):
    source = root / 'benchmark/analysis/outputs/windows-round2-intake-v1/summary.json'
    d = json.loads(source.read_text())
    mh, nuts, f2 = d['MH'], d['NUTS'], d['F2']
    if d['formal_inference_complete'] or d['new_independent_repetitions'] != 0:
        raise ValueError('This text is only for the bounded reception companion')
    if mh['strict_original_Mac_audit_passed'] or f2['completed_workflows'] != 0:
        raise ValueError('Evidence changed: review the interpretation before rendering')
    return '% Input SHA256 ' + hashlib.sha256(source.read_bytes()).hexdigest() + ' ' + source.relative_to(root).as_posix() + '\n' + rf'''第二轮接收把无约束路径、参数变换与下游诊断分别核对。
{mh['workflows']}份MH保存路径均在原容差内，接受事件失配为{mh['acceptance_mismatches']}；但从同一无约束状态在Mac重算原尺度输出时，
{mh['nonexact_outputs']}份不满足原逐位相等要求，最大绝对差为$8.88\times10^{{-15}}$。
这项严格跨系统检查仍记为失败，不能通过事后添加容差改称全部通过。
Windows同机核验与Mac跨系统重算回答不同问题。

CPU Pyro NUTS在{nuts['targets']}个目标上的串行/四进程技术对照中，{nuts['exact_serial_spawn_array_pairs']}组保存数组逐字节相同。
对收到的{nuts['preserved_Windows_binary_roundtrips']}份原二进制重新计算R诊断，有限$\hat R$与tail ESS一致，
bulk ESS最大差约$1.02\times10^{{-12}}$，不可判定位置一致。
这不意味着重复计算后验函数也必然逐位相同，更不增加独立统计重复数。
原短链的探索不足仍然成立。

实际数组传递同样是复现契约的一部分。Windows重新生成的六份候选输入中，
噪声与导数探测数组相同，但对数均匀数组有{f2['differing_log_uniform_elements']}/49152个元素不同，最大差约$4.44\times10^{{-16}}$。
因此原协议正确地拒绝启动{f2['pending_workflows']}项后续机制工作流。
已补齐原始输入文件，尚无该批执行结果；相同种子和依赖版本不能替代实际数组校验。
上述核验定位了差异层次，不证明特定编译器或数学库的因果责任。
'''


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.write_text(render(a.root), encoding='utf-8')
