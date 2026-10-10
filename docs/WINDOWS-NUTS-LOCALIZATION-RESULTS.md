# Windows CPU NUTS有限定位结果

2026-10-11，本机S2执行与只读重建记录。36次主体全部获得终态，34次完成、2次受资源保护停止；4次预选确认中2次完成、2次受保护停止。四条件资格首轮全部通过。另有9个旧轨迹诊断作业，8个完成、1个触发RSS护栏。没有运行GPU、旧正式网格或新增正式统计重复。

本轮能直接定位选定G2/A1失败发生在完整采样持久化之后、旧内置诊断进入之后，并取得原生Job内存限制消息。不能由此重判历史105次未分类失败；所选六个历史失败案例在新插桩下均未复现。新成功不填回历史结果。

## 身份、环境与资格

- 执行提交：`126969036e73b4c077563d6601b030407e7663b8`，来自启动时最新`origin/codex/research-integration`；149个规范执行源文件逐项与Git字节相同。没有本轮采样器或兼容性修复，执行期间未更新源码。
- 新身份：`windows-nuts-localization-v1`；协议SHA256：`5237de1b2dee0d134edc53b5fd225938a90cd34c5c9f5d5747d7f32ffacb1c54`。
- 源/环境绑定：`0930415240de2504c01fd27d838caec30e807e3ef94a2c1aa81aeeeb30fbe3e9`；终态登记SHA256：`9f04e024db65a7e5830db0e7d7e66382ec30a2a58e3646dc3e620b0546a0cfef`。
- 原输入tar为21,544,960字节，SHA256为`3b97a221ea8a5a61644f3394474e2ceaf8f0b981803456181a012a99d26f5b12`。27个成员逐项核验；输入清单SHA256仍为`d92824d78f352295449d80556368fd9ee3bed1e9b7af2d0443c3ffb7bfbc7504`。未生成替代案例或旧诊断轨迹。
- 原生Python3.12.14，NumPy2.2.6、SciPy1.15.3、psutil7.1.0、Pyro1.9.2、torch2.13.0+cu130；完整34项包版本、pip freeze/check保存在原件。CUDA wheel仅使用CPU路径。R4.6.1（2026-06-24 ucrt）、posterior1.7.0、jsonlite2.0.0。原venv标记SHA256仍为`5e8ed0b284b1ef83977fcea0ce45c16349bbf8c1f0eb249be238f8aea547999c`，没有安装或升级依赖。
- 主项目仍在环境锚点`9eac03f`，旧冻结工作树及原件保留。全部阶段使用原`D:/workspace/ParallelBayes/output/runtime/windows-shared-host.lock`。
- 便携检查21通过、0失败、0跳过；真实Windows Job检查3通过、0失败、0跳过。独立Q2高斯资格4调用全部完成，6对/96项路径及实际RNG记录均一致；只有此后才冻结主体协议。本机未发现已迁移的私有研究技能目录，未为本轮重装技能或环境。

## 九案例四条件

每格是一项四链技术调用，1024步预热、4096步采样，depth8、target_accept0.8、对角质量适配；每worker一线程。`完成`只表示本技术工作流完成，不表示收敛、探索充分或成为正式后验样本。

|案例|原任务ID|原状态|1 worker诊断开启|4 worker诊断开启|1 worker整体旁路|4 worker整体旁路|
|---|---|---|---|---|---|---|
|G1|16bc1edb545bad53bf8d780c|未分类失败|完成|完成|完成|完成|
|L1|fc8cf5c25991f6f6c2c3a023|未分类失败|完成|完成|完成|完成|
|L2|2c83781b7323c9b8da3096fb|未分类失败|完成|完成|完成|完成|
|H1|ea2c80626ac8c5eb6ddd48ad|未分类失败|完成|完成|完成|完成|
|H2|4bd166b10537e7004fcf60b4|未分类失败|完成|完成|完成|完成|
|M1|8b9233918258fd15cb0bd300|未分类失败|完成|完成|完成|完成|
|G2|ccb7caa505286acab31d3224|有效|完成|Job内存事件后停止|完成|完成|
|A1|cbe1e119d63775a732099418|有效|完成|Job内存事件后停止|完成|完成|
|W1|d65ab7e78de56284cf7cc8dc|有效|完成|完成|完成|完成|

