# Reviewer 2

## Review setup

**Input scope** 冻结包中的完整中文专题叙述性综述《链内与时间并行 MCMC 统计保证、可并行性与推断成本》。以 `packet/manuscript.tex` 为逐项审查正文，并检查对应 PDF 的文件可读性。本文未报告新的实验。

**Assessment boundary** 只使用冻结包、`sources.json` 中允许的原始论文及其文本提取包，以及 nature-reviewer 技能规定的共同标准。重点是统计保证、数学陈述、数值误差到推断误差的逻辑和定量比较口径。未接触其他审查报告、项目笔记或实时主稿。没有开展新文献检索、程序复现或硬件测试，亦未完成 PDF 的独立视觉版面审校。

**Shared manuscript claim summary** 不同链内与时间并行路线保持的统计性质不同，降低执行深度不等于降低达到后验精度目标的完整成本。综述尝试以保证类型、并行机制和推断成本连接已有成果，为方法选择和后续基准提供依据。

**Visible evidence base** 重点核对 Pozza 与 Zanella 的核比较及谱隙界，Grazzi 与 Zanella 的精确前缀和近似 Picard 分析，Anari 等与 Zhou 和 Sugiyama 的分布误差及查询复杂度，Newton 型 MCMC、现代硬件章、LAPS、FSM 和 PiX-MC 的相应定量摘录，以及核扰动文献。以下原文页码均为所提供 PDF 的页序，必要时同时注明定理或章节。

**Missing materials affecting confidence** Calderhead 2014 的全文不在包中，对其细节只作给定材料允许的有限判断。未核验所有文献的全部证明和实现。个别出处为预印本或早于正式出版的本地版本，应保持 `sources.json` 所列版本边界。没有原始计时数据，不能从表中点估计判断收益的稳定性。

## Overall assessment

稿件的核心区分是成立且有价值的。它没有把路径恢复误写成混合保证，没有把多提议谱隙上界扩张为所有并行 MCMC 的限制，也没有将提前停止或重建质量直接当作后验准确性的证明。式（6）与所给原文 Theorem 3 的尺度优化上界相符。式（11）至式（12）的递推在明确的一步总变差收缩及统一核误差条件下成立，且作者正确地把它限定为说明性推导。

主要不足不是缺少新算法或新定理，而是理论综合仍停留在较抽象的条件提醒。第 4 节要求比较时保留精度、维度、条件数和查询宽度，表 2 却没有把这些量实际组织成可核对的比较，削弱了文章相对于分别阅读原文的增量价值。另有若干局部术语和计量口径需要补充。基于本次材料，没有识别到 Blocking Yes 的问题。

## Who would be interested in the results, and why

开发 MCMC 算法或实现的研究者，可以用本文区分改变转移核与改变执行方式。需要在 GPU 上完成贝叶斯估计的应用研究者，可以据此避免以原始样本吞吐或重建指标替代推断精度。数值分析与概率计算读者会关注轨迹求解误差如何进入统计保证。跨领域价值主要来自这些接口的解释，不依赖作者开展新的硬件基准。

## Major strengths

- 第 2.2 节明确区分轨迹等价、目标不变性和有限时间误差，且说明三者不是简单的包含层级。这是后续比较可信的基础。
- 第 3.3 节保留了可逆核类别、高斯边缘提议、强凸光滑性和维度条件。它对式（6）的适用范围比直接复述“对数加速限制”更准确。对应依据为 Pozza 与 Zanella，PDF 第 4 至 6 页，Theorem 1、Corollary 1 及 Theorem 3。
- 第 4.3 节区分求解器更快恢复尾部轨迹与统计上更快进入典型区域。该解释与 Grazzi 与 Zanella，PDF 第 9 页，Proposition 1 的结论一致。
- 表 3 保留负收益、硬件资源差异和计时阶段的限制。例如 FSM 的 0.8 倍结果与原文 Table 1 一致，PiX-MC 的约 3.1 倍配对执行收益也与原文 Figure 9 及其后讨论一致。
- 第 6 至 7 节明确区分同路径计时、不同核的误差比较及近似输出的附加责任。关于无统一排名、参考计算也可能混合不足、诊断不等于证明的措辞总体克制。

