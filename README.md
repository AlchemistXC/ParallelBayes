# ParallelBayes

2026-10-07 当前论文：[26页中文稿](output/software-paper/软件与基准研究-Windows机制整合.pdf)已纳入192项Windows机制工作流、批次运行和新环境安装实测；[修订及重建证据](docs/WINDOWS-FOLLOWUP-MANUSCRIPT.md)包含六段逐字节重建、完整配置与全拒绝记录。正式推断实验及投稿终稿仍未完成。

2026-10-07 报告接口：完整任务读取、配对统计和[报告生成及规模核验](docs/FORMAL-REPORT-SCALE.md)已实现。九模型人工标量夹具覆盖41,472主任务/9,216缓存槽位，45图/99面板及85页测试PDF已核验；没有新增采样或科学结果。实际v2 Windows验收与正式研究仍待证据。当前[Windows提示词](handoff/windows-completion/CODEX-PROMPT-FORMAL-VALIDATION.md)一次全文提供、按阶段执行；不重跑已完成的F2、旧运行器和安装任务。以下日期段落保留历史状态。

2026-10-07：Windows 三条后续分支已合入并完成[独立接收核验](docs/WINDOWS-FOLLOWUP-INTAKE.md)。五归档7,658文件、1,080份保存MH路径的独立NumPy重放、机制CSV及R诊断重建通过。F2、有限运行器和候选安装门槛已取得证据；正式推断协议/执行及最终论文仍待完成。旧F2／运行器／安装提示词无需再跑。

2026-10-06 当前稿：修复历史CPU段与Windows能力的矛盾表述，完成[五段结果及PDF重建](docs/CURRENT-RESULT-REBUILD.md)，见[23页中文稿](output/software-paper/软件与基准研究-结果重建.pdf)。本次仅重建已保存摘要，未新增实验；正式推断研究仍待完成。

2026-10-06 文献后继：已补核直接软件前作与现代多链方法，见[定位复核](review/文献定位复核_2026-10-06.md)和[23页中文文献修订稿](output/software-paper/软件与基准研究-文献修订.pdf)。结果与协议不变；正式研究仍待完成。

时间并行MCMC的可核验实现、R控制接口与单机基准。本整合开发分支为 **0.2.0.dev2 / R 0.2.0.9002**，实验证据仍按原 **0.2.0.dev1** 归属；历史发布内核 **0.1.1**，Mac CPU主实验使用独立归档的 **0.1.0**。软件与论文均为研究候选，尚非投稿终稿。

## 当前研究阶段

2026-10-05：进入[研究收尾F0–F6](docs/RESEARCH-COMPLETION-PLAN.md)，实际状态见[当前工作包](execution/COMPLETION-WORK-PACKAGES.md)。Windows首轮开发、512项数值实验和回传审查已完成，不能再按初次移植提示词从头开发。

Windows第二轮`ced54ef`已接收并完成[独立核验](docs/WINDOWS-ROUND2-INTAKE.md)：F1、水井、九目标CPU NUTS及CPU/CUDA MH就绪证据已取得；跨系统逐位变换差异保留。当时F2的输入阻塞现已解除：后续192工作流已完成并经独立接收；[原机制续跑提示词](handoff/windows-completion/CODEX-PROMPT-F2-RESUME.md)仅保留历史。无需重跑已完成任务。

本机[批次与最大形状验收](docs/BATCH-MAXIMUM-VALIDATION.md)已完成14/15项，最大NUTS中断记录保留；零重算及搬移归档重建通过。最大MH技术验收不替代正式推断研究。 [成本与误差接口](docs/FORMAL-COST-POLICY.md)已补齐失败/未知时间及逐函数配对处理，正式研究尚待Windows运行门槛与协议冻结。

[测量设计v0.2](docs/FORMAL-MEASUREMENT-DESIGN.md)、[缓存配对统计](docs/CACHE-PROBE-ANALYSIS.md)及[真实CPU缓存记录接收](docs/CACHE-PROBE-EXECUTION.md)已完成有限核验；后继 [Mac 测量运行器](docs/OWNED-CACHE-RUNTIME.md)已完成 20 任务/80 执行及 600 文件零重算、762 资产搬移重建；Windows 原生27主任务、24探测/96调用现已完成并经[独立接收](docs/WINDOWS-FOLLOWUP-INTAKE.md)。技术重放不增加独立重复数。 后继[失败归档接收](docs/OWNED-CACHE-FAILURE-EVIDENCE.md)已保留未启动、资源失败与中断状态，并要求外层完整结束后才产生可用缓存点；21 项相关检查及旧结果重建通过。

