# 当前正文主张与证据

本表维护问题导向版本，2026-10-10同步交付状态。Windows紧凑结果已交付，Mac完整原件接收已通过，全目标统计重建尚未完成；正文先纳入已独立完成的42份数值失败及M1路径伴随分析，不提前纳入全目标性能汇总。新稿中的汇总数字引用下述已经核验的保存记录，不是本轮重新采样。

| 主张 | 依据与边界 |
|---|---|
| 能力矩阵与R用法 | `docs/CAPABILITIES.md`、`docs/EXTENDING-TARGETS.md`、`examples/installed-custom-target.R`、`examples/installed_custom_target.py`；Stan仅CPU顺序MH，Pyro NUTS为独立CLI |
| quasi-DEER 因果恢复 | Gonzalez等 arXiv:2407.19115v3 Proposition 1及推论；仅精确算术、有限矩阵、映射和扫描有定义的确定递推，非浮点/后验误差保证 |
| 代理Jacobian及Picard实现 | `r-package/inst/python/parallelbayes/`及`docs/OPINION-AUDIT-2026-10-09.md`的逐项源码核对；论文伪码门控与实际归档源码分别声明 |
| 历史Mac成本、误差与SBC | `results.generated.tex`、`revision.generated.tex`；对应CPU归档和修订分析。新摘要包中的七个生成器重建一致 |
| Windows首轮执行与诊断 | `windows-native.generated.tex`；`benchmark/analysis/outputs/windows-native-v1/{run-metrics,summary}.json`。四重复为探索性，A1全拒绝保留 |
| 新配对图 | `figures/software-revision/paired-source.csv`；512记录、256对、64组，与上述summary一致；不改变计时边界 |
| Windows机制及跨系统检查 | `followup.generated.tex`、`completion-companion.generated.tex`、`intake.generated.tex`；不是紧凑主研究 |
| 有限v2验收 | `adapter.generated.tex`；27主任务/24缓存，不能作为正式推断证据 |
| 紧凑研究的设计 | `docs/F3-COMPACT-DESIGN-v1.md`及冻结设计，已核对交付提交94bebec及253份冻结源文件；技术组件独立重建通过，完整正式原件文件核验已完成、全量路径/诊断重建进行中，见docs/WINDOWS-COMPACT-MAC-INTAKE.md |
| 42项数值失败 | `benchmark/analysis/outputs/compact-numerical-failure-companion-v1/`：独立NumPy复核原失败路径，42份仍越界，事件零失配；未重新计入样本 |
| M1初始化与符号函数 | `docs/MIXTURE-EXPLORATION-COMPANION.md`：全部432任务原件核对、412有效路径；唯一例外保留。图件选择为事后解释，不是性能比较 |
| 水井正规化及参考 | `docs/WELLS-TARGET-VALIDATION.md`及数据证书；补充材料给四条实际观测、二维短证明。正规化不认证数值求积精度 |

图文自动生成与手写叙述分开：补充生成段继续由原生成器维护，正文汇总修改时须复核本表对应来源，不能用手改生成结果制造一致。