实际注册顺序与冻结调度表一致。每链Python、NumPy和torch CPU实际起始RNG状态逐文件共享和核对；不是仅比较种子。九模型54对条件的864项共同预热/采样前缀及RNG记录全部相同。失败的G2/A1条件也已保存每链1024/4096步，末事件均为`legacy_diagnostics_enter`，没有对应返回标记；没有将它们提升为完成任务。

按冻结模型/条件优先级从全部主体结果独立重算，仅选择G2和A1的四worker诊断开/关对，共4次确认。开启条件各再次出现内存限制消息，旁路各完成；64项确认与原条件的路径/RNG记录全部一致。4资格+36主体+4确认=44次注册四链调用，未用满48次上限，也没有重跑同一调用ID。确认不增加独立n。

## 诊断、资源与归因等级

旧轨迹的G1、G2、W1单worker ESS均返回；G1、W1四worker ESS返回。G2四worker ESS的四链都留下`legacy_ess_enter`，未留下返回标记，触发8 GiB集合RSS护栏后停止。三组R联合四链现代诊断均完成且二进制往返一致；没有将R联合诊断拆成四个独立作业，也没有与单链ESS作速度比。

|新失败调用|观察RSS最大值（字节）|Job峰计数（字节）|收到内存限制消息数|
|---|---:|---:|---:|
|diagnostic-G2-legacy-w4|9502576640|12482658304|0|
|main-G2-w4-d1|10190118912|12923604992|2|
|main-A1-w4-d1|8530022400|13529350144|1|
|confirmation-G2-w4-d1|10987126784|12923654144|4|
|confirmation-A1-w4-d1|11121922048|12923613184|4|

实际Job限制查询仍为12 GiB，RSS每0.2秒观察并使用8 GiB护栏。RSS是进程工作集之和，共享页可重复计数，轮询可能遗漏瞬时尖峰；私有内存只统计已捕获句柄且读取成功的部分。`PeakJobMemoryUsed`是原生计数回执，不能当作成功提交内存的精确峰值、硬上限证明或显存。限制消息是本轮直接证据；没有消息不排除限制事件。资源停止时部分退出码未取得，保留为缺失，不补零。每次继续前核对原Job absent、登记完整性和RAM恢复，只执行未登记的固定条件，护栏未放宽。

已冻结环境的Pyro `ops/stats.py`源码及Apache许可证在归档中保留，源码SHA256为`eedfd0787cbfc7f39765b3d93e4e7808914f3112b7b04a17ec01026606a16df1`。旧ESS的`_cummin`用repeat构造二维长度的临时数组：4096步时正序列长度2047，64维float64重复数组为2,145,387,008字节，布尔掩码另268,173,376字节/链；尚有输入、FFT及运行时等内存。这是源码给出的静态规模，和独立ESS/G2诊断阶段的内存事件相容，不是独占分配峰值实测，也未在失败栈里直接捕获到该具体分配。

直接证据：本轮G2/A1的完整采样已持久化、开启诊断后出现Job内存消息，且预选确认重复同一结果。相容解释：旧ESS的临时数组规模可解释64维四worker的内存压力。未知：所有105个历史`BrokenProcessPool`的根因、未复现案例的原故障及插桩改变对象生命周期/GC/I/O/进程复用的影响。整体诊断旁路成功不能单独把全部原因归给ESS；历史105项分类保持不变。

运行理由中曾把“其他模型维度更低”概括得过宽；A1实际同为64维。该原始记录未改写，更正与后续资源核查单独保留，不影响调度、输入、控制或源码。

## 恢复、费用和交付边界

本轮53个登记Job在2026-10-11 03:54:07 JST实际查询均无活动进程。两次真实只核验恢复均新增执行0、注册数不变，整个研究目录29,444个当时原件的集合/大小/SHA256相同；此后仅增加交付管理记录，没有更改调用资产。这是终态恢复，不是中途恢复资格。

