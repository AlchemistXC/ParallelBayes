# 限定补充工作登记

2026-10-11状态更新，原计划v1.0。S1、S3A及S3B的计算、独立核验与本地归档已完成；S2固定输入包已上传原Windows草稿，尚待原生资格与有限故障定位证据。W1结果已合入论文并完成便携重建；下文逐次记录保留当时状态，不追溯改写。

| 包 | 状态 | 下一步与验收 | 产物 |
|---|---|---|---|
| P 计划 | 完成 | 范围、输入规则、资源及终态一致；两位独立审查 | docs/TARGETED-FOLLOWUPS-PLAN.md、PLAN.json、selection.json |
| S1 H1函数差 | complete | 80项/3200函数行；恢复新增0；42旧失败不变 | docs/H1-FUNCTION-PATH-RESULTS.md；对应delivery.json |
| S2 NUTS故障定位 | windows_complete_with_resource_failures_intake_pending | Windows21便携+3原生检查通过；4资格通过；36主体34完成/2资源失败，4确认2完成/2资源失败；Mac独立接收待进行 | docs/WINDOWS-NUTS-LOCALIZATION-RESULTS.md；nuts-windows-v1/ |
| S3A W1参考 | complete | 双规则均7/7达标；24资产核验；恢复新增0；归档搬移重建一致 | docs/W1-REFERENCE-RESULTS.md；w1-reference-enclosure-v1摘要与原件 |
| S3B L2参考 | complete | 2097152正式点+16384试探；633资产恢复不变；96点独立权重核对 | docs/L2-RARE-REFERENCE-RESULTS.md；对应SUMMARY/audit.json |
| 合并 | partial_S1_S3A_S3B_complete | H1/L2/W1已交付；正文18页及SI40页通过版式及便携重建；S2待实测 | docs/TARGETED-FOLLOWUPS-PAPER.md；w1-paper-integration-v1.json |

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

W1归档准备：本地完整归档工具的6项检查通过0失败0跳过，覆盖缺件/未完成拒绝、恢复新增评价0、磁盘预留、打包时变化检测与稳定tar哈希。只列入必要源码/数据/旧统计，不复制全部主原件；实际终态归档与搬移重建尚待完成，新增科学评价0。见qualification/w1-archive-qualification-v1.json。

W1方法写作：已完成数值包络的方法与两条原始引用核对，三页独立LaTeX预览编译及全页视觉检查通过；8份冻结数值源码未改。Gauss规则达到协议精度，原会话继续Simpson；尚无最终独立核验或双规则表，不更新正文数值结论。见docs/W1-METHOD-WRITING.md及qualification/w1-method-writing-v1.json。

Gauss完成件独立核对：31533单元、两区域覆盖与精确端点聚合通过，7/7函数达到冻结精度；12份完成件读取前后不变，新增目标评价/MCMC均0。原Simpson会话仍运行，全研究终态及恢复未核验。本次系统Python版本误用在读入前失败，改用原独立环境Python3.12.14通过；错误留存，文档已明确解释器。详见qualification/w1-gauss-completed-method-audit-v1.json与docs/W1-INDEPENDENT-AUDIT.md。

2026-10-11：已启动一次性本地收尾进程，绑定原积分PID与创建时间及源码SHA；只等待现有积分结束，不重启科学计算。计划依次进行完整核验、报告、恢复零新增、本地归档和独立目录重建，任一步失败即停止并留日志。启动时这些阶段均未执行，不预记通过。实际状态在主数据工作区output/targeted-followups-v1/w1-finalization-v1/state.json；小型启动记录见qualification/w1-finalization-launch-v1.json。

S2输入交接（2026-10-11）：用户明确授权后，已追加上传固定输入tar及回执到windows-completion-v2-20261005草稿；两份远端大小/SHA256匹配，原215附件未改，现217件且仍draft。包21,544,960字节，SHA256为3b97a221ea8a5a61644f3394474e2ceaf8f0b981803456181a012a99d26f5b12。下载与核验记录见handoff/windows-nuts-localization/TRANSFER-STATUS.md及github-upload-receipt-v1.json；新增采样0，Windows原生资格与主体仍待实测。

S2路径兼容修订（2026-10-11）：实测旧代码无法在Mac读取含Windows反斜杠的嵌套校验清单。新代码对只读核验兼容旧分隔符、拒绝别名/绝对路径/越界路径，新源码清单、结果路径统一使用POSIX形式，避免向git show传Windows文件名。21项便携检查通过0失败0跳过，含7项新回归；修复前失败日志保留。见qualification/nuts-portable-paths-v1.json。无新增采样；输入tar和W1冻结源码未改。已冻结的Windows工作不得直接合并本修订。

