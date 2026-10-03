# Parallelizing MCMC Across the Sequence Length：全文核查卡

> Source coverage: Full paper
> Extraction confidence: Mixed (text reliable; equations/tables checked against PDF where material)
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Targeted external check
> Card completeness: Complete relative to supplied source

输入边界：保存的全文及已提供补充；按正文、附录、图表与结论进行核对，关键推导抽查。**不代表逐行数学重证、全部引文核验或实验复现。** PDF 页码均从文件第一页起计。

## 01 基本信息

- 作者：Zoltowski, David M.; Wu, Skyler; Gonzalez, Xavier; Kozachkov, Leo; Linderman, Scott W.。单位以 [PDF 首页](../../../references/papers/zoltowski2025.pdf)为准。
- 年份/载体：2025，Advances in Neural Information Processing Systems。
- 本地版本：arXiv v2，2025-12-02；NeurIPS 2025 对应稿；36 页。
- 标识与出版记录：[原始来源](https://proceedings.nips.cc/paper_files/paper/2025/hash/202886ee1c9ca735cb5bff3a00a69883-Abstract-Conference.html)；引用键 `zoltowski2025`。
- 类型：methods；领域：贝叶斯计算/并行采样相关方法；关键词：Newton 时间并行。
- 软件/数据：以论文实验节和来源包中的链接为准；本轮未运行。MEADS 已另存官方软件。
- 阅读日期：2026-10-02；用途：时间并行综述主线：DEER、quasi-DEER、HMC 与提前停止。

## 02 一句话概括

固定随机数后，将 MCMC 轨迹写成非线性方程，以 Newton/quasi-DEER 和并行扫描求解；在选定模型上降低运行时间，但快速收敛与统计误差保证仍依条件。

## 03 研究问题

能否同时求出一段 MCMC 状态，而不逐个时间步执行转移？

## 04 背景与发展路线

[External] [Lim 2024](../lim2024/paper-card.md)提供 DEER 方法来源；本文将其适配 Gibbs、MALA、HMC。2026 年 LDS 统一框架已进一步解释这些方法，见[新增核查](../../新增文献核查.md)。

## 05 痛点

| 痛点与表现 | 原因/作者解释 | 证据 |
|---|---|---|
| 单条长链的递推依赖不能靠普通 vmap 消除；完整 Jacobian 又使并行扫描成本高。[Paper: PDF p. 3, §2; PDF p. 4, §3] | 见同列原文；不把机制解释视为普遍已证因果 | 原文定位随主张列出 |

## 06 核心思想

固定噪声使转移成为确定性递推；线性化后利用仿射映射复合的结合律。[Analysis] 改变的是计算顺序，恢复轨迹本身不保证混合。

## 07 方法概览

输入初值、每步固定随机数及转移；猜整段轨迹→计算真转移和近似 Jacobian→并行线性求解→迭代至容差。支持对角/分块近似、Hutchinson 随机对角、滑动窗口和早停。MH 的前向接受决策保留，Jacobian 使用 stop-gradient 等处理。[Paper: PDF p. 4, §3; PDF p. 5, §3; PDF p. 23, Algorithm 1]

## 08 模块拆解

| 模块 | 功能 | 必要性 | 输入→输出 | 来源 | 移除影响（实验或分析） |
|---|---|---|---|---|---|
| 固定随机数 | 定义待恢复的同一轨迹 | 迭代需稳定对象 | 种子→确定转移 | [Paper: PDF p. 3, §2] | 每次重抽噪声就改变待求解问题；分析 |
| quasi-DEER | 降低 Jacobian 成本 | 稠密矩阵扫描昂贵 | JVP/对角→线性迭代 | [Paper: PDF p. 4, §3] | 完整 Newton 内存 O(TD²)，工作 O(TD³) |
| 窗口与早停 | 控制内存和时间 | 长轨迹资源受限 | 轨迹段→近似/收敛输出 | [Paper: PDF p. 5, §3.4; PDF p. 9, §5.5 and Figure 6] | 早停改变输出；文中有经验消融 |

## 09 关键公式与符号

$r_t(x)=x_t-f_t(x_{t-1};u_t)$；Newton 线性化成 $x_t^{k+1}=A_t^k x_{t-1}^{k+1}+b_t^k$，$A$ 为 Jacobian 或近似，$b=f-Ax$。仿射复合可 O(log T) 深度扫描，但还要乘求解轮数，并承担总工作/存储。[Paper: PDF p. 2, Equations 1–2; PDF p. 3, Equations 3–4; PDF p. 23, Appendix A]

以下人工分组目录同时记录自动抽取的误报；编号覆盖不等于逐行证明认证。

| 公式组/抽取标记 | PDF 物理页 | 作用与边界 |
|---|---|---|
| Equation 0 | 23 | 自动识别误报：Algorithm 1 初值下标，不是独立编号公式。 |
| Equation 1; Equation 2 | 2 | 递推残差与块双对角 Jacobian，定义 Newton 要解的问题。 |
| Equation 3; Equation 4 | 3 | 线性化递推及对角近似，决定 scan 的计算/内存成本。 |
| Equation 5; Equation 6; Equation 7 | 3 | Gibbs 条件分布与 Langevin 更新，说明可重参数化的入口。 |
| Equation 8; Equation 9 | 4 | HMC 积分更新及 Jacobian；固定积分步数。 |
| Equation 10; Equation 11 | 5 | 随机对角估计与旋转，已属于本文方法，不能另列为新想法。 |
| Equation 12; Equation 13 | 23 | 附录 HMC 块 Jacobian，辅助实现。 |
| Equation 14; Equation 15; Equation 16; Equation 17; Equation 18; Equation 19 | 24 | 块对角、随机估计与复合映射递推；用于控制近似成本。 |
| Equation 20; Equation 21; Equation 22; Equation 23; Equation 24; Equation 25 | 26 | Gibbs 实验的先验、观测及条件分布，限定实验模型。 |

## 10 实验与证据链

| 实验 | 检验主张 | 数据/基线/预算 | 结果 | 支持结论 | 不支持的更强结论 | 来源 |
|---|---|---|---|---|---|---|
| MALA 德国信用 | 时间并行能否缩短计时 | 小批量、固定步长约 80% 接受率；编译后计时 | 部分配置 20–30 倍；32 链可更慢或内存不足 | 收益依赖链数和资源 | 不支持所有后验统一 30 倍 | [Paper: PDF p. 7, Figure 3] |
| HMC 两种并行轴 | 链转移与 leapfrog 轴比较 | 4 链，不同轨迹长度 | 最佳方案依 leapfrog 长度变化 | 已有局部资源分配证据 | 不是尚无人比较并行轴 | [Paper: PDF p. 9, Figure 5] |
| 随机对角与早停 | 低成本近似是否可用 | MMD 对有限 NUTS 参考样本 | 可明显提速，部分早停 MMD 接近 | 经验准确性证据 | MMD 接近不等于已证明 TV 或无偏 | [Paper: PDF p. 9, Figure 6; PDF p. 26, Appendix B] |

图表清单（先于卡片起草核对）：

| 证据 | PDF 物理页 | 论证作用 |
|---|---|---|
| Figure 1 | 2 | Rosenbrock 轨迹求解示意 |
| Figure 2 | 6 | Gibbs 时间与维度/批量比较 |
| Figure 3; Figure 4 | 7; 8 | MALA 计时、内存与 MMD—时间 |
| Figure 5; Figure 6; Figure 7 | 9; 9; 10 | HMC 两个并行轴、随机对角/早停、IMDB 扩展 |
| Figure 8; Figure 9 | 27; 29 | Gibbs 后验、混合高斯补充 |
| Figure 10; Figure 11; Figure 12; Figure 13; Figure 14; Figure 15; Figure 16; Figure 17; Figure 18; Figure 19 | 30–36 | 补充速度、迭代、MMD、轨迹差和 IRT；不全部支持正收益 |

## 11 正确理解

一轮 O(log T) 不等于总算法 O(log T)。完整收敛与有限容差/最大轮数终止必须分开；轨迹误差、MH 分支变化和后验函数误差也不是同一指标。计时主要排除 JIT，部分长序列 Gibbs CPU 结果为外推。[Paper: PDF p. 25, Appendix B; PDF p. 27, Appendix B]

有界结论：固定随机数后，将 MCMC 轨迹写成非线性方程，以 Newton/quasi-DEER 和并行扫描求解；在选定模型上降低运行时间，但快速收敛与统计误差保证仍依条件。

## 12 作者明确承认的限制

| 限制 | 具体表现 | 作者方向/处理 | 来源 |
|---|---|---|---|
| 几何与数值稳定 | 强非线性、步长和 Jacobian 影响迭代；主要实验单峰 | 阻尼和更广泛模型 | [Paper: PDF p. 10, §6] |
| 动态 NUTS | 本文 HMC 配置固定积分步数 | 研究与 NUTS 的结合 | [Paper: PDF p. 10, §6] |

## 13 批判分析

[Analysis] 应把早停误差与原链 MCSE 同时报告，并包含 OOM、非收敛和 JIT 成本。复核原图确认 Appendix A Algorithm 2 将能量接受率写成 H_L/H_0，且返回变量未定义；标准形式应为 min(1, exp(H_0-H_L))。这属于伪代码问题，未据此判断代码实现错误。[Paper: PDF p. 23, Algorithm 2]

这里是 [Analysis]，不回填为作者自述。尚未执行文中提出的检验。

## 14 知识候选

### Agent-derived knowledge candidates

[Analysis] 容差控制的是数值求解，不自动成为统计正确性证书；随机对角、窗口和早停均是已有工作。

## 15 与已有知识的联系

[External] [Grazzi 2026](../grazzi2026/paper-card.md)对不光滑 MH 使用匹配前缀；[Gonzalez 2026](../../新增文献核查.md#gonzalez2026)已统一 LDS 解释。

## 16 研究候选

### Agent-derived research candidates

Not applicable：本卡不单独宣称新的算法创意。跨论文形成的候选问题及其前作、验证方式、失败条件见[成果与缺口报告](../../截至2026-10-02的成果与缺口.md)。
