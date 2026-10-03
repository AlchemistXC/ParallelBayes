# The No-U-Turn Sampler: Adaptively Setting Path Lengths in Hamiltonian Monte Carlo｜论文精读卡

> Source coverage: Full paper
> Extraction confidence: Mixed
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Paper-only
> Card completeness: Complete relative to supplied source

已读全部正文、算法1–6、7幅图和附录A。该文是2014的slice NUTS构造；不把它等同于所有后续软件实现。

## 01 基本信息

[Paper] **The No-U-Turn Sampler: Adaptively Setting Path Lengths in Hamiltonian Monte Carlo**。作者：Hoffman, Matthew D.; Gelman, Andrew。发表：Journal of Machine Learning Research，2014。标识：https://jmlr.org/papers/v15/hoffman14a.html。

JMLR正式PDF31页，印刷1593–1623；正文p1–28、附录A p29、参考文献p30–31。作者原文列Matlab及Stan示例的个人主页链接，代码未运行。[Paper: PDF p. 2, Introduction]

阅读日期：2026-10-03。来源：[本地 PDF](../../../references/background/hoffman2014.pdf)；[题录/发表页](https://jmlr.org/papers/v15/hoffman14a.html)。类型：methods；关键词：NUTS；动态轨迹；详细平衡；双重平均；ESS/梯度。本综述位置：动态轨迹停止规则及现代批处理方法的原始基准。。

## 02 一句话概括

[Paper] 通过保持可逆性的随机双向倍增树和候选选择自动决定HMC轨迹长度，另用dual averaging在warmup调步长。[Paper: PDF p. 7, §3.1] [Paper: PDF p. 15, §3.2]

## 03 研究问题

[Paper] 怎样移除难以手工选择的跃蛙步数L，同时保留HMC探索效率与正确目标？[Paper: PDF p. 4, §3]

## 04 研究背景与发展路径

[Paper] 作者将HMC、slice sampling、倍增构造与随机优化结合；该历史关系据本文，不把其2014软件状态当作当前信息。[Paper: PDF p. 7, §3.1.1]

## 05 论文指出的核心痛点

[Paper] L过短导致近似随机游走，过长则绕回；直接在回头时停止一般破坏可逆性。[Paper: PDF p. 4, §2] [Paper: PDF p. 5, Equation 1 discussion]

## 06 核心思想

[Paper] 随机向前/后倍增构建B，并选取可从任一候选重建同一树的C；在C上使用保持均匀分布的核，避免停止规则偏向某个起点。[Paper: PDF p. 7, Conditions C.1–C.4] [Paper: PDF p. 8, Equation 2]

## 07 方法总览

[Paper] 输入初值、log目标及梯度、步长、迭代数；每轮抽动量和slice变量，扩树，检查能量与所有相关平衡子树的U-turn条件，更新候选。warmup结束冻结平均步长。[Paper: PDF p. 14, Algorithm 3] [Paper: PDF p. 19, Algorithm 6]

## 08 核心模块拆解

| 模块 | 功能 | 删除/替换风险 | 来源 |
|---|---|---|---|
| 随机双向倍增 | 候选树重建对称 | 单向停止无一般可逆保证 | [Paper: PDF p. 5, Figure 1] |
| 候选排除 | 保证C.4 | 不能保留所有最后半树节点 | [Paper: PDF p. 10, stopping cases] |
| 递归加权选点 | O(j)状态内存代替O(2^j) | 不能任意均匀化不同大小子树 | [Paper: PDF p. 13, §3.1.2] |
| dual averaging | 由接受统计更新logε | 需适应阶段与冻结规则 | [Paper: PDF p. 15, Equation 6] |

## 09 关键公式与符号

[Paper] U-turn条件：(θ+−θ−)·r−<0或(θ+−θ−)·r+<0。它是本文欧氏动能下的规则；质量矩阵改变时需相应坐标解释。dual averaging以累计δ−接受统计调logε，δ仍由使用者选择。[Paper: PDF p. 9, Equation 4] [Paper: PDF p. 17, §3.2.4] [Paper: PDF p. 27, Discussion]

## 10 实验设计与证据链

[Paper] 4个目标（250维Gaussian、25维logistic、302维层级logistic、3001维随机波动），各2000迭代、前1000warmup；HMC扫描10条轨迹长度和8个δ，NUTS扫描15个δ，各10随机种子，共3200/600次。指标是最差坐标均值及二阶中心矩ESS/梯度调用，参照矩来自独立5万步NUTS。[Paper: PDF p. 18, §4] [Paper: PDF p. 20, §4.1] [Paper: PDF p. 29, Appendix A]

[Paper] 两个logistic与最佳HMC相近；Gaussian约2倍、SV约1.5倍。没有统一CPU/GPU墙钟基准。[Paper: PDF p. 24, §4.4] [Paper: PDF p. 25, Figure 6]

### 图表、公式及附录证据目录


无编号表；印刷页=PDF页+1592；附录A在p29。

| 对象 | 位置及用途 |
|---|---|
| Figure 1 | p5，双向倍增树 |
| Figure 2 | p6，候选排除与停止例 |
| Figure 3 | p22，目标/实际接受统计 |
| Figure 4 | p23，步长适应 |
| Figure 5 | p24，轨迹长度分布 |
| Figure 6 | p25，ESS/梯度比较 |
| Figure 7 | p26，Gaussian二维投影定性比较 |
| Equation 1 | p5，距离导数动机 |
| Equation 2 | p8，候选条件分布均匀 |
| Equation 3, Equation 4 | p9，能量及U-turn停止 |
| Equation 5, Equation 6 | p15，随机逼近步长与dual averaging |
| Algorithms 1–3 | p3、11、14，HMC、naive及高效NUTS |
| Algorithms 4–6 | p18–19，初始步长与warmup适应 |
| Appendix A | p29，ESS定义、长链参照、.05截断 |

核心证据矩阵：不变性→C.1–C.4及Equation2；减少内存→§3.1.2；效率→Figure6四目标，不能扩大成普遍优势。


## 11 结论的正确解释

[Analysis] “无需手工调L”不等于完全无调参或保证所有后验混合。轨迹长度随机、分支多，是后续GPU控制流问题的来源；正确性不仅依赖跃蛙积分，还依赖完整选点及停止逻辑。

## 12 作者明确承认的局限

[Paper] 仅比较基本HMC；单位质量矩阵、几何和参数尺度仍可改进。只适于连续可微变量，离散变量须边缘化或交给别的核。SV需要更长warmup。[Paper: PDF p. 23, §4.2] [Paper: PDF p. 27, Discussion] [Paper: PDF p. 28, Discussion]

## 13 批判性分析

[Analysis] 本文ESS用独立长链估计矩，并在自相关首次低于.05时截断；与现代诊断口径不可直接互换。四目标实证不足以证明默认δ=.6普遍最佳。其图7的Gibbs计算预算更大，且只是投影可视化。[Paper: PDF p. 29, Appendix A] [Paper: PDF p. 26, Figure 7]

## 14 学到的知识

### Agent-derived knowledge candidates

[Analysis] 动态停止规则应与候选选择共同验证；加速NUTS时保留每条链树状态与随机性，而非只移植停止内积公式。

## 15 与既有知识的联系

[Analysis] Dance2025用FSM改善不同链树深不一致的执行；这与对一条HMC时间路径的Picard/Newton求解属于不同并行层次。

## 16 研究创意

不适用。本轮核查原算法及比较口径，不提出新的NUTS构造。

