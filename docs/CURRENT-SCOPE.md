# 当前研究范围与证据入口

2026-10-07；本页提供当前入口，带日期的旧报告保留其当时状态。机器可读状态见 [CURRENT-SCOPE.json](../execution/CURRENT-SCOPE.json)，具体验收要求见 [F0–F6计划](RESEARCH-COMPLETION-PLAN.md)。**研究尚未完成**：软件、机制与安装已有实测证据，有限v2原生验收已独立接收，正式共同精度研究尚未冻结或执行。

## 使用哪个版本

统一开发分支为 `codex/research-integration`。当前安装候选是 Python `0.2.0.dev2` / R `0.2.0.9002`，见 [Mac安装验收](RELEASE-CANDIDATE-0.2.md)及 [Windows安装验收](WINDOWS-PACKAGE-CANDIDATE.md)。历史实验各自绑定原源码；安装版号相同或数值文件相同不证明计时等价。

| 使用需求 | 当前入口及范围 |
|---|---|
| Stan模型 | [安装与使用](INSTALL-AND-USE.md)；BridgeStan仅CPU顺序RWM/MALA。没有Stan自动转JAX/torch或时间并行入口；原生Windows Stan编译未验收 |
| 明确的原生目标 | [支持矩阵](CAPABILITIES.md)；JAX CPU或torch CPU/CUDA的对应MH组合；Picard配RWM，quasi-DEER配MALA |
| NUTS | JAX入口使用BlackJAX；Pyro CPU四进程为独立研究CLI，不是R包通用torch NUTS选项；GPU NUTS未接入 |
| 新增目标 | [安装版Poisson扩展示例](EXTENDING-TARGETS.md)；Mac torch/JAX与R已测，该示例Windows/CUDA未测；[水井外部目标](WELLS-TARGET-VALIDATION.md)另有Windows CPU/CUDA/R实测 |
| 正式研究运行 | 独立Python协议、调度及证据工具；`pb_benchmark()`仅运行配置列表，不能替代完整协议冻结、原始记录及检查点 |

Windows路线使用原生Windows 11和原生Python/PowerShell。旧 `handoff/gpu` 的WSL方案是历史归档；初次移植提示词也不再用于当前续跑。

## 哪些结果已经形成

| 独立证据身份 | 已完成范围 | 限制与证据入口 |
|---|---|---|
| 历史Mac `protocol-v1` / 0.1.0 | 1920项CPU主任务；0.1.1修订和64数据集SBC另有身份 | [CPU修订报告](CPU-REVIEW-REVISION.md)、[版本衔接](VERSION-BRIDGE.md)；负结果、失败和L2参考未定保留 |
| `windows-native-v1` / 0.2.0.dev1 | 512项CPU/CUDA任务、实际数组核验 | [首轮实测](WINDOWS-RESULTS.md)；局部缓存收益不等于推断加速，A1全拒绝和不良诊断保留 |
| 第二轮跨系统/外部目标就绪 | F1诊断最小样例、水井接口、九目标MH/NUTS | [独立接收](WINDOWS-ROUND2-INTAKE.md)；60份原尺度严格跨系统逐位检查失败未改写成通过 |
| `mechanism-windows-pilot-v1` | 192工作流、960技术调用路径；原输入传递后通过核验 | [机制回执](WINDOWS-MECHANISM-COMPLETION.md)、[接收核验](WINDOWS-FOLLOWUP-INTAKE.md)；每模型仅两份独立输入，不能按工作流/重放数扩大n |
| 旧原生运行器有限批次 | 27主任务、24缓存探测/96调用、最大形状及恢复 | [运行验收](WINDOWS-RUNTIME-VALIDATION.md)；仅技术能力，不能替代后继v2适配验收或正式统计重复 |
| 有限v2正式适配验收 | 16原生行为用例；27主任务、24缓存/96调用；Mac51项完整重建、零重算恢复 | [独立接收](WINDOWS-FORMAL-V2-INTAKE.md)；正式重复0，诊断不利及旧失败保留 |
| dev2安装候选 | Mac和Windows新依赖环境、已安装包和R显式集成 | 默认跳过与显式通过分开；不是另一研究团队完整复现 |
| 当前中文稿 | 26页；保存分析记录到六段文本及PDF的独立重建 | [论文与回执](WINDOWS-FOLLOWUP-MANUSCRIPT.md)；源提交2a758ba；旧23页及更早稿保留，正式结论尚未完成 |

