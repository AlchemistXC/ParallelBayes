# 限定补充工作登记

2026-10-10，计划v1.0。用户已授权按计划执行。S1已完成80项既有输入重放、图表、恢复与归档核验；S3B已完成固定预算重要性参考及独立复算；S2输入已准备但尚无原生结果；S3A组件资格通过，W1完整认证尚未执行。

| 包 | 状态 | 下一步与验收 | 产物 |
|---|---|---|---|
| P 计划 | 完成 | 范围、输入规则、资源及终态一致；两位独立审查 | docs/TARGETED-FOLLOWUPS-PLAN.md、PLAN.json、selection.json |
| S1 H1函数差 | complete | 80项/3200函数行；恢复新增0；42旧失败不变 | docs/H1-FUNCTION-PATH-RESULTS.md；对应delivery.json |
| S2 NUTS故障定位 | inputs_prepared | 9输入/3旧轨迹已核验；实现原生插桩及资格后冻结协议 | qualification/nuts-input-preparation.json；无新执行提示词 |
| S3A W1参考 | components_qualified | 有限域8项、目标/导数/尾界5项通过；仍需可恢复积分及完整比率 | docs/W1-ENCLOSURE-METHOD-NOTE.md；无W1认证结果 |
| S3B L2参考 | complete | 2097152正式点+16384试探；633资产恢复不变；96点独立权重核对 | docs/L2-RARE-REFERENCE-RESULTS.md；对应SUMMARY/audit.json |
| 合并 | pending | 独立接收新原件；论文只写已完成结果 | 尚未改动结果正文 |

每次推进记录命令、源码提交、依赖、输入SHA、passed/failed/skipped数量、数值/资源终止、结果SHA和恢复行为。计划版本不能冒充正式冻结协议；资格未完成就不得运行主体。大数组在Git外，摘要/协议/脚本入Git；新原件单独归档。保留原105/42失败分类，既有完成状态不变。

S1资格：5项错误注入/恢复/函数检查通过、0失败、0跳过；pytest缓存写入因工作树权限产生提示，不影响检查。两份新源码与依赖绑定至`benchmark/protocols/h1-function-path-companion-v1.json`。旧参考与旧协议未修改。

S1完成证据：1,130,496转移，接受事件与符号函数差异0；3200行数组复核；恢复80复用、162资产不变；约46.34 MiB新分析数据。两图最小字号8.5 pt、对齐及碰撞通过。新归档逐成员核验；源码d901e21，完整SHA见benchmark/analysis/outputs/h1-function-path-companion-v1/delivery.json。

S3B：源码691dcfb，协议SHA256 94e0493dc7e4848a0c4bf375e30f53305f5523c26fafa0694c73bf368f1b9562。两套估计1.565478926e−9和1.760479741e−9，相对MCSE0.3635%和7.0674%；全部预设权重门槛通过，仍是近似随机误差。运行约99.56秒，观察RSS约198.02 MiB；恢复新增点/权重块均0。独立复算96点log权重最大差3.64e−12。原414有效、18失败与常量事件诊断均不变。累计21项组件检查通过0失败0跳过；它们不替代Windows原生验收。

L2交付：约178.94 MiB本地tar的660件成员逐项校验；同机独立目录从归档重建7件报告/表格逐字节一致，恢复新提议/权重均0。完整SHA见benchmark/analysis/outputs/l2-rare-reference-is-v1/delivery.json。W1实际目标的两个方向×七个四阶导数通过128-bit独立幂级数包络检查，NumPy与Arb对数目标差2.27e−13；尚无W1后验认证区间。
