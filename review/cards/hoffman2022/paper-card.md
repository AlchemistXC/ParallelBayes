# Tuning-Free Generalized Hamiltonian Monte Carlo：全文核查卡

> Source coverage: Full paper
> Extraction confidence: Mixed (text reliable; equations/tables checked against PDF where material)
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Targeted external check
> Card completeness: Complete relative to supplied source

输入边界：保存的全文及已提供补充；按正文、附录、图表与结论进行核对，关键推导抽查。**不代表逐行数学重证、全部引文核验或实验复现。** PDF 页码均从文件第一页起计。

## 01 基本信息

- 作者：Hoffman, Matthew D.; Sountsov, Pavel。单位以 [PDF 首页](../../../references/papers/hoffman2022.pdf)为准。
- 年份/载体：2022，Proceedings of The 25th International Conference on Artificial Intelligence and Statistics。
- 本地版本：AISTATS 2022 / PMLR 151；15 页。
- 标识与出版记录：[原始来源](https://proceedings.mlr.press/v151/hoffman22a.html)；引用键 `hoffman2022`。
- 类型：methods；领域：贝叶斯计算/并行采样相关方法；关键词：群体自适应基线。
- 软件/数据：以论文实验节和来源包中的链接为准；本轮未运行。MEADS 已另存官方软件。
- 阅读日期：2026-10-02；用途：群体自适应与 GPU 多链基线；软件未执行。

## 02 一句话概括

MEADS 用群体链调参和广义 HMC 降低手工调参负担，分折机制保持正确联合目标；它是时间并行方法应认真比较的多链基线。

## 03 研究问题

如何从链群状态自动估计几何和动力学尺度，同时避免任意共享自适应破坏目标分布？

## 04 背景与发展路线

[Paper: PDF p. 2, §1] 承接 HMC、GHMC 和 ensemble adaptation。[External] 2026 LAPS 又提出先不校正再校正的 warmup 路线，见新增核查。

## 05 痛点

| 痛点与表现 | 原因/作者解释 | 证据 |
|---|---|---|
| 可调参数多，普通 HMC 完全刷新动量可能低效；直接共享当前链调参可引入偏差。[Paper: PDF p. 3, §2; PDF p. 13, Appendix D] | 见同列原文；不把机制解释视为普遍已证因果 | 原文定位随主张列出 |

## 06 核心思想

部分动量刷新和非可逆 slice 更新，加上 K-fold ECA；更新一折时借其他折估计参数，维持所需条件独立。[Paper: PDF p. 5, Figure 2; PDF p. 7, Algorithm 3]

## 07 方法概览

输入可微 log 密度和链群→按折分组→用其他折的矩估计与梯度估计尺度→GHMC/slice 转移→轮换。默认 K=4，每折 32 链，参数有固定常数；“tuning-free”指减少逐问题调参而非没有超参数。[Paper: PDF p. 7, Algorithm 3; PDF p. 12, Appendix A]

## 08 模块拆解

| 模块 | 功能 | 必要性 | 输入→输出 | 来源 | 移除影响（实验或分析） |
|---|---|---|---|---|---|
| GHMC | 部分保留动量 | 减少随机游走式移动 | 状态/动量→提案 | [Paper: PDF p. 3, §2] | 移除会改变相关结构 |
| K-fold ECA | 联合目标不变 | 避免当前链污染自身核参数 | 其他折→更新参数 | [Paper: PDF p. 5, Figure 2] | Hogwild 反例可破坏不变性 |
| 尺度启发式 | 自动设置步长/阻尼 | 手调负担 | 矩与梯度→超参数 | [Paper: PDF p. 6, §3] | 固定设置的稳健性下降；消融见补充 |

## 09 关键公式与符号

联合目标是多链目标的乘积；使用其他折信息调参时，条件于那些折，被更新折仍须使用保持其目标的核。梯度外积与负 Hessian 的期望联系需要分部积分的边界条件。[Paper: PDF p. 5, §3; PDF p. 15, Appendix E]

以下人工分组目录同时记录自动抽取的误报；编号覆盖不等于逐行证明认证。

| 公式组/抽取标记 | PDF 物理页 | 作用与边界 |
|---|---|---|
| Equation 1; Equation 2 | 3 | GHMC 动力学与能量接受规则。 |
| Equation 3 | 4 | 分折群体自适应的不变性结构。 |
| Equation 4; Equation 5; Equation 6; Equation 7 | 6 | 梯度外积、尺度及谱量估计的调参启发式。 |
| Equation 8 | 7 | 归一化偏差指标，用于达标梯度次数比较。 |
| Equation 9 | 13 | 特征值估计器；谱混合可造成估计偏差。 |
| Equation 10; Equation 11; Equation 12; Equation 13 | 15 | score/Hessian 的分部积分恒等式；需满足相应正则性与边界条件。 |

## 10 实验与证据链

| 实验 | 检验主张 | 数据/基线/预算 | 结果 | 支持结论 | 不支持的更强结论 | 来源 |
|---|---|---|---|---|---|---|
| 8 个目标基准 | 自动化采样效率 | 2–2519 维、TPU v2、128 链、32 次运行；含 MAP 初始化 | MEADS 在多项指标有竞争力，但非每个模型都最佳 | 强多链基线 | 梯度调用收益不等于端到端墙钟比 | [Paper: PDF p. 8, Table 1; PDF p. 9, Table 2] |
| 超参数与谱估计消融 | 启发式稳定性 | 步长倍率、阻尼、折数、有限样本 | 报告偏差、方差及估计限制 | 默认值有经验支持 | 不是对任意目标完全免调参 | [Paper: PDF p. 12, Figure 4; PDF p. 15, Figure 8] |

图表清单（先于卡片起草核对）：

| 证据 | PDF 物理页 | 论证作用 |
|---|---|---|
| Figure 1; Figure 2; Figure 3 | 4; 5; 7 | 依赖结构、分折调参、偏差演化 |
| Table 1; Table 2 | 8; 9 | 目标规模及梯度成本比较 |
| Figure 4; Figure 5; Figure 6; Figure 7; Figure 8 | 12; 12; 13; 14; 15 | 步长/阻尼/折数消融、全目标偏差、谱估计 |

## 11 正确理解

主要指标为达到指定平方偏差的梯度调用次数和每有效样本梯度成本；并非以统一墙钟计时证明优于一切 HMC。谱尺度估计对混合特征值可有偏。[Paper: PDF p. 13, Appendix C]

有界结论：MEADS 用群体链调参和广义 HMC 降低手工调参负担，分折机制保持正确联合目标；它是时间并行方法应认真比较的多链基线。

## 12 作者明确承认的限制

| 限制 | 具体表现 | 作者方向/处理 | 来源 |
|---|---|---|---|
| 几何估计近似 | 最大特征值估计存在偏差 | 更好的估计或问题适配 | [Paper: PDF p. 13, Appendix C] |
| 精确共享条件 | 不恰当异步/hogwild 更新会失败 | 维持分折条件 | [Paper: PDF p. 13, Appendix D] |

## 13 批判分析

[Analysis] 与时间并行比较时必须统一初始化和 warmup 预算；仅比较采样阶段可能偏向预先手调的竞争者。可分别报告冷启动与重复运行摊销成本。

这里是 [Analysis]，不回填为作者自述。尚未执行文中提出的检验。

## 14 知识候选

### Agent-derived knowledge candidates

[Analysis] 多链不仅可用于平均，也可帮助调参；但共享信息的概率结构需要证明。

## 15 与已有知识的联系

[External] [2026 书章](../sountsov2026/paper-card.md)解释硬件实现；[Nested R-hat 与 LAPS](../../新增文献核查.md)进一步补充诊断和冷启动。软件归档见[MEADS](../../../software/meads/README.md)，未执行。

## 16 研究候选

### Agent-derived research candidates

Not applicable：本卡不单独宣称新的算法创意。跨论文形成的候选问题及其前作、验证方式、失败条件见[成果与缺口报告](../../截至2026-10-02的成果与缺口.md)。