人工任务/标量框架、45张图和85页报告用于检验后继分析接口；它们不是科学数据，未写入上述研究结果。[规模核验](FORMAL-REPORT-SCALE.md)与真实研究证据分开阅读。

## 数据在哪里，克隆能得到什么

Git包含源码、测试、协议、分析摘要、第一方图件及论文输入/PDF；不包含完整原始数组、私有技能、环境或第三方受限论文全文。

| 材料 | 当前可用状态 |
|---|---|
| 历史CPU完整证据 | GitHub `cpu-review-v1` Release已公开，18附件；[原始重建说明](REBUILD-RESULTS.md) |
| Windows首轮原始证据 | `windows-native-v1`仍为草稿，5附件；有权限者可取，不能声称公众已可下载 |
| Windows第二轮及后续完整证据 | `windows-completion-v2-20261005`仍为草稿，47附件；新v2回传及后续三分支已接收，见[来源及哈希](WINDOWS-FOLLOWUP-INTAKE.md) |
| 当前论文保存摘要重建包 | 作者本地 `output/research-completion/followup-paper-v1.tar`；64项文件校验，未发布Release；Git中有[清单回执](../benchmark/analysis/outputs/followup-paper-v1/archive-receipt.json) |
| 最终全研究复现包 | 尚未形成；须等正式数据完成后，关联原始证据、分析源码、全部图表和稿件 |

以上公开状态于2026-10-07通过GitHub API核对。解压历史归档时用独立目录，不能覆盖活动检出。保存摘要到PDF成功不等于全部原始轨迹已在本轮重建。

## 下一步及完成条件

当前Windows新入口为 [正式研究提示词](../handoff/windows-completion/CODEX-PROMPT-FORMAL-STUDY.md)：**一次全文提供，按阶段执行**。旧有限v2已由Mac独立接收，不再重跑。正式执行必须从已验收的 `0ba5643a6b580e79b8040f13a5e3165322db0e77` 建立独立干净工作树，先检查存储/环境并冻结全部实际输入，再按预定四批执行。不能在含额外源文件的最新文档检出直接prepare，详见[衔接记录](WINDOWS-FORMAL-V2-INTAKE.md)。

| 门槛 | 剩余必需证据 |
|---|---|
| F0 范围/身份 | 本页、支持矩阵、机器状态与现有文稿已对应；最终发布身份随正式结果确定 |
| F1、F2 | 有限诊断和机制验收已完成；保留数值局限，不重跑已完成任务 |
| F3 | v2实机回执及原数组已独立核验；按资源证据冻结正式协议；再执行并分析共同精度研究 |
| F4 | 水井正式推断比较随F3完成；已参与开发，不能当作未见模型族 |
| F5 | 用最终完整原始证据重建所有主图、主表和PDF，形成互相绑定的软件/分析/数据/论文归档 |
| F6 | 根据真实正式结果重构全文、核对主张和引用；作者、单位、贡献、期刊及最终公开/投稿由研究者确认 |

41,472主任务和9,216缓存探测仍是完整设计草案，不是已执行结果或充分精度保证。本机不能代替Windows运行器实测，没有可访问的Windows实时执行句柄；已接收的活动进程为0只描述回传时的受管理Job；不能代替当前实时观察。Mac约151GiB空闲不足以容纳规划约506GiB主要数组，完整回传存储仍需落实。总目标保持未完成，不自动公开Release、CRAN或投稿。
