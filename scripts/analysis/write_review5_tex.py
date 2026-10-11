#!/usr/bin/env python3
# v5 projection of saved records only. No sampling or replacement of frozen statistics.
from pathlib import Path
import json,re,csv
root=Path(__file__).resolve().parents[2];p=root/'manuscript/software-v5';e=root/'benchmark/analysis/outputs/manuscript-review-v5'
x=json.loads((e/'SUMMARY.json').read_text());d=json.loads((e/'diagnostic-replay.json').read_text())
rows=[]
for r in x['w1_cost_boundaries_same_four_inputs']:
 rows.append(('CPU' if r['device']=='cpu' else 'CUDA')+' '+('Picard' if r['kernel']=='rwm' else 'quasi-DEER')+' & '+' & '.join(f"{r[k]:.3f}" for k in ['prepared','ordinary_workflow','research_execution'])+r'\\')
cost=r'''\begin{table}[htbp]\centering\small
\begin{tabular}{lrrr}\toprule
同核配对 & 准备后内核 & 普通批量推断 & 含核验研究运行\\\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule\end{tabular}
\caption{W1每链4096步的三种速度比（顺序/时间执行）。各列均使用原重复0、8、16、23，配对几何平均；缓存每输入四次调用先取其均值。本表不计算四重复区间。}\label{tab:three-costs}
\end{table}
'''
(p/'review5-cost-boundaries.generated.tex').write_text(cost)
wells=r'''\begin{table}[htbp]\centering\small
\begin{tabular}{lrrrr}\toprule
核 & CPU顺序 & CPU时间执行 & CUDA顺序 & CUDA时间执行\\\midrule
RWM & 4.94 & 11.59 & 5.73 & 6.01\\
MALA & 10.58 & 68.85 & 13.99 & 45.51\\
NUTS & 11.62 & --- & --- & ---\\\bottomrule
\end{tabular}
\par\medskip
\begin{tabular}{lrr}\toprule
核 & $\alpha$参考平方误差（$10^{-6}$） & $\beta$参考平方误差（$10^{-6}$）\\\midrule
RWM & 2.06 [1.16, 3.40] & 4.91 [2.72, 7.94]\\
MALA & 0.58 [0.39, 0.89] & 1.11 [0.68, 2.00]\\
NUTS & 0.28 [0.14, 0.51] & 0.52 [0.32, 0.84]\\\bottomrule
\end{tabular}
\caption{W1每链4096步的普通批量推断时间均值（秒，上表）和参考平方误差（下表）。每工作流24次四链重复；同核误差在显示精度下相同，合并列示。方括号为条件95\% BCa区间，参考区间的影响另见补充材料A。}\label{tab:wells-v5}
\end{table}
'''
(p/'review5-wells.generated.tex').write_text(wells)
phase=[]
for r in x['w1_phase_means']:
 name=r['workflow'].replace('cpu-','CPU ').replace('cuda-','CUDA ').replace('-sequential',' seq').replace('-online_picard',' Picard').replace('-quasi_deer',' quasi-DEER').replace('-spawn_chains','')
 phase.append(name+' & '+' & '.join(f"{r[k]:.2f}" for k in ['startup_gaps_exit','target','sampling_transfer_transform','output','functions_R_diagnostics','ordinary','additional_audit'])+r'\\')
