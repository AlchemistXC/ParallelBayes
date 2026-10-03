# 主张—证据核查表

核查日期 2026-10-03。`evidence-backed` 表示证据支持表中限定表述，不代表本项目已运行验证。软件 `latest/main` 会变；正式复现需锁定版本。既有算法以项目全文卡定位，本輪新论文的访问层级另注明。

| ID | 待审核主张及判断 | 证据/来源 | 强度、用途与风险 | 状态 |
|---|---|---|---|---|
| C01 | 当前综述无原创实验，已有资源配置议程：准确 | [主稿](../../../manuscript/中文综述.tex)，引言、§7.2 | 已读本地正文；可支持研究衔接 | evidence-backed |
| C02 | 做 R 包一定比综述更易形成论文：证据不足 | 无发表概率证据 | 可称候选原创研究路线；不能许诺 | unsupported |
| C03 | compareMCMCs 已能比较 NIMBLE/JAGS/Stan：准确 | [作者仓库](https://github.com/nimble-dev/compareMCMCs) | 官方功能；非性能复现 | evidence-backed |
| C04 | BridgeStan R 暴露密度、梯度、Hessian、HVP：准确但不等于全为 AD | [R API](https://roualdes.us/bridgestan/latest/languages/r.html)、[编译选项](https://roualdes.us/bridgestan/v2.9.0/getting-started.html) | 默认二阶导数有限差分；AD 为可选构建，正式方案要指定实现 | evidence-backed |
| C05 | BUGS 风格无法做梯度推断：不可如此解释语言选择 | [NIMBLE AD 手册](https://r-nimble.org/manual/cha-AD.html) | 官方列出 AD/HMC 及函数限制 | evidence-backed |
| C06 | Stan 直接采样离散参数：不支持；边缘化是有条件替代 | [Stan 文档](https://mc-stan.org/docs/stan-users-guide/latent-discrete.html) | 模型支持边界，不妨碍离散观测 | evidence-backed |
| C07 | BridgeStan 接 JAX 自动获得 GPU：错误；FFI 本身又并非永远只能 CPU | [JAX FFI](https://docs.jax.dev/en/latest/ffi.html)、[Stan ecosystem](https://mc-stan.org/docs/stan-users-guide/ecosystem.html) | 设备实现、导数、批处理须分别提供 | evidence-backed |
| C08 | BlackJAX 可接原生 JAX log density：准确 | [官方文档](https://blackjax-devs.github.io/blackjax/) | 文档对应 main，不能替代版本测试 | evidence-backed |
| C09 | parallel-mcmc 可直接当有成功证书的求解器：不成立 | [仓库](https://github.com/lindermanlab/parallel-mcmc)、[工程核查](qa_logs/feasibility-review.md) | 静态查到裁剪/非有限值替换和返回信息不足；不据此断言论文错误 | evidence-backed |
| C10 | ParallelMH 是现成通用并行库：过强 | [仓库](https://github.com/SebaGraz/ParallelMH)、[工程核查](qa_logs/feasibility-review.md) | Julia 核心循环与 MATLAB 专用并行脚本须区分；当前树未见许可证 | evidence-backed |
| C11 | 已有 ParallelMCMC.jl 接 AbstractMCMC：准确 | [作者仓库](https://github.com/rsenne/ParallelMCMC.jl) | README/API 存在；未复现其扩展性主张 | evidence-backed |
| C12 | BayesForge 已有 R/NumPyro/JAX 路线：准确 | [R 手册](https://cran.r-universe.dev/BayesForge/doc/manual.html) | R 包版本 0.0.1；存在性不等于性能验证 | evidence-backed |
| C13 | BayesForge 只有软件文档可比较：需更新 | [2026-08-14 v2 预印本](https://www.biorxiv.org/content/10.64898/2026.01.19.700318v2) | 已检索到作者页元数据/摘要；直开 403，未全文验证其速度声明 | evidence-backed |
| C14 | Stan→NumPyro 编译完全无前作：错误 | [DeepStan 论文](https://arxiv.org/abs/1810.00873)、[实现](https://github.com/deepppl/stan-num-pyro) | 摘要/仓库级确认；当前语言兼容性未实测 | evidence-backed |
| C15 | 统一模型契约是新的：单独这样说不成立 | [Inference Gym](https://github.com/tensorflow/probability/tree/main/spinoffs/inference_gym) | 已有 shape/dtype、变换、密度、函数、参考量及 MC 标准误 | evidence-backed |
| C16 | 跨模型/跨软件基准是新的：单独这样说不成立 | [PPL Bench](https://github.com/facebookresearch/pplbench)、[Beraha 等](https://arxiv.org/abs/2107.09357) | 仓库/论文摘要；可识别前作，不冒充全文评论 | evidence-backed |
| C17 | posteriorDB 可提供全部函数的精确真值：错误 | [AISTATS 2025 正式论文](https://proceedings.mlr.press/v258/magnusson25a.html)、[仓库](https://github.com/stan-dev/posteriordb) | 参考抽样仍需检查误差；不得将全部模型数视为全部有参考 | evidence-backed |
| C18 | 独立参考使经验误差直接等于算法 MSE：错误 | [统计专项](qa_logs/inference-review.md)，直接代数分解 | 独立无偏参考下仍多参考方差 | evidence-backed |
| C19 | 墙钟截止仅影响计时：错误 | [Anytime Monte Carlo](https://www.cambridge.org/core/journals/data-centric-engineering/article/anytime-monte-carlo/3E8ED0F13E0A1E3AF37D09E1515ABFA2) | 专项读原文 §2/Cor.2；末状态与均值须区分 | evidence-backed |
| C20 | SBC 通过足以证明实现正确：错误 | [Stan SBC](https://mc-stan.org/docs/stan-users-guide/simulation-based-calibration.html)、[Modrák 等](https://arxiv.org/html/2211.02383v3) | 专项查原文数据依赖测试量与盲点 | evidence-backed |
| C21 | 同整数 seed 等于同轨迹输入：错误 | [Newton 精读卡](../../../review/cards/zoltowski2025/paper-card.md)、[Picard 精读卡](../../../review/cards/grazzi2026/paper-card.md) | 需固定实际噪声、坐标与转移规则 | evidence-backed |
| C22 | 短探测自动选执行器会有净收益 | 待预实验和留出验证 | 合理假设；统计保证取决于是否保持同一输出 | hypothesis |
| C23 | 所列周数足以完成全部阶段 | 无团队/安装/重实现实测依据 | 不可作为交付排期；改为验收门槛 | unsupported |
| C24 | JAX 计时需考虑异步、编译、精度：准确 | [官方基准指南](https://docs.jax.dev/en/latest/benchmarking.html) | 同步后外层墙钟计时，分项避免重叠相加 | evidence-backed |
| C25 | 用户 Win11 5080 可直接用原生 Windows JAX GPU：不可这样承诺 | [JAX 支持表](https://docs.jax.dev/en/latest/installation.html)、[NVIDIA WSL 指南](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)、[GPU 架构表](https://developer.nvidia.com/cuda/gpus) | 原生 Windows GPU no，WSL2 experimental；5080 CC12.0，具体软件栈待测 | evidence-backed |
| C26 | JSS 要求源码与全部结果的复现材料：准确 | [正式投稿指南](https://www.jstatsoft.org/guides/submission) | 是必要要求，不是选题/录用保证 | evidence-backed |
| C27 | 原生 JAX 内核先行、Stan 用户入口随后 | 综合 C04–C11、C25 | 针对本项目主线的工程判断，不是通用 PPL 排名 | plausible-inference |

## 计划 v1.0 的设计决定

以下是基于审核制定的实验/工程设计，不伪装成文献发现。

| ID | 决定 | 依据 | 验证及风险 | 状态 |
|---|---|---|---|---|
| C28 | 首批两模型族四任务与变换夹具，先单链小网格 | C18–C21、C27；限制初期工作量 | 维度、样本量、条件数及窗口是预实验设计值，正式协议另行冻结 | plausible-inference |
| C29 | 首版 Stan CPU 顺序入口与 JAX 基准模型时间并行分开 | C04–C11、C27 | 不保证任意 Stan 自动 GPU；能力矩阵依实际测试更新 | plausible-inference |
| C30 | WP04 落实解析统计/SBC 管道，WP06 冻结正式统计验证 | C18–C20；计划统计/工程 QA | 有限 SBC 功效不等于全面正确性证明 | plausible-inference |
| C31 | 选择器测试族在 WP06 封存，否则 WP08 新增未参与开发族 | C22；计划统计 QA | 若已看过结果即不能作为未见测试，需记录访问或降低泛化声明 | plausible-inference |
