"""Write only completed formal evidence into the Chinese manuscript."""
import json
from pathlib import Path
import numpy as np
def number(value):
 formatted=f'{value:.3g}'
 if 'e' in formatted:
  mantissa,exponent=formatted.split('e')
  return mantissa+r'\times10^{'+str(int(exponent))+'}'
 return formatted

root=Path('benchmark/analysis/outputs/cpu-formal')
s=json.loads((root/'formal-summary.json').read_text());pairs=json.loads((root/'paired-speedups.json').read_text())
if s['pending'] or s['observed']!=s['planned']:raise SystemExit('Formal results incomplete; no final manuscript claims generated')
groups=s['groups'];methods=['mala/sequential','mala/quasi_deer','rwm/sequential','rwm/online_picard','nuts/sequential']
models=['G1','G2','L1','L2','H1','H2','A1','M1']
records=json.loads((root/'run-metrics.json').read_text());ok=[r for r in records if r['status']=='completed']
max_error=max([r.get('max_path_error',0) for r in ok],default=0)
branch=sum(r.get('acceptance_mismatches',0) for r in ok)
text=[f'本机按冻结协议登记了 {s["planned"]} 项正式任务，全部结束，其中 {s["failed"]} 项未返回满足输出标准的正常样本。失败计数与原始输出均保留；该总任务数包含配对执行，并非 {s["planned"]} 个独立模型。每个模型、预算及工作流的独立重复数为 24。',
 f'正常输出中，独立核验记录的最大数值路径差为 ${number(max_error)}$，接受事件失配总数为 {branch}。这一陈述以数值核验及当前目标库为边界，不构成一般轨迹或平稳分布证明。']
if pairs:
 for method,label in [('mala/quasi_deer','quasi-DEER MALA'),('rwm/online_picard','Online Picard RWM')]:
  selected=[p for p in pairs if p['method']==method]
  group_medians=[];full=[]
  for model in models:
   for n in [256,2048]:
    a=[p for p in selected if p['model']==model and p['retained_draws']==n]
    if a:group_medians.append(np.median([x['cached_speedup'] for x in a]));full.append(np.median([x['complete_speedup'] for x in a]))
  if group_medians:
   text.append(f'{label} 的模型—预算组中位缓存执行速度比范围为 {min(group_medians):.3g} 至 {max(group_medians):.3g}，研究审计工作流速度比范围为 {min(full):.3g} 至 {max(full):.3g}。速度比定义为同核顺序时间除以并行时间，小于 1 表示并行执行更慢；这里只统计成对有效输出，失败另行报告。')
 text.append(r'''\begin{figure}[htbp]\centering
\includegraphics[width=\linewidth]{../../figures/software/paired-costs.pdf}
\caption{同核成对成本。上、下行分别为每链保留256和2048步；左列为两次缓存重放时间的中位数之比，右列为含编译、预热/丢弃段和独立核验的工作流时间比。每个点为一个独立重复中的配对比，短线为组中位数；同一轨迹的计时重放不当作统计重复。虚线表示速度比1。任何缺失配对均在原始任务及失败表中保留。}
\end{figure}''')
text.append('表中列出较大预算下的函数最大平方误差。L1/L2 采用有限参考，因此相应数值是参考平方差。完整逐函数误差、逐点区间、参考敏感性区间、失败比例区间及两预算结果随机器可读材料交付。不能把表中的最小数值自动解释为确定排名。')
text.append(r'\begin{table}[htbp]\centering\small\setlength{\tabcolsep}{3pt}\begin{tabular}{lrrrrr}\toprule')
text.append(r'目标 & 顺序MALA & quasi-DEER & 顺序RWM & Picard & NUTS\\\midrule')
for model in models:
 cells=[]
 for method in methods:
  group=next(g for g in groups if g['model']==model and g['method']==method and g['retained_draws']==2048)
  value=group.get('max_mean_squared_error')
  cells.append(('$'+number(value)+'$' if value is not None else '--')+(' $\\dagger$' if not group['reference_usable'] else '')+f' ({group["failed"]})')
 text.append(model+' & '+' & '.join(cells)+r'\\')
text.append(r'\bottomrule\end{tabular}\caption{每链保留2048步时的最大函数平方误差/参考平方差。括号内为该组24次重复中的输出失败数；有失败时，误差仅描述成功输出。误差不包含失败的假定损失，不代表无条件达标。$\dagger$表示参考精度未确定，该行仅展示参考平方差，不能判断全函数精度达标。}\end{table}')
divergences=sum(r.get('divergences',0) for r in ok if r['method']=='nuts/sequential')
divergent_runs=sum(r.get('divergences',0)>0 for r in ok if r['method']=='nuts/sequential')
text.append(f'按前述工作流口径汇总，正式尝试合计耗时 {sum(r["t_total"] for r in records):.1f} 秒，其中失败任务耗时 {sum(r["t_total"] for r in records if r["status"]!="completed"):.1f} 秒。另有缓存计时重放开销{sum(r["replay_overhead"] for r in records):.1f}秒，完整保留但不重复计入单次工作流成本。逐组成本及全部失败分母另存分析结果。')
text.append(f'NUTS 在 {divergent_runs} 个已返回有限样本的任务中记录到发散，总计 {divergences} 个保留转移的发散事件。发散与数值输出失败分别呈现，不能因为数组有限而删除这一诊断。多峰和漏斗目标上的误差须结合模式占比及尺度函数理解。')
text.append(f'NUTS另有{sum(r.get("retained_transitions_at_step_cap",0) for r in ok)}个保留转移达到255个积分步的设定上限；积分步数及逐次适配参数随原始记录保存。')
rss=[r['host_peak_rss']/2**20 for r in records if r.get('host_peak_rss')]
text.append(f'采样接口期间记录的逐任务进程RSS峰值范围为{min(rss):.1f}至{max(rss):.1f} MiB；它包含进程已驻留内存，只覆盖接口调用阶段，不能解释为每种算法的独占增量内存或整项任务的严格峰值。')
for method,label in [('mala/quasi_deer','quasi-DEER'),('rwm/online_picard','Online Picard')]:
 values=[]
 for model in models:
  for n in [256,2048]:
   subset=[r['kernel_forward_evals_per_transition'] for r in ok if r['method']==method and r['model']==model and r['retained_draws']==n]
   if subset:values.append(float(np.median(subset)))
 if values:
  text.append(f'{label}的模型—预算组中，单个输出转移对应的前向转移映射求值次数中位数范围为{min(values):.2f}至{max(values):.2f}，顺序MH为1。')
