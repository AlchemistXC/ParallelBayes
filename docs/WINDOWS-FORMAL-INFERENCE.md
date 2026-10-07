# Windows 正式研究执行记录

2026-10-08。本轮授权完整四批，尚未产生正式采样结果。执行目录
`D:/workspace/ParallelBayes/f` 固定在
`0ba5643a6b580e79b8040f13a5e3165322db0e77`；独立文档/交付目录 `rf`
从 `fe850061defb79be69355a0d5db4c2fad87fb5ea` 建立。
旧 v2 工作树、3167 文件的完整原件及历史失败均保留。

## 已完成的预检

- 旧有限验收只读 verify 返回0，3166门槛资产通过；验收文件SHA256
  `1b71fc0809c5019140768778572681f076bfbf8e7810523f2aed92047c1dd173`。
  没有重新执行16行为用例或27/24技术任务。
- 原共享锁下观察51个v1及51个v2登记的102个原生Job，活动进程0。
  这是登记集合的实时观察，不是全操作系统的无进程证明。
- 原生Python3.12.14、torch2.13.0+cu130、CUDA13.0、驱动616.56、RTX5080
  sm120、完整34包版本、R4.6.1/posterior1.7.0和原venv标记通过实际核对。
  float64框架探针通过，不将其称为采样器或性能验证。
- 188个执行规范源文件与Git LF字节一致；原水井快照八文件哈希通过。
  最大G2主任务/缓存的17个实际目录长度与Mac已接收长度一致。

首次环境预检未通过：唯一差异是`pip freeze`为editable包动态读取主目录
Git HEAD，原安装来源6df0479已经随主目录更新到fe85006。
没有依赖版本变化。原失败日志和两份锁完整保留。确认无Python/R采样进程后，
在空闲主目录新建`codex/windows-editable-environment-anchor`，检出真实原安装
来源6df04793e0cecb2633f5cc3bbdeea5a8b3228145；原分支及fe85006提交保留。
再次预检的完整环境与验收完全一致。没有修改site-packages、venv标记、
验收文件、v2工作树或执行树。后续运行必须保留这个editable来源锚定状态。
R的四条C.UTF-8 locale启动警告原样保留。

## 存储分配

实际卷记录在执行树`output/formal-costs-v1/storage-preflight.json`。
D是WD_BLACK SN770 2TB，C是ZHITAI TiPlus9100 2TB，均健康NTFS、不同物理NVMe。
预检D空闲约1735GiB，C约1526GiB。历史文件已经占用的容量包含在空闲量中。

| 卷 | 新目录与用途 | 事前储备分配 |
|---|---|---|
| D | `f/output/windows-formal-inference-v1`完整原件及外层费用 | 700GiB |
| D | `f/output/formal-return`未压缩导出tar | 700GiB |
| D | 未分配运行/文件系统余量 | 至少150GiB |
| C | `ParallelBayes-formal-delivery-v1`新解压树，完成核验后成为第二物理盘完整副本 | 700GiB |
| C | `ParallelBayes-formal-analysis-v1`索引、函数副本、统计、图表 | 200GiB |
| C | `ParallelBayes-formal-backup-v1`封存输入、控制文件及小型终态/失败回执备份 | 64GiB |
| C | 操作系统及未分配余量 | 至少400GiB |

以上是目录容量安排，不是产物大小预测或全程空间保证。无压缩、一次成功情景：
命名数组506.13GiB、保留故障预留49.5GiB；原件/tar/解压三份及独立接收函数
80.68GiB合计1747.57GiB。每个700GiB目录另留约144GiB用于尚未计入的日志、
头/文件系统、失败及唯一基础设施重试；日志随运行增长，没有已知上限。
不将G2或小模型实测压缩率用于完整网格预测，不删除预留文件或历史结果。
每阶段继续核对实际字节和卷余量；大复制前再次核算，空间不足保留资源等待。

输入与小型控制证据在冻结后、阶段之间复制到C并逐文件核对，不与测量并行。
全轨迹在完整导出及跨盘解压核验前仍只有Windows D原件，不能声称已经全部双盘
备份或Mac独立接收。Mac约149GiB空闲，先回传冻结、状态/清单和分析小包；完整
原始回传需要后续可用存储。此安排不依赖删除或购买设备。

## 外层测量与下一步

新增`witness_formal_study.py`只位于独立交付树，导入精确执行树的已验收Job API。
它不持有科学锁，不新增时间/资源限制，不生成输入、改变采样策略或资格。
记录真实外层Job全部后代、stdout/stderr、命令/源、完整墙钟和终态；包含内部任务
费用，不能相加。其元数据明确128次原四链重复及41472/9216计划，不沿用旧有限
witness的`formal_repetitions=0`字段。已用必需的旧验收只读verify实际核对退出0、
Job终态活动0。执行树未添加任何源文件。

实际完整证据保存在执行树`output/formal-costs-v1`；大数组和原始环境不入Git。
私有技能目录/ZIP缺失，未声称使用codebase-design、tdd或nature-experiment-log。
接下来冻结1152份实际输入，核对设计SHA与源/环境门槛，提交小型冻结报告后依序
运行四批。数值失败、资源等待、基础设施中断、未执行和证据缺失分别保留。

