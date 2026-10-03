# Reviewer 3

## Review setup

**Input scope**

仅审阅 `/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet` 的冻结材料。先读取 `BOUNDARY.md`，再读取稿件、R/Python 接口、冻结与恢复代码、分析脚本、安装与计算契约、协议、测试及既有测试日志。没有读取其他审查报告或综合，没有运行采样实验，没有修改实现。

**Assessment boundary**

评估尺度为未指定期刊的方法与软件研究，不把 Nature 的突破性或跨学科影响作为接收门槛。本报告强调接口、重放与恢复、安装和资源记录、贡献定位及可读性。CPU 正式 1920 项任务仍在运行，正式结果和 GPU 性能均不在本次可评估范围。下述实现问题来自冻结源码的静态控制流核对，不是新实验结果，也不表示已经证明现有输出遭到污染。

**Shared manuscript claim summary**

稿件的现阶段贡献是把现有时间并行方法组织成目标、核、执行器可分别核对的研究实现，通过 R 输出标准后验抽样对象，并提供独立核验、失败记录、冻结协议及完整成本比较材料。稿件不把统一接口视为新采样算法，也不根据 CPU 开发探测声称通用加速。见[摘要和研究范围](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:16)。

**Visible evidence base**

可见材料支持代码层面的接口检查、既有测试范围及局部复现判断。[Python 测试日志](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/execution/logs/python-release.xml)记载 43 项测试、零失败和零跳过，[R 检查日志](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/execution/logs/r-check.txt)以 `Status: OK` 结束。冻结协议包含具体目标、配置和任务，现有测试包含正常任务跳过、文件损坏检测、固定噪声回退及跨提供方核验。

**Missing materials affecting confidence**

包内没有完整安装锁文件、R 安装脚本、R 测试源码、完整发布归档或架构图文件，因此不能独立确认干净机器上的安装体验、最低 R/Python 版本兼容性或图形可读性。这些是材料边界，不据此推定项目缺少相应文件。正式运行原始输出和 GPU 回传也不在本包中，不要求以本次审查补做或完成这些结果。

## Overall assessment

这是定位相对准确的软件研究稿。将固定随机输入下的轨迹一致性与不同核的统计精度分开，是实质性的比较设计贡献；显式承认 quasi-DEER 适配差异、Stan CPU 路径限制、失败与发散的不同含义，也让读者有机会正确解释结果。现有材料足以支持“已经形成可检查的研究原型”，不足以支持一个不附条件的、端到端已闭合的复现保证。

需要优先处理的是冻结协议与分析输入没有强制关联。另有三个重要但不独立否定整项工作的接口缺口，分别涉及恢复时环境、失败路径保留及约束后输出有限性。它们应在相应软件契约被当作论文证据之前修正或明确缩小声明范围。这里不判断尚未完成的正式性能、精度或硬件结论。

## Who would be interested in the results, and why

R 中开展贝叶斯分析的研究者会关心能否在不丢失后验对象语义的情况下检查并行执行失败。MCMC 方法开发者会关心共同随机输入、独立 oracle 与完整成本记录能否区分算法效应和实现开销。计算研究复现者会关心协议、原始数组和恢复记录是否能形成可追踪的证据链。这些读者构成合理的软件研究受众，无须把工作包装成新的通用采样算法。

## Major strengths

- 贡献与前作的边界清楚。稿件承认窗口调度和停止判据相对上游有所改变，也明确 Online Picard 为按论文独立实现。没有将本实现的 CPU 负例扩张为对前作的普遍否定。见[两类时间执行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:55)和[解释与限制](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:123)。
- R 的数组维度转换与结果分层明确。`pb_sample` 将 Python 的 chain × iteration × variable 转为 iteration × chain × variable，仅在 `completed` 状态创建 `posterior::draws_array`，其他记录独立保留。见[R 接口第 24 至 36 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/R/interface.R:24)。
- 固定实际随机数组、独立 NumPy 核验和参数变换核验，明显强于只比较同名 seed 或把同一函数执行两次。Stan 与原生模型测试还比较接受事件，且拒绝不支持的组合。见[随机输入及审计实现](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:61)和[Stan 测试](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/tests/python/test_stan.py:10)。
- 恢复机制已有实际结构。原子 JSON 替换、逐任务尝试目录、原始数组校验和、运行锁及保留失败状态均可定位，正常恢复和损坏检测也已有测试。见[实验运行器](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/experiment.py:26)和[恢复测试](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/tests/python/test_experiments.py:14)。

## Major Concerns

### R3-M1 冻结协议与分析输入尚未形成强制的身份关联

**Severity** Major

