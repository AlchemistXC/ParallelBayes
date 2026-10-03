# Noisy Monte Carlo: convergence of Markov chains with approximate transition kernels｜论文精读卡

> Source coverage: Full paper
> Extraction confidence: Mixed
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Paper-only
> Card completeness: Complete relative to supplied source

已读正文§1–5及附录A、全部8图与2表。附录按主要推导链核对，不宣称逐行证明认证。正式版与该早期预印本尚未逐字比对；原文若干公式/算法疑误不能直接作为实现规范。

## 01 基本信息

[Paper] **Noisy Monte Carlo: convergence of Markov chains with approximate transition kernels**。作者：Alquier, P.; Friel, N.; Everitt, R.; Boland, A.。发表：Statistics and Computing，2016。标识：10.1007/s11222-014-9521-x。

本地是arXiv:1403.5496v3（2014-04-15；扉页4月16日），36页；正式卷年2016，Statistics and Computing26:29–47，DOI10.1007/s11222-014-9521-x。没有将预印本页码当正式页码。

阅读日期：2026-10-03。来源：[本地 PDF](../../../references/background/alquier2016.pdf)；[题录/发表页](https://link.springer.com/article/10.1007/s11222-014-9521-x)。类型：methods；关键词：近似转移核；noisy MH；MCWM；exchange；Langevin偏差。本综述位置：说明近似核误差理论早已存在，以及调用条件。。

## 02 一句话概括

[Paper] 用Markov核稳定性将接受概率或梯度近似误差转化为分布误差，并比较noisy exchange与Langevin等近似方法的偏差和混合收益。[Paper: PDF p. 4, Theorems 2.1–2.2] [Paper: PDF p. 6, Corollary 2.3]

## 03 研究问题

[Paper] 当理想转移无法准确或便宜执行时，什么条件可保证替代核仍足够接近目标？[Paper: PDF p. 3, §2]

## 04 研究背景与发展路径

[Paper] 核心框架调用Mitrophanov的一致遍历扰动界及Ferré等的V几何遍历稳定性结果，具体化于不可计算归一化常数问题。前作与扩展不应混成本文新证明。[Paper: PDF p. 4, Theorems 2.1–2.2]

## 05 论文指出的核心痛点

[Paper] 无偏接受率估计不自动产生精确MH；Langevin还叠加离散误差。理论常要求难验证的一致遍历性质。[Paper: PDF p. 7, Remark 2.3 discussion] [Paper: PDF p. 8, §2.3]

## 06 核心思想

[Paper] 先控制supθ核TV差，再乘由原链混合决定的敏感性常数。共同drift与V几何遍历提供另一渐近途径，不能忽略稳定性要求。[Paper: PDF p. 4, Theorem 2.1] [Paper: PDF p. 5, Theorem 2.2]

## 07 方法总览

[Paper] 理想MH接受比α→随机估计αhat→用min(1,αhat)构成近似核；若E|αhat−α|≤δ(θ,θ′)，对提议积分后得到核差界。Langevin先比较noisy与精确梯度离散链，再单独比较离散目标与连续目标。[Paper: PDF p. 6, Algorithm 2 and Corollary 2.3] [Paper: PDF p. 8, §2.3]

## 08 核心模块拆解

| 模块 | 作用与限制 | 来源 |
|---|---|---|
| 统一核差 | 把逐提议误差整合到分布误差 | [Paper: PDF p. 6, Corollary 2.3] |
| 保留/重抽辅助估计 | GIMH与MCWM精确性不同；不能任意重抽分母 | [Paper: PDF p. 9, §2.4] |
| 多个exchange辅助样本 | N1与N∞为精确端点，中间N一般有偏 | [Paper: PDF p. 12, §3.3] |
| drift稳定性 | noisy Langevin的不变分布存在与逼近 | [Paper: PDF p. 15, Theorem 3.4] |

## 09 关键公式与符号

[Paper] 统一遍历时，任意n的分布差≤[λ+Cρ^λ/(1−ρ)] supθ∫h(θ′|θ)δ(θ,θ′)dθ′。noisy exchange的O(N^−1/2)来自方差控制并加先验/提议有界等强假设；固定N再跑更久不消掉核偏差。[Paper: PDF p. 6, Corollary 2.3] [Paper: PDF p. 13, Theorem 3.2]

[Paper] Theorem3.4仅给一维Gaussian先验、Σ<s²下N→∞趋近πΣ；πΣ与真实π仍有离散偏差。[Paper: PDF p. 15, Theorem 3.4]

## 10 实验设计与证据链

[Paper] Ising为20个16×16格点数据集，各算法30秒，辅助链1000步并追加样本；可用精确归一化常数的数值后验作参照。ERGM为16节点两参数和20节点四参数，各30/100秒，参照为2/4小时BERGM，非解析真值。[Paper: PDF p. 18, §4.1] [Paper: PDF p. 22, §4.2.1] [Paper: PDF p. 25, §4.2.2]

[Paper] 混合改善并不确保不确定性准确：表1多种方法SD低估，noisy Langevin均值也偏；表2的noisy Langevin有些SD高估，不能笼统称全部低估。[Paper: PDF p. 23, Table 1] [Paper: PDF p. 25, Table 2]

### 图表、公式及附录证据目录


36页预印本，正文至p28，附录A p30–36。原脚本打印页识别把坐标轴6000等当页码，本卡只用真实PDF页。

| 对象 | 位置及角色 |
|---|---|
| Figure 1 | p19，20个Ising数据集的均值误差 |
| Figure 2 | p20，一例Ising密度 |
| Figure 3 | p21，Florentine网络 |
| Figure 4 | p23，edge轨迹、密度、ACF |
| Figure 5 | p24，2-star轨迹、密度、ACF |
| Figure 6 | p25，Molecule网络 |
| Figure 7 | p26，Molecule四参数密度 |
| Figure 8 | p27，Molecule ACF |
| Table 1 | p23，Florentine均值与SD；部分不确定性低估 |
| Table 2 | p25，Molecule均值与SD；noisy Langevin并非全低估 |
| Equation 1 | p3，遍历平均 |
| Equation 2 | p6，平均接受比误差假设 |
| Equation 3, Equation 4 | p10–11，Gibbs随机场及不可计算MH比 |
| Equation 5, Equation 6 | p12，归一化常数比估计 |
| Equation 7 | p14，score恒等式 |
| Equation 8 | p18，Ising参照积分 |
| Equation 9 | p22，曲率式疑有Cov符号问题 |
| Equation 10 | p33，minorisation证明 |
| Algorithms 1–10 | p5–17，MH/noisy MH、Langevin、MCWM、exchange和MALA变体 |
| Theorems 2.1–2.2 | p4–5，一致遍历界与V几何遍历稳定性 |
| Corollary 2.3 / Theorem 3.2 | p6、13，接受误差到分布误差及N速率 |
| Theorem 3.4 | p15，一维Gaussian先验的离散Langevin极限 |
| Appendix A | p30–36，核分解、二阶矩与共同drift主要证明链 |


## 11 结论的正确解释

[Analysis] 理论结论是误差随近似质量参数改善，不是任意噪声MCMC随链长自动变精确。无偏似然估计的pseudo-marginal精确性还依赖扩展目标构造及适当非负性，不能等同于无偏接受比。

## 12 作者明确承认的局限

[Paper] 一致遍历性很强、实际常不满足；估计器渐近方差与计算/统计联合效率仍需研究。某些几何遍历扩展只给渐近收敛而无显式速率。[Paper: PDF p. 5, Theorem 2.2 discussion] [Paper: PDF p. 27, Conclusion] [Paper: PDF p. 28, Conclusion]

## 13 批判性分析

[Analysis] 理论辅助样本通常按目标独立生成，实验以有限内链近似，又引入额外误差；不能把外层O(N^−1/2)直接当完整实验保证。[Paper: PDF p. 13, Algorithm 7] [Paper: PDF p. 18, experimental setup]

[Analysis] 预印本Equation9把log配分函数贡献写成正Cov，而由Equation7微分应为负Cov；涉及曲率预处理，复现需核对正式版及代码。该观察不等于主扰动结论无效。[Paper: PDF p. 14, Equation 7] [Paper: PDF p. 22, Equation 9]

## 14 学到的知识

### Agent-derived knowledge candidates

[Analysis] 区分理想连续目标、离散核目标、近似核目标与有限时间输出；每层误差有各自控制参数。固定核偏差和非平稳偏差不可互换。

## 15 与既有知识的联系

[Analysis] 与Mitrophanov2005共同支持本综述的误差框架；与PiX的score/分裂/迭代分解联系在误差来源区分，不能把两种定理度量直接互换。

## 16 研究创意

不适用。本轮只核实背景结果，不将2005/2014已有的核稳定性问题作为原创空白。

