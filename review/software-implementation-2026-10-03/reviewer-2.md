# Reviewer 2

## Review setup

- **Input scope** 方法、软件实现、冻结统计协议、开发汇总和正式分析脚本的局部审查。
- **Assessment boundary** 遵守 [BOUNDARY.md](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/BOUNDARY.md)。CPU 正式 1920 项任务仍在运行，正式结果仅为占位，GPU 尚未实测。上述未完成结果均不构成本次缺陷判定的依据。目标尺度是一般方法与软件研究，不以 Nature 突破性作为通过条件。
- **Emphasis** 统计设计、独立重复与共同随机数、MSE 与有限参考、SBC、成本核算、失败和不确定性。
- **Shared manuscript claim summary** 软件将目标、核和执行器分开，借助实际随机数组和独立 oracle 核验轨迹，并以冻结的重复实验区分执行速度与后验函数误差。稿件明确不声称新采样算法、通用加速或普遍校准。
- **Visible evidence base** 仅使用 packet 内的稿件、源码、协议、测试、开发及参考汇总，以及 nature-reviewer 的分类与评审标准。静态读取任务表确认了 80 个模型/工作流/预算组，每组均有编号 0 至 23 的 24 个重复；768 个并行任务均能匹配具有相同步长、长度、丢弃段及随机种子的同核顺序任务。没有运行采样、测试或重实验，没有修改实现。
- **Missing materials affecting confidence** 开发与参考的逐任务原始数组未随本 packet 提供，因而不能独立重算其统计量。正式性能、正式误差分布、正式 SBC 和 GPU 推断均不可评估。未读取其他审查报告或综合。

## Overall assessment

统计协议的基本区分是合理的。24 次重复是每个指定工作流内的随机化重复，四链先汇总为一次估计，计时重放没有被算作额外样本。实际随机数组在同核执行器之间配对，NUTS 使用单独的随机机制。解析误差与有限参考平方差、成功条件下的误差与输出失败、局部执行时间与完整任务时间，也在稿件中得到了明确区分。

现阶段足以支持一个值得继续评估的软件研究实现。本次识别出两项非阻断的 Major Concerns 和三项 Minor Comments，主要位于分析及报告层。失败成本的展示口径与常量函数诊断需要修订。未发现足以否定当前有界实现主张的 Blocking Yes 问题，也不根据尚未完成的正式结果作投稿决定。

## Who would be interested in the results, and why

时间并行 MCMC 的实现者、R/Stan/JAX 使用者，以及需要在有限硬件预算下评估推断成本的研究者，会关注这些结果。其价值在于把同轨迹计算收益、统计混合、核验开销和失败保留放入同一可检查工作流。对应用领域的外推仍受合成模型和固定配置限制，这一点与稿件自己的定位一致。

## Major strengths

1. **实验单位与配对关系清楚。** [稿件第 53、96 至 110 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:96)、[随机数组生成第 61 至 68 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:61)与协议任务表一致。分析先对链和保留步求均值，再在重复层面重采样，没有将相关链内样本直接当独立重复。
2. **没有把有限参考伪装成真值。** [稿件第 108 至 110 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:108)报告独立参考拟合、两类 MCSE 和共同偏差限制，并拒绝无条件减去参考方差。[分析第 122 至 133 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:122)确实对同一次敏感性抽样中的全部重复使用同一个参考扰动。
3. **精度和校准声明受到克制。** [稿件第 79、98、110 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:79)没有把 12 个开发数据集或 24 次计算重复解释为充分功效，也没有把逐点区间当同时保证。正式 SBC 更换数据和采样种子。顺序与并行的相同秩直方图被视为相同计算流程的结果，没有被当成两份独立校准证据。
4. **主要时间边界可追踪。** [稿件第 115 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:115)、[运行器第 131 至 157 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/experiment.py:131)和[分析第 105 至 107 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:105)支持将建模、原始输出和校验和保留在任务成本内，另扣除基准专用重放并加入函数摘要与诊断时间。明确排除进程导入和安装也避免了冷启动口径混淆。

## Major Concerns

### R2-M1 失败任务的成本尚未进入成本展示

