# Reviewer 1

## Review setup

- **Input scope** 冻结的 `packet` 中的方法稿、计算契约、Python/R 实现、测试源码与既有检查记录、协议和开发摘要。审查强调数值算法、目标与坐标语义、实际随机输入、求解停止、失败与回退。
- **Assessment boundary** 按 [BOUNDARY.md](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/BOUNDARY.md) 评价一般方法与软件研究，不要求 Nature 级突破。CPU 正式 1920 项结果正在运行，GPU 尚未实测，均不作结果评价。未读取其他审查报告或综合，未运行测试或实验，未修改实现。下述构造例均是依据所列代码的静态推导，不冒充实际运行记录。
- **Shared manuscript claim summary** 软件将目标、固定随机输入下的转移核、时间执行器和独立核验分开，提供 R 后验对象及失败和成本记录。quasi-DEER 是改动过窗口与停止规则的适配实现，Online Picard 按增量前缀实现，贡献限定为可核验实现与比较材料。
- **Visible evidence base** [Python 测试记录](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/execution/logs/python-release.xml) 记载 43 项测试通过，[R 检查记录](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/execution/logs/r-check.txt:67) 为 `Status: OK`。这些记录支持所列测试通过，不等于覆盖所有返回状态和极端输入。开发和上游复现数字只按包内摘要理解，本轮没有从全量原始轨迹重算。
- **Missing materials affecting confidence** 正式性能、正式统计校准、GPU 行为及一般容差误差界均不可评估。它们已经被稿件明确保留，未据其缺席提出缺陷。

## Overall assessment

稿件的核心数学语义大体能由实现追踪。MALA 的步长与 Hastings 修正、lognormal 的 Jacobian 抵消、中心化与非中心化漏斗的密度和变换，以及硬转移残差与独立接受事件核验之间的区分，均有具体代码依据。工作定位克制，适合继续作为方法与软件研究完善。

当前最重要的缺口在有效输出和失败证据的边界。有限的无约束轨迹在约束变换后可以成为非有限或越出支持集的输出，而实现仍标记 `completed`。成功回退还会覆盖原始失败轨迹。另有一个部分窗口的停止语义问题，quasi-DEER 将补齐的虚构转移纳入失败判定。这些问题不能由现有普通输入测试的通过记录排除。

## Who would be interested in the results, and why

时间并行 MCMC 的实现者、使用 R 与 Stan 的贝叶斯计算研究者，以及比较编译、核验和实际推断成本的研究者会感兴趣。将同一固定核的执行问题与跨核的后验精度问题分开，有助于解释局部加速为何未必转化为完整工作流收益。当前证据支持这种研究设计的用途，尚不足以评价更广泛的硬件或应用收益。

## Major strengths

- [稿件第 41 至 53 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:41) 与 [kernels.py 第 7 至 57 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/kernels.py:7) 一致地给出 MALA 和 RWM 的固定输入语义。NumPy oracle 使用独立密度、解析梯度和循环，没有重新调用 JAX 转移作为所谓独立证据。
- [models.py 第 70 至 91、115 至 120 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/models.py:70) 对正值模型和两种漏斗坐标的定义正确区分了计算坐标与返回变换。[Stan 交叉测试第 12 至 28 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/tests/python/test_stan.py:12) 同时核对相对密度、梯度、约束映射、路径和事件。
- [random_tape 第 61 至 76 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:61) 分离采样与导数方向的 Philox 流，按数组和形状计算指纹。[正式协议默认值](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/protocols/protocol-v1.json:2) 打开独立审计并关闭顺序回退，符合正式比较不通过回退掩盖求解失败的声明。
- [executors.py 第 44 至 64 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/executors.py:44) 对更新后的路径重新计算硬转移残差。[稿件第 63、127 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:63) 正确承认局部残差不是全路径误差界或统计精确性证明。对上游实现的适配边界也有明确说明。

## Major Concerns

### R1-M1 约束变换可以绕过有效输出门槛