si=r'''\section{v5既有记录再分析与公开接口示例}
\subsection{完整运行的分段费用}
本分析只读取既有W1长预算的216项原始计时与两个L1固定输入，新增正式采样为零。每个原成员先按接收索引的字节数与SHA256核对。四个不重叠worker阶段分别为目标/输入准备、含转换的采样、数组输出、函数与R诊断。用外层普通进程墙钟减去四阶段之和得到启动、导入、记录间隙及退出余量；该余量不是单独测出的纯启动时间。
\begin{table}[htbp]\centering\footnotesize\setlength{\tabcolsep}{3pt}
\begin{tabular}{lrrrrrrr}\toprule
工作流 & 余量 & 准备 & 采样段 & 输出 & R诊断 & 普通总计 & 额外核验\\\midrule
'''+ '\n'.join(phase)+r'''
\bottomrule\end{tabular}
\caption{W1每链4096步的费用分解，秒。每行原24次四链拟合的均值；采样段包含预热/丢弃、传输与转换。额外核验为研究总时间减普通总时间。阶段和不重复加到嵌套总时间上。NUTS采样阶段包含内部旧诊断，R诊断是外部独立后处理。}
\end{table}
普通CPU顺序RWM的采样段占总费用约51\%，其余包括记录在内的工作流费用约49\%。这说明共有费用的稀释效应存在；Picard和quasi-DEER的采样段同时也高于对应顺序费用，二者共同解释本例减速。三边界对照只使用与缓存相同的四个输入，见正文；其他缓存目标的完整记录继续按原协议呈现。

\subsection{L1尾部ESS对重复状态的敏感性}
原重复21、4096预算的CPU MALA顺序与quasi-DEER均满足路径标准，接受数组逐元素相同。第二条链在保留段接受202次，最长连续拒绝段为'''+str(x['l1_tie_case'][0]['longest_rejection_run'][1])+r'''步。顺序路径$q_1$在其经验5\%分位数处有3673个完全相同值；quasi-DEER的微小浮点变化改变并列值分组。整段$q_1$最大配对差为$4.51398918244195\times10^{-11}$，均值相差约$2.1\times10^{-14}$。

直接读入二进制并调用posterior 1.7.0复现两套保存结果：顺序tail ESS为4.80946123897633，quasi-DEER为31.8769113282662。两者上尾指示序列ESS均为4041.53，差异来自5\%下尾；第二条链满足$q_1\leq\widehat q_{0.05}$的计数分别为3677和755。秩正态化/折叠$\hat R$为1.30168486811451和1.30827731478091，均清楚显示探索不足。

仅作数值敏感性检查，将两组数值分别四舍五入到小数点后12位后，下尾ESS均约4.80946。完整路径在这种舍入下仍非逐元素相同，故该检查不用于合并路径、替换诊断或改变标准。原完整附件的两套诊断全部保留。重建入口为\texttt{review5\_evidence.py}与\texttt{review5\_diagnostics.R}；源成员和结果摘要随本版清单提供。

\subsection{R技术示例与迭代保护}
\texttt{paper-api-v5.R}在安装版parallelbayes 0.2.0.9002、R 4.6.0、posterior 1.7.0及Mac torch 2.13.0/CPU上运行两种RWM执行。每链8192步、步长0.8、窗口16、种子2026；实际随机数组指纹相同，最大路径差$1.13659082146\times10^{-14}$，接受事件零失配。两份输出各通过独立NumPy路径检查，主体/尾部ESS及$\hat R$见正文。

初次短示例扩展时未显式提高默认256轮上限，Picard只确认3848步后返回失败；失败记录未作为样本。最终脚本明确设\texttt{max\_iter=8704}，两调用完成。一次依赖库路径缺失的环境启动失败亦记录在技术QA中。这是公开接口的技术使用检查，不进入3888项主实验、缓存速度比或24次独立重复。样本和日志随独立技术材料提供。

\subsection{此前实验和适配实现的身份}
历史Mac主实验为0.1.0、1920项（每格24份四链输入，保留256/2048步）；解析SBC为64个数据集的配对检查。Windows首轮0.2.0.dev1为512项（每格4份四链输入，保留128/512步）；另有独立Windows机制协议192工作流、每模型2份输入和窗口4/16。主实验则为独立compact协议的九目标、九工作流、两预算、24份输入。本节之后或此前历史章节中的数值继续按各自身份解释。

quasi-DEER代理门控差异也具有版本身份。原文伪代码使用$\sigma(\min(0,a)-\log u)$；项目归档上游提交5e5b637与本文采用$\sigma(a-\log u)$。硬接受规则等价，代理导数一般不同。本文使用非重叠窗口、重复起点初猜和硬残差停止，不使用上游NaN归零或状态裁剪；torch对硬前向另作停止梯度包裹以避免软表达式舍入抵消。有限轮因果性质以精确算术为前提，浮点与有限迭代输出由本文独立标准检查。
'''
(p/'review5-si.generated.tex').write_text(si)
