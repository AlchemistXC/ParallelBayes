# Parallel Markov chain Monte Carlo Simulation by Pre-Fetching｜论文精读卡

> Source coverage: Full paper
> Extraction confidence: Mixed
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Paper-only
> Card completeness: Complete relative to supplied source

全文§1–6及附录A–B已读，全部4图与2算法已核查；未获得正式排版全文作逐字版本比较，未运行旧硬件实验。

## 01 基本信息

[Paper] **Parallel Markov chain Monte Carlo Simulation by Pre-Fetching**。作者：Brockwell, A. E.。发表：Journal of Computational and Graphical Statistics，2006。标识：10.1198/106186006X100579。

本地是CMU作者技术报告，扉页2005-03-15，18页；正式引用为JCGS 2006,15(1):246–261，二者不冒充相同分页版本。[Paper: PDF p. 1, title block]

阅读日期：2026-10-03。来源：[本地 PDF](../../../references/background/brockwell2006.pdf)；[题录/发表页](https://doi.org/10.1198/106186006X100579)。类型：methods；关键词：预取；MH决策树；单链并行；通信；负载不均。本综述位置：链内时间并行的早期原始来源。。

## 02 一句话概括

[Paper] 预先并行计算MH未来接受/拒绝树的候选密度，再沿实际决策路径取值，在昂贵似然主导时用指数硬件宽度换取单链串行深度减少。[Paper: PDF p. 8, Figure 1] [Paper: PDF p. 10, Algorithm 3.2]

## 03 研究问题

[Paper] 当多链均需昂贵burn-in且模型不易条件分块时，怎样加快一条有效MH链的产生？[Paper: PDF p. 3, Introduction]

## 04 研究背景与发展路径

[Paper] 对比多独立链、再生段、条件独立分块和直接并行似然；这些路线的适用条件不同。发展叙述仅据本文历史位置。[Paper: PDF p. 5, §3]

## 05 论文指出的核心痛点

[Paper] 串行依赖、通信粒度及处理时间方差限制加速；随意并行更新依赖变量会改变不变分布。[Paper: PDF p. 4, §2] [Paper: PDF p. 15, Appendix A]

## 06 核心思想

[Paper] 所有未来二叉分支的提议可提前生成，密度并行求值后再按标准MH决定实际路径。多做的计算被丢弃，保留下来的链仍执行原接受规则。[Paper: PDF p. 10, Algorithm 3.2]

## 07 方法总览

[Paper] 输入起点、提议机制、树深h和P=2^h处理器；生成所有候选→并行评估密度→串行判定h步→输出该段。要求提议、控制及通信相对密度计算可忽略，才能达到文中理想速度。[Paper: PDF p. 9, §3.3] [Paper: PDF p. 10, Algorithm 3.2]

## 08 核心模块拆解

| 模块 | 作用 | 限制 | 来源 |
|---|---|---|---|
| 全树预取 | 覆盖真实未来路径 | 大量无用候选 | [Paper: PDF p. 8, Figure 1] |
| 实际MH判定 | 保留原目标与路径法则 | 不能用预测代替最终判定 | [Paper: PDF p. 10, Algorithm 3.2] |
| 条件独立分块 | 并行不同变量块 | 需Property3.1，不是任意Jacobi Gibbs | [Paper: PDF p. 6, Property 3.1] |
| 等待所有处理器 | 实现简单 | 最慢响应决定完成时间 | [Paper: PDF p. 13, §4] |

## 09 关键公式与符号

[Paper] h步需2^h处理器，因此理想加速log2P，不是线性P。附录A对相关二维正态给同时旧值条件更新：若初始协方差非对角为ρ，更新后变为ρ³，目标不变性失败。[Paper: PDF p. 10, §3.3] [Paper: PDF p. 15, Appendix A]

## 10 实验设计与证据链

[Paper] 一项模拟ARFIMA(1,d,0)，长度1000，参数φ=.5,d=.3,σ²=1；三个参数随机游走更新。32台双CPU 1.6GHz Athlon、1Gb网络，似然约8ms，链长10000，每处理器配置3次运行。Figure3显示4处理器接近理想，8及以上偏离，归因于响应方差。[Paper: PDF p. 11, §4] [Paper: PDF p. 12, Figure 2 and setup] [Paper: PDF p. 13, Figure 3]

### 图表、公式及附录证据目录


18页CMU技术报告（2005-03-15），不是2006正式分页PDF。

| 对象 | 位置及用途 |
|---|---|
| Figure 1 | p8，未来两步MH二叉树与重复状态 |
| Figure 2 | p12，长度1000的ARFIMA模拟数据 |
| Figure 3 | p13，3次重复的迭代/秒及理想曲线 |
| Figure 4 | p16，顺序与同时条件更新的依赖图 |
| Equation 1, Equation 2 | p2，目标期望及MC平均 |
| Equation 3 | p9，接受/拒绝分支状态 |
| Equation 4 | p11，ARFIMA数据生成 |
| Equation 5, Equation 6 | p16，状态空间分块因子化 |
| Algorithm 3.1 | p7，合法条件独立块更新 |
| Algorithm 3.2 | p10，预取流程及理想log2P收益 |
| Appendix A | p14–15，ρ变ρ³的不变性反例 |
| Appendix B | p15–17，一种状态空间合法分块 |

无编号表。主张—证据：保留MH路径由Algorithm3.2；真实加速受开销限制由Figure3；盲目块并行不合法由AppendixA。


## 11 结论的正确解释

[Analysis] 证据支持预取可加速特定昂贵单链；没有改善每步混合的主张，也没有现代GPU的一般速度保证。log2P是所给全树方案及成本假设下的结果，不是所有预取方法的普遍上界。

## 12 作者明确承认的局限

[Paper] 作者明确指出浪费计算及对处理时间方差敏感；讨论异步取消和不平衡预测树可能超过该全树的log2P收益。[Paper: PDF p. 13, Discussion] [Paper: PDF p. 14, Discussion]

## 13 批判性分析

[Analysis] 该2005报告算法框中的α写成密度比，未显式写min(1,·)，而正文称标准MH规则；复现应保留合法截断，不能机械照抄概率大于1的表达。未核对正式版是否修订。[Paper: PDF p. 10, Algorithm 3.2]

[Analysis] speedup测量是迭代/秒；由于原核保留可在相同随机化约定下解释为执行加速，但仍需包含通信及未用分支成本。

## 14 学到的知识

### Agent-derived knowledge candidates

[Analysis] 多链并行摊薄估计方差，预取减少单条路径墙钟等待，两者目标不同；合法分块必须有条件独立等结构性理由。

## 15 与既有知识的联系

[Analysis] Angelino2014的预测预取可放在此全树路线后；现代并行轨迹求解需要另说明是否保留相同核、相同噪声路径或仅近似目标。

## 16 研究创意

不适用。不把作者已讨论的预测不平衡树与取消机制当作新的研究创意。

