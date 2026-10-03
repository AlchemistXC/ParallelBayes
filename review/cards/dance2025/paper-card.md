# Efficiently Vectorized MCMC on Modern Accelerators｜论文精读卡

> Source coverage: Full paper
> Extraction confidence: Mixed
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Paper-only
> Card completeness: Complete relative to supplied source

补读正文及附录 A–B，包括全部图表、成本证明的条件和算法构造。自动图表识别漏报，已人工补目录。未认证每条代数推导，未执行程序。

## 01 基本信息

[Paper] **Efficiently Vectorized MCMC on Modern Accelerators**。作者：Dance, Hugh; Glaser, Pierre; Orbanz, Peter; Adams, Ryan P.。发表：Proceedings of the 42nd International Conference on Machine Learning，2025。标识：2503.17405。

机构：UCL Gatsby Unit、Princeton Computer Science。正式版 ICML 2025，PMLR 267:12436–12458，本地23页。代码 github.com/hwdance/jax-fsm-mcmc；未复现。任务含合成目标、UCI Real Estate、PosteriorDB 与四个复杂几何模型。[Paper: PDF p. 1, author block] [Paper: PDF p. 7, §7]

阅读日期：2026-10-03。来源：[本地 PDF](../../../references/updates/dance2025.pdf)；[题录/发表页](https://proceedings.mlr.press/v267/dance25a.html)。类型：methods；关键词：FSM；自动向量化；动态控制流；多链；ESS/s。本综述位置：动态 NUTS 的硬件执行前作及多链对照。。

## 02 一句话概括

[Paper] 将含可变循环的单链采样程序转成有限状态机后再向量化，减少每个样本完成时的链间等待，在若干任务提高 ESS/s，但收益受全部分支执行成本限制。[Paper: PDF p. 5, §4] [Paper: PDF p. 9, Table 1]

## 03 研究问题

[Paper] vmap 对含 while 的采样核会在每次样本处等待最慢链。能否保持各链的采样计算语义，却让链在不同内部步骤上继续推进，从而降低同步成本？[Paper: PDF p. 2, §2]

## 04 研究背景与发展路径

[Paper] 作者从递归 HMC 的框架兼容实现、批处理递归程序，发展到 while-loop-free 代码块的 FSM 表示。其“首次”归属是作者陈述，未在本卡独立检索证实。[Paper: PDF p. 7, §6]

## 05 论文指出的核心痛点

| 痛点 | 表现 | 作者解释 | 证据 |
|---|---|---|---|
| 同步等待 | 每个样本由最慢链定成本 | 循环长度分布有长右尾 | [Paper: PDF p. 3, Figure 1] |
| FSM也有开销 | 向量化switch执行全部分支 | 掩码丢弃不代表免计算 | [Paper: PDF p. 5, §4] |
| 小状态过多 | 状态调度、重复log-density成本高 | 并非拆得越细越好 | [Paper: PDF p. 6, §5] |

## 06 核心思想

[Paper] 表面做法是代码块改写；关键是将“每次样本同步”转成“所有链取得足够样本后同步”，并用 bundling 与昂贵函数 amortization 抵销状态机开销。[Analysis] 并行性能可由程序的完成时间分布决定，而不改变目标核。[Paper: PDF p. 5, §3.2]

## 07 方法总览

[Paper] 输入可转换的 MCMC 程序、初值、随机状态和每链目标样本数；输出通过 isSample 标志筛出的完整样本。代码块→FSM图→step与状态转移→批量运行→完成样本筛选。原始核的正确性是前提；成本定理另要求有界内部迭代次数、平稳联合链及谱隙。没有额外训练步骤；TESS 使用的预训练flow属基线组件。[Paper: PDF p. 4, Algorithms 2–3] [Paper: PDF p. 12, Appendix A]

## 08 核心模块拆解

| 模块 | 功能/必要性 | 输入→输出 | 证据 | 移除后果 |
|---|---|---|---|---|
| FSM转换 | 保留循环内进度 | 程序→图和局部状态 | [Paper: PDF p. 4, §3.1] | [Analysis] 回到逐样本同步 |
| 完成标志 | 不把中间状态当样本 | step→isSample | [Paper: PDF p. 4, Algorithm 3] | [Analysis] 样本语义会变，不只是速度变 |
| bundling | 合并便宜连续状态 | 多step→复合step | [Paper: PDF p. 8, Figure 6] | 已测：延迟拒绝例失去约3倍效率收益 |
| amortization | 减少重复昂贵函数调用 | 状态→一次g调用 | [Paper: PDF p. 8, Figure 5] | 已测：GP例损失约2倍相对性能 |

## 09 关键公式与符号

[Paper] 若 N_ij 为第j链第i样本的内部循环次数，则忽略开销时 C₀∝Σ_i max_j N_ij，理想去同步 C*∝max_jΣ_i N_ij。将max移到sum外解释潜在收益，不能忽略实际调度成本。[Paper: PDF p. 2, Equations 1–2]

完整效率 E(m)=[c_¬k+c_k E max_jN_j]/[α(c_¬k+c_k)(K−1+EN₁)]；R(m)=E max_jN_j/EN₁ 只是上界。K为状态数，α控制成本压缩，c为各块成本。即使R大，E也可能小于1。[Paper: PDF p. 6, Equations 12–13]

## 10 实验设计与证据链

[Paper] JAX与BlackJAX原语、A100，合成实验10种子、混合Gaussian5种子；不同实验的采样/预热预算明确区分。附录只明确若干廉价任务扣除编译时间，不能推称所有计时口径完全相同。[Paper: PDF p. 7, §7] [Paper: PDF p. 22, Compilation]

| 实验 | 主张 | 比较与条件 | 结果 | 支持／不支持 | 来源 |
|---|---|---|---|---|---|
| GP椭圆切片 | 缓解逐样本等待 | 1024链、每链10000样本，标准/完整FSM | 超过半小时→约10分钟 | 支持该硬件任务；不是混合速度提高 | [Paper: PDF p. 8, Figure 5] |
| 四个实际模型 | NUTS/TESS能否获益 | 128链×1000样本，400预热 | NUTS ESS/s比1.5、3.5、1.2、0.8 | 3/4改善；不是所有模型加速 | [Paper: PDF p. 9, Table 1] |
| PosteriorDB补充 | 廉价目标影响收益 | 同上预算 | GPR3.15、Soil2.43、Pilots0.91 | 计算昂贵程度影响边际收益 | [Paper: PDF p. 23, Table 2] |

### 图表、公式及附录证据目录


正文 p.1–9、附录 A–B（p.12–23）均纳入；自动脚本漏检带句点图表题，以下人工补足。未复现程序。

| 证据 | 页 | 论证作用 |
|---|---|---|
| Figure 1 | 3 | 单次循环与链平均循环次数的分布，说明同步浪费 |
| Figure 2; Figure 3 | 4–5 | 单循环与四类采样器的 FSM 结构 |
| Figure 4 | 6 | 迭代次数偏度改变理论效率上限 |
| Figure 5; Figure 6 | 8 | GP 椭圆切片的时间/ESS；延迟拒绝 bundling 消融 |
| Figure 7; Table 1 | 9 | 100 维混合 Gaussian；四类实际模型 ESS/s 比 |
| Figure 8; Figure 9; Figure 10; Figure 11 | 17–21 | 语法树、粗化、含空节点及折叠后 FSM；不是额外采样实验 |
| Figure 12; Figure 13; Table 2 | 22–23 | 数据规模、likelihood 成本；GPR/Soil/Pilots 的补充 ESS/s |
| Equation 1; Equation 2; Equation 3; Equation 4; Equation 5 | 2–3 | sum-of-max 与 max-of-sum 的成本差 |
| Equation 6; Equation 7; Equation 8; Equation 9 | 5 | 含各状态执行成本的有限样本模型及集中界 |
| Equation 10; Equation 11; Equation 12; Equation 13 | 6 | 长程成本、效率及上界 R(m) |
| Equation 14; Equation 15; Equation 16; Equation 17; Equation 18; Equation 19 | 12 | 有界循环次数、平稳性与谱隙条件下的集中不等式推导 |
| Equation 20; Equation 21; Equation 22; Equation 23; Equation 24; Equation 25; Equation 26 | 13 | FSM 成本的 union bound 推导；不用于证明原采样核混合更快 |
| Equation 27; Equation 28; Equation 29; Equation 30; Equation 31; Equation 32; Equation 33 | 13–14 | 相对效率上界及紧性 |
| Equation 34 | 16 | 顺序循环 FSM 拼接规则 |

正文 Algorithms 1–5：串行接口、step、完成样本筛选、bundling、amortization；附录 Algorithms 6–13：向量化、椭圆切片、自动语法转换。p.22 明确 Python 外层循环与分块 JIT、部分实验扣除编译时间，不能一概写成“所有结果均不含编译”。p.8 图注 n=411 与正文 n=414 不一致，卡片保留歧义。


## 11 结论的正确解释

[Analysis] 这是多链控制流与向量化执行改造，不是跨同一条链未来时间步的并行求解。较高ESS/s不自动验证多峰探索；文中MALA例就说明速度与分布覆盖应并看。FSM保留采样语义的目标与其理论成本模型是两层结论。[Paper: PDF p. 9, §7.3]

## 12 作者明确承认的局限

| 作者明确的限制 | 表现 | 作者对应做法/方向 | 来源 |
|---|---|---|---|
| 分支掩码仍付成本 | 每step可能执行全部状态函数 | bundling和amortization | [Paper: PDF p. 5, §4] |
| 便宜密度收益较小 | 状态调度占比高，Pilots未加速 | 讨论更长运行可平衡资源，未保证一定获益 | [Paper: PDF p. 23, Table 2 discussion] |
| 一般程序转换 caveats | 空状态自环、不可能转移 | 识别不终止状态、删除不可能边 | [Paper: PDF p. 20, Remarks B.1–B.2] |

## 13 批判性分析

| [Analysis] 观察 | 潜在问题 | 为何重要 | 检验方式 | 依据 |
|---|---|---|---|---|
| 比较包含多个成本口径 | JIT与CPU搬运在不同任务中的占比 | 小任务的全流程收益可能更小 | 统一报告编译、预热、采样、转存时间 | [Paper: PDF p. 22, Runtime/Compilation] |
| GP样本量不一致 | Figure5写411而§7.2写414 | 复现数据预处理需要澄清 | 查固定版本代码的删行/缺失处理；本轮未据此任选一个 | [Paper: PDF p. 8, Figure 5 and §7.2] |
| NUTS虽加速仍可能弱于其他核 | 表1标准NUTS基数小 | 只给倍数会掩盖实际推断效率 | 同表报告绝对ESS/s与偏差/覆盖 | [Paper: PDF p. 9, Table 1] |

## 14 学到的知识

### Agent-derived knowledge candidates

[Analysis] 用内部工作量的尾部分布预测同步浪费；把采样核、执行程序和硬件成本分层比较；报告基线绝对效率，以免大倍数来自低基数。

## 15 与既有知识的联系

[Analysis] 本项目NUTS与MEADS材料给出动态路径和多链调参背景；FSM解决其执行问题，和Zoltowski的时间递推求解可形成不同并行轴的比较。作者也引用这两类硬件工作，但本卡不独立宣称可直接组合仍保持所有性质。[Paper: PDF p. 7, §6]

## 16 研究创意

### Agent-derived research candidates

Not applicable。本轮补齐证据与条件，不额外提出逐篇创新主张；综合候选保留在成果与缺口报告。

