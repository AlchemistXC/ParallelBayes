# 限定补充工作登记

2026-10-10，计划v1.0。用户已授权按计划执行。S1已完成80项既有输入重放、图表、恢复与归档核验；S3B已完成固定预算重要性参考及独立复算；S2工具与输入交接已准备，但尚无原生结果；S3A的21项资格检查通过，W1完整包络计算已启动，尚未产生最终认证结果。

| 包 | 状态 | 下一步与验收 | 产物 |
|---|---|---|---|
| P 计划 | 完成 | 范围、输入规则、资源及终态一致；两位独立审查 | docs/TARGETED-FOLLOWUPS-PLAN.md、PLAN.json、selection.json |
| S1 H1函数差 | complete | 80项/3200函数行；恢复新增0；42旧失败不变 | docs/H1-FUNCTION-PATH-RESULTS.md；对应delivery.json |
| S2 NUTS故障定位 | handoff_prepared | 14项便携检查通过；Windows实际通过Job及四条件资格后冻结 | handoff/windows-nuts-localization/README.md；qualification/nuts-portable-qualification.json |
| S3A W1参考 | running | 21项检查通过；冻结后运行两种积分组织，随后独立核对及参考敏感性分析 | benchmark/protocols/w1-reference-enclosure-v1.json；无最终W1认证结果 |
| S3B L2参考 | complete | 2097152正式点+16384试探；633资产恢复不变；96点独立权重核对 | docs/L2-RARE-REFERENCE-RESULTS.md；对应SUMMARY/audit.json |
| 合并 | partial_S1_S3B | H1/L2已写入正文及SI；W1/S2待实际结果 | docs/TARGETED-FOLLOWUPS-PAPER.md；5项报告检查通过 |

每次推进记录命令、源码提交、依赖、输入SHA、passed/failed/skipped数量、数值/资源终止、结果SHA和恢复行为。计划版本不能冒充正式冻结协议；资格未完成就不得运行主体。大数组在Git外，摘要/协议/脚本入Git；新原件单独归档。保留原105/42失败分类，既有完成状态不变。

S1资格：5项错误注入/恢复/函数检查通过、0失败、0跳过；pytest缓存写入因工作树权限产生提示，不影响检查。两份新源码与依赖绑定至`benchmark/protocols/h1-function-path-companion-v1.json`。旧参考与旧协议未修改。

S1完成证据：1,130,496转移，接受事件与符号函数差异0；3200行数组复核；恢复80复用、162资产不变；约46.34 MiB新分析数据。两图最小字号8.5 pt、对齐及碰撞通过。新归档逐成员核验；源码d901e21，完整SHA见benchmark/analysis/outputs/h1-function-path-companion-v1/delivery.json。

S3B：源码691dcfb，协议SHA256 94e0493dc7e4848a0c4bf375e30f53305f5523c26fafa0694c73bf368f1b9562。两套估计1.565478926e−9和1.760479741e−9，相对MCSE0.3635%和7.0674%；全部预设权重门槛通过，仍是近似随机误差。运行约99.56秒，观察RSS约198.02 MiB；恢复新增点/权重块均0。独立复算96点log权重最大差3.64e−12。原414有效、18失败与常量事件诊断均不变。累计21项组件检查通过0失败0跳过；它们不替代Windows原生验收。

L2交付：约178.94 MiB本地tar的660件成员逐项校验；同机独立目录从归档重建7件报告/表格逐字节一致，恢复新提议/权重均0。完整SHA见benchmark/analysis/outputs/l2-rare-reference-is-v1/delivery.json。W1实际目标的两个方向×七个四阶导数通过128-bit独立幂级数包络检查，NumPy与Arb对数目标差2.27e−13；尚无W1后验认证区间。

W1运行更新：执行源码504253c3f1ed5fa890cf213de40f7601b3a6c450；协议在278c04a提交，SHA256为85506f871a4fedb6f1cb30da1d9509afa764d2621e40ee51c48a1a6b44a97d36。21项资格检查通过、0失败、0跳过，明细见qualification/w1-driver-qualification.json。运行命令为`scripts/analysis/run_w1_enclosure.py run --protocol benchmark/protocols/w1-reference-enclosure-v1.json --data <已核验原件>/formal/external --output <补充输出>/w1-reference-enclosure-v1`，使用独立.venv-followups、warnings-as-errors及协议绑定的单线程环境。进度、SQLite检查点和资源记录保存在输出目录；截至本次核对仍在有限域细分，不能提前填写最终认证状态。

S2实现更新：增加scripts/followups中的独立阶段记录、诊断前持久化、受管Job消息/退出/私有内存观察、固定调用登记、原生资格门槛、分阶段协调、只核验恢复、独立分析和导出。14项Mac便携检查通过0失败0跳过；原生测试尚未运行，未新增MCMC调用。输入tar 21,544,960字节，27个文件独立解包逐项相同，SHA256为3b97a221ea8a5a61644f3394474e2ceaf8f0b981803456181a012a99d26f5b12。使用新handoff/windows-nuts-localization/CODEX-PROMPT.md整份提示词；原48调用上限不变。

论文整合：targeted-paper-companion-v1从已核验的9份汇总输入生成4份LaTeX片段。H1保留原失败，L2两套提议、近似MCSE及全部八批结果均列SI；没有主网格重算。5项报告检查通过0失败0跳过；Tectonic 0.17.0编译正文18页、SI37页，新增表格和引用已核对。W1/S2仍未生成最终结论。

论文交付：源码1de637b；论文包17,346,560字节，159输入核验；汇总包798,720字节，26输入核验，五个文件搬移重建一致。两份PDF全部55页文本/72 dpi像素一致，旧67页PDF哈希不变。新归档只保存在本地，未上传。详见targeted-paper-companion-v1/delivery.json。

W1独立核验准备：新增只读有理数端点/分区/汇总/比率及参考敏感性脚本，13项针对性检查通过0失败0跳过；实际21122单元一致性快照通过分区和聚合检查。原432份W1拟合的126/504行敏感性接口开发检查完成，不是终态结果。新增目标评价和MCMC调用均0，原冻结四份积分源码未改，正式会话仍运行。见docs/W1-INDEPENDENT-AUDIT.md及qualification/w1-independent-auditor-qualification.json。

W1结果表准备：新增从完整独立核验生成区间/成本/敏感性表的程序，9项针对性检查通过0失败0跳过，含精确端点向外舍入、未达标保留和搬移重建。实际终态输入尚缺；没有以合成样例或中途检查点填入论文。原积分和Windows状态不变。见qualification/w1-report-qualification-v1.json。
