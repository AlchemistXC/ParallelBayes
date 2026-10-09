# Windows紧凑正式研究交回（2026-10-10）

三批预定采样、终态核验及Windows只读完整分析已经结束。全部失败、实际输入、
成本和原始资产保留；本报告不判定整个研究、统计收敛或一般加速已经完成。
完整原始组件已追加到既有草稿，完整分析和管理记录作为独立组件回传。
Mac须独立接收、重建及审阅，F5完整复现和F6最终论文仍未关闭。

## 身份与环境

执行源码始终为 `codex/windows-compact-study` / `3a37a891896faedc62c0d6af185bfad77696054f`，
目录 `D:/workspace/ParallelBayes/c`，253个规范源文件。交付工具/报告位于独立分支
`codex/windows-compact-delivery`，未替换已冻结执行树。旧正式研究在启动后因用户
资源要求中止，是启动后的资源修订；旧1,152输入、1,010终态及全部partial独立保留，
没有抽取旧成功结果作为新重复，也未重新运行旧网格或既有有限验收。

| 绑定 | SHA256 |
|---|---|
| 新身份 | `windows-compact-inference-v1` |
| 协议内部身份 | `91bbff0ec47f9f47b64ac4acfd328e2df8834a67b1d24a1c9e35c4fa0a980aeb` |
| 设计 | `f9417eb01c01bbc16a6d676870922c479da6c970c69ca8827f270f79ad22626f` |
| freeze-manifest文件 | `84f350d2a1015d61eda51a6ff9fe6afdfbc285c75df86dc2121b890243b5e784` |
| FROZEN文件 | `2d155e8a979cb11fcec7396f7e71296da5f4e666d37107822a44f39a224a0fa0` |
| 新原生差异验收文件 | `fae450b9170efac576370f8b59e632b44bb78df8ea036aadb459a9a1928e307b` |
| 原venv标记 | `5e8ed0b284b1ef83977fcea0ce45c16349bbf8c1f0eb249be238f8aea547999c` |
| 完整pip锁 | `796a6e23b5bbdfc8d82b62ffd904a1b78cc2b0905e8439b337394af222517f9b` |

原生Windows11/Ryzen7 9800X3D/RTX5080；Python3.12.14、torch2.13.0+cu130、CUDA13.0、
NumPy2.2.6、SciPy1.15.3、Pyro1.9.2、psutil7.1.0、pytest8.4.2；34个完整包记录。
R4.6.1/posterior1.7.0、驱动616.56，GPU sm120/17,066,033,152设备字节、
主机RAM33,346,146,304字节。实际包元数据仍为0.2.0.dev1，未安装升级来改写历史身份。

实际Python为 `D:/workspace/ParallelBayes/.venv-win-torch/Scripts/python.exe`；
Rscript为 `D:/Tools/R-4.6.1/bin/Rscript.exe`，R库为 `D:/Tools/R-library-4.6`。
共享锁为 `D:/workspace/ParallelBayes/output/runtime/windows-shared-host.lock`。
重启后完整源/输入/环境/驱动/R/标记重新核对通过，未bootstrap或重装依赖。

## 完整预定状态

216份新实际输入、24次原四链重复、两个固定预算1024/4096，3,888主任务，
256预选缓存探测/1,024技术调用。技术重放不增加后验样本或独立重复。

| 批次 | 主任务valid | numerical_failure | output_failure_unclassified | 缓存合格 |
|---|---:|---:|---:|---:|
| 0 | 1236 | 12 | 48 | 64 |
| 1 | 1236 | 16 | 44 | 64 |
| 2 | 1269 | 14 | 13 | 128 |
| 合计 | 3741 | 42 | 105 | 256 |

主任务未运行、资源失败及基础设施中断在最终任务框架中均为0。原终态分类没有改写。
105个未分类输出失败均属于CPU四spawn NUTS；原因尚未确定，不能写成OOM或数值失败。
42个数值失败均为H1：CPU/CUDA quasi-DEER各20，CPU/CUDA顺序MALA各1。
这些轨迹未成为合格后验。其余原始NUTS发散、差诊断、全拒绝和常量函数仍保留。
主任务失败未取消缓存，缓存成功未回填主任务。

每个计划任务在 [tasks.csv](formal-results/tasks.csv) 有一行；完整原始/无约束数组、
实际噪声/log_uniform/directions、接受事件、自环、独立NumPy路径、NUTS初值/随机状态/
适应/worker证据及R现代诊断在原始组件及只读重建组件中。3,741个valid包括
3,414个MH和327个CPU NUTS。NUTS没有宣称与MH固定路径等价。

缓存256个measurement_available，1,024次调用全部technical_output_valid；
samples_eligible始终false。初次调用及三次prepared均路径/事件核验通过且计时齐全后，
才计算每输入三次prepared中位数；每格仅4份预选输入，无BCa区间。

## 实际检查、恢复与读取

新契约35便携检查/4受影响原生行为检查均通过，0失败/0跳过；独立技术18主任务、
16探测/64调用全部合格，恢复零重算及有界Windows搬移重建通过。
历史读取/统计/报告检查71通过、0失败、2个仅非Windows拒绝行为跳过，1条matplotlib
弃用警告保留。交付工具增量安全检查最终29通过、0失败/0跳过；人工检查不算研究重复。
首轮接收partial冲突、pytest错误路径、预关机中断、外围上传相对路径错误均保留。
后处理上传首轮因另一个附件从starter变为uploaded而触发既有附件变更拒绝，
只读核对确认唯一差异后使用新回执顺序重传，原失败包保留；未放宽远端身份检查。

