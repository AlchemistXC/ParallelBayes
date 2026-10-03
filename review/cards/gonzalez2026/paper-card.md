# A Unifying Framework for Parallelizing Sequential Models with Linear Dynamical Systems｜论文精读卡

> Source coverage: Full paper
> Extraction confidence: Mixed
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Paper-only
> Card completeness: Complete relative to supplied source

本地全文含附录；正文逐节核对、全部图表入目录，附录核对证明用途、实验参数、数值限制与扩展算法；不宣称算法复现或独立重证。

## 01 基本信息

[Paper] **A Unifying Framework for Parallelizing Sequential Models with Linear Dynamical Systems**。作者：Gonzalez, Xavier; Buchanan, E. Kelly; Lee, Hyun Dong; Liu, Jerry Weihong; Wang, Ke Alexander; Zoltowski, David M.; Kozachkov, Leo; Ré, Christopher; Linderman, Scott W.。发表：Transactions on Machine Learning Research，2026。标识：2509.21716。

机构：Stanford 多个院系及Wu Tsai Neurosciences Institute，Brown School of Engineering/Carney Institute。TMLR 2026正式发表；本地arXiv 2509.21716v2，2026-04-03，37页，9位作者。代码 github.com/lindermanlab/parallelizing_with_lds，未运行；研究群字、GRU、Gaussian混合势Langevin。[Paper: PDF p. 1, author block] [Paper: PDF p. 10, code link]

