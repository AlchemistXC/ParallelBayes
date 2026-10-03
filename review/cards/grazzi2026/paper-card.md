# Parallel computations for Metropolis Markov chains with Picard maps：全文核查卡

> Source coverage: Full paper
> Extraction confidence: Mixed (text reliable; equations/tables checked against PDF where material)
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Targeted external check
> Card completeness: Complete relative to supplied source

输入边界：保存的全文及已提供补充；按正文、附录、图表与结论进行核对，关键推导抽查。**不代表逐行数学重证、全部引文核验或实验复现。** PDF 页码均从文件第一页起计。

## 01 基本信息

- 作者：Grazzi, Sebastiano; Zanella, Giacomo。单位以 [PDF 首页](../../../references/papers/grazzi2026.pdf)为准。
- 年份/载体：2026，Biometrika。
- 本地版本：期刊正文，113(2), asag022；22 页。
- 标识与出版记录：[原始来源](https://doi.org/10.1093/biomet/asag022)；引用键 `grazzi2026`。
- 类型：methods；领域：贝叶斯计算/并行采样相关方法；关键词：Picard 时间并行。
- 软件/数据：以论文实验节和来源包中的链接为准；本轮未运行。MEADS 已另存官方软件。
- 阅读日期：2026-10-02；用途：无梯度 Metropolis 的精确与近似 Picard 方法

独立补充：[grazzi2026-supplement](../../../references/supplements/grazzi2026-supplement.pdf)；补充页码单独计数。

## 02 一句话概括

Online Picard 利用固定随机数和已确认前缀并行执行无梯度 Metropolis 链；在特定光滑和缩放条件下有并行轮数保证，也分析了允许错配的近似版本。

## 03 研究问题

带离散接受拒绝的 Metropolis 转移能否沿时间并行，并在何种条件下比逐步执行更快？

## 04 背景与发展路线

[External] 与[预测性预取](../angelino2014/paper-card.md)共享恢复原轨迹目标，但并行对象从未来分支变为整段增量。与[Newton 方法](../zoltowski2025/paper-card.md)依赖光滑线性化的处理不同。

## 05 痛点

| 痛点与表现 | 原因/作者解释 | 证据 |
|---|---|---|
| MH 的不连续分支不适合直接套光滑收缩论证；初始化会影响轨迹求解。在 Proposition 1 的强凸条件下，远端尾部的 Picard 求解反而趋于更快。[Paper: PDF p. 6, §3; PDF p. 9, Proposition 1] | 见同列原文；不把机制解释视为普遍已证因果 | 原文定位随主张列出 |

## 06 核心思想

把固定噪声下的接受增量写成 Picard 累加，识别已与串行算法一致的前缀并滑动窗口。[Analysis] 不需要所有未确认位置同时稳定。

## 07 方法概览

输入势函数、步长、固定噪声/阈值与 K 个并行点→评估接受增量→前缀和→确认前缀→推进窗口。精确版保留串行轨迹；近似版允许比例 r 的错配。理论 RWM 采用 h/sqrt(Ld) 缩放；MwG 理论的正交方向与实作坐标版本需分开。[Paper: PDF p. 6, Algorithm 2; PDF p. 7, Assumptions 1–2; PDF p. 10, §4; PDF p. 11, §5]

## 08 模块拆解

| 模块 | 功能 | 必要性 | 输入→输出 | 来源 | 移除影响（实验或分析） |
|---|---|---|---|---|---|
| Picard 累加 | 并行计算轨迹增量 | 绕开逐步依赖 | 旧轨迹→新轨迹 | [Paper: PDF p. 4, Figure 1] | 回到串行执行 |
| 确认前缀 | 保证与串行链一致 | 错误后缀不能输出 | 匹配标记→可用样本 | [Paper: PDF p. 6, Figure 2] | 移除后需统计误差控制 |
| 容错 r | 用错误率换并行进度 | 更大的窗口未必能一次全部确认 | 近似前缀→改变的输出 | [Paper: PDF p. 12, Proposition 3] | r=0 恢复精确策略 |

## 09 关键公式与符号

$\widehat G=L^{(J)}/J$ 表示每个并行轮平均推进步数，$L^{(J)}$ 为已确认位置、J 为轮数（Eq. 8，PDF p.13）；不是墙钟比。Theorem 2 要求 $K\le\sqrt{d/(8c_0)}$，其中 $c_0=15h^4(\sqrt{2/\pi}+h\gamma/2)^2$。维度扩展还要控制隐藏常数；Corollary 2 的 TV 结论额外要求强凸性和指定初始化。[Paper: PDF p. 7, Theorem 1; PDF p. 8, Theorem 2; PDF p. 9, Corollary 2]

以下人工分组目录同时记录自动抽取的误报；编号覆盖不等于逐行证明认证。

| 公式组/抽取标记 | PDF 物理页 | 作用与边界 |
|---|---|---|
| Equation 0 | 5 | 自动识别误报：算法初值，不是编号公式。 |
| Equation 1; Equation 2 | 3 | 固定随机输入的顺序递推与 Picard 迭代。 |
| Equation 3; Equation 4 | 5 | 在线窗口及已确认前缀。 |
| Equation 5; Equation 6 | 7 | Metropolis 增量与失配概率界；依赖步长、维度及正则性。 |
| Equation 7 | 9 | RWM Picard 映射的期望差异界，与光滑 ULA 的收缩性质比较；不是独立的 TV 混合公式。 |
| Equation 8 | 13 | 理想并行增益估计量；不直接等于硬件墙钟速度比。 |
| Equation 9 | 15 | 近似算法的矩误差实验指标。 |
| Equation 10 | 17（自动匹配另落在 p.4） | 实质是 SIR 例子的模型表达；自动抽取的 p.4 匹配来自 Figure 1 标号，不应作为公式定位。 |
| Equation 11; Equation 12 | 18 | SIR 后验及条件更新，限定昂贵似然案例。 |
| Equation 13 | 4 | 自动识别误报：Figure 1 中轨迹标号；未将其视作第 13 个数学公式。 |

## 10 实验与证据链

| 实验 | 检验主张 | 数据/基线/预算 | 结果 | 支持结论 | 不支持的更强结论 | 来源 |
|---|---|---|---|---|---|---|
| 回归与 SIR | 理论机制是否出现 | 线性/Logistic/Poisson 回归及 SIR；固定窗口 | 并行轮效率随设置变化；所测尾部初始化可加快 Picard 收敛 | 特定模型能推进多个串行步 | 不可直接把 G 叫墙钟加速 | [Paper: PDF p. 14, Figure 3; PDF p. 17, Figure 6; PDF p. 19, Table 1] |
| 昂贵黑箱似然 | 真实计时收益 | 14 维 ODE，Mac M3，K=8 | G=4.37，墙钟加速 2.52 倍 | 开销实际减少收益 | 不是完全忽略开销的论文 | [Paper: PDF p. 20, §6] |
| 近似版本 | 错配与均值/方差误差 | r 扫描、有限参考链 | 经验上存在精度—速度权衡 | 可用作探索性近似 | 没有一般不变分布 TV 偏差定理 | [Paper: PDF p. 16, Figure 5; PDF p. 12, §5] |

图表清单（先于卡片起草核对）：

| 证据 | PDF 物理页 | 论证作用 |
|---|---|---|
| Figure 1; Figure 2 | 4; 6 | Picard 与 Online Picard 示意 |
| Figure 3; Figure 4 | 14; 15 | 线性、Logistic、Poisson 回归 |
| Figure 5; Figure 6 | 16; 17 | 近似误差与尾部初始化 |
| Figure 7; Table 1 | 19 | SIR 轨迹与 ESS/轮数统计 |
| Supplement Figure 1; Supplement Figure 2 | 补充14; 补充16 | 附加实验与并行开销 |
| Assumptions 1–2; Theorems 1–2; Corollary 2; Proposition 3 | 7–12 | 主要保证及额外条件；补充 B–D 为证明 |

## 11 正确理解

Thm 1–2 是高维步长缩放与光滑条件下的轨迹计算结论；TV 混合还需附加条件。MwG 的一般混合界作者明确留待研究。补充材料 A–G 已核对，错误率上界不能直接升格为后验偏差保证。

有界结论：Online Picard 利用固定随机数和已确认前缀并行执行无梯度 Metropolis 链；在特定光滑和缩放条件下有并行轮数保证，也分析了允许错配的近似版本。

## 12 作者明确承认的限制

| 限制 | 具体表现 | 作者方向/处理 | 来源 |
|---|---|---|---|
| MwG 混合复杂度 | 理论方向与实际模型下的混合仍难分析 | 进一步的混合时间理论 | [Paper: PDF p. 11, §4] |
| 近似分布误差 | Proposition 3 控制错配比例，不控制 π_r 与 π 的一般距离 | 近似目标误差分析超出本文 | [Paper: PDF p. 12, §5] |

## 13 批判分析

[Analysis] Supplement §A 的 gamma 上界可能随 d 增长，故需检验常数后才能移植 sqrt(d) 结论；可用 n/d 固定的回归序列检查。Table 1 的 RWM d=372 行 ESS×G 数值与所列因子不符，已回看原图，具体记录见原文问题文件；这不否定主要定理。[Paper: PDF p. 19, Table 1]

这里是 [Analysis]，不回填为作者自述。尚未执行文中提出的检验。

## 14 知识候选

### Agent-derived knowledge candidates

[Analysis] 精确前缀证书可避免把不光滑接受决策交给连续残差阈值；昂贵似然有利于摊薄调度开销。

## 15 与已有知识的联系

[External] [Pozza 2025](../pozza2025/paper-card.md)限制的是不同的多候选核，不能据其定理否定本论文时间并行。

## 16 研究候选

### Agent-derived research candidates

Not applicable：本卡不单独宣称新的算法创意。跨论文形成的候选问题及其前作、验证方式、失败条件见[成果与缺口报告](../../截至2026-10-02的成果与缺口.md)。
