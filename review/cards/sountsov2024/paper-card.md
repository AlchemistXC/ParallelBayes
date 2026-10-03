# Running Markov Chain Monte Carlo on Modern Hardware and Software：全文核查卡

> Source coverage: Full paper
> Extraction confidence: Mixed (text reliable; equations/tables checked against PDF where material)
> Locator mode: page-grounded
> Primary analytical lens: review
> Secondary analytical lens: None
> Context verification: Targeted external check
> Card completeness: Complete relative to supplied source

输入边界：保存的全文及已提供补充；按正文、附录、图表与结论进行核对，关键推导抽查。**不代表逐行数学重证、全部引文核验或实验复现。** PDF 页码均从文件第一页起计。

## 01 基本信息

- 作者：Sountsov, Pavel; Carroll, Colin; Hoffman, Matthew D.。单位以 [PDF 首页](../../../references/papers/sountsov2024.pdf)为准。
- 年份/载体：2024，arXiv（书章公开版本）。
- 本地版本：arXiv v1，2024-11-06；不是 2026 书章终稿；26 页。
- 标识与出版记录：[原始来源](https://arxiv.org/abs/2411.04260v1)；引用键 `sountsov2024`。
- 类型：review；领域：贝叶斯计算/并行采样相关方法；关键词：现代硬件与基线。
- 软件/数据：以论文实验节和来源包中的链接为准；本轮未运行。MEADS 已另存官方软件。
- 阅读日期：2026-10-02；用途：保留公开稿用于版本对照；正式引用优先使用 2026 书章。

## 02 一句话概括

2026 正式书章的公开前版，保留用于版本追溯；核心硬件论点及主要基准延续至书籍版。

## 03 研究问题

硬件的吞吐、向量化和内存特征如何影响 MCMC 的实现与算法选择？

## 04 背景与发展路线

[Paper: PDF p. 1, Title page] arXiv v1，2024-11-06；[External] 已对照 2026 书籍版，正式版实际为第 21 章。

## 05 痛点

| 痛点与表现 | 原因/作者解释 | 证据 |
|---|---|---|
| 低精度、SIMD 控制流与内存约束需要一起处理。[Paper: PDF p. 16, §6; PDF p. 20, §6.3] | 见同列原文；不把机制解释视为普遍已证因果 | 原文定位随主张列出 |

## 06 核心思想

让链、数据与模型并行适配硬件；群体调参可以利用链间信息。[Paper: PDF p. 11, §4; PDF p. 14, §5]

## 07 方法概览

硬件与软件简介→三种并行维度→群体调参→数值与工程实践。[Paper: PDF p. 3, §2; PDF p. 7, §3; PDF p. 11, §4; PDF p. 14, §5; PDF p. 16, §6]

## 08 模块拆解

| 模块 | 功能 | 必要性 | 输入→输出 | 来源 | 移除影响（实验或分析） |
|---|---|---|---|---|---|
| 并行轴 | 链/数据/模型维度选择 | 资源和计算任务不同 | 模型→并行执行 | [Paper: PDF p. 11, §4] | 效果取决于计算密度 |
| 工程约束 | 精度、控制流与内存 | 正确运行所需 | 执行→诊断 | [Paper: PDF p. 16, §6] | 忽略可能导致低效或数值问题 |

## 09 关键公式与符号

ESS/sec 衡量所选函数的采样效率，不能单独检验近似偏差。[Paper: PDF p. 10, Table 1]

## 10 实验与证据链

| 实验 | 检验主张 | 数据/基线/预算 | 结果 | 支持结论 | 不支持的更强结论 | 来源 |
|---|---|---|---|---|---|---|
| HMC/NUTS | 硬件吞吐差异 | 64 链、预调参、不含调参时间 | GPU HMC 2.4 s，GPU NUTS 4.3 s | 指定模型的采样阶段比较 | 不等于完整推断流程提速 | [Paper: PDF p. 10, Table 1; PDF p. 11, §4] |

图表清单（先于卡片起草核对）：

| 证据 | PDF 物理页 | 论证作用 |
|---|---|---|
| Table 1 | 10 | HMC/NUTS 预调参基准 |
| Figure 1; Figure 2 | 11; 12 | GPU/CPU 链数扩展 |
| Figure 3 | 15 | K-fold 群体调参 |
| Figure 4 | 20 | 控制流 profiling |

## 11 正确理解

仅代表 2024 arXiv v1。核心实验和讨论与 2026 版本一致；2026 末尾额外有 Style Demo 与短链诊断图表，不将其理解为本文新增算法。

有界结论：2026 正式书章的公开前版，保留用于版本追溯；核心硬件论点及主要基准延续至书籍版。

## 12 作者明确承认的限制

| 限制 | 具体表现 | 作者方向/处理 | 来源 |
|---|---|---|---|
| 实验设定 | 手调 HMC 不代表实际自动化流程 | 比较时披露调参成本 | [Paper: PDF p. 11, §4] |
| 精度/内存 | 单精度和存储开销 | 高精度调试、流式统计 | [Paper: PDF p. 16, §6.1; PDF p. 20, §6.3] |

## 13 批判分析

[Analysis] 不应用 2024 公开稿覆盖用户提供的正式书章。引用主版本、保存旧版本有助于解释章号、页码和内容差异。

这里是 [Analysis]，不回填为作者自述。尚未执行文中提出的检验。

## 14 知识候选

### Agent-derived knowledge candidates

[Analysis] 算法并行轴与硬件类别应分开；FP32 的大数相减可能直接扰动 MH 接受决策。

## 15 与已有知识的联系

[External] 正式版本和完整综合解读见[2026 书章卡](../sountsov2026/paper-card.md)。

## 16 研究候选

### Agent-derived research candidates

Not applicable：本卡不单独宣称新的算法创意。跨论文形成的候选问题及其前作、验证方式、失败条件见[成果与缺口报告](../../截至2026-10-02的成果与缺口.md)。