逐调用费用和阶段日志、父/worker身份及创建时间、私有内存、Job消息、退出证据、失败与部分链、诊断结果都在完整原件中。外层命令墙钟包含内部调用，不能相加；新的插桩与过程复用差异使其不等于原正式性能。未记录的整会话/初始拉取审查费用为未知，不用时间戳差填补。所有技术产物均`posterior_samples_eligible=false`；旁路诊断不可取得的计数和其他未定义诊断保留缺失。

原件：`output/nuts-localization-v1`；只读分析：`output/nuts-localization-analysis-v1`。小型结果及回执见`execution/targeted-followups-v1/nuts-windows-v1/`。完整tar包含study、analysis、每个实际源绑定的源码及许可证和逐成员MANIFEST。归档大小/SHA256、后续搬移核验与草稿追加状态由独立交付回执提供，避免归档自引用。原件、旧附件与原环境不覆盖、不删除；不公开Release。

Mac接收按`docs/WINDOWS-NUTS-INTAKE.md`，核对外部SHA后安全解包，运行只读身份核验和便携分析重建，再核对Git源对象及确认选择规则。Windows同机搬移验证不能替代Mac独立接收。S2论文/SI整合仍待该接收与审阅；本报告不是总体失败率、性能复现、收敛或整个补充研究完成的证明。

## 实际交付回执

完整`windows-nuts-localization-v1.tar`为703,969,280字节，SHA256为`5fffe7f83783651ef58198aab4bad1bfb28be1d2244b9a0738c8f66fbdb88705`；MANIFEST SHA256为`83e76fb56f6ec87ecee27de99a662d28fb5c9776a446725988e9c01b5d611881`，30,044成员实际核验。本机新目录身份核对通过，8份分析逐字节重建一致。完整原件、tar及搬移树仍分别保留，没有删除旧数据。

2026-10-11 04:08:24 JST，tar、`.tar.sha256`和`.tar.receipt.json`追加至[原Windows草稿](https://github.com/AlchemistXC/ParallelBayes/releases/tag/untagged-a38d1dfe63e5584ac2ef)，tag仍为`windows-completion-v2-20261005`，release ID403644544。原217件ID/名称/大小/状态/摘要/创建和更新时间全部一致，新增3件后为220件；远端tar asset ID628766423、摘要与本地一致。发布及覆盖调用均0，实际上传命令已退出0。源码bundle和封存后的管理回执作为后继独立附件，不更改这个tar。

接收端使用明确SHA和新目录：

```sh
python scripts/analysis/audit_nuts_return.py unpack --archive windows-nuts-localization-v1.tar --sha256 5fffe7f83783651ef58198aab4bad1bfb28be1d2244b9a0738c8f66fbdb88705 --output <new-reception>/received
python scripts/analysis/audit_nuts_return.py audit --root <new-reception>/received --report <new-reception>/identity-audit.json
python scripts/followups/analyze_nuts_localization.py --study <new-reception>/received/study --output <new-reception>/rebuilt-analysis
```

获取分支后须用可信本地工具，勿自动执行归档内任意源码；比较全部8份分析并独立重算确认选择，逐项核对绑定的149个Git源对象。原件只读，不运行Windows协调器、采样器或按种子重建输入。

封存后的搬移/上传管理证据另成`windows-nuts-localization-v1-delivery-evidence.tar`，839,680字节、79个内容成员，SHA256为`02dbc6da8d9622a6fa21d2fd3612cb1f57d03d5a600d2f0fe46b83f485429a7d`；逐成员校验通过。2026-10-11 04:14:19 JST追加该tar/摘要/回执后，原220件全部不变、草稿共223件。原主tar未改，后续上传自己的费用不递归写入这个管理tar，另有终交付证明。

最近一次本轮53个Job实际查询为2026-10-11 04:12:22 JST，活动调用0，可用RAM21,083,242,496字节，D卷余量1,808,224,477,184字节。本机新增研究、归档和同机接收总量不足3 GiB，未达到20 GiB上限。最终交付分支仅增加报告和小型回执，149个冻结执行源仍与1269690一致；Git bundle在报告提交后另行生成，实际提交/摘要/上传状态由单独终交付证明绑定。