- **Concern ID** R2-M1
- **Severity** Major
- **Blocking** No
- **Axis** experimental-design
- **Claim pointer** 稿件第 110 行承诺分别呈现失败率、成功输出上的条件误差及全部成本，第 115 行定义完整工作流时间。
- **Evidence pointer** [analyze.py 第 105 至 107 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:105)为所有已读任务保存 `t_total`，但[第 111 至 138 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:111)只从 `ok` 计算三个时间中位数，且整个统计块要求至少一个成功结果。[figures.py 第 75 至 86 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/figures.py:75)使用这个成功条件下的时间作为误差曲线横轴；完全失败的组没有点，面板仅汇总该模型的失败总数。[write-results-tex.py 第 45 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/scripts/write-results-tex.py:45)说明误差是条件结果，却没有相应说明横轴也以成功为条件。
- **Concern** 原始成本保留是正确的，但展示层尚未实现“全部成本分别呈现”。如果失败运行较慢，成功条件下的中位时间不能代表所有尝试的资源开销。完全失败的工作流还会从成本图中消失。这是脚本中可以确认的条件筛选，不是对正在运行的正式实验失败率或偏差大小的推测。
- **Why it matters** 完整成本是稿件的核心比较维度之一，失败与运行时间可能相关。读者需要同时看见成功时的误差/时间、失败率和失败消耗，才可解释工作流的实用代价。现有逐任务成本仍然保留，且稿件没有提出无条件精度达标结论，因此此项不单独阻断当前有界的软件主张。
- **Resolution test** 在每个模型/方法/预算组中报告所有尝试的总成本或明确的分布摘要，并分别列出成功与失败成本及各自分母。保留成功条件下的误差曲线，但将横轴条件明确写出；完全失败的组应有可见的失败与成本入口，不必为失败虚构平方误差。用一个含成功和失败记录、且失败耗时不同的微型分析输入检查所有成本能闭合，完全失败组也不会被静默省略。

### R2-M2 常量函数被报告为理想收敛与零参考不确定性

- **Concern ID** R2-M2
- **Severity** Major
- **Blocking** No
- **Axis** statistical-rigor
- **Claim pointer** 稿件第 108 行以函数 split-Rhat 及参考 MCSE 说明有限参考质量，第 125 行要求结合模式探索和诊断解释压力目标。[reference-v1.json](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/protocols/reference-v1.json)的 `policy.acceptance` 要求参考未解决时保持比较未判定。
- **Evidence pointer** [analyze.py 第 47 至 54 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:47)在链内与链间方差都为零时直接返回 Rhat 等于 1；[第 69 至 78 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:69)对相同常量函数得到零批均值 MCSE 和零拟合间 MCSE，并让它通过参考可用性判定。[reference-summary.json 第 66 至 128 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/outputs/reference-summary.json:66)已出现具体实例，L2 的第四个函数 `q0_above_0` 的参考均值和两类 MCSE 均为 0，Rhat 为 1，整体标记 `usable=true`。
- **Concern** 对预先定义的非恒定事件函数，所有保存样本的函数值相同，无法由方差比诊断得到“混合良好”的结论。相同输出可能来自极小事件概率，也可能来自没有探索到另一侧。这里将未定义的方差比映射成 1，又用零经验方差传播参考误差，使输出看起来比证据允许的更确定。L2 的真实事件概率可能确实很小，本材料不能证明其参考均值有实质误差；问题是当前处理没有区分这些情况。同一 `split_rhat` 还用于正式目标的符号与模式占比函数。
- **Why it matters** 软件的诊断和参考有效性是重要证据链，常量输出应被识别为信息不足，不能自动形成理想诊断。解析目标的重复平方误差和其他连续函数仍可提供独立信息，因此这不意味着全部比较失效，也不构成当前全部主张的阻断。
- **Resolution test** 对链内、链间都无变化的非恒定函数返回不可判定标志，并单列观察事件数。对零事件参考，给出有依据的不确定性界限或明确标注“该函数参考精度未确定”，不能把相关 MCMC 转移数直接作为独立伯努利试验数。加入全零、全一及各链停留不同常量的诊断输入，确认不会产生错误的“Rhat 等于 1 且精度已证实”状态。若要保留 L2 的参考可用性，应逐函数说明该退化事件的处理依据和对最大误差结论的影响。

## Minor Comments

### R2-m1 参考不可用标记没有控制图表输出

- **Concern ID** R2-m1
- **Severity** Minor
- **Blocking** No
- **Axis** reproducibility
- **Claim pointer** `reference-v1.json` 的 `policy.acceptance` 规定未解决的参考产生未判定比较。
- **Affected element** 有限参考有效性标记的展示路径。
- **Evidence pointer** [analyze.py 第 113 至 133 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:113)保存 `reference_usable`，但只要参考均值存在仍计算误差；[write-results-tex.py 第 35 至 39 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/scripts/write-results-tex.py:35)及[figures.py 第 77 至 83 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/figures.py:77)不读取该标记。
- **Issue** 如果参考因诊断或 MCSE 不合格而 `usable=false`，图表仍会按普通数值输出。当前提供的两份参考都标记为可用，因此这是有明确触发条件的报告保护缺口，不是声称当前图表已使用不合格参考。
- **Required correction / Resolution test** 不可用参考仍可保留探索性平方差，但必须显式显示未判定，不能按普通精度结果渲染。用一个包含有限均值且 `usable=false` 的记录检查表格和图例能传播状态。

### R2-m2 共同参考敏感性采用了未说明的函数间独立扰动