**Blocking** Yes

**Axis** reproducibility

**Claim pointer**

稿件称冻结源码、协议校验和及逐任务原始状态支持可核验研究，并称正式表图由原始任务记录重建。安装说明进一步称复制新代码不能继续旧协议。见[稿件第 117 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:117)、[正式结果占位说明](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/results.generated.tex:1)及[安装说明第 54 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/docs/INSTALL-AND-USE.md:54)。

**Evidence pointer**

[source_hash 与 load_protocol 第 36 至 85 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/experiment.py:36)、[分析 records 第 14 至 22 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:14)、[reference_summary 第 57 至 81 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:57)、[formal_summary 第 84 至 107 行与第 140 至 142 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:84)。

**Concern**

执行入口会调用 `load_protocol`，分析入口则直接读取传入的协议 JSON。`records` 核对逐任务文件字节与 state 内的校验和，却不读取或核对运行目录的 `manifest.identity`，也不验证输入任务集合属于该协议。`formal_summary` 再直接用传入协议的模型定义计算标准化函数和真值。例如，若分析时换入另一份模型均值不同的协议，而运行文件保持完整，现有检查没有拒绝这一组合的条件。这里是代码路径推论，没有实际制造或运行该错误输入。

另外，`source_hash` 覆盖内核、R 接口和 Stan 文件，不包含 `benchmark/analysis/analyze.py`。输出摘要没有保存分析脚本哈希、所用协议哈希及参考摘要哈希。因而“原始文件未损坏”目前不能推出“摘要由这份冻结协议和这版分析逻辑生成”。

**Why it matters**

冻结材料的可核验性是本文现阶段的中心贡献，而分析正是把原始输出转成论文证据的环节。即使采样记录本身正确，身份关联缺失仍会容许错误协议、错误参考或混入额外任务得到表面完整的结果。标为 Blocking Yes，针对的是端到端可核验这一中心声明，不是声称正式数据已经混用，也不是要求暂停或重跑全部正式任务。

**Resolution test**

分析时验证协议自身哈希，核对运行 manifest 的协议、源码、平台身份，并按协议验证任务标识集合及其配置。参考摘要应携带可核对的模型和来源身份，分析输出应记录上述输入及分析代码的哈希。用小型文件级夹具证明错误协议、缺失或额外任务、错误参考身份会被拒绝；正确夹具可以重建相同数值摘要。不要求为这项检验重跑大型实验。

### R3-M2 恢复执行能够跨环境继续，却只保留第一次启动的环境记录

**Severity** Major

**Blocking** No

**Axis** reproducibility

**Claim pointer**

稿件将整台指定机器作为比较平台，并用冻结协议和原始状态支持中断恢复。见[稿件第 113 至 117 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:113)。

**Evidence pointer**

[恢复身份与 manifest 第 105 至 115 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/experiment.py:105)、[逐任务记录第 129 至 157 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/experiment.py:129)、[environment 第 79 至 92 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:79)。

**Concern**

恢复时的 identity 只有协议哈希、源码哈希和 `cpu` 或 `gpu` 平台标签。已有 manifest 时只比较这三个值，不比较当前设备、Python 或线程环境，也不创建新的启动会话记录。环境与线程变量仅在第一次创建 manifest 时写入。依赖版本锁的检查是有益的，但同一套依赖仍可以在不同 CPU、GPU 或线程配置下运行。若复制同一输出目录到另一台同平台机器继续执行，后续任务会继承第一次启动的环境描述，逐任务记录无法区分两段运行。

**Why it matters**

本文比较的是指定机器上的工作流成本，而不仅是抽样数值。恢复后成本记录与硬件或线程设置的对应关系不可丢失。当前材料没有证明发生过跨环境恢复，因此不能据此否定现有运行；这是所承诺恢复机制的重要证据缺口。

**Resolution test**

每次启动保存独立环境会话，并把每个 attempt 关联到该会话。对需要同机比较的协议，可直接拒绝实质环境变化；若允许变化，则明确分组并保留变化原因。通过模拟设备或线程元数据变化的轻量测试，证明恢复会拒绝该变化或生成可区分的新会话，而不会静默沿用旧环境。

### R3-M3 失败状态保留不等于失败轨迹已经完整保留

**Severity** Major

**Blocking** No

**Axis** data-resource-quality

**Claim pointer**

稿件称失败结果记录原始失败轨迹，顺序回退仍保留并行阶段的失败及成本；计算契约也称未通过标准的轨迹存为 `failed_trajectory`。见[稿件第 67 至 70 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:67)及[计算契约第 29 至 33 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/docs/COMPUTATION-CONTRACT.md:29)。

