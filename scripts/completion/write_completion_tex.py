"""Rebuild the bounded F1/F2 manuscript companion from retained analysis outputs."""
import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def render(root):
    paths = ["benchmark/fixtures/rhat-midpoint-v1/case.json",
             "benchmark/analysis/outputs/completion-f1/mac-02/result.json",
             "benchmark/analysis/outputs/completion-f1/mac-02/receipt.json",
             "benchmark/analysis/outputs/completion-f2/summary.json"]
    case, result, receipt, costs = [read(root / p) for p in paths]
    if not receipt["passed"] or not all(result["checks"].values()):
        raise ValueError("Diagnostic fixture has not passed")
    if costs["tasks"] != 512 or costs["map_and_prefix_trace_checks"] != 512:
        raise ValueError("Incomplete mechanism accounting")
    if case["protocol_sha256"] != costs["protocol_sha256"]:
        raise ValueError("Companion sources use different protocols")
    q = costs["group_median_ranges"]["cuda/quasi_deer"]
    p = costs["group_median_ranges"]["cuda/online_picard"]
    rows = []
    for model in ["A1", "G2", "G1", "L1"]:
        cell = next(g for g in costs["groups"] if g["device"] == "cuda" and
                    g["executor"] == "online_picard" and g["model"] == model and g["draws"] == 512)
        v = [cell[m]["median"] for m in ["paired_warmed_speed_ratio", "acceptance_fraction",
                                        "maps_per_transition", "mean_confirmed_prefix"]]
        rows.append(f"{model} & {v[0]:.3f} & {v[1]:.5f} & {v[2]:.3f} & {v[3]:.3f}" + r"\\")
    tex = r"""\subsection{收尾阶段新增的诊断与工作量伴随分析}
\label{sec:completion-companion}
以下分析于2026年10月5日从原始Windows记录追加，没有重新采样或更改原冻结协议。
二进制输入后剩余的两个$\hat R$差异，来自H2/RWM顺序、512步、重复3的CPU与CUDA任务；
丢弃128步后的q2数组逐值相同，故不是两份独立的差异证据。
在Mac R 4.6.0、posterior 1.7.0中，未折叠分量为@BULK@，
折叠中位数比精确中点正确舍入值低一个ULP，约$2.1684\times10^{-19}$。
固定输入和其余计算，仅替换这个折叠中心，就使@RANKS@个观测的秩改变，
折叠$\hat R$由@LOWER@变为@ROUNDED@，后者重现原Windows记录。
这定位了足以解释差异的数值机制；Windows原生R中位数和构建信息的实际回执仍待核对。
两种$\hat R$都远高于1.01，不改变混合不足判断，也没有用较小值替换原诊断。
12KiB二进制样例、精确有理数中点、两中心对照和Mac回执随分析源码保存。

对512项原记录逐轮核算映射、JVP和确认前缀，全部计数检查通过。
在16个模型/预算组的中位数中，quasi-DEER每输出转移有@QMAP@次前向映射和@QJVP@次JVP；
Picard有@PMAP@次前向映射，每轮沿每链平均确认@PREFIX@步。
对应CPU/CUDA工作量一致，拒绝自环计入输出转移。映射次数不是密度调用数或FLOPs，
JVP不能当作一次普通映射定价；这些记录尚不能把总减速因果分解到各个组件。

\begin{table}[htbp]\centering\small
\begin{tabular}{lrrrr}\toprule
目标 & warmed速度比 & 接受率 & 映射/转移 & 确认前缀/轮\\\midrule
@ROWS@
\bottomrule\end{tabular}
\caption{CUDA Picard、512步的四个说明性配置；每格4份独立数组的中位数。
接受率包含丢弃段，分母包括拒绝自环。完整八目标记录另存，未据此筛除任何配置。
该表跨目标的几何和求值成本也不同，不能解释为接受率对速度的单独因果效应。}
\end{table}

A1全拒绝时每轮确认整个窗口；G2的执行加速也伴随很低的接受率。
因此执行收益仍须与合理调参后的函数误差共同考察。
CUDA首次执行的标量等待/采样时间比例，quasi-DEER组中位数范围为@QWAIT@，
Picard为@PWAIT@；等待含未完成设备工作且没有覆盖全部控制活动，不是独立的主机开销估计。
本伴随分析没有混加首次审计与warmed重放，也不将两次技术重放算作独立统计重复。
有限窗口/链数干预、探针扰动核验和共同推断任务的补充实验仍待新协议实施。
"""
    fmt_range = lambda x: f"{x[0]:.3f}--{x[1]:.3f}"
    replacements = {
        "BULK": f'{result["rhat"]["bulk"]:.10f}', "RANKS": str(result["changed_rank_count"]),
        "LOWER": f'{result["rhat"]["folded_lower"]:.10f}',
        "ROUNDED": f'{result["rhat"]["folded_correct_midpoint"]:.10f}',
        "QMAP": fmt_range(q["maps_per_transition"]), "QJVP": fmt_range(q["jvps_per_transition"]),
        "PMAP": fmt_range(p["maps_per_transition"]), "PREFIX": fmt_range(p["mean_confirmed_prefix"]),
        "QWAIT": fmt_range([100*v for v in q["first_scalar_wait_fraction"]]) + r"\%",
        "PWAIT": fmt_range([100*v for v in p["first_scalar_wait_fraction"]]) + r"\%",
        "ROWS": "\n".join(rows),
    }
    for key, value in replacements.items():
        tex = tex.replace("@" + key + "@", value)
    header = "".join(f"% Input SHA256 {hashlib.sha256((root/p).read_bytes()).hexdigest()} {p}\n" for p in paths)
    return header + tex


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.root / "manuscript/software/completion-companion.generated.tex"
    output.write_text(render(args.root), encoding="utf-8")
    print(output)
