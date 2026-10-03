# Parallelizing non-linear sequential models over the sequence length：全文核查卡

> Source coverage: Full paper
> Extraction confidence: Mixed (text reliable; equations/tables checked against PDF where material)
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Targeted external check
> Card completeness: Complete relative to supplied source

输入边界：保存的全文及已提供补充；按正文、附录、图表与结论进行核对，关键推导抽查。**不代表逐行数学重证、全部引文核验或实验复现。** PDF 页码均从文件第一页起计。

## 01 基本信息

- 作者：Lim, Yi Heng; Zhu, Qi; Selfridge, Joshua; Kasim, Muhammad Firmansyah。单位以 [PDF 首页](../../../references/papers/lim2024.pdf)为准。
- 年份/载体：2024，International Conference on Learning Representations。
- 本地版本：arXiv v3；首页标注 ICLR 2024 accepted；27 页。
- 标识与出版记录：[原始来源](https://proceedings.iclr.cc/paper_files/paper/2024/hash/f3bfbd65743e60c685a3845bd61ce15f-Abstract-Conference.html)；引用键 `lim2024`。
- 类型：methods；领域：贝叶斯计算/并行采样相关方法；关键词：DEER 方法来源。
- 软件/数据：以论文实验节和来源包中的链接为准；本轮未运行。MEADS 已另存官方软件。
- 阅读日期：2026-10-02；用途：理解非线性递推并行化与 DEER 来源。

## 02 一句话概括

DEER 将非线性序列求值转成 Newton 迭代和并行线性求解，在部分 RNN/ODE 配置上获得大幅加速；论文并未直接完成 MCMC 算法或后验保证。

## 03 研究问题

非线性递推是否可以用并行扫描反复求解，从而减少沿序列的执行深度？

## 04 背景与发展路线

[Paper: PDF p. 14, Appendix A] 与 Newton、multiple shooting 等思想有关。[External] [Zoltowski 2025](../zoltowski2025/paper-card.md)之后将这一方法适配到 MCMC。

## 05 痛点

| 痛点与表现 | 原因/作者解释 | 证据 |
|---|---|---|
| 非线性函数复合通常不能像仿射映射那样保持紧凑表示，直接扫描困难。[Paper: PDF p. 3, §3] | 见同列原文；不把机制解释视为普遍已证因果 | 原文定位随主张列出 |

## 06 核心思想

每轮线性化非线性问题，然后并行解线性递推；前向多轮求解，隐式微分计算反向梯度。[Paper: PDF p. 4, §3]

## 07 方法概览

输入序列转移和初始条件→初猜→求 Jacobian→构造线性递推→并行扫描→收敛输出；可用于 ODE/RNN，训练部分利用隐式微分。局部二次收敛需要光滑、可逆和足够好的初始点。[Paper: PDF p. 15, Appendix A.3]

## 08 模块拆解

| 模块 | 功能 | 必要性 | 输入→输出 | 来源 | 移除影响（实验或分析） |
|---|---|---|---|---|---|
| 线性化 | 保持仿射复合闭合 | 直接非线性复合昂贵 | 当前状态→A,b | [Paper: PDF p. 4, §3] | 失去 Newton 校正 |
| 并行 inverse operator | 求线性序列 | 去除时间顺序依赖 | A,b→整段更新 | [Paper: PDF p. 5, §3.5] | 回到逐步求解 |
| 隐式反向 | 避免对所有求解轮反传 | 训练内存成本 | 收敛状态→梯度 | [Paper: PDF p. 5, §3] | 训练成本改变；未视为 MCMC 步骤 |

## 09 关键公式与符号

仿射对 $(A_2,b_2)\circ(A_1,b_1)=(A_2A_1,A_2b_1+b_2)$ 可结合扫描。稠密状态维数 n、序列长 L 时，存储约 O(n²L)，矩阵扫描工作有 n³ 因子；对数时间深度不能抹去这些成本。[Paper: PDF p. 5, §3.5]

以下人工分组目录同时记录自动抽取的误报；编号覆盖不等于逐行证明认证。

| 公式组/抽取标记 | PDF 物理页 | 作用与边界 |
|---|---|---|
| Equation 1; Equation 2; Equation 3; Equation 4; Equation 5 | 3 | 算子方程和 Newton 线性化。 |
| Equation 6; Equation 7 | 4 | 隐式微分与反向传播。 |
| Equation 8; Equation 9; Equation 10; Equation 11 | 5 | ODE 线性化、仿射 scan 和离散算子逆。 |
| Equation 12; Equation 13; Equation 14; Equation 15; Equation 16; Equation 17; Equation 18 | 14 | Newton 与 multiple shooting 的关系。 |
| Equation 19; Equation 20; Equation 21; Equation 22; Equation 23; Equation 24; Equation 25 | 15 | 局部收敛条件、算子范数及 Neumann 展开。 |
| Equation 26; Equation 27; Equation 28; Equation 29; Equation 30; Equation 31 | 16 | 局部二次收敛证明的递推界。 |
| Equation 32; Equation 33; Equation 34; Equation 35; Equation 36; Equation 37; Equation 38; Equation 39; Equation 40; Equation 41 | 17 | 局部证明结尾与 Burgers 方程实验定义。 |
| Equation 42; Equation 43; Equation 44; Equation 45; Equation 46; Equation 47; Equation 48; Equation 49 | 18 | 连续 ODE 的矩阵指数/局部展开推导；未据此主张一般非交换算子的全局公式成立。 |
| Equation 50; Equation 51; Equation 52; Equation 53 | 19 | 插值与局部截断误差。 |
| Equation 54; Equation 55; Equation 56; Equation 57 | 20 | 中点附近的输入展开；这些辅助推导不自动提供 MCMC 不变性。 |

## 10 实验与证据链

| 实验 | 检验主张 | 数据/基线/预算 | 结果 | 支持结论 | 不支持的更强结论 | 来源 |
|---|---|---|---|---|---|---|
| 合成 GRU | 并行序列执行速度 | 低状态维、长序列、V100/A100 等 | 部分极端配置前向约 516 倍，前向+反向约 1000 倍 | 特定神经序列任务可很快 | 不能写成 MCMC 获得 1000 倍 | [Paper: PDF p. 6, Figure 2; PDF p. 26, Table 4] |
| 训练任务 | 端到端训练收益 | Hamiltonian NN、Eigenworms、CIFAR | 部分训练加速，性能不全面占优 | 展示训练可用性 | 没有后验分布精度证据 | [Paper: PDF p. 8, Figure 4; PDF p. 8, Table 1; PDF p. 9, Table 2] |

图表清单（先于卡片起草核对）：

| 证据 | PDF 物理页 | 论证作用 |
|---|---|---|
| Figure 1; Figure 2; Figure 3; Figure 4 | 1; 6; 7; 8 | 执行结构、计时、数值轨迹差、训练 |
| Table 1; Table 2 | 8; 9 | Eigenworms 与 CIFAR 性能 |
| Figure 5; Figure 6; Figure 7; Figure 8 | 23; 25; 25; 27 | 结构、容差、硬件、同内存预算比较 |
| Table 3; Table 4; Table 5; Table 6 | 21; 26; 26; 27 | 插值/完整计时/瓶颈/内存；不隐去负收益与 OOM |

## 11 正确理解

这是方法祖先，应在综述中明确标成“非 MCMC”。不同状态维度、批量和内存限制导致收益反转；论文 Appendix D–F 包含硬件、内存及 OOM 案例。

有界结论：DEER 将非线性序列求值转成 Newton 迭代和并行线性求解，在部分 RNN/ODE 配置上获得大幅加速；论文并未直接完成 MCMC 算法或后验保证。

## 12 作者明确承认的限制

| 限制 | 具体表现 | 作者方向/处理 | 来源 |
|---|---|---|---|
| 初值与非线性 | 远离根时可能收敛缓慢或失败 | 更稳健求解 | [Paper: PDF p. 6, §3.6] |
| 内存 | 状态维度增大产生平方存储和矩阵乘成本 | 利用结构、分组等 | [Paper: PDF p. 5, §3.5] |

## 13 批判分析

[Analysis] 在移植到 MH 前需处理不可微接受分支；本文的光滑局部 Newton 保证不足以支持一般 MH。可用相同随机数对照原链并检查接受分支分歧。

这里是 [Analysis]，不回填为作者自述。尚未执行文中提出的检验。

## 14 知识候选

### Agent-derived knowledge candidates

[Analysis] 并行线性求解是通用数值部件，采样正确性仍属于后续应用的证明责任。

## 15 与已有知识的联系

[External] [Zoltowski 2025](../zoltowski2025/paper-card.md)解决部分 MCMC 适配；[Gonzalez 的 2025/2026 工作](../../新增文献核查.md)进一步研究可预测性与统一框架。

## 16 研究候选

### Agent-derived research candidates

Not applicable：本卡不单独宣称新的算法创意。跨论文形成的候选问题及其前作、验证方式、失败条件见[成果与缺口报告](../../截至2026-10-02的成果与缺口.md)。