- **Concern ID** R1-M1
- **Severity** Major
- **Blocking** Yes
- **Axis** technical soundness / claim-moderation
- **Claim pointer** [稿件第 67 至 70 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:67) 声明非有限状态不进入正常抽样对象，并通过 R 返回标准后验样本。[计算契约第 33、37 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/docs/COMPUTATION-CONTRACT.md:33) 给出同一有效输出承诺。
- **Evidence pointer** [sampling.py 第 178、197 至 198 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:178) 在调用 `model.constrain(draws)` 前确定 `valid`，变换结果不再检查。[models.py 第 70 至 79、116 至 118 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/models.py:70) 接受任意有限 `mu`，对 lognormal 使用 `np.exp`。同样的检查顺序出现在 [nuts.py 第 54 至 56 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/nuts.py:54) 和 [stan.py 第 77 至 81 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/stan.py:77)。[R 接口第 28 至 31 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/R/interface.R:28) 只根据 `completed` 构造抽样对象，没有另作有限性检查。
- **Concern** 一个不依赖随机事件的静态构造是一维 lognormal，`mu=1000`、`sigma=1`、初值 `q=1000`、一条零噪声 MALA 转移和 `log_uniform=-1`。无约束密度与梯度均为零，路径和独立 oracle 完全一致，全部已有判据通过；但返回的 `exp(1000)` 超过 float64 范围，输出成为无穷大。将 `mu` 与初值改为 `-1000` 时，`exp(-1000)` 下溢为零，虽仍有限，却不属于严格正值支持集。现有正值测试使用普通范围的 T1，未覆盖这些情况。
- **Why it matters** 有效性门槛是本文软件贡献的一部分。无约束路径正确不足以保证返回的后验对象满足接口契约。这里阻塞的是正常输出与失败输出的分隔承诺，不是在断言已有 192 项开发任务发生了该错误。
- **Resolution test** 在构造后验对象之前检查变换执行及结果的有限性，并对软件明确支持的约束检查其可表示的支持集。变换失败应返回可诊断失败，保留无约束轨迹，不能保留 `completed`。补入上述正、负极端 lognormal 构造及普通范围对照，并核对原生 MH、NUTS 和 Stan 返回路径的统一处理规则。若某类表示范围被排除，应在输入处明确拒绝并写入契约。

### R1-M2 部分失败路径没有保住所声明的原始轨迹

- **Concern ID** R1-M2
- **Severity** Major
- **Blocking** No
- **Axis** reproducibility
- **Claim pointer** [稿件第 68 至 70 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:68) 声明结果记录原始失败轨迹，并在顺序回退时保留并行阶段的失败及成本。[计算契约第 27 至 33 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/docs/COMPUTATION-CONTRACT.md:27) 强调失败诊断与 `failed_trajectory`。
- **Evidence pointer** [sampling.py 第 170 至 177 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:170) 只复制 `diagnostics` 为 `primary`，随后用顺序结果覆盖 `draws`。[第 197 至 199 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:197) 在回退成功时返回 `failed_trajectory=None`。另一路径中，[第 181 至 192 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:181) 未捕获 oracle 的异常，而 [kernels.py 第 50 至 51 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/kernels.py:50) 可以抛出 `FloatingPointError`。[experiment.py 第 139 至 154 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/experiment.py:139) 只有正常返回后才保存原始数组，异常分支仅写错误信息。
- **Concern** 迭代耗尽后成功回退的输出保留了原始诊断，未保留原始失败轨迹本身。独立 oracle 若抛出异常，已经生成的 JAX 路径和事件也不会进入 `raw.npz`。这是由控制流直接可见的记录缺口，未将其表述为已经观察到的实验事故。[现有回退测试第 41 至 60 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/tests/python/test_kernels.py:41) 核对相同噪声、最终输出和原始状态码，没有检验原始失败数组是否仍可读取。
- **Why it matters** 本文的重要用途是复核失败及其成本。只保留最终顺序轨迹或异常栈，不能重建首次并行失败发生在哪些状态。正式协议未启用回退，因此回退覆盖问题不直接推翻正式设计；审计异常路径仍关系到失败证据的完整性。
- **Resolution test** 将首次轨迹与回退后轨迹分开保存，保留首次事件、状态和停止原因。对审计异常返回结构化失败并保存已得到的路径和实际输入。用现有迭代耗尽夹具检查成功回退前后的两套数组均存在，再注入一次 oracle 异常，验证任务失败、原始轨迹可读取、校验和包含相应文件且成本仍被保留。