**Evidence pointer**

[MH 回退及返回值第 170 至 200 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:170)、[NUTS 返回值第 54 至 62 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/nuts.py:54)、[Stan 失败处理第 67 至 85 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/stan.py:67)、[NumPy 参考循环第 36 至 57 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/kernels.py:36)。

**Concern**

MH 顺序回退前复制了 `primary_diagnostics`，但原并行路径没有复制；`draws` 被回退路径覆盖，回退成功后 `failed_trajectory` 为 `None`。因此原始失败诊断保留了，原始失败轨迹没有保留。NUTS 在 `valid=False` 时把 `draws` 与 `unconstrained` 都设为 `None`，返回对象没有 `failed_trajectory` 字段。Stan 路径若在某条链中途抛出异常，也只能保留已经完整返回的其他链，该失败链的已生成前缀不会从 `numpy_reference` 返回。

**Why it matters**

失败计数可以继续统计，但缺失路径会削弱异常定位、错误复查以及“所有失败原始材料可重放核验”的声明。正式协议关闭回退，因此回退部分不直接影响当前正式比较；NUTS 和 Stan 的情形仍说明失败对象的公共契约不统一。故为 Major、Blocking No。

**Resolution test**

明确正常路径、主执行失败路径、回退路径和仅完成部分前缀的存储语义，使用独立字段保存已有状态，不能因回退成功而覆盖主失败输出。为回退、NUTS 非有限输出和 Stan 中途异常分别加入确定性的短测试，检查错误链、停止位置及可用原始状态实际进入返回对象和导出文件。若某类异常确实无法保留路径，应把该边界写入契约与稿件。

### R3-M4 正常后验对象入口没有验证约束变换后的输出有限性

**Severity** Major

**Blocking** No

**Axis** reproducibility

**Claim pointer**

稿件将非有限状态与未通过输出标准的轨迹排除于正常抽样对象之外，并以 R 的标准后验对象作为交付结果。见[稿件第 68 至 70 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:68)。

**Evidence pointer**

[原生模型变换第 70 至 79 行与第 114 至 120 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/models.py:70)、[MH 有效性及返回值第 178 至 198 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:178)、[NUTS 第 54 至 56 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/nuts.py:54)、[Stan 第 77 至 81 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/stan.py:77)、[R 后验对象入口第 28 至 31 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/R/interface.R:28)。

**Concern**

三条采样路径均先检查无约束状态，再执行 `model.constrain`，没有对变换后的实际返回数组重新检查有限性。`lognormal` 的变换是 `np.exp`，非中心化漏斗也包含指数变换，因此有限 q 不能保证有限 θ。一个代码级边界例是接口允许有限的 lognormal 均值和初值约为 1000，无约束目标及轨迹可以保持有限，但 `exp(q)` 超出 float64 表示范围。现有控制流可以继续以 `completed` 交付非有限约束输出，R 包随后只根据该状态构造后验对象。本报告没有执行该例；这一判断限于静态控制流和所用变换。

**Why it matters**

这是实际交付对象的有效性检查缺口，不能通过无约束轨迹核验替代。它不表明目前正式目标发生过该问题，也不否定有限区域内的路径测试；但会使面向用户的软件契约在支持的变换模型上失效。

**Resolution test**

对约束输出的形状及有限性执行最终验证，失败时保存无约束轨迹与变换失败原因，并禁止进入正常 `draws_array`。使用边界变换的短测试覆盖 native MH、NUTS 和 Stan 提供方，并验证 R 侧 `draws` 为空且 record 保留原因；或明确收窄支持的输入与输出范围并在入口强制执行。

## Minor Comments

### R3-m1 统一配置中的 warmup 对 MH 没有与 NUTS 相同的含义

**Severity** Minor

**Blocking** No

**Axis** writing-clarity

**Claim pointer**

R 是建模与分析入口，正式五种工作流具有分别定义的预热或丢弃段。用户需要知道 API 的 `draws` 和 `warmup` 如何对应这一设计。

**Evidence pointer**

[默认配置第 15 至 19 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:15)、[MH 随机数组形状第 61 至 68 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/sampling.py:61)、[NUTS 预热第 20 至 25 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/nuts.py:20)、[正式分析丢弃段第 93 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/benchmark/analysis/analyze.py:93)、[安装示例第 23 至 31 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/docs/INSTALL-AND-USE.md:23)。

**Issue**

