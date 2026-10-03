# Fast parallel sampling under isoperimetry：全文核查卡

> Source coverage: Full paper
> Extraction confidence: Mixed (text reliable; equations/tables checked against PDF where material)
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Targeted external check
> Card completeness: Complete relative to supplied source

输入边界：保存的全文及已提供补充；按正文、附录、图表与结论进行核对，关键推导抽查。**不代表逐行数学重证、全部引文核验或实验复现。** PDF 页码均从文件第一页起计。

## 01 基本信息

- 作者：Anari, Nima; Chewi, Sinho; Vuong, Thuy-Duong。单位以 [PDF 首页](../../../references/papers/anari2024.pdf)为准。
- 年份/载体：2024，Proceedings of Thirty Seventh Conference on Learning Theory。
- 本地版本：COLT 2024 / PMLR 247；PDF 内部页码 1-25；25 页。
- 标识与出版记录：[原始来源](https://proceedings.mlr.press/v247/anari24a.html)；引用键 `anari2024`。
- 类型：methods；领域：贝叶斯计算/并行采样相关方法；关键词：并行 Langevin 理论。
- 软件/数据：以论文实验节和来源包中的链接为准；本轮未运行。MEADS 已另存官方软件。
- 阅读日期：2026-10-02；用途：区分并行轮数、总工作量以及 KL/TV 分布误差保证。

## 02 一句话概括

用 Picard 并行近似 Langevin 动力学，在等周/函数不等式条件下取得 polylog 维度依赖的并行查询轮数，同时给出 KL/TV 误差保证。

## 03 研究问题

给定大量并行 score 查询资源，能否减少达到指定分布误差所需的顺序轮数？

## 04 背景与发展路线

[Paper: PDF p. 5, §1] 区分同期随机中点工作和误差度量。[External] Zhou–Sugiyama 2025 已改进部分设定的轮数依赖，见新增核查。

## 05 痛点

| 痛点与表现 | 原因/作者解释 | 证据 |
|---|---|---|
| 串行离散化长 Langevin 轨迹使查询深度大；并行评估需要控制离散化、score 与 Picard 误差。[Paper: PDF p. 1, Abstract; PDF p. 8, §3] | 见同列原文；不把机制解释视为普遍已证因果 | 原文定位随主张列出 |

## 06 核心思想

固定 Brownian 随机数，在短时间片内并行更新网格，以 Picard 收敛替代逐网格推进；再把数值误差与混合分析结合。

## 07 方法概览

输入目标势、score 或 δ-准确近似、初始化→分时间片→并行网格 Picard→输出近似目标样本。LSI、光滑性、初始 KL、步长、处理器数均进入保证；仅有 Poincaré 不等式不是其全部混合结论的充分替代。[Paper: PDF p. 10, Theorem 13; PDF p. 12, Theorem 15; PDF p. 5, Remark 2]

## 08 模块拆解

| 模块 | 功能 | 必要性 | 输入→输出 | 来源 | 移除影响（实验或分析） |
|---|---|---|---|---|---|
| 并行离散化 | 降低顺序 score 轮数 | 串行网格昂贵 | Brownian 路径→近似轨迹 | [Paper: PDF p. 9, §3] | 恢复串行离散化成本 |
| 混合分析 | 把路径模拟连到目标误差 | 轨迹准确还不够 | 初始 KL/LSI→分布误差 | [Paper: PDF p. 10, Theorem 13] | 不能由模拟准确性独立推出后验误差 |
| 误差分解 | 统一数值与 score 误差 | 近似不可忽略 | 步长/网格/δ→界 | [Paper: PDF p. 16, Appendix A] | 丧失目标精度保证 |

## 09 关键公式与符号

Theorem 13 的典型条件：$\beta h\le0.1$、$M\ge7\max\{\kappa d/\epsilon^2,\kappa^2\}$、$K\ge2+\log M$，$\kappa=\beta/\alpha$。输出 KL 控制可再用 Pinsker 转成 TV；M 是每轮并行查询数，K 是片内迭代数。[Paper: PDF p. 10, Theorem 13]

以下人工分组目录同时记录自动抽取的误报；编号覆盖不等于逐行证明认证。

| 公式组/抽取标记 | PDF 物理页 | 作用与边界 |
|---|---|---|
| Equation 0 | 4 | 自动识别误报：Algorithm 初始值。 |
| Equation 1 | 1 | Langevin 扩散。 |
| Equation 2 | 3 | Langevin Monte Carlo 更新。 |
| Equation 3 | 4 | Picard 近似误差。 |
| Equation 4 | 5 | 离散化误差所需条件。 |
| Equation 5; Equation 6 | 9 | Fisher 信息及运输不等式，不能与混合所需 LSI 混淆。 |
| Equation 7 | 10 | Theorem 13 的时间/参数设置。 |
| Equation 8; Equation 9; Equation 10 | 11 | 欠阻尼位置、动量和噪声更新。 |
| Equation 11; Equation 12; Equation 13 | 17 | KL 插值误差的证明步骤。 |
| Equation 14; Equation 15 | 19 | Girsanov 路径测度控制。 |
| Equation 16; Equation 17; Equation 18; Equation 19; Equation 20 | 20–21 | 欠阻尼局部误差与 Picard 收敛辅助界；核对作用，未独立重证全部常数。 |

## 10 实验与证据链

| 实验 | 检验主张 | 数据/基线/预算 | 结果 | 支持结论 | 不支持的更强结论 | 来源 |
|---|---|---|---|---|---|---|
| 理论分析 | 查询轮数与分布误差 | 过阻尼/欠阻尼动力学，指定函数不等式和初始化 | 给出 KL/TV 上界及复杂度 | 条件下的采样复杂度改善 | 没有 GPU 墙钟实测结论 | [Paper: PDF p. 10, Theorem 13; PDF p. 12, Theorem 15] |

图表清单（先于卡片起草核对）：

| 证据 | PDF 物理页 | 论证作用 |
|---|---|---|
| 无主文图表 | 1–25 | 理论论文；不虚构硬件实验 |
| Theorem 13; Corollary 14; Theorem 15 | 10–12 | 过阻尼与欠阻尼主结果、初始化 |
| Theorems 20–21; Appendices A–C | 16–25 | 误差控制、连续混合与耦合；主要证明链 |

## 11 正确理解

是近似采样复杂度结果，不是精确 MH 的轨迹等价定理。忽略 κ、ε、初始状态和并行宽度会误读 polylog(d)。prefix-scan 本身的额外对数深度不等同于 score oracle 的自适应轮数。[Paper: PDF p. 5, §1]

有界结论：用 Picard 并行近似 Langevin 动力学，在等周/函数不等式条件下取得 polylog 维度依赖的并行查询轮数，同时给出 KL/TV 误差保证。

## 12 作者明确承认的限制

| 限制 | 具体表现 | 作者方向/处理 | 来源 |
|---|---|---|---|
| 假设差异 | 部分离散化分析只需 T2，但连续混合仍需 LSI | 更弱等周条件下的方法 | [Paper: PDF p. 5, Remark 2] |
| 计算模型 | oracle 轮数之外仍有前缀和成本 | 实现需计入该成本 | [Paper: PDF p. 5, §1] |

## 13 批判分析

[Analysis] 理论足够多处理器与实际 GPU 内存未必匹配；可把 M、K、片数逐项转为有限设备时间和存储，而不是给出单个理论加速倍数。

这里是 [Analysis]，不回填为作者自述。尚未执行文中提出的检验。

## 14 知识候选

### Agent-derived knowledge candidates

[Analysis] 轨迹模拟误差与目标分布误差需要不同证明环节；TV、KL、W2 结果只能在附加不等式下转换。

## 15 与已有知识的联系

[External] [Zhou 2025 上界与下界](../../新增文献核查.md)分别推进轮数上界和高精度难例；精度区间不同，不构成简单冲突。

## 16 研究候选

### Agent-derived research candidates

Not applicable：本卡不单独宣称新的算法创意。跨论文形成的候选问题及其前作、验证方式、失败条件见[成果与缺口报告](../../截至2026-10-02的成果与缺口.md)。