### R1-M3 quasi-DEER 的补齐后缀参与实际轨迹的失败判定

- **Concern ID** R1-M3
- **Severity** Major
- **Blocking** No
- **Axis** technical soundness / experimental-design
- **Claim pointer** [稿件第 58 至 63 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:58) 将停止残差定义在固定实际随机输入的轨迹上，[第 73 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:73) 声明验证覆盖部分窗口。
- **Evidence pointer** [executors.py 第 34 至 48 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/executors.py:34) 用零噪声和 `logu=-1` 补齐最后一块，但残差和有限性对整块取最大值或全称判定。[第 61 至 71 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/executors.py:61) 将补齐位置影响的状态汇总为整体状态，最后才截短返回路径。相比之下，[Online Picard 第 92 至 95 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/executors.py:92) 对有限性使用了有效位置掩码。[部分窗口测试第 30 至 38 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/tests/python/test_kernels.py:30) 只验证一个普通高斯案例。
- **Concern** 最后几个虚构转移可能尚未达到容差，尽管全部请求位置已经正确，结果仍会因其残差或非有限性而失败。一个静态构造是二维零均值高斯，精度矩阵为 `[[1, 0.5], [0.5, 1]]`，`draws=5`、`window=4`、`max_iter=1`、`h=0.1`、初值零，前四个噪声为零，第五个噪声为 `(1,0)`，全部 `logu=-1`、方向为 `(1,1)`。首块保持零；末块第一个真实状态一次更新即可得到 `sqrt(0.2)*(1,0)`。在后续补齐位置，对角近似给出系数 `0.85`，硬转移却产生系数 `(0.9,-0.05)`，因此虚构第二状态存在约 `0.05*sqrt(0.2)` 的残差。整个请求的五步轨迹已满足递推，程序仍返回迭代上限失败。
- **Why it matters** 失败率、求解次数和残差此时包含用户未请求的递推方程，削弱部分窗口接口及停止规则的可解释性。冻结主实验的 MH 总长度为 768 或 2560，窗口为 64，均整除，因此这个问题不直接指向该正式网格的结果错误。
- **Resolution test** 最后一块的残差、有限性、确认状态和停止判定应只使用真实位置，或使用等效的变长末块策略。用上述相关高斯构造验证真实五步路径可通过，并加入补齐位置不应影响结果状态的回归用例。若仍执行填充工作，其额外求值成本可以如实记录，但不应作为真实轨迹不合格的理由。

## Minor Comments

### R1-m1 独立路径审计的通过阈值需在方法中写全

- **Concern ID** R1-m1
- **Severity** Minor
- **Blocking** No
- **Axis** writing-clarity / reproducibility
- **Claim pointer** [稿件第 63 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:63) 在独立路径和接受事件核验的同一段中给出 `atol=rtol=1e-10`，但未给出路径审计的实际通过公式。
- **Affected element** 数值停止标准与独立审计标准的对应关系。
- **Evidence pointer** [sampling.py 第 186 至 192 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:186) 要求事件零失配，路径最大绝对误差则允许 `100*(atol + rtol*max(1, max(abs(path))))`。这包含额外的 100 倍因子、整链最大尺度与尺度下限 1，和局部逐坐标残差规则不同。
- **Issue** 局部残差不等于全路径误差界的限制已写清，但读者仍不能从方法文字还原独立核验的通过门槛。
- **Required correction / Resolution test** 明列两个判据，说明审计比较使用无约束坐标、整链最大绝对误差和零事件失配，并解释 100 倍因子的定位。以一个已存配置手算阈值应与程序一致，不将 `1e-10` 读作全路径绝对误差上界。

