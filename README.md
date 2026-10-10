# ParallelBayes

带 R 接口的时间并行 MCMC 研究软件。项目将目标、转移核与执行器分开，支持固定实际随机输入下的独立路径核验、成本比较和后验诊断。

2026-10-10：Windows 紧凑研究已完成，Mac 独立接收、4144 项重建、统计比较及中文论文材料已完成。**当前不需要重跑任何 Windows 提示词。** 研究完成指本版约定范围内的计算与材料交付，不代表所有配置收敛或普遍加速；署名、公开原件和投稿由作者决定。

本版完成后的[三项限定补充计划](docs/TARGETED-FOLLOWUPS-PLAN.md)已制定：H1函数差、NUTS故障定位、W1/L2参考改进。现已授权执行；[S1 H1函数分析](docs/H1-FUNCTION-PATH-RESULTS.md)完成，S2/S3继续推进，不重跑原网格。

## 阅读与使用

- [中文正文：17页](output/software-paper/软件与基准研究-审查修订v2.pdf) · [LaTeX](manuscript/software/软件与基准研究.tex)
- [补充材料：34页](output/software-paper/补充材料-审查修订v2.pdf) · [完整结果附录：67页](output/software-paper/完整结果附录-审查修订v2.pdf)
- [研究交付报告](docs/RESEARCH-COMPLETION-REPORT.md) · [当前范围](docs/CURRENT-SCOPE.md) · [收尾计划与完成标准](docs/RESEARCH-COMPLETION-PLAN.md)
- [安装与使用](docs/INSTALL-AND-USE.md) · [原生Windows](docs/WINDOWS-NATIVE.md) · [新增Poisson目标示例](docs/EXTENDING-TARGETS.md)
- [从紧凑原件重建](docs/COMPACT-REPRODUCTION.md) · [历史CPU重建](docs/PORTABLE-REPRODUCTION.md)

- [逐项审核与本轮修订](docs/MANUSCRIPT-REVIEW-V2.md) · [三份论文的便携编译包](output/software-paper/parallelbayes-paper-review-v2.tar)

本轮补全最终配置、逐函数参考、失败分母、参考敏感性与误差—耗时主图，未增加采样或修改冻结结果。

## 本版范围

开发入口为 `codex/research-integration`，Python 0.2.0.dev2 / R 0.2.0.9002。实验仍绑定各自冻结源码；Windows 紧凑执行源为 `3a37a89`、交付为 `94bebec`。

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