- **Concern ID** R2-m2
- **Severity** Minor
- **Blocking** No
- **Axis** statistical-rigor
- **Claim pointer** 稿件第 110 行说明共同参考误差的敏感性传播，第 108 行说明参考 MCSE 的来源。
- **Affected element** 有限参考敏感性区间的假设和图例。
- **Evidence pointer** [analyze.py 第 125 至 133 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:125)对每个函数独立生成正态扰动，所用协方差为对角阵；[第 30 至 31 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:30)的函数含同一个参数的值、sigmoid 和符号事件。[figures.py 第 80 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/figures.py:80)直接使用敏感性扩展区间绘图。
- **Issue** 脚本正确保持了参考误差在重复之间的共同性，但没有保持函数之间的相关性。最大函数误差的敏感性依赖这种联合结构。稿件已将其限定为敏感性分析，故不据此断言区间失效或当前数值受到重大影响，不过读者需要知道这是额外工作假设。
- **Required correction / Resolution test** 在方法和图例中明确说明正态、对角协方差扰动的假设，并区分基本重复 bootstrap 区间与参考敏感性范围。若希望传播联合参考误差，可从已有参考拟合或批均值向量联合重采样；用两个高度相关的函数检查一次参考扰动在重复之间共享且保留所声明的函数相关结构。

### R2-m3 SBC 成功记录丢弃了 NUTS 的发散诊断

- **Concern ID** R2-m3
- **Severity** Minor
- **Blocking** No
- **Axis** statistical-rigor
- **Claim pointer** 稿件第 68 行明确区分有限样本输出与 NUTS 发散，第 79 行将生成式检查作为验证链路的一部分。
- **Affected element** SBC 逐次拟合记录及汇总。
- **Evidence pointer** [statistical-validation.py 第 48 至 58 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/scripts/statistical-validation.py:48)在成功时仅保存秩、覆盖、矩和抽稀相关性，在失败分支才保存 diagnostics；[nuts.py 第 54 至 59 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/nuts.py:54)允许有发散但样本有限的任务返回 `completed`。
- **Issue** 因而 SBC 中“已完成”的 NUTS 拟合即使存在保留期发散，其诊断也不会进入该验证档案。没有证据表明现有 12 个简单正态数据集实际发生过这种情况；这是验证记录覆盖不完整，不能据此推断已经失校准。
- **Required correction / Resolution test** 对成功和失败拟合都保留关键诊断，至少汇总 NUTS 发散次数、涉及的数据集数和覆盖率分母。若有失败，继续明确覆盖率以成功拟合为条件。用一个返回有限数组且含发散事件的结果对象检查这些字段能进入 SBC 输出，无需增加生成数据集或重做大型实验。

## Technical failings that need to be addressed before the case is established

正式误差与成本解释发布前，应完成 R2-M1 的失败成本展示和 R2-M2 的退化函数诊断处理，并让 R2-m1 的参考状态贯穿输出。R2-m2 与 R2-m3 是局部假设说明及诊断记录修订。它们均不要求增加正式采样重复，也没有理由因本次审查停止或重跑正在进行的冻结实验。

## Assessment against the shared review criteria

- **Originality** 材料支持的是对已有方法的可核验适配、接口和比较协议。稿件第 16、24、56 行已明确承认这一点，没有将统一 API 或窗口改动夸大为新采样算法。仅凭本 packet 不能判断它相对于全部现有软件的独特程度，但没有据此提出额外新颖性门槛。
- **Scientific importance** 对方法与软件研究，核验成本、失败保留和统计误差的联合核算有明确用途。实际收益大小须待正式结果，当前不能评价速度或精度结论的强弱。
- **Interdisciplinary readership** 读者可理解何时一种更快的局部计算未必降低推断总成本。合成目标提供机制可查性，但未提供跨真实应用领域的证据，稿件对此已有边界声明。
- **Technical soundness** 独立重复、共同随机数、冻结配置和有限参考的基本设计合理。主要薄弱处集中在诊断退化处理及失败成本的报告契约，见 R2-M1 与 R2-M2。
- **Readability for nonspecialists** 第 22 行先区分执行与推断两个问题，能帮助读者理解全文。补充条件时间、常量函数不可判定标志及敏感性假设后，结果图表的含义会更明确。

## Recommendation posture

建议在保持冻结采样协议的前提下修订分析和报告层，随后再对完成的正式结果作独立评估。当前不作接收或拒绝意见，不要求 Nature 级突破性，也不将 CPU 正式任务或 GPU 数据尚未完成列为审查缺陷。本报告没有 Blocking Yes 项。

## Risk / unsupported claims

- 不能由开发探测的全部完成、配对路径接近或相同 SBC 秩直方图推导一般后验正确性。稿件目前没有这样声称。
- 不能把 1920 个任务视为 1920 个独立模型或独立配对证据。每组 24 次重复和方法内配对的结构已可从协议确认。
- 当前不能判断正式工作流排名、阈值达标、失败代价大小、GPU 加速或正式 SBC 覆盖率。
- 本次没有重算参考原始样本，不声称 L2 的零事件概率估计造成了实质科学误差。R2-M2 指向的是可确认的诊断解释和信息不足处理问题。
- 当前展示问题由静态源码确认，所述修订检验是建议的验收条件，并非已执行实验或测试结果。

## Freeze declaration

本报告在本独立上下文内完成，未接收、读取或比较其他审查报告与综合。完成后冻结为只读文件，交由后续独立综合使用；不根据其他审查的发现回改。