### R1-m2 顺序回退的触发范围没有明确限定

- **Concern ID** R1-m2
- **Severity** Minor
- **Blocking** No
- **Axis** writing-clarity
- **Claim pointer** [稿件第 70 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:70) 与 [使用说明第 31 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/docs/INSTALL-AND-USE.md:31) 将 `on_failure='sequential'` 描述为相同噪声顺序回退。
- **Affected element** 失败策略的用户可见语义。
- **Evidence pointer** [sampling.py 第 172 至 192 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:172) 只在执行器状态非零时选择回退，随后才进行独立审计。审计事件或路径失配不会重新进入回退分支。
- **Issue** 目前回退实际指执行器状态失败后的回退，未覆盖全部最终 `failed` 状态。读者可能将该选项理解为也处理独立核验失配。
- **Required correction / Resolution test** 明确列出可回退和不可回退的失败类别。若设计意图涵盖独立审计失配，应调整流程并验证仍复用原数组；若不涵盖，收窄稿件和接口说明即可。对“执行器失败”和“执行器成功但审计失配”两个场景分别固定预期行为。

## Technical failings that need to be addressed before the case is established

R1-M1 必须解决，才能成立“正常后验对象已通过数值有效性门槛”的软件核心承诺。R1-M2 与 R1-M3 分别需要恢复失败证据的完整性和部分窗口的真实停止语义。它们均不构成已有开发汇总数值错误的直接证据，也不要求停止正在进行的正式实验；若据此改变实现，应与既有冻结版本及结果保持可追踪区分。

## Assessment against Nature-style criteria

这里沿用技能的五个评价维度，发表尺度按边界限定为一般方法与软件研究。

- **Originality** 稿件将贡献限定为执行器适配、验证与冻结比较，没有将共同接口或既有并行扫描包装成新采样算法。包内文献卡足以支持这一克制定位，本轮不作外部优先权裁决。
- **Scientific importance** 可核验实现和包含失败的成本比较具有明确领域用途。正式结果尚不可评估，因而不判断其性能结论的分量。
- **Interdisciplinary readership** 主要读者来自贝叶斯计算、科学软件和使用 Stan/R 的应用领域。是否形成更广泛结论取决于后续实测，本轮不施加 Nature 的广泛影响门槛。
- **Technical soundness** 常规目标语义、转移核和独立验证思路较扎实；输出变换及失败路径仍有上述可定位缺口。
- **Readability for nonspecialists** 开篇区分轨迹延迟与可靠推断成本，且主动解释拒绝自环、残差和 NUTS 预热差异，逻辑清晰。独立审计门槛和回退类别需要补足精确定义。

## Recommendation posture

建议实质性修订软件契约与相应验证后再确认方法与软件部分成立。当前材料可以支撑“已有可追踪的研究实现与开发验证”，不能无条件支撑“所有正常返回对象均排除了非有限或不可表示的约束结果”。不对正式研究结果或投稿作最终编辑判断。

## Risk / unsupported claims

- 本报告的构造例由代码与数值表示范围推导，未在本轮执行。建议的回归检查属于关闭问题的检验要求，不能算作已完成验证。
- 没有发现所列普通输入测试与 43 项通过记录之间的直接矛盾。提出的缺口主要位于这些测试未覆盖的边界分支。
- CPU 正式精度与性能、GPU 能力、一般混合保证、一般容差到后验函数误差的界均不可从本包现阶段材料得出；稿件已明确保留这些结论。
- 本报告仅为 Reviewer 1 的独立判断。未进行跨审查比较，也未执行审查冻结后的编辑性一致性审计。

## Freeze status

本报告定稿后冻结，不依据其他审查或综合结果回改。
