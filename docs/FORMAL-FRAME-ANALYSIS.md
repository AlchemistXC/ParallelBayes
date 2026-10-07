# 冻结任务框架的归档读取与配对统计

2026-10-07，源码 `6014af3597a0fab5abd2b698e79a67568161c5b1`。本轮把逐任务科学读取接入完整任务登记、可恢复分析和按模型的配对统计。**接口已实现并通过本机有限核验；尚未收到新 v2 Windows 验收包，更没有正式全量研究结果。** F3、F4 正式比较、F5 全结果到表图/PDF的重建和 F6 最终稿保持未完成。

本轮使用 `codebase-design` 技能，将清单索引、科学读取、统计汇总分别置于可独立检查的接口后。新增代码仅在 `scripts/analysis/`；执行源码、数值方法、模型、冻结协议和旧结果未改。[现有 Windows 提示词](../handoff/windows-completion/CODEX-PROMPT-FORMAL-VALIDATION.md)继续有效，没有额外一轮 Windows 任务。

## 三个步骤

`formal_archive.py` 流式读取外层 `WINDOWS-RETURN-MANIFEST.json`，核对所有实际文件的大小、SHA256和清单完整性，再建立独立 SQLite 索引。索引及接收目录可搬移；不在原 Windows 活动登记上工作。不载入整个百万文件清单，不按每个任务重新扫描全量文件列表。路径越界、重复JSON字段、遗漏文件、分叉历史和损坏索引均拒绝。

`formal_analyze.py` 读取封存的完整正式方案，或明确独立的51任务技术方案；不能从随意缩小的表格冒充正式协议。每个计划任务都有一行。未收到历史导出是 `evidence_gap`，不等同 `not_run`；读取失败是 `reader_error`，不变成采样器失败。多份导出必须是同一事件链的延长，按事件数量选择，不按文件修改时间挑选旧成功记录。

有证据的任务调用[逐任务科学读取器](FORMAL-RAW-READER.md)：实际输入、独立 NumPy 路径、接受事件、原坐标函数、R重建、失败资格和费用规则保持原约定。逐任务完成后封存输出哈希和事务回执；显式恢复先核对源码、环境、输入、输出及完整计划，再跳过已完成的数值/R重放。未提交的部分分析目录原样保留，需要查明原进程和文件状态，不自动覆盖。

`formal_statistics.py` 从已核验的标量记录汇总，每次只处理一个模型，沿用既有统计政策：

- 全部主任务与预声明缓存探测必须保留；证据缺失阻止受影响模型/阶段的统计，不删除这些行。
- 每模型共享完整四链重复的9,999次重采样索引；原来的至少20个有效重复、退化区间不可判定及逐点覆盖规则不变。技术验收只出描述记录，没有正式区间。
- 解析真值、有限MCMC参考及其MCSE、未认证数值积分、未确定参考分别保留。参考偏移敏感性不是传播了参考误差的置信区间。L2 未确定符号函数不移除。
- 同核顺序/时间执行的配对，以及MH工作流与CPU NUTS的端到端配对分别标识。所有预算使用同一重复身份；跨模型不混为同一总体样本。
- 普通工作流、研究审计执行、额外核验及全部调用保留各自范围，嵌套时间不相加。某个有效函数重复缺时间时，不删除该重复来制造误差—成本坐标。
- 缓存统计使用预选原输入，四次调用不变成四个统计重复；失败探测的已知费用保留，没有普通后验样本资格。

汇总保留原 Windows 均值和诊断，重建结果仍是伴随核验。读取模块的源码身份与下游统计模块身份分开，因此只修改下游汇总不必重跑无变化的原始读取；变更读取器、输入或依赖时不能冒用原分析。

## 接收端使用