## 完整冻结及启动门槛（2026-10-08）

prepare实际退出0，1152份最大预算主输入全部封存。外层墙钟805.423秒、
原生Job终态活动0。后续完整verify退出0（21.293秒），用户指定的
verify_native_acceptance正式源/环境门槛退出0（26.354秒）。

| 身份 | SHA256 |
|---|---|
| 正式设计 | 68a1cba1b9309216d237ac4613531216f167ff344dfdfcb72dc3aaca0ca0baa5 |
| 正式协议 | 62ca9db5547c2701232d200f2978255a3ef1b0f06c47b9ccd0145b1f19364176 |
| FROZEN.json字节 | 34f257dbdaaf009ec17966a7d74f32a691fce80dba0c897028c563e82e084c4f |
| 冻结文件清单字节 | 0e37ef98965a867429bdeab57458e332f8f62e30716583b8aec1d4a2f3b9f77b |

九目标/四预算/128次原四链重复、41472主任务和9216预选缓存探测完整保留。
全部实际文件与数组哈希见execution/windows-native/formal-inference-v1中的
input-identities及freeze-manifest；完整协议/任务顺序/参考及所有源/输入在原包。

新C盘备份实际核对3665文件、13,019,612,404字节，全部SHA一致，外层63.869秒，
原生Job终态活动0。这包括全部封存输入/控制/源/环境，尚不包括未来科学轨迹。
不由这个实际压缩后大小推断全研究容量。两块盘的当前余量另存小回执。

独立外层sequence_formal_study按八个明确阶段逐一运行原CLI，每阶段核对退出码、
外层/内部真实Job结束及完整关闭框架后才推进。异常即停止，不自动重启或重试，
恢复必须显式指定保留的原管理者目录并核对原PID创建身份/原生Job实际结束。
它只在阶段之间短暂取得原共享锁作状态观察，不在内部CLI运行期间持锁。
新增8项顺序/不完整框架拒绝/保留失败契约检查通过，无失败或跳过；不是新的
16项原生验收，不增加研究重复。全部辅助代码只在rf，执行源保持0ba5643干净。

冻结时正式主任务0/41472，缓存探测0/9216；冻结小报告先提交推送，再启动0 main。
没有正式统计或性能结论。输入准备与各核验/备份外层费用分列，不与内部费用相加；
未单独计量的初始预检/工程成本保持未知，不使用时间戳差补齐。

## 四批执行正在进行

冻结报告f77a415已推送后，真实启动batch0 main。顺序管理者PID25080、创建身份
134358637075414703，工具会话77014；实际身份和全部Job在
`f/output/formal-costs-v1/sequence-attempt01/`保存。此前旧验收/prepare/核验Job均已
结束，本阶段存在真实活动进程，不能重复启动。动态任务状态以共享登记、原生
观察及formal-runs为准；run-start-observation只是带时间的小型只读快照。

后处理脚本finish_formal_study独立保存源码/日志，通过原管理者真实同步句柄等待，
同时核对创建身份；不持有Job句柄以免延长kill-on-last-handle-close生命周期。
实际一次只读核对身份相符、WaitForSingleObject(0)返回258（仍未终止），不将
等待超时当作终止。微软依据：[WaitForSingleObject](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject)。
此单次接口核对不是重启恢复或新一轮16原生行为验收。

后处理仅在八阶段完整关闭、原管理者真正结束、阶段Job观察无后代及原科学登记
无活动任务后，重新核算真实容量，运行现有导出/逐成员核验/新C盘安全解压。
新delivery施加仅该目录的写入/删除拒绝规则，分析输出在其他目录；使用最新分析
检出，不加fixture或cross-platform，逐任务独立重放/R重建/统计/报告。
终态分析恢复要求新分析0/复用50688且全部不可变资产不变；生产读取器明确更新
可变SUMMARY bookkeeping，因此其前后原件单列保留，不能声称它逐字节不变。
任一异常停止并保留原件，不重新采样、自动重试或修改源/门槛。