阅读日期：2026-10-03。来源：[本地 PDF](../../../references/updates/gonzalez2026.pdf)；[题录/发表页](https://openreview.net/forum?id=fw6GgAIGur)。类型：methods；关键词：LDS；Jacobian近似；Newton；Picard；Jacobi；scan。本综述位置：综述的统一数值分析语言，并划定已有统一工作的范围。。

## 02 一句话概括

[Paper] 将Newton、对角quasi-Newton、Picard、Jacobi统一为反复求解LDS的不同Jacobian近似，用近似误差与LDS稳定性解释各自适用场景，实例显示不存在总是最快的方法。[Paper: PDF p. 4, Table 1] [Paper: PDF p. 8, Proposition 3]

## 03 研究问题

[Paper] 表面不同的非线性序列并行法为何在某些系统有效、另一些系统缓慢？能否用同一更新式连接方法、迭代率与每轮代价？[Paper: PDF p. 2, Introduction]

## 04 研究背景与发展路径

[Paper] 作者明确承认经典数值分析已连接Picard和Newton，也讨论parareal；本文的定位是机器学习序列、LDS与并行scan的共同框架。不能将本综述包装为首次统一这些算法。[Paper: PDF p. 13, §5] [Paper: PDF p. 14, related work]

## 05 论文指出的核心痛点

| 痛点 | 表现 | 作者解释 | 证据 |
|---|---|---|---|
| 方法术语分散 | 各领域算法难比较 | 不同记号掩盖同一线性化结构 | [Paper: PDF p. 2, Introduction] |
| 高阶方法昂贵 | 完整Jacobian内存/矩阵乘开销 | 每轮更准未必总时间短 | [Paper: PDF p. 5, §2.1–2.2] |
| 粗近似也会失败 | Picard在GRU、Jacobi在Langevin慢 | 与真实Jacobian不相似 | [Paper: PDF p. 12, Figure 3] [Paper: PDF p. 13, Figure 4] |

## 06 核心思想

[Paper] 以近似矩阵Ã替代动力学Jacobian，保留真转移的残差，再用scan求解该轮的仿射递推。[Analysis] 合理近似要同时兼顾保真、稳定与组合成本，而不是只追求更少迭代。[Paper: PDF p. 3, Equation 4]

## 07 方法总览

[Paper] 输入确定性递推f_t、初值、整段猜测和容差；随机递推先固定噪声。并行计算真转移与Ã→scan/前缀和/map→误差检查→迭代。Newton用J_f，对角近似用diag J_f，Picard用I，Jacobi用0。按因果结构至多T轮的精确算术恢复不保证实用的亚线性总时间。[Paper: PDF p. 4, Algorithm 1 and Table 1]

## 08 核心模块拆解

| 模块 | 功能/必要性 | 输入→输出 | 证据 | 移除影响 |
|---|---|---|---|---|
| 真转移残差 | 保留同一固定点 | x→f(x)−x | [Paper: PDF p. 7, Equation 10] | [Analysis] 随意近似原转移可能改变目标轨迹 |
| Ã选择 | 控制每轮成本与收敛 | J/结构→近似矩阵 | [Paper: PDF p. 4, Table 1] | 有四方法实测对照，未证明某个近似普适 |
| 仿射scan | 利用组合封闭性 | Ã,b→全轨迹线性解 | [Paper: PDF p. 3, Figure 1] | 串行求解失去该并行深度 |
| 容差/窗口 | 限制迭代与内存 | 误差/显存→停止策略 | [Paper: PDF p. 33, Appendix E.5] | [Analysis] 窗口与截断改变成本，截断还需误差评估 |

## 09 关键公式与符号

[Paper] x_t^(k+1)=f_t(x_(t−1)^k)+Ã_t(x_(t−1)^(k+1)−x_(t−1)^k)，即Equation4的换指标写法。Ã=J、diag J、I、0依次给四方法。[Paper: PDF p. 3, Equation 4]

||e_(k+1)||≤||J̃⁻¹||[||J̃−J||·||e_k||+(L/2)||e_k||²]。e为整段轨迹误差，L是动力学Jacobian的Lipschitz常数。第一项衡量近似，第二项是Newton非线性余项，逆矩阵范数体现稳定性。它是上界而非所有实例的精确收敛率。[Paper: PDF p. 8, Proposition 3]

完整scan工作O(TD³)、内存O(TD²)；对角scan可为O(TD)，但获取对角的自动微分成本另计。作者采用随机估计对角，不能说任意模型免费得到精确对角。[Paper: PDF p. 5, §2.2]

## 10 实验设计与证据链

[Paper] JAX/Equinox，H100 80GB；主文三类任务10种子，batch16，每种子5次计时均值后取中位数；终止残差目标≤5×10⁻⁴。未做后验覆盖率/ESS验证。[Paper: PDF p. 28, Appendix E] [Paper: PDF p. 29, E.1–E.4]

| 实验 | 主张 | 条件 | 结果 | 支持／不支持 | 来源 |
|---|---|---|---|---|---|
| S5 | 精确Jacobian值得其成本 | 本质线性，D≤群大小 | Newton一轮；其他随T增长 | 结构选择有效；不是一般非线性一步解 | [Paper: PDF p. 11, Figure 2] |
| GRU | I近似可能失配 | 随机初始化、小状态维度 | Picard接近T轮，其他快 | 该GRU设定；不是所有RNN | [Paper: PDF p. 12, Figure 3] |
| Langevin | 接近I时Picard适合 | 小步长10⁻⁵、D32–256、混合势 | Jacobi慢；完整Newton部分OOM | 路径计算收益；非后验抽样精度证明 | [Paper: PDF p. 13, Figure 4] |
| 步长改变 | 方法排序可变 | 10⁻⁵至10⁻³ | Picard相对Newton优势下降 | 不能脱离步长比较 | [Paper: PDF p. 32, Figure 10] |

### 图表、公式及附录证据目录


正文 p.1–15逐节，附录B–F核对scan、误差界解释、全部补充图表与实验协议；未独立重证每条引理或运行代码。

| 证据 | PDF页 | 作用 |
|---|---|---|
| Figure 1; Table 1 | 3–4 | 并行scan及四方法近似矩阵/深度对照 |
| Figure 2 | 11 | S5群字问题，完整Newton一步解线性系统 |
| Figure 3 | 12 | GRU：Picard的单位矩阵近似不合适 |
| Figure 4 | 13 | Langevin：Jacobi零近似不合适；完整Newton有OOM |
| Figure 5; Figure 6 | 21; 23 | scan与LGSSM结构示意 |
| Table 2; Table 3 | 24 | up-sweep/down-sweep，不是性能benchmark |
| Figure 7 | 27 | 标量LDS中Picard/Jacobi误差轨迹，说明上界不完全预测 |
| Figure 8 | 30 | GRU近似误差、逆Jacobian与收敛的对应 |
| Figure 9; Figure 10 | 31–32 | 混合成分数、Langevin步长改变方法排序 |
| Figure 11 | 34 | parallel-chord名词的几何解释，区别于硬件并行 |
| Equation 0 | 3 | 误识别：初始猜测的上标(0)，不是独立公式 |
| Equation 1; Equation 2; Equation 3; Equation 4 | 2–3 | 递推、固定点及统一LDS更新 |
| Equation 5; Equation 6; Equation 7; Equation 8; Equation 9 | 4–7 | Newton、对角近似、ODE/Picard、Jacobi |
| Equation 10; Equation 11; Equation 12; Equation 13; Equation 14 | 7–8 | 残差、块Jacobian、一般更新与误差上界 |
| Equation 15; Equation 16 | 9 | 线性项控制量与逆Jacobian的乘积结构 |
| Equation 17; Equation 18 | 14; 22 | 一般迭代与结合操作 |
| Equation 19; Equation 20 | 25 | 近似块Jacobian及Picard特例 |
| Equation 21; Equation 22; Equation 23; Equation 24; Equation 25 | 33–34 | 与经典parallel-chord框架的对应 |
| Equation 26; Equation 27; Equation 28; Equation 29 | 35–36 | 经典渐近迭代分析与有限T精确恢复的区别 |

核心证据链：近似矩阵选择 → LDS稳定性及近似误差 → 迭代轮数 → 每轮成本/内存 → 实际时间；没有最后一步“后验质量”的实验认证。附录F.2已经包含scale-ELK、clip-ELK，不能把简单稳定化/裁剪重新宣称空白。


## 11 结论的正确解释

[Analysis] 统一的是递推求解机制，非MCMC统计保证。固定随机数轨迹相同、有限容差误差小和输出已接近π是不同主张；本论文主要提供前两层的工具。总轮数必须乘每轮成本，并记录OOM、精度和初始化。

## 12 作者明确承认的局限

| 作者局限 | 表现 | 方向/处理 | 来源 |
|---|---|---|---|
| 上界预测不完整 | 有限T恢复与渐近率语言有张力 | 案例和进一步误差分析 | [Paper: PDF p. 9, Proposition 3 discussion] |
| 显存与有限精度 | 稠密矩阵、长序列可能溢出 | 分窗、截断、监控数值发散 | [Paper: PDF p. 33, E.5] |
| 结构近似范围未穷尽 | 对角只是一个特例 | 缩放I、置换、分块等组合封闭族 | [Paper: PDF p. 15, Future directions] |

## 13 批判性分析

| [Analysis] 观察 | 问题 | 意义 | 检验 | 依据 |
|---|---|---|---|---|
| 残差阈值不按TD归一 | 不同T/D的相同阈值未必相同相对精度 | 速度排序与停止标准有关 | 同时报告每步残差和路径误差 | [Paper: PDF p. 29, tolerance] |
| 随机对角已用在基准 | 实际Ã不是精确diag | 收敛受估计噪声影响 | 区分精确/随机对角，在同预算比较 | [Paper: PDF p. 28, Appendix E] |
| 稳定化已有方案 | clip-ELK已写入附录 | 避免重复提出“新方法” | 任何候选须与scale/clip-ELK及窗口对比 | [Paper: PDF p. 37, F.2] |

## 14 学到的知识

### Agent-derived knowledge candidates

[Analysis] 选择近似的代价函数应是“每轮成本×轮数”，再加统计误差和内存约束；组合封闭性让结构矩阵真正适用于scan。

## 15 与既有知识的联系

[Analysis] 与Zoltowski共享MCMC中的随机对角/分块应用，与可预测性论文共享稳定性解释。本文已统一数值框架，本综述的贡献应转向统计保证和推断成本的证据整合。

## 16 研究创意

### Agent-derived research candidates

Not applicable。此卡只记录前作已覆盖的结构近似、稳定化和选择问题，防止将其重命名为原创。