`warmup` 是所有核都接受并写入 record 的字段，但 MH 的 `random_tape` 和返回路径只按 `draws` 执行，不使用该字段；正式 MH 的 512 步丢弃由任务配置和后续分析处理。安装示例提醒短链不保证均衡，但没有明确告诉直接调用 R 接口的用户，给 MH 设置 `warmup` 不会额外运行或删除这些步。

**Required correction / Resolution test**

在 API 文档与最小例中明确区分 MH 总转移数、用户丢弃段和 NUTS 自适应预热。对未使用的参数给出清楚提示或拒绝，避免 record 看似执行了未实际发生的预热。检查说明中的示例可以预测各核实际返回的数组长度。

### R3-m2 RSS 峰值的监测时间范围应与任务墙钟范围区分

**Severity** Minor

**Blocking** No

**Axis** writing-clarity

**Claim pointer**

稿件报告每 20 ms 采样的 CPU 进程 RSS 峰值，并在相邻段落定义包含建模与输出的完整任务时间。见[稿件第 115 至 117 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/manuscript/software/软件与基准研究.tex:115)。

**Evidence pointer**

[ResourceMonitor 第 46 至 58 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/experiment.py:46)、[调用范围第 131 至 149 行](/Users/haku/Workspace/ParallelBayes/review/software-implementation-2026-10-03/packet/r-package/inst/python/parallelbayes/experiment.py:131)。

**Issue**

RSS monitor 只包围 `sample`，启动于 `make_model` 之后，并在原始数组压缩写盘之前结束。它还是同一长期进程的绝对 RSS，包含此前驻留内存。现有文字准确说明了采样频率和进程范围，但容易被理解成与完整任务墙钟同范围的任务峰值。

**Required correction / Resolution test**

明确标记为“采样 API 期间的进程绝对 RSS 采样峰值”，说明建模、输出阶段及子进程不在该监测范围。若另有全任务峰值，使用不同名称。核对稿件、契约和图表字段说明一致即可，不要求增加实验。

## Technical failings that need to be addressed before the case is established

R3-M1 是本报告唯一 Blocking Yes 项。必须使分析使用的冻结协议、运行记录、参考与分析版本形成可检查的关联，才能把“可核验比较材料”作为闭合的软件证据链。R3-M2 至 R3-M4 也需处理或收窄相应接口声明，但现有材料没有证明它们已经改变本轮正式结果。

## Assessment against Nature-style criteria

这里保留技能规定的五个评估维度，但采用本次要求的方法与软件研究尺度。

- **Originality** 原创性主要在可核验实现、接口契约和比较协议的组织，稿件没有把已有时间并行机制归为自己的算法发明。现有两篇前作核查卡与稿件表述相容。尚不能由这些材料确立所有相关软件中的首创性，稿件目前也不需要这样的主张。
- **Scientific importance** 对计算方法评估有明确用途，尤其能避免把固定轨迹执行收益与后验推断效率混为一谈。效用大小仍需正式结果支持，本次不评判其完成状态，也不把 CPU 开发负例视为低价值结果。
- **Interdisciplinary readership** R 用户、贝叶斯计算者和复现研究者具有共同兴趣。跨学科意义目前更多是可复用的方法评价实践，而不是已证明的领域应用收益。
- **Technical soundness** 数学约定、独立核验和失败计数意识较强。端到端来源关联及结果对象的边界处理尚不足，具体问题见 R3-M1 至 R3-M4。测试成功仅支持已测试范围。
- **Readability for nonspecialists** 两个研究问题的开篇区分、核与执行器分层、限制声明都较清楚。API 的预热语义和资源监测范围仍需更精确。架构图本体未提供，不能评价图示效果。

## Recommendation posture

支持继续作为方法与软件研究完善。对现有局部材料的姿态是需要修订后再确认端到端复现主张，而不是因缺少 Nature 级突破否定研究，也不是要求以本轮审查决定投稿。关闭 R3-M1，并使其余软件契约与实际返回行为一致后，这份稿件将更容易成为可独立检查的比较研究。

## Risk / unsupported claims

- 正式 CPU 结果、GPU 性能、跨机器速度排名及正式 SBC 校准结论均不可由本次材料评估。
- 不把上述静态漏洞表述为已发生的数据混入、已出现的非有限后验对象或已丢失的某次正式轨迹。
- 安装文件不在审查包中，不据此宣称项目无法安装。既有 R 包检查通过也不能代替干净机器和全部声称版本组合上的验证。
- 现有测试、有限参考和生成式检查均不提供一般统计正确性证明。稿件已明确这些边界，本报告不另行制造超出其声明的要求。

## Freeze declaration

此文件是 Reviewer 3 独立报告。完成后以只读权限冻结，供后续独立综合使用；不因比较或综合结果改写本报告。
