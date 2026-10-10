# 当前研究范围与证据入口

2026-10-10。Windows紧凑研究已完成采样、分析和上传；Mac已独立接收全部21组件、232755文件（29,311,383,786字节）及完整源码bundle。**全量4144项NumPy/R重建正在运行，研究尚未完成。**当前不需要Windows重新执行任何提示词。

## 已完成的独立核验

- [接收与源码核验](WINDOWS-COMPACT-MAC-INTAKE.md)：交付94bebec、冻结执行源3a37a89；253个冻结源文件与原件和Git对象相符。有限技术34项重建及零新增恢复通过。
- [失败审查](../review/WINDOWS-COMPACT-FAILURE-AUDIT.md)：全部432个NUTS任务保留327有效/105未分类失败；已定位部分有效任务的旧ESS分配异常，未据此推断所有失败根因。
- 全部42项原数值失败由实际数组和独立NumPy递推再次核对，仍越过原路径界限，事件失配0；不进入后验统计。
- [双峰伴随分析](MIXTURE-EXPLORATION-COMPANION.md)：412份有效拟合中的411份无保存状态符号穿越而合并比例恰为1/2；保留唯一例外及20个原失败，不把共享初值计作收敛证据。
- [当前文稿](MANUSCRIPT-COMPACT-COMPANIONS.md)：15页中文正文、24页补充材料已编译，完整最终统计尚未纳入。

## 当前剩余任务

| 工作包 | 下一步 | 完成依据 |
|---|---|---|
| F3 独立正式重建 | 完成4144项、真实恢复、全模型统计及跨系统差异审阅 | 原数组→NumPy/R→完整统计；无读取缺口，失败分母不变 |
| F4 R使用费用 | 重建进程退出后执行已冻结有限计时 | 32个新R进程、最多64次技术调用；普通/审计区分，不新增正式重复 |
| F5 可复现交付 | 从独立统计重建正文主表图、完整结果附录及便携构建材料 | 版本、输入、输出校验与搬移重建记录 |
| F6 论文收尾 | 更新主结果、摘要与讨论，检查整份PDF及证据映射 | 限定范围的贡献和负结果；作者终审另列 |

[当前研究计划](RESEARCH-COMPLETION-PLAN.md)、[工作登记](../execution/COMPLETION-WORK-PACKAGES.md)与[机器状态](../execution/CURRENT-SCOPE.json)共同记录进展。跨平台汇总和正文结果生成器见[重建审查](COMPACT-RECONSTRUCTION-REVIEW.md)，当前只有明确标记的预览。独立统计不得用预览替代。

## 使用范围

统一开发分支为`codex/research-integration`；安装候选Python 0.2.0.dev2 / R 0.2.0.9002。历史和正式实验各自绑定原源码，不能用候选版号替代实验身份。

| 使用需求 | 支持范围与入口 |
|---|---|
| Stan模型 | BridgeStan CPU顺序RWM/MALA；[安装说明](INSTALL-AND-USE.md)。没有Stan自动转JAX/torch或时间并行；Windows原生Stan编译未验收 |
| 明确的原生目标 | [能力矩阵](CAPABILITIES.md)：JAX CPU、torch CPU/CUDA对应MH组合；Picard配RWM，quasi-DEER配MALA |
| NUTS | BlackJAX入口；Pyro CPU四进程为独立研究CLI，不是R包通用torch NUTS；GPU NUTS未接入 |
| 新增目标 | [Poisson安装版示例](EXTENDING-TARGETS.md)已在Mac实测；[水井案例](WELLS-TARGET-VALIDATION.md)另有Windows CPU/CUDA/R核验 |
| 实验管理 | 正式运行依赖Python CLI与冻结协议；`pb_benchmark()`只组织配置列表 |

Windows使用原生Windows 11、Python和PowerShell，旧WSL交接仅为历史。源码、摘要与第一方图件进入Git；原始大文件保留在分块归档。Windows草稿Release尚未自动公开，私有技能和第三方全文不进入仓库。

历史Mac1920项、Windows首轮512项、机制与安装证据均保留，其独立单位、配置和时间边界不能与紧凑研究混算。[前期状态记录](CURRENT-SCOPE-through-2026-10-10-intake.md)完整保存此前条目，仅供追溯，不作为新执行命令。
