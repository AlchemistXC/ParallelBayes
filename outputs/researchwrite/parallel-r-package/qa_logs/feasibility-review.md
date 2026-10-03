# R 包构想的软件可行性专项审查

审查日期：2026-10-03（Asia/Tokyo）。对象：用户提供的 ChatGPT 评价与开发路线。范围：模型入口、导数与执行契约、代码复用及实施顺序。依据为官方文档和当前公开源代码；本次没有安装或运行这些采样器，也没有确认任何速度收益。本报告为独立专项审查，未接触另一专项审查的结果；并非外部真人专家意见。

## 判断与最重要的修改

该构想有可实施的核心，原评价关于“不先开发通用语言”“模型—核—执行方式分离”“同核执行比较与跨核推断比较分开”的判断成立。但“首版以 Stan 为主要入口”应拆成两个决策：**面向用户的模型入口可以以 Stan 为主；用于验证时间并行机制的第一条实现路径应优先使用原生 JAX。** 先在原生 JAX 内形成两种执行方式的同后端闭环，再增加 BridgeStan 的独立 CPU 路线。否则，研究尚未证明有可测量增量，工程就同时承担 R、Stan C++、JAX 以及 Julia/MATLAB 代码适配。

这是实施顺序的建议，不是已由性能实验验证的最优架构。JAX 的优势是否抵过编译和调参成本仍需实测。

## P0

无。当前是研究计划，没有足够证据认定存在不可修复的设计错误。以下 P1 项会影响实施路线或比较有效性，应在承诺完整开发周期前解决。

## P1：必须修改的事项

### F1. “HVP 可用”不能等同于“自动微分 HVP 可用”

**位置：原评价第二、三节；模型能力表。已证实，证据强。** BridgeStan 的 R 接口确实暴露密度、梯度、Hessian、HVP 和坐标变换。但默认 Hessian 采用有限差分；官方文档要求以 `BRIDGESTAN_AD_HESSIAN=true` 启用嵌套自动微分，部分隐式函数或 ODE 模型不支持该路线。同一进程不宜混用相关编译设置。源代码确认 HVP 也按这一编译开关选择 `hessian_times_vector` 或 `finite_diff_hessian_times_vector_auto`。

