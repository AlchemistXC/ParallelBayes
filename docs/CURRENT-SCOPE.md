# 当前研究状态

2026-10-10：本版F0–F6的技术、分析和论文交付已完成。**无需继续任何旧Windows提示词，也不追加正式采样。** 作者署名/单位、数据公开范围和投稿终审另由研究者决定。

[交付报告](RESEARCH-COMPLETION-REPORT.md) · [计划与完成标准](RESEARCH-COMPLETION-PLAN.md) · [复现命令](COMPACT-REPRODUCTION.md) · [机器状态](../execution/CURRENT-SCOPE.json)

- Windows正式3888主任务保留3741有效、42数值失败、105未分类失败；256缓存/1024调用全部留档。
- Mac接收全部21组件、232755文件；4144项独立读取无缺口，恢复新增0、42035资产不变。
- 全模型统计、72个普通费用对照及完整36函数结果已重建。跨系统浮点差别保留，不改变状态/分母/阈值结论。
- R补测32个新进程/64次技术调用通过独立核验，不增加正式重复。
- 中文正文16页、SI27页、完整结果附录66页；便携论文输入在新目录重新编译通过。

## 能力与证据边界

开发分支`codex/research-integration`，Python0.2.0.dev2 / R0.2.0.9002。紧凑冻结执行源3a37a89、Windows交付94bebec；各历史实验继续使用原源码身份。

Stan/BridgeStan仅CPU顺序RWM/MALA；明确原生JAX/torch目标支持对应时间执行；Pyro CPU NUTS是独立研究CLI，GPU NUTS未接入。Windows使用原生Python/PowerShell，原生Stan编译未验收。详见[能力矩阵](CAPABILITIES.md)和[安装说明](INSTALL-AND-USE.md)。

105项进程失败根因未完全确定，L2稀有参考未定，W1求积非认证，压力目标仍有探索不足。它们已作为结果和限制报告，不再以补采或删除失败的方式追求全达标。自动配置器和昂贵新模型是可选新研究。

Windows原始证据仍在草稿Release；当前源码和稿件公开不等于原数组公开。私有技能、第三方全文和本地环境不进入仓库。[历史状态](CURRENT-SCOPE-through-2026-10-10-intake.md)与归档计划仅供追溯，不作为续跑指令。
