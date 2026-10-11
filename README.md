# ParallelBayes

带 R 接口的时间并行 MCMC 研究软件。项目将目标、转移核与执行器分开，支持固定实际随机输入下的独立路径核验、成本比较和后验诊断。

2026-10-12：新审读意见已拆为106项并完成v5写作修订，正文按研究问题组织，补入W1分段费用、L1尾ESS敏感性分析和完整R示例。[逐项审核](docs/MANUSCRIPT-REVIEW-V5.md)与[构建验收](docs/MANUSCRIPT-V5-BUILD.md)说明采纳范围及依据。原主实验、v4封存稿和v4一致版中文计划/报告保留，无新正式Windows任务。

2026-10-10：Windows 紧凑研究已完成，Mac 独立接收、4144 项重建、统计比较及中文论文材料已完成。**当前不需要重跑任何 Windows 提示词。** 研究完成指本版约定范围内的计算与材料交付，不代表所有配置收敛或普遍加速；署名、公开原件和投稿由作者决定。

本版完成后的[三项限定补充计划](docs/TARGETED-FOLLOWUPS-PLAN.md)已制定：H1函数差、NUTS故障定位、W1/L2参考改进。四项现均完成计算与独立核验：[H1函数差](docs/H1-FUNCTION-PATH-RESULTS.md)、[NUTS有限定位与Mac审阅](docs/WINDOWS-NUTS-MAC-REVIEW.md)、[W1数值包络](docs/W1-REFERENCE-RESULTS.md)、[L2独立重要性参考](docs/L2-RARE-REFERENCE-RESULTS.md)。[当前交付](docs/TARGETED-FOLLOWUPS-PAPER.md)保留全部历史失败，无需续跑Windows任务。

2026-10-11：第三轮意见已逐项核对并完成v4中文修订。新增稀有事件IID解释、W1中间界和公开R API示例；原实验不改，2次接口技术调用不计正式重复。原件审稿访问仍由作者落实。

2026-10-11投稿候选：内部安装、41组件核验、4144既有分析记录重聚合、全部九目标表图及论文重编译已通过；科学结果保持v4。当前入口为 [候选验收与封存](docs/SUBMISSION-RC1.md)、[完整复现入口](docs/SUBMISSION-REPRODUCE.md)、[作者确认清单](docs/AUTHOR-DECISIONS.md)。分支 `codex/submission-rc1`；固定源码和归档哈希以封存清单为准。外部审稿原件访问尚未验收。

## 阅读与使用

- [当前中文正文v5：16页](output/software-paper/软件与基准研究-审读修订v5.pdf) · [LaTeX](manuscript/software-v5/软件与基准研究.tex)
- [补充Av5：47页](output/software-paper/补充材料A-审读修订v5.pdf) · [补充Bv5：67页](output/software-paper/补充材料B-审读修订v5.pdf) · [全部TeX依赖与构建入口](output/software-paper/parallelbayes-paper-v5.zip)
- [v4封存正文](output/software-paper/软件与基准研究-审查修订v4.pdf) · [v4封存补充](output/software-paper/补充材料-审查修订v4.pdf)
- [研究交付报告](docs/RESEARCH-COMPLETION-REPORT.md) · [当前范围](docs/CURRENT-SCOPE.md) · [收尾计划与完成标准](docs/RESEARCH-COMPLETION-PLAN.md)
- [公开R API示例v5](examples/paper-api-v5.R) · [材料访问清单](docs/REVIEWER-ACCESS.md)
- [安装与使用](docs/INSTALL-AND-USE.md) · [原生Windows](docs/WINDOWS-NATIVE.md) · [新增Poisson目标示例](docs/EXTENDING-TARGETS.md)
- [从紧凑原件重建](docs/COMPACT-REPRODUCTION.md) · [历史CPU重建](docs/PORTABLE-REPRODUCTION.md)

- [逐项审核与本轮修订](docs/MANUSCRIPT-REVIEW-V3.md) · [当前便携论文包与重建记录](docs/TARGETED-FOLLOWUPS-PAPER.md)

本轮加入四项限定补充及独立核验；NUTS技术调用不增加正式重复，原冻结主结果不变。

## 本版范围

当前候选入口为 `codex/submission-rc1`；此前开发入口为 `codex/research-integration`，Python 0.2.0.dev2 / R 0.2.0.9002。实验仍绑定各自冻结源码；Windows 紧凑执行源为 `3a37a89`、交付为 `94bebec`。

| 目标入口 | 顺序 RWM/MALA | Picard RWM / quasi-DEER MALA | NUTS |
|---|---|---|---|
| Stan/BridgeStan CPU | 支持 | 不支持 | 不支持 |
| 明确原生 JAX 目标 | 支持 | 支持对应组合 | BlackJAX |
| 明确原生 torch CPU/CUDA 目标 | 已核验 | 已核验，仍含主机控制 | CPU Pyro为独立研究CLI；GPU未接入 |

详见[能力矩阵](docs/CAPABILITIES.md)。没有任意Stan模型自动转JAX/torch的通用编译器；原生Windows Stan编译未验收。`pb_benchmark()`组织配置，完整实验管理依赖Python CLI。

## 主要证据

3888 主任务保留 3741 有效、42 数值失败、105 未分类失败；256 缓存探测的1024调用不计后验样本。Mac重建全部4144项，接受事件失配0，实际恢复新增分析0。两平台统计的浮点末位差另存，状态、分母和阈值判断没有变化。

普通工作流的同核配对显示Picard收益依设备和模型变化，quasi-DEER全部组更慢。水井的参数误差与成本、H1路径失败和M1均衡初值均进入正文。R前端另有32新进程/64技术调用的直接计时，不扩大正式独立重复。

## 数据与许可

Git保存第一方源码、测试、协议、摘要、稿件和图表。历史CPU原始证据在 `cpu-review-v1` Release；Windows紧凑原件仍在草稿Release，需相应访问权限，不能仅凭克隆源码取得原数组。本轮不自动公开草稿，也不提交CRAN或期刊。

源码采用[MIT](LICENSE)，上游许可见[第三方说明](docs/THIRD-PARTY.md)。第三方论文全文、私有技能和本地环境不发布。原[中文综述](manuscript/中文综述.tex)独立保留。[历史README](README-history-through-2026-10-10.md)保存前期状态，仅供追溯。
