# Parallel MCMC algorithms: theoretical foundations, algorithm design, case studies：全文核查卡

> Source coverage: Full paper
> Extraction confidence: Mixed (text reliable; equations/tables checked against PDF where material)
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Targeted external check
> Card completeness: Complete relative to supplied source

输入边界：保存的全文及已提供补充；按正文、附录、图表与结论进行核对，关键推导抽查。**不代表逐行数学重证、全部引文核验或实验复现。** PDF 页码均从文件第一页起计。

## 01 基本信息

- 作者：Glatt-Holtz, Nathan E.; Holbrook, Andrew J.; Krometis, Justin A.; Mondaini, Cecilia F.。单位以 [PDF 首页](../../../references/papers/glattholtz2024.pdf)为准。
- 年份/载体：2024，Transactions of Mathematics and Its Applications。
- 本地版本：期刊版，8(2), tnae004；70 页。
- 标识与出版记录：[原始来源](https://doi.org/10.1093/imatrm/tnae004)；引用键 `glattholtz2024`。
- 类型：methods；领域：贝叶斯计算/并行采样相关方法；关键词：多候选方法与理论限制。
- 软件/数据：以论文实验节和来源包中的链接为准；本轮未运行。MEADS 已另存官方软件。
- 阅读日期：2026-10-02；用途：多候选并行采样的统一理论、算法与数值案例。

## 02 一句话概括

以扩展状态空间和对合映射统一多候选核的构造，推导 mpCN 等算法并提供 GPU 与 PDE 逆问题案例；理论首先保证不变性/可逆性，不提供普遍加速率。

## 03 研究问题

如何在一般状态空间构造正确的多候选接受机制，并把它用于复杂几何和无梯度逆问题？

## 04 背景与发展路线

[Paper: PDF p. 7, §1.2] 本文承接 Tjelmeland/Calderhead 等多候选构造，明确不把标准两阶段 multiple-try MH 当作本文主体。[External] 2026 Mad Props 已扩展这条线，见新增核查。

## 05 痛点

| 痛点与表现 | 原因/作者解释 | 证据 |
|---|---|---|
| 随意按候选密度归一化并不总能保留目标；一般正确接受率可能包含 O(p²) 代价。[Paper: PDF p. 23, Equations 4.8–4.11] | 见同列原文；不把机制解释视为普遍已证因果 | 原文定位随主张列出 |

## 06 核心思想

先定义扩展空间测度与对合，再从不变性/详细平衡条件推导接受规则。[Analysis] 这是算法设计框架，不是把同一串行轨迹改写为并行求解。

## 07 方法概览

状态 q→辅助变量/候选云 v→对合 S_j→按 α_j 选择下一状态；另一框架允许候选云内多次重采样。条件独立的两层提案在平衡条件下简化为 Barker 型接受。mpCN 以高斯基准测度为先验结构。[Paper: PDF p. 11, Theorem 2.2; PDF p. 15, Theorem 2.11; PDF p. 19, Theorem 3.3; PDF p. 27, Algorithm 5]

## 08 模块拆解

| 模块 | 功能 | 必要性 | 输入→输出 | 来源 | 移除影响（实验或分析） |
|---|---|---|---|---|---|
| 扩展空间与对合 | 建立不变性/可逆性 | 候选选择可能引入偏差 | q,v,S→核 | [Paper: PDF p. 11, Theorem 2.2] | 失去正确性条件 |
| 两层条件独立提案 | 简化接受率 | 一般表达式昂贵 | 中间点→候选云 | [Paper: PDF p. 15, Theorem 2.11] | 独立围绕当前点并非等价替代 |
| mpCN | 适配高斯先验逆问题 | 梯度不可得、维度高 | 先验样本→后验转移 | [Paper: PDF p. 27, Algorithm 5] | 不能由一般 RWM 直接获得函数空间结构 |

## 09 关键公式与符号

$\mu(dq)\propto e^{-\Phi(q)}\mu_0(dq)$，在两阶段 pCN 提案和相应平衡条件下，$\alpha_j=e^{-\Phi(q_j)}/\sum_{k=0}^p e^{-\Phi(q_k)}$。必须连同提案机制引用，不能把它理解为任何候选云都可这样选。[Paper: PDF p. 26, Equation 4.21; PDF p. 27, Equation 4.22]

以下人工分组目录同时记录自动抽取的误报；编号覆盖不等于逐行证明认证。

| 公式组/抽取标记 | PDF 物理页 | 作用与边界 |
|---|---|---|
| Equation 0; Equation 1; Equation 2 | 14; 2; 8 | 自动识别误报：初值或正文列举编号。有效关键式为 (2.2)、(2.5)、(2.12)、(2.15) 的不变性条件及 (3.13)、(4.21)–(4.22) 的具体算法；不能按误报编号引用。 |

## 10 实验与证据链

| 实验 | 检验主张 | 数据/基线/预算 | 结果 | 支持结论 | 不支持的更强结论 | 来源 |
|---|---|---|---|---|---|---|
| GPU 多候选 | 大量提案能否并行 | P100、TensorFlow，对比 CPU，多达 100000 候选 | 固定预算下改善所测多峰案例 | 某些昂贵评估适合并行 | 不保证任意高维后验都更优 | [Paper: PDF p. 37, Figure 1] |
| PDE 逆问题 | mpCN 的探索效果 | 196 维平流扩散、320 维形状估计，对比 pCN | 某些可观测量 ESS 改善；仍有模式质量不平衡 | 具有应用可行性 | 每样本改善不等于墙钟或全部模式已收敛 | [Paper: PDF p. 45, Figure 9; PDF p. 48, Figure 10] |

图表清单（先于卡片起草核对）：

| 证据 | PDF 物理页 | 论证作用 |
|---|---|---|
| Figure 1 | 37 | GPU/CPU 计时与多峰有效样本 |
| Figure 2; Figure 3 | 39 | 多链与多候选均值/二阶矩误差 |
| Figure 4 | 41 | 6 维玩具逆问题后验几何 |
| Figure 5; Figure 6; Figure 7 | 42; 42; 43 | mpCN 自相关、轨迹与调参 |
| Figure 8; Figure 9 | 45 | 平流扩散调参及模式探索 |
| Table 1 | 46 | Stokes 逆问题参数 |
| Figure 10; Figure 11; Figure 12 | 48; 49; 50 | Stokes 接受率、ESS、函数均值、边界分位数 |
| Figure C13; Figure C14; Figure C15; Figure C16; Figure C17; Figure C18; Figure C19; Figure C20 | 64–70 | 附录补充目标、参数扫描、先验/后验与 PDE 可视化 |

## 11 正确理解

Theorem 2.2 区分不变性与可逆性；Theorem 3.3 主要给不变性。不能由不变性单独推出唯一平稳分布、任意初值收敛或快速混合。不同候选数、硬件和存储约束必须披露。

有界结论：以扩展状态空间和对合映射统一多候选核的构造，推导 mpCN 等算法并提供 GPU 与 PDE 逆问题案例；理论首先保证不变性/可逆性，不提供普遍加速率。

## 12 作者明确承认的限制

| 限制 | 具体表现 | 作者方向/处理 | 来源 |
|---|---|---|---|
| 最优缩放与混合率 | p、接受结构和模式几何共同影响效果 | 定量混合、几何遍历性与大 p 研究 | [Paper: PDF p. 50, §6; PDF p. 51, §6] |
| 两种框架关系 | Algorithm 1 与 Algorithm 3 有重叠但不完全一致 | 系统刻画关系及可逆性 | [Paper: PDF p. 49, §6] |

## 13 批判分析

[Analysis] 本文 2024 年的“大 p 接受机制”开放问题在 2026 后续已有实质进展，不能原样列作缺口。测试途径：逐一对照 Mad Props 的退化结果、有限 p 偏差和极限核。

这里是 [Analysis]，不回填为作者自述。尚未执行文中提出的检验。

## 14 知识候选

### Agent-derived knowledge candidates

[Analysis] 增广空间便于证明正确性；Rao–Blackwell 化、重复候选输出和不同转移核的 ESS 要分清。

## 15 与已有知识的联系

[External] [Pozza 2025](../pozza2025/paper-card.md)提供受条件约束的效率上界；[Mad Props 2026](../../新增文献核查.md#glattholtz2026)发展大候选极限并指出部分构造退化。

## 16 研究候选

### Agent-derived research candidates

Not applicable：本卡不单独宣称新的算法创意。跨论文形成的候选问题及其前作、验证方式、失败条件见[成果与缺口报告](../../截至2026-10-02的成果与缺口.md)。
