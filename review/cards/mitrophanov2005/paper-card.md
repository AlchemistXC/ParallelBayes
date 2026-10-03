# Sensitivity and convergence of uniformly ergodic Markov chains｜论文精读卡

> Source coverage: Full paper
> Extraction confidence: Mixed
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Paper-only
> Card completeness: Complete relative to supplied source

阅读全文§1–5及附录A；已核对定理、证明递推和唯一数值表，未执行数值复算或逐条审计其参考文献。

## 01 基本信息

[Paper] **Sensitivity and convergence of uniformly ergodic Markov chains**。作者：Mitrophanov, A. Yu.。发表：Journal of Applied Probability，2005。标识：10.1239/jap/1134587812。

正式出版PDF，印刷页1003–1014对应PDF p1–12。页脚明确给出DOI 10.1239/jap/1134587812，修正此前仅题录阶段的未决标识记录。[Paper: PDF p. 1, title and footer]

阅读日期：2026-10-03。来源：[本地 PDF](../../../references/background/mitrophanov2005.pdf)；[题录/发表页](https://www.cambridge.org/core/journals/journal-of-applied-probability/article/sensitivity-and-convergence-of-uniformly-ergodic-markov-chains/26A9854BCB8D103B3A63A9B272616EC0)。类型：methods；关键词：一致遍历性；转移核扰动；总变差；遍历系数。本综述位置：近似并行核的误差预算所需理论背景。。

## 02 一句话概括

[Paper] 将一致遍历链的核扰动敏感性与收敛常数、迭代核遍历系数联系起来，给有限时间及不变分布的误差界。[Paper: PDF p. 3, Theorem 3.1] [Paper: PDF p. 5, Theorem 3.2]

## 03 研究问题

[Paper] 已知原链收敛速度时，转移核的数值或模型误差会怎样放大为分布误差？[Paper: PDF p. 1, Introduction]

## 04 研究背景与发展路径

[Paper] 作者比较有限矩阵扰动和一般状态空间算子方法；附录比较Anisimov/Kartashov已有界。历史优先权仅据原文，未独立重读所引前作。[Paper: PDF p. 10, Appendix A]

## 05 论文指出的核心痛点

[Paper] 一般状态空间的遍历系数难计算；只看单步核差不足以评估长期影响，需要原链的收敛控制。[Paper: PDF p. 1, Introduction]

## 06 核心思想

[Paper] 用望远镜分解把每步扰动经后续原链传播，再以零质量有符号测度上的收缩系数求和。[Paper: PDF p. 4, Equations 3.2–3.6]

## 07 方法总览

[Paper] 输入原核P、扰动核Ptilde、初始分布差z0和一致界Cρ^n；令E=Ptilde−P，输出所有n的误差界。若另已知扰动链存在不变测度，再得稳态界。有限状态时可由谱分解或可逆化计算收敛界。[Paper: PDF p. 4, Corollary 3.1] [Paper: PDF p. 7, Theorem 4.1]

## 08 核心模块拆解

| 模块 | 作用 | 边界 | 来源 |
|---|---|---|---|
| τ(P^n) | 零质量测度收缩 | 不等于一般L2谱隙 | [Paper: PDF p. 3, Equation 2.3] |
| m步骨架 | 用τ(P^m)<1替代一步收缩 | 需选择m并估计多步核差 | [Paper: PDF p. 5, Theorem 3.2] |
| 谱界 | 由β及特征向量条件数得Cρ^n | 定理4.1要求可对角化 | [Paper: PDF p. 7, Theorem 4.1] |

## 09 关键公式与符号

[Paper] 本文范数是总变差质量|q|(S)，对概率差为常用sup事件距离的两倍。核心界为‖zn‖≤‖z0‖τ(P^n)+‖E‖Σ(i=0至n−1)τ(P^i)。若supx‖P^n(x,·)−π‖≤Cρ^n，则稳态差≤[n̂+Cρ^n̂/(1−ρ)]‖E‖，n̂=⌈logρ(C⁻¹)⌉；还需扰动链存在不变测度。[Paper: PDF p. 2, norm convention] [Paper: PDF p. 4, Equations 3.3 and 3.8]

## 10 实验设计与证据链

[Paper] 数值例是三个3×3转移矩阵，来源于离子通道模型。表1固定P2与扰动E改变m：F1从m3的.339降至m50的.068，m300反升至.196，说明块长优化影响界的松紧。[Paper: PDF p. 8, §5] [Paper: PDF p. 10, Table 1]

[Analysis] 这是界的比较，不是高维MCMC的吞吐实验，也没有证明所有实例中新界都比一步界紧。

### 图表、公式及附录证据目录


无图；全部正文与附录已读。印刷页=PDF页+1002。

| 对象 | 位置及论证角色 |
|---|---|
| Table 1 | p10，扰动界随骨架步数m非单调变化 |
| Equations 2.1–2.5 | p2–3，算子范数、统一收敛、遍历系数 |
| Equations 3.1–3.8 | p3–4，望远镜分解、一致时间界及稳态界 |
| Equations 3.9–3.17 | p5–6，多步骨架及m‖E‖控制 |
| Equations 4.1–4.4 | p7–8，有限状态谱与可逆化收敛界 |
| Equations A.1–A.2 | p10–11，与前作比较及额外小扰动条件 |

核心证据矩阵：核差→分布差由Theorem3.1；稳态界另要求存在性由Corollary3.1；可计算实例只有§5三个小矩阵，不能外推高维常数。


## 11 结论的正确解释

[Analysis] 该文支持“误差放大受混合性质控制”，不支持“任何并行近似误差都至多除以某个谱隙”。一致遍历界、所用范数和扰动链不变分布存在性必须明示。[Paper: PDF p. 3, Theorem 3.1] [Paper: PDF p. 4, Corollary 3.1]

## 12 作者明确承认的局限

[Paper] 无穷状态遍历系数难计算；可逆化可能给θ=1的无效收缩界；精确谱参数也可能不易获得。更紧多步界计算成本更高。[Paper: PDF p. 1, Introduction] [Paper: PDF p. 8, Remarks 4.1–4.2] [Paper: PDF p. 10, §5]

## 13 批判性分析

[Analysis] 应先判定近似误差能否控制supx核TV差，再调用本结果；轨迹欧氏残差小本身不能提供该控制。论文没有针对多GPU、随机停机或共享自适应证明这一桥梁。依据是其输入明确为算子范数E。[Paper: PDF p. 2, Equation 2.1] [Paper: PDF p. 3, Theorem 3.1]

## 14 学到的知识

### Agent-derived knowledge candidates

[Analysis] 核扰动界的关键输入是强范数及收敛常数；页码引用时保留该文TV的两倍约定，避免常数比较错误。

## 15 与既有知识的联系

[Analysis] 为Alquier等的近似核理论提供基础；本综述的一步强收缩例应标为说明性推导，并与本文较一般的一致遍历结果区别。

## 16 研究创意

不适用。本次为背景理论核查，不提出新方法。