## Major Concerns

### R2-M1 理论比较没有落实文章提出的共同计量要求

**Severity** Major

**Blocking** No

**Axis** technical soundness；novelty-significance

**Claim pointer** 第 4.4 节称理解并行 Langevin 的结果需要同时保留误差、维度和条件数，并说明表 2 对主要保证作条件化归纳。第 7.2 节进一步以有限处理器理论作为资源选择的已有基础。见冻结 `manuscript.tex` 第 260 至 285 行、表 2，第 401 行。

**Evidence pointer** [Anari 等原文](/Users/haku/Workspace/ParallelBayes/references/papers/anari2024.pdf)，PDF 第 10 页，Theorem 13 与 Corollary 14，明确列出 LSI、初始 KL、score 误差、每轮查询数及总轮数。其第 12 页 Theorem 15 又区分欠阻尼路线的查询宽度。[Zhou 与 Sugiyama 原文](/Users/haku/Workspace/ParallelBayes/references/updates/zhou2025parallel.pdf)，PDF 第 6 至 7 页，Theorem 4.2、Corollary 4.3、Remarks 4.4 至 4.6，分别给出条件数、每轮查询宽度、空间代价及有限核心阈值。对应表 2 目前把两篇文献合并为“并行 Langevin”一行，只保留定性条件。

**Concern** 现有表格能告知读者不要如何外推，却不足以说明哪一项理论改善付出了什么代价。尤其是 Anari 的 LMC 与 ULMC 之间主要查询宽度不同，而 Zhou 的交错方案用更大的并行查询宽度换取更少轮数，有限处理器下的优势又取决于核心规模。把它们合并后，读者无法从本文判断“改进部分设定下的并行轮数”究竟对应何种误差目标、资源量级和条件数依赖。文中的免责说明不代替这一综合工作。

**Why it matters** 文章的贡献定位在统计保证与成本的连接。缺少至少一个实际完成的理论对照，会使这部分仍像原则性导读，降低综述的独立使用价值。但定性中心结论仍成立，因此该问题不构成全篇有效性的阻断。

**Resolution test** 在正文或补充表中选取少量代表性、可核对的定理，分别列出输出对象和误差度量、精度参数的约定、目标与初始化条件、并行轮数、每轮查询宽度、主要空间代价以及定理定位。至少把 LMC、ULMC 与交错方案分开，解释有限核心范围内哪些改善会消失。允许保留不同定理不能统一的部分，并明确缺项；无须推导新定理或开展新实验。

## Minor Comments

### R2-m1 “Fisher 信息”应明确为相对于目标的 Fisher 信息

**Severity** Minor

**Blocking** No

**Axis** statistical-rigor；writing-clarity

**Claim pointer / Affected element** 第 2.2 节、第 4.5 节及表 2 的 PiX-MC 行使用“Fisher 信息”“平均 Fisher 信息”或“时间平均 Fisher 信息”，没有给出相对目标及平均对象的定义。见冻结 `manuscript.tex` 第 127、280、293 行。

**Evidence pointer** [PiX-MC 原文](/Users/haku/Workspace/ParallelBayes/references/updates/wei2026.pdf)，PDF 第 11 页，Theorem 1 控制的是 \(T^{-1}\int_0^T\mathrm{FI}(\mu_t\Vert\pi)\,dt\)，随后以凸性讨论时间平均边缘分布。[Zhou 与 Sugiyama 原文](/Users/haku/Workspace/ParallelBayes/references/updates/zhou2025parallel.pdf)，PDF 第 2 页，明确将 FI 定义为相对 Fisher 信息。

**Issue and impact** 通常意义的参数 Fisher 信息与这里衡量分布偏离的相对 Fisher 信息是不同对象。“平均”也可能被理解为样本平均或末时刻误差。稿件已经正确提醒它不是末时刻总变差保证，补足定义即可让这一提醒更严谨。

