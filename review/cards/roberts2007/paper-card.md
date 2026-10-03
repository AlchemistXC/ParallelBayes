# Coupling and ergodicity of adaptive Markov chain Monte Carlo algorithms｜论文精读卡

> Source coverage: Full paper
> Extraction confidence: Mixed
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Paper-only
> Card completeness: Complete relative to supplied source

全文§1–10、全部定理与反例已读；没有图表或独立附录。阅读不等同于所有中间证明细节的形式化认证。

## 01 基本信息

[Paper] **Coupling and ergodicity of adaptive Markov chain Monte Carlo algorithms**。作者：Roberts, Gareth O.; Rosenthal, Jeffrey S.。发表：Journal of Applied Probability，2007。标识：10.1239/jap/1183667414。

正式出版PDF18页，印刷458–475；2007卷年，网站后来的上线日期不改变引用年份。[Paper: PDF p. 1, title block]

阅读日期：2026-10-03。来源：[本地 PDF](../../../references/background/roberts2007.pdf)；[题录/发表页](https://doi.org/10.1239/jap/1183667414)。类型：methods；关键词：自适应MCMC；渐消自适应；containment；耦合；弱大数律。本综述位置：共享调参及持续自适应的正确性条件。。

## 02 一句话概括

[Paper] 用耦合给出自适应MCMC收敛的充分条件，并以反例区分固定核不变性、渐消自适应、分布收敛和大数律。[Paper: PDF p. 6, Theorem 1] [Paper: PDF p. 10, Theorem 2]

## 03 研究问题

[Paper] 每个Pγ都以π为不变分布，依据链历史改变γ后是否仍收敛至π？[Paper: PDF p. 2, §2]

## 04 研究背景与发展路径

[Paper] 作者沿经验协方差调参与随机逼近发展说明动机，提出较直观的耦合条件。该历史定位依据作者引述，未全面外部验证。[Paper: PDF p. 1, Introduction]

## 05 论文指出的核心痛点

[Paper] 自然的接受后放大、拒绝后缩小策略可能强烈偏离π；原例的极限TV差可任意接近1。[Paper: PDF p. 5, Example 2]

## 06 核心思想

[Paper] 在较晚时间的一小段内冻结调参核，通过渐消条件让自适应路径与冻结路径高概率一致，再让冻结路径耦合至π。[Paper: PDF p. 6, Theorem 1 proof]

## 07 方法总览

[Paper] 输入共同不变目标的核族、随机调参序列Γn；检验Dn=supx‖PΓ(n+1)(x,·)−PΓn(x,·)‖→0（依概率），加同时一致遍历或沿实际过程的混合时间概率有界，得到Xn的TV收敛。[Paper: PDF p. 6, Theorem 1] [Paper: PDF p. 10, Theorem 2]

## 08 核心模块拆解

| 模块 | 功能/必要区分 | 来源 |
|---|---|---|
| 渐消自适应 | 控制短段中核的变化；不要求Γn收敛 | [Paper: PDF p. 6, §5] |
| Mε概率有界 | 避免进入越来越慢的核/状态组合；常称containment | [Paper: PDF p. 10, Theorem 2] |
| 共同drift/minorisation | 一组可验证的更强充分条件 | [Paper: PDF p. 11, Theorem 3] |
| 有限调参 | a.s.有限时刻后冻结且各固定核遍历则渐近有效 | [Paper: PDF p. 4, Proposition 2] |

## 09 关键公式与符号

[Paper] Mε(x,γ)=inf{n≥1:‖Pγ^n(x,·)−π‖≤ε}。Theorem2要求对每ε，该量在(Xn,Γn)上概率有界；它不是“自适应步幅变小”的同义词。Theorem5在Theorem1更强条件下仅给有界g的弱大数律。[Paper: PDF p. 10, definition and Theorem 2] [Paper: PDF p. 14, Theorem 5]

## 10 实验设计与证据链

| 证据 | 结论 | 边界/来源 |
|---|---|---|
| Example1四状态 | 固定核均遍历，确定交替仍可困在子集 | [Paper: PDF p. 4, Example 1] |
| Example2接受率自适应 | 可任意偏离目标 | [Paper: PDF p. 5, Example 2] |
| Stairway to Heaven | 两个有效核依赖历史切换可暂留失败/逃逸 | [Paper: PDF p. 13, Example 3] |
| Example4稀疏长适应段 | Theorem1条件不保证强大数律 | [Paper: PDF p. 16, Example 4] |

[Analysis] 本文主证据是定理与构造反例，讨论中的“promising”模拟没有提供可用作量化比较的基准表。

### 图表、公式及附录证据目录


无图、无表、无独立附录。全文18页，印刷页=PDF页+457。

| 对象 | 位置及用途 |
|---|---|
| Equation 1 | p2，依历史选择核的条件分布 |
| Equation 2, Equation 3 | p6，适应事件与冻结核耦合 |
| Equation 4 | p8，密度核的TV及连续性 |
| Equation 5, Equation 6, Equation 7 | p15，分块平均、初末段控制、WLLN |
| Proposition 1–2 | p3–4，独立/有限调参的不同结论 |
| Theorem 1–2 | p6–10，同时一致遍历/概率有界混合时间与渐消 |
| Theorem 3–4 | p11–12，共同几何/多项式drift充分条件 |
| Theorem 5 | p14–16，有界函数WLLN |
| Examples 1–4 | p4、5、13–14、16，不可约性、偏差、逃逸、SLLN失败 |
| Open Problems 1–2 | p13，原文尚未解决的弱drift及复返条件 |

主张—证据：固定核正确不充分→Examples1–3；两条件充分→Theorems1–2；边际收敛不能替代强大数律→Example4。


## 11 结论的正确解释

[Analysis] 足够条件不应写成所有自适应算法的必要条件；渐消自适应单独不够，边际分布收敛也不自动得到强大数律、CLT或有限时刻准确性。

## 12 作者明确承认的局限

[Paper] §7–8给两个开放问题，分别涉及较弱drift和无穷次返回好的混合状态；作者未在本文解决。§9明确给强大数律反例。[Paper: PDF p. 13, Open Problems 1–2] [Paper: PDF p. 16, Example 4]

## 13 批判性分析

[Analysis] 将该理论用于现代共享调参时，需把整个多链系统和调参变量定义清楚，不能只验证某一条链固定参数下的核。§10的外部链调参想法也不能直接为双向共享统计或任意相依链背书。[Paper: PDF p. 17, Discussion]

## 14 学到的知识

### Agent-derived knowledge candidates

[Analysis] 有限warmup后冻结与无限持续调参分开论证；收敛、WLLN、SLLN及CLT分开记录；渐消条件在核TV层面。

## 15 与既有知识的联系

[Analysis] MEADS、LAPS和嵌套Rhat涉及跨链信息，应分别核查各自理论条件。本篇为边界提醒，不替代它们专门的正确性论证。

## 16 研究创意

不适用。本文开放问题仅作为2007原文所述问题，不在未检索后续解答时声称仍未解决。