先按既有 `scripts/verify-windows-return.py` 安全核验和解压完整回传归档。`DELIVERY` 是含外层清单的解压根，`BUNDLE_RELATIVE` 是其内含 `FROZEN.json` 的目录；不能混用历史 v1 运行器包和新 v2 接口。`MANIFEST_SHA256` 必须来自已完成的外层来源核验。输出目录全部新建，且与原件及其他步骤目录分开：

```text
python scripts/analysis/formal_analyze.py index --delivery DELIVERY --bundle-relative BUNDLE_RELATIVE --manifest-sha256 MANIFEST_SHA256 --output INDEX
python scripts/analysis/formal_analyze.py run --delivery DELIVERY --index INDEX --output ANALYSIS --rscript RSCRIPT --r-library R_LIBRARY --cross-platform
python scripts/analysis/formal_statistics.py --delivery DELIVERY --index INDEX --analysis ANALYSIS --output STATISTICS
```

`--cross-platform` 显式启用原冻结输出容差，不改变MH路径或接受事件的要求；省略时要求精确重建。恢复第二步使用相同命令加 `--resume`。第一步不覆盖部分索引，第三步不覆盖已有统计目录。接收输出保留 Python、NumPy、SciPy、R、posterior和jsonlite身份；环境变更不隐式续用旧检查点。

主要产物为 `INDEX.json/files.sqlite3`、`identity.json/analysis.sqlite3/tasks/*/RECEIPT.json`、全任务 `FRAME.json`、各模型的完整任务表、误差/费用/缓存JSON、原始重采样索引和统计量NPZ及校验和。`formal_inference_complete=false` 不因文件齐全自动变真；这些命令不负责运行采样器、启动Windows任务或判断整个后验已收敛。

## 本轮核验

26项不同 pytest 检查通过，0失败、0跳过：11项清单/历史索引、7项实际NumPy/R文件下的分析恢复与篡改拒绝、5项完整人工标量框架的统计衔接、3项冻结任务及参考契约检查。修改源码绑定后仅重跑受影响检查；多轮执行不重复计数。人工数据与v2历史夹具不构成Windows实测或正式统计重复。

九模型36个原坐标函数参考独立重建，与冻结记录一致；水井来源八文件逐一核验。既有NumPy `slogdet`警告原样保留，没有修改冻结目标以消除警告。

规模伴随检查实际写入50,688个**人工元数据文件**，建立约20.14MiB索引，再核对全部任务查找。清单约8.28MiB；索引27.44秒、全查找28.63秒，本进程峰值RSS约207.44MiB。所有缺失历史均保持证据缺失。这里只证明该文件布局下的索引行为，不是完整正式原始数组的吞吐、存储上界或MCMC性能证据。

另外实际运行完整CLI链路：真实源码/三份NumPy输入的技术封存夹具 → 清单索引 → 51项证据缺失记录 → 恢复时0重放/51复用 → 三模型仅描述汇总。原件哈希不变，没有人工填充Windows执行结果。首轮伴随脚本因本机环境未安装pip而在准备前失败，日志保留；修正该测试脚本，以importlib.metadata如实记录接收环境，在新目录完成检查。此修正没有改正式Windows依赖冻结方式或生产源码，也不把接收端环境记录称作原生pip核验。

证据在 `benchmark/analysis/outputs/formal-analysis-frame-v1/`，包含测试各轮XML、源码身份、参考重建、规模检查、命令与校验记录。完整测试夹具留在忽略的本地输出中，不向Git提交原始大数组或第三方资料。

## 接下来

等待并独立接收新v2原生验收，继续接通原始结果到诊断表、图和论文的重建，再按全部门槛冻结正式实验。当前没有新正式数据，不能用人工测试填充论文或声称41,472主任务/9,216缓存探测已完成。原有CPU负结果、Windows试验和所有失败继续保留。

本轮GitHub核对仍是机制 `1cfc83d`、旧运行器 `b0582c3`、安装 `0e44c2d` 和原草稿27附件；五个结果归档的大小/摘要与已接收记录一致，没有发现新的v2验收资料。无需重复下载或重跑已完成的旧提示词。