**Resolution test / Required correction** 首次出现时定义 \(\mathrm{FI}(\mu\Vert\pi)=\mathbb E_\mu\|\nabla\log(\mathrm d\mu/\mathrm d\pi)\|^2\)，注明所需密度和正则性语境，并在 PiX-MC 行写明其时间积分对象。区分平均 FI、时间平均边缘分布和末时刻分布，不必扩展证明。

### R2-m2 总变差递推与后验函数 MSE 之间还需要一个明确边界

**Severity** Minor

**Blocking** No

**Axis** statistical-rigor

**Claim pointer / Affected element** 第 7.1 节以“从数值残差到后验函数误差”为题，给出式（11）至式（12）；第 2.3 节的统一比较目标则是式（5）中的后验函数 MSE。见冻结 `manuscript.tex` 第 140 至 161 行、第 372 至 397 行。

**Evidence pointer** 式（12）的左侧是第 \(n\) 步边缘分布差。[Mitrophanov 原文](/Users/haku/Workspace/ParallelBayes/references/background/mitrophanov2005.pdf)，PDF 第 3 至 4 页，Theorem 3.1 与 Corollary 3.1；[Alquier 等原文](/Users/haku/Workspace/ParallelBayes/references/background/alquier2016.pdf)，PDF 第 4 页，Theorems 2.1 与 2.2，区分总变差与加权范数控制。

**Issue and impact** 现有推导正确，也没有声称它已经是通用误差证书。但读者还需要知道，即使核模型和 \(\delta\) 已得到控制，式（12）也不是式（5）的 MSE 界。对于有界函数，可以控制相对于精确链的期望差；对常见的坐标均值和二阶矩，有限二阶矩本身不提供统一的总变差到函数误差常数。估计均值的方差还依赖轨迹相关性，不能只由单时刻边缘差推出。

**Resolution test / Required correction** 在式（12）后补充函数类别与控制对象。例如有界 \(f\) 的期望差可由 \(\operatorname{osc}(f)\delta/(1-\rho)\) 控制，同时说明这仍需叠加原链对目标的初始化偏差，且尚未控制样本平均的方差。对无界函数注明需要相应矩或加权范数条件。此处是澄清现有示例的范围，无须解决文中列为开放问题的一般误差证书。

### R2-m3 表 3 的部分计量口径仍不足以独立复核

**Severity** Minor

**Blocking** No

**Axis** figures-and-tables；reproducibility

**Claim pointer / Affected element** 表 3 的 Newton 型 MALA 行给出小批量约 20 至 30 倍，LAPS 行给出约 2 至 20 倍的每链梯度效率改善。见冻结 `manuscript.tex` 第 343、345 行。

**Evidence pointer** [Zoltowski 等原文](/Users/haku/Workspace/ParallelBayes/references/papers/zoltowski2025.pdf)，PDF 第 7 页，Figure 3 与 MALA 实验，报告 20 个随机种子和速度比的 90% 区间；第 9 页分别讨论提前停止与窗口化实验。[Robnik 与 Seljak 原文](/Users/haku/Workspace/ParallelBayes/references/updates/robnik2026.pdf)，PDF 第 6 页，式（12）至式（13）定义坐标二阶矩的标准化平方偏差；第 7 页 Table 1 使用最大值与 4096 链，第 8 页 Table 2 使用平均值与 256 链。

**Issue and impact** 数字本身可以定位，且稿件已经避免跨研究排名。但“偏差阈值”没有说明 LAPS 衡量的是坐标二阶矩的标准化平方偏差，而不是一般后验误差或 MSE。Newton 行又把两组配置压在一起，没有标明图号和小批量范围，也没有说明原文已有逐研究的不确定性信息。读者因而仍需重新寻找分母和误差定义。