W1终态（2026-10-11）：原积分正常结束，两规则分别31533/37671活动单元、七函数全部达标；全程预留评价1351046次，新增MCMC为0。独立核验检查24份科学资产、全部69204叶单元的分区/聚合、有符号比率及区间交集；504项配对敏感性中408项符号固定、96项恒等，没有翻转或跨零未定。恢复新增评价0且24份原件哈希未变。本地tar 303360000字节、81个内容成员；同机独立目录的9份核验/报告及2份清单逐字节相同。归档SHA256为c1bf12eb937ba57582647c7eb81cea21d01b6f204e1305d459cdc1175bd368d1。原归档回执记载打包时尚未重建，随后成功的portable-rebuild.json单独保留，未改旧回执。来源摘要SHA256为d2a1b675be99e19c9e59c57407451098eb157bedbb4664c5e50b397bf9498b32；见docs/W1-REFERENCE-RESULTS.md和qualification/w1-finalization-completed-v1.json。

论文v2交付（2026-10-11）：来源6f894c5，正文18页、SI40页，W1方法/七函数区间/504项敏感性已写入，原统计结果保持不变。163个便携输入逐项核验，独立目录重编译全部58页文字和72 dpi像素一致；最终无未解析引用/超宽警告，旧67页附录SHA不变。论文包17356800字节、SHA256为455d0119cb5bb873ada3a2342742d19a92706bfdb3676d404caf7f1fbaab849b，仅本地保存；PDF及小型清单随研究分支。见targeted-paper-companion-v2/delivery.json。普通表注再生成首次使用缺少matplotlib的数值环境在导入阶段失败，改用既有报告环境完成；数值claims及另两片段逐字节相同，相关记录保留。S2仍待原生结果，不宣布全研究完成。

S2接收准备（2026-10-11）：新增Mac标准库只读归档与身份核验器，17项合成证据检查通过、0失败、0跳过。核对解包安全、固定输入、冻结源码/环境、注册配额、原生门槛记录、分析分母及失败标签；明确不宣称真实轨迹资格、Git对象或远端当前进程已核验。未改Windows执行器绑定的源文件，新增采样0。接收步骤和仍需独立重建的内容见docs/WINDOWS-NUTS-INTAKE.md。当前远端尚无本轮结果分支/附件；已有输入包和回执仍为草稿，S2未完成。

S2 Windows本机终态（2026-10-11）：执行源126969036e73b4c077563d6601b030407e7663b8、149文件与Git字节一致，原34项依赖及venv标记未改。21便携+3真实原生Job检查通过、0失败、0跳过；首轮4条件资格通过后冻结协议5237de1b2dee0d134edc53b5fd225938a90cd34c5c9f5d5747d7f32ffacb1c54。主体36项34完成/2资源失败；按冻结规则选择4确认，2完成/2资源失败；9旧诊断作业8完成/1RSS停止。44注册四链调用，技术链不计入正式重复。G2/A1开启诊断的4 worker失败及确认均保存完整采样后进入诊断的阶段记录与Job内存限制消息；六个原失败案例未复现，旧105标签不变。54对/864项主条件路径及RNG、64项确认记录完全一致；没有改变采样核、指标、输入或内存限制。

S2保全和返回：两次真实verify各新增执行0、29,444个当时研究文件保持不变；53登记Job实时查询无活动进程。完整tar 703,969,280字节、30,044内容成员逐项核验，SHA256为5fffe7f83783651ef58198aab4bad1bfb28be1d2244b9a0738c8f66fbdb88705。Windows新目录安全解包及只读身份检查通过，8份搬移重建分析文件逐字节一致，无新增采样；这不替代Mac接收。完整原件保留在本机独立n工作树，归档/回执追加上传以nuts-windows-v1/receipts的实际终态为准；未公开草稿。当前中文报告见docs/WINDOWS-NUTS-LOCALIZATION-RESULTS.md；S2 Mac独立接收、故障审阅与论文整合仍待进行。

S2实际上传：主tar及两份校验附件于04:08:24 JST追加至原私有草稿，217→220件、全部旧资产字段不变。封存后管理证据tar为839,680字节/SHA256 02dbc6da8d9622a6fa21d2fd3612cb1f57d03d5a600d2f0fe46b83f485429a7d，79成员核对；于04:14:19 JST追加3件，220→223件且仍draft、旧附件不变。04:12:22 JST实时查询本轮53个Job无活动调用。小型delivery.json绑定两包与原生/搬移证据，完整原件未变；源码bundle及最后传输费用在报告提交后单独绑定，不递归修改封存tar。Mac接收仍未完成。