证据：[R API](https://roualdes.us/bridgestan/latest/languages/r.html)、[编译设置](https://roualdes.us/bridgestan/latest/getting-started.html#autodiff-hessian-calculations)、[model.hpp，核查提交 fdd18fd](https://github.com/roualdes/bridgestan/blob/fdd18fdb566416e575feb6e3c6c01195e7d1ad4d/src/model.hpp)。

**修改：** 能力声明至少记录 `derivative_method = analytic/autodiff/finite_difference`、导数阶数、所需变换、精度和编译选项；用有针对性的导数一致性检查验证，而不是只有 `has_hvp = TRUE`。不能预先把有限差分与 JAX JVP 的成本和误差视为同一种输入条件。ODE 等昂贵似然应作为后续压力测试，不能仅凭“支持 Stan”纳入首版 Newton 路线。

### F2. Newton 路线需要的是转移映射导数，且上游使用了接受分支的替代导数

**位置：原评价第三节导数警告、第四节 quasi-DEER 优先实现。已证实，证据强。** 该评价已经指出密度 HVP 不等于完整转移导数，但还应具体说明上游实现。当前 `samplers.py` 的 `sigmoid_accept` 前向值仍是硬阈值接受判定，通过 `stop_gradient` 使求导采用 sigmoid 替代导数。`qdeer.py` 对完整递推作 JVP，并以随机 Rademacher 方向估计 Jacobian 对角线；这不是仅将 Hessian 对角线传给求解器。

证据：[samplers.py 第 15–17 行及 MALA 递推](https://github.com/lindermanlab/parallel-mcmc/blob/5e5b637b1214580d0be4e495215e0e5ed6eb2688/src/samplers.py#L15)、[qdeer.py 第 173 行及 245–250 行](https://github.com/lindermanlab/parallel-mcmc/blob/5e5b637b1214580d0be4e495215e0e5ed6eb2688/src/qdeer.py#L173)。

**修改：** 执行器契约除密度导数外，应指定递推函数、前向接受规则、线性化/替代导数规则及求解器随机性。提议噪声、接受均匀数与随机 Jacobian 估计器应有分开的随机流。前向硬接受规则没有因 sigmoid 求导而直接改成 Barker 核；但是否最终恢复目标递推仍需收敛与分支核验。不要把替代导数宣称为非光滑 MH 映射的普通解析 Jacobian。

### F3. 上游返回轨迹并不意味着求解已经通过验证

**位置：原评价第三节失败处理、第五节轨迹一致性。已证实的源代码行为，证据强；实际影响尚未实测。** 当前 `qdeer.py` 与 `windowed_qdeer.py` 按 dtype 内置绝对/相对容差，主要使用相邻迭代差作为推进或终止依据。两者含坐标裁剪以及将 NaN 改成零的迭代逻辑。常规返回值是轨迹和迭代次数，窗口版未把最终推进位置作为独立成功状态返回。这不证明论文结果错误，但足以说明不能不加审计地封装为通用稳定采样器。

证据：[qdeer.py 第 176–243 行](https://github.com/lindermanlab/parallel-mcmc/blob/5e5b637b1214580d0be4e495215e0e5ed6eb2688/src/qdeer.py#L176)、[windowed_qdeer.py 第 179–286 行](https://github.com/lindermanlab/parallel-mcmc/blob/5e5b637b1214580d0be4e495215e0e5ed6eb2688/src/windowed_qdeer.py#L179)。

**修改：** 第一阶段应先补齐求解审计：用户可见容差、最大迭代、停止原因、完成长度、真正递推残差、接受事件差异，以及裁剪/非有限值修复次数。应保留上游行为用于复现实验，并另设严格生产输出判定。小迭代差本身不是小递推残差，更不是严格轨迹证明。裁剪是迭代稳定化手段时，不应自动认定它改变了最终目标；真正需要验证的是返回解是否仍满足原递推及原分支。

### F4. ParallelMH 不是开箱即用的 R/JAX 通用并行依赖，许可也尚未明确

**位置：原评价第四节“先复现并记录版本，再包装、适配或重写”。已证实，证据强。** 实时 GitHub 树为 `b03ef0f3a46947d0253c75e41cd7d060c6aa1111`。其 `src/online_picard.jl` 使用 Julia；`refresh!` 虽标注可并行，实际是普通 `for`，`solve_path!` 也是顺序循环。另有 MATLAB 的 ODE 实验例程，包含限定 14 个 worker 的 `parfor`。因此，“存在公开代码”支持算法复现，不支持“现成通用并行内核可直接接入”的判断。实时仓库 API 的 `license` 为 null，递归文件树未列出许可证文件；当前未确认可再分发许可。

证据：[Julia 核心](https://github.com/SebaGraz/ParallelMH/blob/b03ef0f3a46947d0253c75e41cd7d060c6aa1111/src/online_picard.jl)、[MATLAB 例程](https://github.com/SebaGraz/ParallelMH/blob/b03ef0f3a46947d0253c75e41cd7d060c6aa1111/Parallel_Picard_Sec_6_8/ONLINE_PICARD.m)、[仓库元数据](https://api.github.com/repos/SebaGraz/ParallelMH)、[完整树](https://api.github.com/repos/SebaGraz/ParallelMH/git/trees/b03ef0f3a46947d0253c75e41cd7d060c6aa1111?recursive=1)。

**修改：** 明确选择“原作者环境中的结果复现”和“依据论文独立实现 CPU/JAX 执行器”两项工作。若直接复制或派生分发其代码，先核实授权；公开可读不自动提供再分发许可。可依据论文独立实现并保留来源说明，不必让许可问题阻止所有科学验证。[GitHub 许可说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)。这项建议只适用于代码复用范围，不是要求用户为阅读公开代码再确认。

### F5. 并发安全必须实现到 C ABI 和模型生命周期，而非只设置 workers

**位置：原评价第三节 R/CPU/Python 分层与示例 API。已证实的约束，实施方案为推断。** BridgeStan 文档允许同一模型并发求值，但要求 `STAN_THREADS=true`；同进程所有模型的线程编译设置须一致。R 前端通过 `.C` 逐次调用，接口本身不是向量化或线程调度器；R 模型对象保存进程内资源，不能把其原始指针跨进程序列化当作可用模型。C API 提供模型创建/销毁、独立 RNG 和错误缓冲区等明确生命周期。输出回调在目前 C++ 实现中还是全局对象。

证据：[线程编译设置](https://roualdes.us/bridgestan/latest/getting-started.html#enabling-parallel-calls-of-stan-programs)、[R FFI 说明](https://roualdes.us/bridgestan/latest/internals/ffi.html#r)、[R 源码](https://github.com/roualdes/bridgestan/blob/fdd18fdb566416e575feb6e3c6c01195e7d1ad4d/R/R/bridgestan.R)、[C API](https://roualdes.us/bridgestan/latest/languages/c-api.html)、[输出回调源码](https://github.com/roualdes/bridgestan/blob/fdd18fdb566416e575feb6e3c6c01195e7d1ad4d/src/bridgestan.cpp#L122)。

**修改：** R 层以整段轨迹或批量求值调用本地 C/C++ 执行器；worker 内不调用 R API 或 R 的 RNG。进程式并行在各进程创建模型；线程式并行固定 ABI/编译标志，并为可变 RNG、输出缓冲和临时工作区明确所有权。还应限制 BLAS、Stan 内部线程与外层 worker 的嵌套超额订阅。具体对象共享策略须由压力测试与实际后端实现确认，不能仅以文档支持线程安全推导任意 R 封装均安全。

### F6. 计划低估了兼容性和代码审计成本，时间表只能视为情景估计

**位置：原评价第八节阶段表。已证实前提＋工程推断。** `parallel-mcmc` 是 BSD-3-Clause，可在遵守声明条件下复用；README 明确其效率收益以 GPU 为目标，CPU 主要用于测试，已测试的 JAX 版本为 0.5.3/0.6.2。当前 `pyproject.toml` 还声明 TensorFlow、TFP、inference_gym 等依赖，并未锁定这些版本。这是值得复用的研究代码，但尚不能仅靠 reticulate 安装一句话推导成可移植的 R 产品依赖。

证据：[固定提交 README](https://github.com/lindermanlab/parallel-mcmc/blob/5e5b637b1214580d0be4e495215e0e5ed6eb2688/README.md)、[依赖声明](https://github.com/lindermanlab/parallel-mcmc/blob/5e5b637b1214580d0be4e495215e0e5ed6eb2688/pyproject.toml)、[BSD-3-Clause 许可](https://github.com/lindermanlab/parallel-mcmc/blob/5e5b637b1214580d0be4e495215e0e5ed6eb2688/LICENSE)。

**修改：** 用户已确认拥有 Mac，以及 AMD CPU + RTX 5080 的 Windows 11 台式机。建议 Mac 先做 CPU 正确性开发，台式机先在 WSL2 内预验证 JAX GPU；正式 CPU/GPU 对照尽量在该台式机的同一 WSL 环境内运行，以减少操作系统差异。JAX 当前支持表把原生 Windows NVIDIA GPU 标为不支持、WSL2 标为 experimental；NVIDIA 将 RTX 5080 列为 compute capability 12.0，并提供 CUDA on WSL 路线。这里是文档可行性，不代表这台机器已经验证成功；只有 WSL 实测不稳定才考虑原生 Linux，不需要据此更换显卡。[JAX 安装支持表](https://docs.jax.dev/en/latest/installation.html)、[NVIDIA GPU 表](https://developer.nvidia.com/cuda/gpus)、[CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)。

把“上游按原环境复现”“最小审计包装”“跨版本/跨平台安装”分成验收门槛。在 F1–F5 尚未解决前，不确认原评价的 13–22 周总投入是可靠排期。第一阶段应以结果门槛而非固定周数结束。

## P2：应保留但进一步限定的建议

1. **JAX 回调与 GPU 的区分正确，但不应扩大成“FFI 不可能高效”。** 官方说明 `pure_callback` 在主机执行，GPU 输入/输出涉及传输与同步；CPU 可以避免部分数据传输成本。JAX 的 FFI 可调用本地 CPU 或 CUDA 内核，但需自行提供对应平台实现，以及导数、批处理和分片规则；挂接 Stan CPU 函数并不会自动生成 CUDA。建议首版避免把这一桥接作为核心 GPU 路线，保留今后单独评估的可能。[回调](https://docs.jax.dev/en/latest/external-callbacks.html)、[FFI](https://docs.jax.dev/en/latest/ffi.html)。已证实，证据强；具体开销需实测。

2. **Stan 优先是当前研究范围下的工程选择，不是语言优劣结论。** NIMBLE 官方接口确实支持 NUTS，可对连续节点配置 HMC，离散节点使用其他采样器，并有参数变换系统；因此原评价对 BUGS 风格梯度能力的纠偏正确。若科学问题改变为结构化局部 Gibbs、离散连续混合模型，应重新评估 NIMBLE；在当前固定维度连续目标与 JAX 时间并行路线下，不建议首版同时承担这个入口。[nimbleHMC](https://search.r-project.org/CRAN/refmans/nimbleHMC/html/configureHMC.html)、[参数变换](https://r-nimble.org/manual/cha-AD.html)。

3. **模型身份还应包含构造随机性。** BridgeStan 的构造 seed 可用于 `transformed data` 中的随机操作。两个相同文件/数据的模型若构造随机种子不同，未必是同一个已实例化目标。因此目标 hash/记录应含模型构造 seed 或禁止首版模型内随机 transformed-data 计算。Generated quantities 的 RNG 也应与采样驱动流分离。[C API 模型构造及 RNG](https://roualdes.us/bridgestan/latest/languages/c-api.html)。

4. **支持矩阵应描述具体组合。** “Stan CPU 可用”“JAX GPU 可用”“HVP 可用”并不能组合推出 `Stan + windowed quasi-DEER + GPU` 可用。应按模型 provider × kernel × executor × dtype × device 给出已实现、已测试、明确不支持的组合；示例中的 RWM + Online Picard + BridgeStan CPU 可以作为拟议目标，暂不能写成已证实兼容的调用。

## 调整后的最小验收顺序

1. 用两个原生 JAX 连续目标，在固定实际随机输入下复现顺序 MALA 与 quasi-DEER；独立记录上游输出、求解残差、接受分支、迭代及编译/执行时间。这个阶段不需要新语言或完整 R 包。
2. 增加同后端 Picard 原型，或先将 Picard 限定为 CPU 路线并明确不做跨后端机制归因。将算法复现与真实硬件并行实现分别验收。
3. 建立 BridgeStan CPU 接口和对应目标的跨实现一致性测试，暴露 F1 的导数来源与 F5 的并发边界。
4. 再封装 R 控制层及最少支持矩阵。在该矩阵内开展公平基准，之后才决定是否需要更广语言入口或配置选择器。

以上顺序保持原计划的科学目标，但不会将“Stan 主入口”和“所有研究必须从 Stan 数值内核开始”绑定。

## 评分与不能由现有材料确定的事项

评分为此专项的工作判断，不是验证后的软件评价，满分 5：问题收窄 **4/5**（避免造新语言合理）；架构分层 **4/5**（需补转移导数与保证能力）；现成组件可复用性 **3/5**（上游代码、依赖、许可和 CPU 并行仍需处理）；当前排期可信度 **2/5**（没有环境复现、实际实现量和硬件预算）。

已知硬件为 Mac 与 AMD CPU + RTX 5080 的 Windows 11 台式机。尚不能确认：准确 CPU 型号、内存/显存可用预算和驱动/WSL 配置；JAX/TFP 依赖组合在该平台是否稳定；预期模型中可用的高阶导数比例；各执行器真实的求解失败率与修复代价；CPU/JAX 跨后端一致性阈值；首个发表结果需要的实现规模。上述问题需要小规模实测或作者提供资源约束，不应在审核中虚构答案。

检索版本记录：BridgeStan `fdd18fdb566416e575feb6e3c6c01195e7d1ad4d`；parallel-mcmc `5e5b637b1214580d0be4e495215e0e5ed6eb2688`；ParallelMH `b03ef0f3a46947d0253c75e41cd7d060c6aa1111`。滚动官方文档访问日期同审查日期。旧缓存仓库页面与当前源码不一致时，上述固定提交源码和实时 API 优先。