**Resolution test / Required correction** 给相关行补充原始图表定位、对应函数与聚合方式，并区分 LAPS 两张表的最大偏差和平均偏差。对 Newton 行说明被摘录的比较配置及原文区间信息，或以注释指出点估计来自何处。无需合并不同研究的不确定区间，也无需在综述中重估原始数据。

### R2-m4 近似 Picard 的“路径失配”应具体到增量事件

**Severity** Minor

**Blocking** No

**Axis** statistical-rigor；claim-moderation

**Claim pointer / Affected element** 表 2 把近似 Online Picard 的主要控制对象写为“允许比例的路径失配”。第 7.1 节再概括为接受事件失配率。见冻结 `manuscript.tex` 第 277、397 行。

**Evidence pointer** [Grazzi 与 Zanella 原文](/Users/haku/Workspace/ParallelBayes/references/papers/grazzi2026.pdf)，PDF 第 11 页第 5 节的 \(A_\ell^{(j)}\) 使用相邻 Picard 迭代的增量不一致比例；第 12 页 Proposition 3 则控制给定条件下与精确递推增量不同的比例及其概率。同页明确说明不变分布误差的严格分析不在该文范围内。

**Issue and impact** 增量失配、整条轨迹中状态失配的比例，以及算法可观察的相邻迭代差异不是同一个量。一次增量错误可以影响其后的许多状态。表格末列已经正确否认它等于后验函数偏差，但“路径失配”仍使保证对象显得比原文更宽。

**Resolution test / Required correction** 改为具体的接受／增量事件失配，并用短注区分实际容忍规则与 Proposition 3 的概率控制。不要把该命题写成对自适应输出的通用逐次误差证书。保留现有关于不能直接推得后验偏差的限制即可。

## Technical failings that need to be addressed before the case is established

未发现 Blocking Yes 项。R2-M1 是应优先解决的综合深度问题。R2-m1 至 R2-m4 可通过定义、口径和原文定位的局部补充解决。它们不要求作者完成新的算法、实验或一般统计理论。

## Assessment against Nature-style criteria

**Originality** 按叙述性综述评价，合理的创新点是把统计保证、求解器和完整推断成本组织在一起。稿件主动承认统一框架与可预测性已有前作，定位诚实。R2-M1 完成后，这种综合贡献会更具体。

**Scientific importance** 问题对并行贝叶斯计算具有明确的重要性。稿件支持“应比较达到共同精度的成本”，尚不支持某一方法在广泛任务上的优越性；作者总体已保持这一边界。

**Interdisciplinary readership** 对数值计算、统计推断和计算成像有交叉价值。一般科学读者仍需要对查询复杂度、相对 Fisher 信息及函数误差的简短解释。

**Technical soundness** 已核对公式与关键限制整体稳健。较大的风险来自不同误差对象在缩略表述中被读成同一种保证，而非现有推导本身错误。

**Readability for nonspecialists** 文章先说明问题再展开机制，结构清晰。表 2 的定性概括易读，但需要更具体的定理层次支撑；局部数学对象的定义也应补齐。

## Recommendation posture

支持在补充理论比较并澄清局部误差口径后继续推进。本文作为专题综述无需以新实验或新理论作为成立前提。没有选定目标期刊，以上 Nature-style 标准只作批判性阅读视角，不构成期刊适配或编辑决定。

## Risk / unsupported claims

- 已检查范围内，未见将普遍算法最优性或原创定理作为已证明贡献。稿件也明确说明没有新基准实验。
- 表 3 支持各原始设置下的局部结果，不能建立相同硬件、相同后验误差目标下的跨方法排序。稿件已有这一限制，应继续保留。
- 近似轨迹对一般无界后验函数及样本平均 MSE 的统一保证尚未由本文建立。作者将其列为开放问题是恰当的，应避免通过简略术语使读者误以为已解决。
- Calderhead 全文细节、全部源文献证明的完整正确性、计时复现和 PDF 视觉排版均不在此次已确认范围内。不能把这些未审查事项直接解释为稿件缺陷。

本报告在独立上下文中完成，完成后冻结。未进行跨审查比较或编辑性事后一致性审计。