六阶段终态核验新增科学执行0，127,636个原任务资产不变。已完成的batch0闭合检查
在本轮重新核对其哈希/原生结束证据后复用；batch1/2四项实际verify-only重新执行，
没有以--resume派发任务。新静止登记快照5290个注册Job inactive、5239个索引active=0。
该证明限于登记所属进程，不冒充整个Windows所有进程的清查。

Windows只读源树视图索引和分析覆盖4,144行：3,888主任务、256缓存；reader_error=0、
evidence_gap=0，失败行也读取。实际再次 `formal_analyze.py run --resume` 复用4,144行、
新增分析/采样0，42,035原分析资产不变（SUMMARY是单独记录的可替换账本）。
分析Job、统计Job、报告Job终态均active_processes=0，其后原生观察均absent；
管理者PID472退出本身不是其后代结束的唯一证据。

实际命令及stdout/stderr、创建时间、Job成员观察、墙钟、退出码、源哈希均在
`output/compact-postprocess-v3/commands/` 和独立成本组件；原始采样命令在
`output/compact-formal-costs-v1/invocations/`。本轮后处理次序为四项缺余verify-only、
静止登记、传输规划、index、run、同目录run --resume、statistics、report；
没有运行采样器、生成新输入或使用--fixture/跨平台放宽选项。

## 统计、图表与费用边界

全部9目标/36函数统计完成；45张图（9费用、36函数），原件PDF/SVG/PNG和完整CSV/JSON、
中文Markdown/LaTeX附录均返回。Git只保存 [显示版报告](formal-results/report.md)、
小型CSV和同一图SVG，LF规范化差异由 [ORIGIN.json](formal-results/ORIGIN.json) 记录；
Git显示副本不是原始字节档案。抽查G2误差、H1费用、L2未定参考和W1稀有事件图，
未发现标签碰撞/裁切，失败分母、缺点和不可判定区间保留。

按24个完整四链重复配对；区间使用9,999次共享整体重复重采样的逐点95% BCa，
至少20合格重复，退化/不足/不可判定不填理想区间。不是96条链独立重复。
L1有限MCMC参考及MCSE、L2未定参考、W1非认证积分保留；参考不确定性未传播进BCa，
另给敏感性，不声称同时覆盖、精确time-to-accuracy、普遍加速或一般收敛。

| 原始统计文件 | SHA256 |
|---|---|
| statistics/SHA256.json | `0c1857a7767ab5c8a117c00b75992db40c03c06e2453ad64c1398a64080a0c00` |
| report/SHA256.json | `9f7c551f0b5b6bebd99fcfaf1b5ae310ef8bb15b913bc3447d17a0b3f9b5b75d` |
| 完整后处理有界清单 | `4a3f55e60bb13d1fe08b58deaeedad048d942c130f4433a62efb4c67e4055e3c` |

七段不重叠的科学阶段外层墙钟已知合计82,874.8095126秒；这包含子任务，不能再加
子任务费用。管理者未测开销、整个研究端到端费用和预关机中断后处理墙钟保持null。
本轮首次完整分析墙钟6934.5816467秒，零重算核验752.9760968秒，统计123.3843329秒，
报告25.0735919秒；准备、测试、核验、重建、传输单列，不冒充普通推断费用。
Job kernel peak commit、轮询RSS与CUDA显存有各自边界；未把它们互换或称无遗漏硬峰值。

## 有界交付与接收

既有草稿 `AlchemistXC/ParallelBayes` / `windows-completion-v2-20261005`（release403644544）
保留draft；无覆盖、公开发布、合入main或强推。正式原始组件为180,582成员/
19,671,228,544字节，74个256MiB上限块，manifest SHA256：
`38e68557b03e4e153a2321fe6b8e5210c99557500746c86f855480edc81ab75e`。
全部块已由GitHub实际size/digest确认，Windows原件保留。
完整后处理组件为42,616成员/6,070,464,691字节，23块；失败验收、开发证据、
所有外层费用、暂停/关机/重启/静止登记、交付测试和源历史分别绑定清单。
最终总清单名为 `windows-compact-complete-return-v1-catalog.json`，另附SHA256；
它逐组件列实际附件名/ID/大小/哈希、分块顺序及源bundle，不递归把自身上传回执写入自身。

Windows新研究采用原件加有界分析/单块缓存；不生成全量tar再split、不额外复制正式大树。
2026-10-10 07:02 JST，C余量1,598,892,883,968字节，D余量1,810,798,104,576字节，
均包含旧证据实际占用。Mac实际卷余量仍需在接收时检查，Windows余量不能供给Mac。
所有清单含失败reserve，未删除难任务或保留文件以制造空间/性能优势。

准确下载/分块ingest/全成员verify/只读重建/零新分析命令见
[接收说明](../../docs/WINDOWS-COMPACT-RECEIVE.md)。Mac用正式接收目录自己的
WINDOWS-RETURN-MANIFEST哈希，不使用Windows原件视图清单冒充搬移回执。
完整远端原始传输已完成；Mac独立接收和最终图表/PDF复核仍未完成。