当前统一开发入口为 `codex/research-integration`，已合入软件安装候选、测量运行器和失败证据接收。原分支及冻结实验保留；整合检查见[统一交付记录](docs/RESEARCH-INTEGRATION.md)。Windows 安装候选现已完成[实测及接收](docs/WINDOWS-PACKAGE-CANDIDATE.md)，Python129检查、R显式4测试56断言通过，默认跳过单列。

本轮已完成[有限参考复用审计](docs/REFERENCE-REUSE.md)、[水井Mac模型/R核验](docs/WELLS-TARGET-VALIDATION.md)和参考伴随分析。[独立调参](docs/F3-TUNING-RESULTS.md)212/216有效、失败保留；[九目标多预算pilot](docs/F3-BUDGET-PILOT-RESULTS.md)323/324满足各自输出标准，1项长路径容差失败已完成[有限定位](docs/BUDGET-PATH-LOCALIZATION.md)，仍保留失败。诊断仍显示H1发散、M1探索不足及稀有事件未判定。正式推断协议、Windows同机比较和统一发布/论文尚未完成。

**本开发分支已完成原生PyTorch后端及RTX 5080实测。** 新协议512项CPU/CUDA任务通过数值输出核验，65项CPU和63项CUDA测试通过；详细结果、负例与限制见[Windows实测报告](docs/WINDOWS-RESULTS.md)和[安装/运行说明](docs/WINDOWS-NATIVE.md)。许多短链尚未混合，数值核验通过不等于推断收敛。`handoff/windows-native`保留移植前交接状态；历史`handoff/gpu`仅是WSL/JAX归档。

## 当前支持范围

| 模型提供方式 | 顺序RWM/MALA | Picard RWM / quasi-DEER MALA | NUTS |
|---|---|---|---|
| Stan/BridgeStan CPU | 支持 | 不支持 | 不支持 |
| 明确实现和核验的原生JAX目标 | 支持 | 支持相应组合 | BlackJAX |
| 原生Windows PyTorch CPU/CUDA | 内置目标已实测 | 相应组合已实测，eager Python控制 | GPU未接入；独立研究CLI的Pyro CPU九目标串行/spawn就绪核验通过 |

完整[能力矩阵](docs/CAPABILITIES.md)、[计算契约](docs/COMPUTATION-CONTRACT.md)、[Mac安装与使用](docs/INSTALL-AND-USE.md)、[新增Poisson目标示例](docs/EXTENDING-TARGETS.md)。本开发版本支持torch/NumPy独立导入，JAX依赖移至可选安装；CUDA torch构建须按[Windows说明](docs/WINDOWS-NATIVE.md)安装并验证。

## 已完成的CPU研究

- 1920项正式任务、320次正式SBC拟合、72项补充机制任务全部留档，负结果保留。
- 两条时间执行路线的所有模型—预算组中位缓存速度比均未达到1；这不是CPU普遍无收益的证明。
- 同64组数据的解析SBC覆盖54/64；完成1928次拟合的现代Rhat/ESS诊断。NUTS发散集中于H1，M1无发散仍有探索问题，L2参考符号事件保持不可判定。
- 40组历史随机输入的版本对照接受事件零失配；不据此宣称0.1.0/0.1.1性能等价。
- 独立Python环境、迁移目录及完整归档重建通过；仍共享同一Mac、R库和编译器，不声称外部团队或异构平台已复现。

阅读[当前26页中文稿PDF](output/software-paper/软件与基准研究-Windows机制整合.pdf)、[LaTeX与完整输入](manuscript/software/软件与基准研究.tex)、[CPU审查修订报告](docs/CPU-REVIEW-REVISION.md)、[版本衔接](docs/VERSION-BRIDGE.md)。当前26页稿纳入后续机制及安装实测并完成[六段重建与编译](docs/WINDOWS-FOLLOWUP-MANUSCRIPT.md)；[旧23页稿](output/software-paper/软件与基准研究-结果重建.pdf)及其[独立输入搬移构建](docs/MANUSCRIPT-INTEGRATION.md)保留；[旧21页稿](output/software-paper/软件与基准研究-收尾修订.pdf)及[原20页回传稿](output/software-paper/软件与基准研究.pdf)保留。正式推断与最终投稿稿仍未完成。历史CPU稿保留于Git历史和CPU复现Release。原[中文综述](manuscript/中文综述.tex)独立保留，文献结果不与新实验混同。