text.append('这些程序层面的映射调用计数包含丢弃段和拒绝自环，尚不包含独立审计；它们不是浮点运算量或密度/梯度调用次数。quasi-DEER的JVP另存，因此不能仅据调用数精确分解运行瓶颈。')
text.append(r'''\begin{figure}[htbp]\centering
\includegraphics[width=\linewidth]{../../figures/software/error-cost.pdf}
\caption{固定采样计划的误差—成本关系。横轴为成功输出条件下的工作流时间中位数，全部尝试和失败成本另表保存。每条线连接同一指定工作流的两个预算点，不表示中间预算已被测量。蓝色为MALA、橙色为RWM、灰色为NUTS；实线/圆或方形为顺序MH，虚线/叉号为相应时间执行器，三角形为NUTS。误差取预声明函数中最大的重复平均平方误差；L1/L2为有限参考平方差。线段区间为逐点95\%重复重采样区间，有限参考的共同误差敏感性另行传播；传播采用正态对角协方差工作假设，非同时保证。星号表示参考精度未确定，该面板仅供探索性平方差比较。面板标题列出该模型全部正式任务中的输出失败数，失败组的误差为条件结果。点虚线标出0.01作为预声明误差阈值。}
\end{figure}''')
for method in methods:
 counts={key:0 for key in ['below_threshold_pointwise','above_threshold_pointwise','undetermined','not_assessable']}
 for group in groups:
  if group['method']==method and group['retained_draws']==2048:
   counts[group['precision_assessment'][0]['status']]+=1
 text.append(r'\noindent '+method.replace('_',r'\_')+f'在较长预算、$\\epsilon=0.1$下的逐点判断为：区间低于阈值{counts["below_threshold_pointwise"]}个目标，区间高于阈值{counts["above_threshold_pointwise"]}个，跨阈值{counts["undetermined"]}个，参考或输出条件不足{counts["not_assessable"]}个。\\par')
text.append('这些判断仅对应两个已测量预算中的较长预算，不构成同时置信结论，也不提供单次运行可观测的停止规则或精确的达标时间。')
stats_path=Path('execution/statistical-v4/summary.json')
if stats_path.exists():
 stats=json.loads(stats_path.read_text());fit_failures=sum(x['failed'] for x in stats['methods'])
 text.append(f'正式生成式检查完成64个新数据集、五种工作流，共320次拟合，其中{fit_failures}次输出失败。90\\%后验区间的覆盖估计及其二项区间按数据集作为独立单位报告；保留所有秩与原始样本。抽稀秩仍可能相关，这一检查不提供一般SBC一致性证明。')
 for r in stats['methods']:
  if r['coverage'] is not None:
   lo,hi=r['coverage_95_binomial_interval']
   text.append(r'\noindent '+r['method'].replace('_',r'\_')+f'：覆盖率 {r["coverage"]:.3f}，95\\%二项区间 [{lo:.3f}, {hi:.3f}]。\\par')
 text.append(f'正式生成式检查另记录到{sum(r.get("divergences",0) for r in stats["methods"])}个保留转移的发散事件，涉及{sum(r.get("divergent_fits",0) for r in stats["methods"])}次拟合；该诊断与输出失败分开保存。')
 text.append('本次覆盖率点估计均低于名义90\\%，而相应二项区间均包含90\\%。这一有限重复结果既不能证明完全校准，也不应被改写为已确证系统性覆盖不足。')
 companion=json.loads(Path('execution/statistical-v4/likelihood-ranks.json').read_text())
 text.append(f'对数似然测试量也完成{len(companion["rows"])}次拟合的伴随分析，共记录{sum(r.get("ties",0) for r in companion["rows"])}个秩并列。逐方法秩直方图、抽稀后相关性及解析期望误差随原始数据交付；这些描述性诊断不构成统一性检验或正确性证书。')
else:text.append('正式64组SBC尚在运行；不得以已完成的小型SBC替代。')
text.append('L2 的参考符号事件在262144个相关样本中均为零，Rhat 对该函数不可判定，不能把零经验方差当作事件概率已被精确确定。因此保留原函数集合，并将L2全函数精度判定标记为未确定。没有通过删除该函数得到达标结论。')
text.append('上述结果仅为Mac CPU实测；原生Windows GPU后端未实现，处于本轮研究范围之外。')
Path('manuscript/software/results.generated.tex').write_text('\n\n'.join(text)+'\n')