本轮尚未完成四批、完整归档或分析；后处理源码目前只有句法和真实等待句柄
核对，不能提前称完整后处理通过。所有成功/失败/未知费用与Mac独立接收仍需
最终核验。Github当前每附件小于2GiB、单Release至多1000资产；完整大包如需
分块须事前核对这些限制及已有附件，不覆盖或发布草稿。[官方限制](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

publish_formal_study独立等待后处理管理者真实结束，保留其成功或失败终态；
未来仅提交小型终态/图表/压缩完整清单，生成包含固定执行源的Git bundle。
仅对已有草稿追加并核对API返回的逐附件SHA256，核对旧资产未变、draft/原target
未变。大原tar按1.5GiB字节范围上传；完整本地tar/原始输出保持不动，临时范围
副本只有远端size/digest核验后才释放，范围顺序/偏移/哈希完整记录，可由原tar
重建且不调用RNG。任何权限、容量或API错误停止并保留部分交付，不覆盖旧附件。
此工具尚未实际执行上传，不能预报最终归档大小、哈希或通过状态。

## 早期终态及恢复交接（2026-10-08 02:34 JST）

此时只读登记快照核对记录/索引身份及校验和：主任务137 valid、3 numerical_failure、
1 output_failure_unclassified、1 active、41330未登记；缓存9216均未登记。
原生观察确认活动H1 CPU quasi-DEER任务的Job存在且有5个成员。该快照不是完整
阶段关闭证明；更新状态以实时登记/Job和各阶段latest-closed为准。

三项H1 MH失败任务为99ab308cabb7daa08c242c58、5d0b15d1cc89bbf91b3e1882、
448e3c4638d373592247b63f。独立NumPy核验均为四链接受事件失配0，完整路径最大
绝对差分别约0.0238193、7.64386e-7、4.68070e-6；原冻结标准未通过，
samples_eligible=false。原始路径、诊断、已付费用及失败状态全部保留，无重试。

W1 CPU四spawn NUTS任务60f2f74ece8d9dd573ed9ada在pool中保存四个
BrokenProcessPool错误。退出原因未知，保留原output_failure_unclassified分类，
不宣称OOM、数值问题或可重试基础设施故障。原Job终态活动0，轮询RSS峰值
5,400,756,224字节，原始PeakJobMemoryUsed计数13,018,619,904字节；后者不是
已证明成功提交峰值或显存。四项失败的另一次实际Job观察均无活动后代，
小型原始回执及其哈希在early-failures，完整原数组仍在执行包内。

真实科学管理者PID25080/创建身份134358637075414703和会话77014继续工作。
后处理PID1920/创建身份134358651343620295、会话63639仍只持同步进程句柄等待；
草稿交付等待器会话30517同样没有开始上传。不要重复执行活跃阶段。

如果原科学管理者确已结束，先以原生Job确认其全部后代结束并保留异常回执，
才可从独立交付树显式继续原计划：

```powershell
& 'D:/workspace/ParallelBayes/.venv-win-torch/Scripts/python.exe' `
  'D:/workspace/ParallelBayes/rf/scripts/windows/sequence_formal_study.py' `
  --config 'D:/workspace/ParallelBayes/f/output/formal-costs-v1/sequence-config.json' `
  --output 'D:/workspace/ParallelBayes/f/output/formal-costs-v1/sequence-attempt02' `
  --resume --previous 'D:/workspace/ParallelBayes/f/output/formal-costs-v1/sequence-attempt01'
```

此命令不是现在需要运行的第二份进程。它核对原管理者出生身份和旧Job，
已有完整阶段只核验；未封存阶段调用原formal_batch的--resume，不重算数值失败，
不自动重试main/cache。原attempt02若已存在，应保留并调查，不覆盖。原等待器只
绑定attempt01，不会偷偷跟随新管理者；实际中断后的后处理需要新的独立目录。
全部41472/9216终态、正式归档/分析、Mac完整独立接收与F5/F6尚未完成。

## 首次小型冻结回传（2026-10-08 02:40 JST）

已用原export_results/verify-windows-return实际导出并核对87个成员，包含完整
protocol、study-plan、catalog、freeze-manifest、全输入身份、小型环境/源/失败
回执和Git bundle。仅回传冻结及带时点的早期状态；没有NPZ、venv、私有技能或
凭证，不把本包称为四批终态原始包，也不声称Mac已核验1152份实际数组。

| 资产 | 字节 | SHA256 |
|---|---:|---|
| windows-native-20261007T173931Z.tar | 57825280 | 1bcf67145ff4aaddfbf65557abf3fcb0c465fba4a4e8b4a9bf3c1779af2883d3 |
| windows-formal-freeze-source-7c5cdc955bf4.bundle | 23759848 | 98723a92d740bed0680583701bf27027f1a88a0e02f3230211e04a3382759bdc |

bundle包含完整历史与报告7c5cdc955bf4b0c6781ff63c14fb27c97aa5b13f、执行
0ba5643a6b580e79b8040f13a5e3165322db0e77两引用，git bundle verify通过。
tar、tar.sha256、逐成员核验JSON、bundle、bundle.sha256五个新增附件已追加
原草稿windows-completion-v2-20261005，所有远端size/digest/state通过；原47
附件及draft/原target不变。上传外层墙钟20.886秒，单列行政费用，不能作为
推断或缓存时间。完整机器回执在early-draft-upload.json。

接收方在新目录用有权限的账号下载，不能覆盖旧归档：

```sh
gh release download windows-completion-v2-20261005 --repo AlchemistXC/ParallelBayes --dir NEW_FREEZE_RECEIPTS --pattern 'windows-native-20261007T173931Z.tar*'
python scripts/verify-windows-return.py NEW_FREEZE_RECEIPTS/windows-native-20261007T173931Z.tar
```

该命令只检查早期小包的87成员完整性，不重采样、不执行统计，不是完整正式
原件独立接收。完整原件仍在Windows D执行包内；八阶段任务持续运行，完整
原始归档的大小/哈希目前尚不存在，不预填未来状态。
