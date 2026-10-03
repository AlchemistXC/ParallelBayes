# Accelerating MCMC via Parallel Predictive Prefetching：全文核查卡

> Source coverage: Full paper
> Extraction confidence: Mixed (text reliable; equations/tables checked against PDF where material)
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Targeted external check
> Card completeness: Complete relative to supplied source

输入边界：保存的全文及已提供补充；按正文、附录、图表与结论进行核对，关键推导抽查。**不代表逐行数学重证、全部引文核验或实验复现。** PDF 页码均从文件第一页起计。

## 01 基本信息

- 作者：Angelino, Elaine; Kohler, Eddie; Waterland, Amos; Seltzer, Margo; Adams, Ryan P.。单位以 [PDF 首页](../../../references/papers/angelino2014.pdf)为准。
- 年份/载体：2014，arXiv（本地保存版本）。
- 本地版本：arXiv v1；本条按本地预印本著录；14 页。
- 标识与出版记录：[原始来源](https://arxiv.org/abs/1403.7265v1)；引用键 `angelino2014`。
- 类型：methods；领域：贝叶斯计算/并行采样相关方法；关键词：预测性预取。
- 软件/数据：以论文实验节和来源包中的链接为准；本轮未运行。MEADS 已另存官方软件。
- 阅读日期：2026-10-02；用途：连接早期预取与近期时间并行；最终投稿时可再补 UAI 正式版著录信息。

## 02 一句话概括

用近似似然差预测 MH 接受路径并调度未来分支的精确计算，预测错误只浪费工作；选定昂贵似然案例显示墙钟提速，特别是在 burn-in。

## 03 研究问题

如何用多核预先计算串行链很可能访问的未来状态，同时保留最终真实接受决策？

## 04 背景与发展路线

[Paper: PDF p. 3, §2] 预取早于本文，本文贡献是预测性调度。[External] [Grazzi 2026](../grazzi2026/paper-card.md)和[Zoltowski 2025](../zoltowski2025/paper-card.md)发展了不同的时间并行路线。

## 05 痛点

| 痛点与表现 | 原因/作者解释 | 证据 |
|---|---|---|
| 无方向预测的完整二叉预取树随深度指数增长；错误分支浪费工作。[Paper: PDF p. 4, Figure 1] | 见同列原文；不把机制解释视为普遍已证因果 | 原文定位随主张列出 |

## 06 核心思想

廉价数据子集只用于预测接受概率，最终提交的真实路径仍完成精确计算。[Analysis] 近似调度器不等于近似目标。

## 07 方法概览

固定随机数定义树→渐进估计 log 密度差→估计接受概率→把工作分配给高概率节点→真实接受决策完成后提交路径。要求提案相对廉价、目标评估昂贵并可分阶段近似。[Paper: PDF p. 5, §3; PDF p. 8, §4]

## 08 模块拆解

| 模块 | 功能 | 必要性 | 输入→输出 | 来源 | 移除影响（实验或分析） |
|---|---|---|---|---|---|
| 固定随机树 | 对应串行执行 | 保证同一路径 | 种子→分支树 | [Paper: PDF p. 4, Figure 1] | 无法对照完全相同轨迹 |
| 近似预测器 | 分配算力 | 避免均匀展开浪费 | 部分数据→路径概率 | [Paper: PDF p. 8, §4] | 预测差会减少收益但不必引入偏差 |
| 精确提交 | 维持真实 MH | 预测不是接受依据 | 完整计算→最终状态 | [Paper: PDF p. 5, §3] | 如改为近似接受，需要另证正确性 |

## 09 关键公式与符号

无预测二叉预取的深度只按 $\log_2 J$ 随处理器数 J 增长；预测提高有效路径命中率。该复杂度不是多候选核谱隙界。[Paper: PDF p. 3, §2; PDF p. 4, Figure 1]

以下人工分组目录同时记录自动抽取的误报；编号覆盖不等于逐行证明认证。

| 公式组/抽取标记 | PDF 物理页 | 作用与边界 |
|---|---|---|
| Equation 1 | 5 | 固定随机数的 MH 更新。 |
| Equation 2; Equation 3; Equation 4 | 6 | 接受判定与预测调度；预测不替代最终接受检验。 |
| Equation 5; Equation 6; Equation 7; Equation 8; Equation 9; Equation 10 | 7 | 独立同分布似然差的抽样估计及正态近似。 |
| Equation 11; Equation 12; Equation 13; Equation 14; Equation 15 | 8 | 方差、预测概率及相关性启发式；错误预测损失计算量而不改变已确认路径。 |

## 10 实验与证据链

| 实验 | 检验主张 | 数据/基线/预算 | 结果 | 支持结论 | 不支持的更强结论 | 来源 |
|---|---|---|---|---|---|---|
| 高斯混合 | 实测精确路径加速 | 8 分量、8 维、100 万数据，最多 64 workers | burn-in 9575 步约 16.8 倍；50000 步总程约 5.8 倍 | 昂贵似然和可预测阶段有益 | 不可把短时超过 40 倍当全程稳定收益 | [Paper: PDF p. 9, Table 1; PDF p. 10, Figure 3] |
| Bayesian Lasso | 另一大数据案例 | 180 万数据、56 特征；C++/Python/MPI | 展示加速，但 50000 步未收敛 | 计算加速可以成立 | 不能称后验已准确恢复 | [Paper: PDF p. 11, §5; PDF p. 12, Figure 5] |

图表清单（先于卡片起草核对）：

| 证据 | PDF 物理页 | 论证作用 |
|---|---|---|
| Figure 1 | 4 | 预取二叉树 |
| Figure 2; Table 1 | 9 | 混合模型加速与总时长 |
| Figure 3; Table 2 | 10 | 随链进展的收益与 ESS/Rhat |
| Figure 4 | 11 | 预测器比较 |
| Figure 5 | 12 | Lasso 案例 |

## 11 正确理解

执行同一伪随机轨迹意味着串行混合问题全部保留。用 wall-clock 比较有价值，但硬件、网络、burn-in 与平稳段预测能力不能忽略。

有界结论：用近似似然差预测 MH 接受路径并调度未来分支的精确计算，预测错误只浪费工作；选定昂贵似然案例显示墙钟提速，特别是在 burn-in。

## 12 作者明确承认的限制

| 限制 | 具体表现 | 作者方向/处理 | 来源 |
|---|---|---|---|
| 算法适用范围 | 需要廉价提案与昂贵、可逐步近似的目标评估 | 扩展应用与调度器 | [Paper: PDF p. 5, §3] |
| 实际收敛 | Lasso 例子在给定预算内尚未收敛 | 更长计算 | [Paper: PDF p. 11, §5] |

## 13 批判分析

[Analysis] 应与当前 GPU 多链基线按相同总预算重新比较，不能由 2014 年硬件实验推断今天的相对优势；可通过同语言实现和控制通信成本检验。

这里是 [Analysis]，不回填为作者自述。尚未执行文中提出的检验。

## 14 知识候选

### Agent-derived knowledge candidates

[Analysis] 精确性可来自最后提交机制，调度预测允许出错。

## 15 与已有知识的联系

[External] [Pozza 2025](../pozza2025/paper-card.md)补充 Remark 3 明确说明预取不属于其 Algorithm 1 类，避免错误套用上界。

## 16 研究候选

### Agent-derived research candidates

Not applicable：本卡不单独宣称新的算法创意。跨论文形成的候选问题及其前作、验证方式、失败条件见[成果与缺口报告](../../截至2026-10-02的成果与缺口.md)。
