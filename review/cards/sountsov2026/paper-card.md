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

- 作者：Sountsov, Pavel; Carroll, Colin; Hoffman, Matthew D.。单位以 [PDF 首页](../../../references/papers/sountsov2026.pdf)为准。
- 年份/载体：2026，Handbook of Markov Chain Monte Carlo, Second Edition。
- 本地版本：用户提供的 2026 第二版书籍 PDF，第 21 章；提取副本；22 页。
- 标识与出版记录：[原始来源](https://doi.org/10.1201/9781003453420-21)；引用键 `sountsov2026`。
- 类型：review；领域：贝叶斯计算/并行采样相关方法；关键词：现代硬件与基线。
- 软件/数据：以论文实验节和来源包中的链接为准；本轮未运行。MEADS 已另存官方软件。
- 阅读日期：2026-10-02；用途：硬件、链/数据/模型并行与软件基线；与 2024 公开稿为同一作品的不同版本。

## 02 一句话概括

解释如何在现代硬件上运行 MCMC，讨论链、数据、模型并行、群体调参、精度和控制流；它是新综述必须区分的直接前作。

## 03 研究问题

硬件的吞吐、向量化和内存特征如何影响 MCMC 的实现与算法选择？

## 04 背景与发展路线

[Paper: PDF p. 1, Chapter 21] 2026 第二版正式书籍中的第 21 章；本地保留 2024 arXiv 对照稿。两者属于同一作品，不能算作两项独立成果。

## 05 痛点

| 痛点与表现 | 原因/作者解释 | 证据 |
|---|---|---|
| GPU 上动态控制流产生等待，低精度影响接受率，保存大量链消耗内存。[Paper: PDF p. 13, §21.6; PDF p. 17, §21.6.3] | 见同列原文；不把机制解释视为普遍已证因果 | 原文定位随主张列出 |

## 06 核心思想

让并行维度和硬件执行模型相匹配。[Analysis] 增加链数往往先提供强基线，时间并行需要证明额外收益。

## 07 方法概览

教程流程：理解硬件→利用软件变换/向量化→选择链、数据、模型并行→群体调参→检查精度、SIMD 与内存。没有新的独立采样定理。[Paper: PDF p. 8, §21.4; PDF p. 10, §21.4; PDF p. 12, §21.5]

## 08 模块拆解

| 模块 | 功能 | 必要性 | 输入→输出 | 来源 | 移除影响（实验或分析） |
|---|---|---|---|---|---|
| 链并行 | 批量运行多条链 | 硬件吞吐 | 初值和随机数→多链 | [Paper: PDF p. 8, §21.4] | 减少链数可能降低吞吐；依硬件而定 |
| ECA | 共享调参信息 | 单链调参成本 | 链群→参数 | [Paper: PDF p. 12, Figure 21.3] | 不能任意共用当前链状态，否则正确性需重证 |
| 数值与内存管理 | 控制误差和存储 | FP32、长链存储 | 数值运算→可用实现 | [Paper: PDF p. 13, §21.6.1; PDF p. 17, §21.6.3] | 可能改变数值可靠性或导致 OOM；工程边界 |

## 09 关键公式与符号

$\mathrm{ESS}/\mathrm{second}$ 只在指定估计对象和可信平稳性下解释效率；多链均值的方差可下降，但共同初始化偏差不会由平均自动消失。[Paper: PDF p. 8, Table 21.1; PDF p. 9, §21.4]

## 10 实验与证据链

| 实验 | 检验主张 | 数据/基线/预算 | 结果 | 支持结论 | 不支持的更强结论 | 来源 |
|---|---|---|---|---|---|---|
| HMC/NUTS CPU/GPU | 并行吞吐影响有效采样 | P100 vs 28 核 Xeon，64 链、预调参数 | GPU HMC 2.4 s、10017 ESS/s；GPU NUTS 4.3 s、3731 ESS/s | 该模型及配置下的采样阶段差异 | 不含调参，不能当作端到端或现代所有 GPU 排名 | [Paper: PDF p. 8, Table 21.1] |
| 链数扩展与 profiling | 吞吐饱和及控制流成本 | GPU/CPU 链数扫描、HMC/NUTS | 曲线显示扩展性和执行开销差异 | 需要在具体硬件实测 | 不是链数越多一定越快 | [Paper: PDF p. 9, Figure 21.1; PDF p. 16, Figure 21.4] |

图表清单（先于卡片起草核对）：

| 证据 | PDF 物理页 | 论证作用 |
|---|---|---|
| Table 21.1 | 8 | HMC/NUTS 的预调参硬件基准 |
| Figure 21.1; Figure 21.2 | 9 | GPU 与 CPU 链数扩展 |
| Figure 21.3 | 12 | K-fold 群体调参 |
| Figure 21.4 | 16 | 控制流 profiling |
| Table 21.2; Figure 21.5 | 18; 19 | Style Demo 的短链诊断示例；源文件编辑痕迹 |

## 11 正确理解

p.9 明确承认手调 HMC 的基准不等于实际工作流。2026 年出版并不意味着所有基准在 2026 硬件重跑。书内 p.18–19 存在 Style Demo、Table 21.2 和 Figure 21.5；已回看图像，保留来源，不把它们当作新增时间并行结果。

有界结论：解释如何在现代硬件上运行 MCMC，讨论链、数据、模型并行、群体调参、精度和控制流；它是新综述必须区分的直接前作。

## 12 作者明确承认的限制

| 限制 | 具体表现 | 作者方向/处理 | 来源 |
|---|---|---|---|
| 控制流开销 | NUTS 等链间长度变化带来等待 | 选取硬件适配的算法与实现 | [Paper: PDF p. 14, §21.6.2] |
| 数值与内存 | 较低浮点精度与大量样本存储 | 高精度调试、流式统计量 | [Paper: PDF p. 13, §21.6.1; PDF p. 17, §21.6.3] |

## 13 批判分析

[Analysis] 书章缺乏统一的链长时间并行方法比较；这给专题综述留下补充空间。可检验方式：以 DEER、Online Picard、预取和现代多链方法在相同精度目标下对照。

这里是 [Analysis]，不回填为作者自述。尚未执行文中提出的检验。

## 14 知识候选

### Agent-derived knowledge candidates

[Analysis] 算法并行轴与硬件类别应分开；FP32 的大数相减可能直接扰动 MH 接受决策。

## 15 与已有知识的联系

[External] [Hoffman 2022](../hoffman2022/paper-card.md)给出保持联合目标的 ECA；[Dance 2025](../../新增文献核查.md#dance2025)已推进 NUTS 向量化控制流，更新本章的实践边界。

## 16 研究候选

### Agent-derived research candidates

Not applicable：本卡不单独宣称新的算法创意。跨论文形成的候选问题及其前作、验证方式、失败条件见[成果与缺口报告](../../截至2026-10-02的成果与缺口.md)。