## 原始证据与复现

Git包含源码、完整测试、冻结协议、分析摘要、论文/图件及历史内核源；**不把5GB原始数组放进Git历史**。完整三部分复现包在[cpu-review-v1 Release](https://github.com/AlchemistXC/ParallelBayes/releases/tag/cpu-review-v1)，大证据tar按512MiB分块；用仓库内SHA256清单重组，见[交接说明](handoff/windows-native/README.md#数据与证据)。新模型和后端开发无需等待下载全部历史证据。

解压完整CPU复现包到独立目录后，按[独立复现说明](docs/PORTABLE-REPRODUCTION.md)从根目录运行`reproduce.py`；校验、分析、1928项诊断重算、绘图和论文编译均有实际记录。仅克隆Git并不包含全部原始证据，不能跳过缺失输入继续声称完整重建成功。

## 许可与发布范围

原始构想与历史选题讨论保留在[研究材料](materials/README.md)，属于待核验的历史资料，不是当前操作指令。

本项目源码采用[MIT](LICENSE)，上游quasi-DEER比较源码保留BSD许可，详见[第三方说明](docs/THIRD-PARTY.md)。本仓库不分发第三方论文/书籍PDF、全文提取、私有技能源码、虚拟环境或缓存。文献引用、研究摘要和本项目原创稿件另保留。

R包作者/维护者元数据仍是项目占位，不是正式CRAN发布。GPU声明限于已保存并核对的Windows实测组合；没有自动配置选择器、任意Stan转GPU或通用加速声明。Windows结果包已上传`windows-native-v1`草稿Release并通过接收端校验；未代用户将草稿公开。首次复核见[回传复核报告](docs/WINDOWS-RETURN-AUDIT.md)，后续见[中位数敏感性最小复现](docs/DIAGNOSTIC-MIDPOINT.md)、[工作量核算](docs/WINDOWS-MECHANISM-ACCOUNTING.md)和[伴随重建入口](docs/COMPANION-REPRODUCTION.md)。

自定义技能迁移见[Windows技能安装说明](handoff/windows-native/SKILLS-SETUP.md)。30个技能的正文以私下ZIP转交；公开仓库仅含清单、校验和及安装脚本。

外部水井案例的后续参考证据见[有限参考复核](docs/WELLS-REFERENCE-AUDIT.md)和[独立二维积分](docs/WELLS-QUADRATURE.md)。两者不代替Windows目标核验或正式推断实验。

第二轮Windows交接：[可直接转交的提示词](handoff/windows-completion/CODEX-PROMPT-F2-F4.md)，包含F1回执、水井CPU/CUDA/R核验和已冻结机制pilot；[试验设计及Mac运行器证据](docs/MECHANISM-PILOT.md)。Windows第二轮和后续F2均已回传并核验；本段提示词为历史索引，下一步是新正式协议的准备。

F3成熟基线的新增[Windows CPU NUTS核验提示词](handoff/windows-completion/CODEX-PROMPT-F3-NUTS.md)已就绪。[Mac九目标配对验证](docs/NATIVE-NUTS-READINESS.md)通过样本/预热/RNG字节检查，短链不利诊断保留；Windows同项实测已回传并核验，见第二轮接收报告。这是独立研究CLI，不扩充R包核心的NUTS或GPU支持声明。

已选步长与仿射目标的时间执行组合核验见[SELECTED-MH-READINESS](docs/SELECTED-MH-READINESS.md)：Mac 54工作流/36配对及独立保存数组重放通过，仍有全拒绝链及保留的库警告；Windows CPU/CUDA实测已回传并经第二轮接收核验。下列已选MH提示词仅作历史入口，无需重复执行；Windows原提示词为[已选MH组合提示词](handoff/windows-completion/CODEX-PROMPT-F3-MH.md)，它与CPU NUTS及机制任务分别留证，不是正式推断实验。
