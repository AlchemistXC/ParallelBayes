> **2026-10-08 已被资源修订替代：用户确认旧正式采样已开始；不要再按下文派发/恢复完整旧网格。先用[HOLD提示词](CODEX-PROMPT-HOLD-FORMAL.md)准确停止并保全，再按[紧凑提示词](CODEX-PROMPT-COMPACT-STUDY.md)适配新3888/256研究。旧正文作为历史说明保留。新[设计](../../docs/F3-COMPACT-DESIGN-v1.md)与旧冻结源码/协议分开，新入口尚待实现及原生差异验收。**

你正在原生 Windows 11 / Ryzen 7 9800X3D / RTX 5080 上继续 ParallelBayes 正式研究。用户已授权完整研究实施。本提示词一次全文提供，按阶段顺序执行；不再重复F2、旧运行器、安装或已经通过的有限v2验收。

一、先读证据，分开文档检出与执行检出

从最新 `origin/codex/research-integration` 读取 AGENTS.md、docs/WINDOWS-FORMAL-V2-INTAKE.md、docs/F3-FORMAL-DESIGN-DRAFT.md、docs/FORMAL-COST-POLICY.md、docs/FORMAL-MEASUREMENT-DESIGN.md、docs/FORMAL-DISPATCH.md、docs/FORMAL-RAW-READER.md、docs/FORMAL-FRAME-ANALYSIS.md、docs/FORMAL-STORAGE-COMPANION.md及本提示词。旧报告保留当时状态，当前入口以Mac接收报告为准。

有限v2已由Mac独立接收：真实16/0/0、27主任务、24探测/96调用全部读取，接受事件零失配，主包3167文件未变。验收文件SHA256为1b71fc0809c5019140768778572681f076bfbf8e7810523f2aed92047c1dd173。前期失败及修复原件保留，不再重跑以“刷新”结果。

**执行工作树必须固定提交 `0ba5643a6b580e79b8040f13a5e3165322db0e77`。不能直接用最新分支头prepare。** Mac已验证该提交188个规范源文件与有限验收完全相同；最新头新增三个归档辅助脚本会使清单不匹配。不要改动source_files判据、复制额外.py到执行树或绕过验收。这是正常使用被验收版本，不是退回失败版本；NUL句柄修复已包含其中。

保留旧v2冻结工作树。先检查所有工作树、分支和未提交文件，在有足够空间的短路径建立独立工作树，分支建议 `codex/windows-formal-inference`，从上述精确提交创建。已有同名分支时检查实际内容，禁止reset/强推/覆盖。读取新文档可用另一检出；采样命令的cwd始终是固定执行树。后续报告提交到独立交付分支，不修改已冻结执行源。

二、环境与存储预检

由你从上一轮实际回执解析这些绝对路径，不要求用户重新手填：

- `$pbPython`：被验收的原生Python，原记录为 `D:\workspace\ParallelBayes\.venv-win-torch\Scripts\python.exe`。必须核验实际路径和完整环境，不能猜测或换成系统Python。
- `$pbRscript` / `$pbRlib`：原R4.6.1/posterior1.7.0路径。
- `$pbAcceptance`：原有限v2包内native-acceptance.json；整个旧包及其绑定文件必须保留且可读取，不能只复制这一个JSON。
- `$pbExternal`：posteriordb固定快照根目录，包含source-manifest指定的八文件及许可证。
- `$pbLock`：原全项目共享绝对锁路径；原记录 `D:\workspace\ParallelBayes\output\runtime\windows-shared-host.lock`。不要另建锁绕开旧进程。
- `$pbFormal`：新执行工作树下 `output/windows-formal-inference-v1`，首次不存在；父目录先建立。
- `$pbCosts`：另一个新目录，保存外层命令开始/完成、墙钟、退出码、stdout/stderr、源码身份和资源观察；不能嵌入旧验收包。

继续原生PowerShell和原生Windows Python，不用WSL2、Linux VM或容器。冻结环境不升级、不重装、不bootstrap、不更改原venv标记；驱动/OS/R/依赖变化必须被识别，不能静默续跑。不安装GPU NUTS、Stan编译器或新模型语言。可用已安装且适用的技能；先读SKILL.md，记录实际用途，私有ZIP缺失不阻塞、不公开私有代码。

**先落实实际存储方案。** 完整主要数组逻辑容量约505.95GiB，不包含逐轮JSON、重复的诊断二进制、失败原件、Git/环境、归档和解压/分析副本；输入自身约23.78GiB。这不是压缩后估计或足够空间保证。记录每个拟使用卷的容量/余量、文件系统、原始包/归档/分析目录、备份方式及预留。结合已保存最大G2任务的实际目录字节检查可行性；不以某个小模型压缩率推算全部任务。空间不足时保留为资源等待并报告所需存储，不缩减网格、不删历史或原始数组、不购买设备。

2026-10-08补充的只读容量核算见docs/FORMAL-STORAGE-COMPANION.md：已验收保存格式的完整命名数组约506.13GiB；若50,688任务均一次成功，现实现保留的1MiB/任务故障记录预留另占49.5GiB。独立接收时三份函数二进制另约80.68GiB。原件＋未压缩tar＋解压树＋这些接收函数文件的无压缩情景约1747.57GiB，仍不含JSON/观察日志、索引、失败重试、文件系统及其他副本开销，不能当作容量保证或放行阈值。不要把有限批次NPZ压缩率推广到完整研究，也不要删除预留文件。按每个实际卷分配记录这些目录；无需执行新的有限验收，采样源码/网格/资源保护不变。

Mac最近仅约149GiB空闲，不默认将500GiB以上数据直接传过去。完整原件先可靠保存在Windows；先回传协议、清单、状态和分析小包。完整接收由用户可用的外置/网络存储安排承接，或由Mac提供后续已核验的分批读取方案。不能因此声称独立完整复现已完成。

核对共享登记的真实原生Job/进程状态，不只看文件；存在活动旧任务则等待或调查，不误杀无关进程。保留原12GiB准备可用RAM、3GiB空闲GPU要求及每任务8GiB观察RSS、12GiB Job commit、4GiB启动磁盘/1GiB运行储备。原PeakJobMemoryUsed计数不能冒充实际成功提交峰值或VRAM。不得增加总实验时限；数值轮数、内存/磁盘和失败终止规则继续生效。

三、冻结完整科学设计和实际输入

正式身份固定 `windows-formal-inference-v1`；设计元数据SHA256预期 `68a1cba1b9309216d237ac4613531216f167ff344dfdfcb72dc3aaca0ca0baa5`。九目标G1/G2/A1/L1/L2/H1/H2/M1/W1、预算256/1024/4096/16384、每目标128次四链重复、九工作流，共41472主任务；预选9216缓存探测，缓存调用不增加后验样本或独立n。四批均为预定任务，每批10368主任务＋2304探测，不按结果方向中止或追加。

固定执行树应干净，规范源码字节与Git一致。先只读检查旧验收：

```powershell
& $pbPython scripts/windows/validate_formal_adapter.py verify --bundle (Split-Path $pbAcceptance)
```

退出码必须0。然后记录外层命令完整墙钟、输出和环境，执行：

```powershell
& $pbPython scripts/windows/prepare_formal_study.py prepare --output $pbFormal --identity windows-formal-inference-v1 --external $pbExternal --host-lock $pbLock --rscript $pbRscript --r-library $pbRlib
& $pbPython scripts/windows/prepare_formal_study.py verify --bundle $pbFormal
```

一条结束且检查退出码之后才执行下一条。prepare保存全部1152份最大预算实际输入、源码/环境/水井数据和固定任务顺序，最后写FROZEN.json。输入不得由有限验收样本替代。保存协议、FROZEN、freeze-manifest、study-plan、source、environment、pip锁及所有实际输入的校验和。准备完成后先把小型冻结报告提交/推送，原始数组不入Git；只要以下门槛满足可继续，不需要再等用户重复许可。

在采样前显式核对正式协议与旧原生门槛，使用固定源码自带接口：

```powershell
& $pbPython -c 'import sys,json; from pathlib import Path; sys.path[:0]=["scripts/completion","scripts/windows"]; from formal_freeze import verify_sealed_study; from formal_acceptance import verify_native_acceptance; b=Path(sys.argv[1]); _,p=verify_sealed_study(b); e=json.loads((b/"archive.json").read_text())["binding"]["environment"]; verify_native_acceptance(Path(sys.argv[2]),p,Path.cwd(),environment=e); print("formal source/environment gate passed")' $pbFormal $pbAcceptance
```

退出码0、实际主输入数1152、任务数量/控制参数/设计SHA均正确，才可运行。门槛失败时保留原报错，检查是否误用了最新检出或环境发生变化，不能更改验收文件；源/科学参数确需改变时另立版本并按影响重新验收，不在本包伪装续跑。

准备中断时使用相同源码/身份/环境加 `--resume`。仅对被明确诊断的未封存失败输入，可指定 `--recover-input 完整文件名 --recovery-reason 明确原因`，原件保留；不能重建已核验输入或覆盖FROZEN。已封存输入恢复只核对，不重新调用RNG。

四、按冻结顺序运行四批

批号为0、1、2、3，顺序严格为0 main→0 cache→1 main→1 cache→2 main→2 cache→3 main→3 cache。首次每阶段运行：

```powershell
& $pbPython scripts/windows/formal_batch.py --bundle $pbFormal --host-lock $pbLock --rscript $pbRscript --r-library $pbRlib --native-acceptance $pbAcceptance --batch 0 --phase main
& $pbPython scripts/windows/formal_batch.py --bundle $pbFormal --host-lock $pbLock --rscript $pbRscript --r-library $pbRlib --native-acceptance $pbAcceptance --batch 0 --phase cache
```

确认各阶段结束、`latest-closed.json`完整任务框架与真实原生终态一致后，对1/2/3批逐条使用相同命令，仅改变batch。**不要把所有命令盲目放入忽略退出码的循环。** 不并行跑其他benchmark/分析/游戏/GPU压力任务。阶段外层墙钟包含内部任务，二者不相加；解释器/源核对/归档/传输成本另列，未知保持未知。

CLI自己的子任务由已验收原生Job管理。长运行保留真实进程句柄/工具会话；工具返回“仍在运行”时继续等待/读取日志，不能重发命令。不要用 `run_owned_command.py` 外包formal_batch，因为它会先持有同一科学锁而阻塞内部运行。旧witness_formal_stage标记formal_repetitions=0、用途为有限验收，不直接用其硬编码字段报告正式重复；可用PowerShell Stopwatch、开始/完成回执及原运行器Job记录记外层费用，不改动采样源码。

原始轨迹、实际输入、接受事件、自环、残差/数值修复、确认前缀、无进展、回退成本及全部失败均保留。H1/H2/M1等困难目标按原输出门槛执行；失败不能转普通样本，不用换输入、容差、步长、窗口、终止轮数或模型制造通过。NUTS发散与差诊断不删去，零事件不填理想ESS/Rhat。

资源等待或基础设施异常时，先确认原Job实际结束。保存全部未完成及失败日志后，用该阶段同一命令加 `--resume`：原终态只核验，未启动继续；已结束中断可按规定保留。数值失败不重试。确属基础设施且原因已记录的main任务，最多一次显式 `--resume --retry-task TASK_ID --retry-reason REASON`；cache没有重试。旧耗时未知不能补零。不要对阶段所有任务统一重试，也不能在resume时改源/环境/身份。

阶段正常关闭后保存任务状态、已付成本、实际目录大小/可用存储和原生活动观察。四批不做效果驱动的中期选择。若需人员交接，报告当前batch/phase/任务、会话/Job身份和精确恢复命令；不把工具会话中断误报为整批通过。

五、归档、分析与回传

四批任务全部得到预定终态后，源冻结和任务原件保持不动。在无活动任务时创建完整性清单，包含正式包、外层命令/资源/成本记录、原生验收原件、共享登记的可搬移证据及执行源码身份。归档位置与实验目录分开，不把归档嵌入被归档目录。

固定执行树已有可用完整归档命令：

```powershell
& $pbPython scripts/windows/export_results.py --run output/windows-formal-inference-v1 --include <本执行树内的外层记录相对目录> --output output/formal-return
```

尖括号占位由你替换为已核实路径，不原样执行。工具限定包含项必须在本执行工作树内；旧验收包在别处时另保留其已有完整主归档和SHA，不复制成假新验收。导出需干净Git，不能通过删除未提交工作“清理”。先核算原件＋tar＋解压＋分析空间；不足时不要开始一个必然挤满磁盘的大复制。可以先交回小型状态/完整文件清单，请Mac协同已有存储方案，不修改网格或丢弃证据。

超大文件分块时保留整体及每块大小/SHA、顺序、重组命令；按当前服务限制上传原Windows草稿，保持draft，不能自动公开或只回传截图。原始归档未完整上传时必须明确写“原件仍在Windows，完整独立接收未完成”，同时提供位置和保留清单。

在足够存储的全新目录安全解压，逐文件验证manifest，形成独立不可写入的delivery树。禁止覆盖正在执行的检出。后继读取从最新文档/分析检出运行；分析不运行采样，也不改变固定执行树。设 `$pbDelivery`为完整解压根，`$pbRelative`为manifest内正式包路径（使用上述export通常为output/windows-formal-inference-v1），`$pbManifestHash`为manifest实际SHA256，`$pbIndex`、`$pbAnalysis`、`$pbStats`、`$pbReport`为不存在的独立目录：

```powershell
& $pbPython scripts/analysis/formal_analyze.py index --delivery $pbDelivery --bundle-relative $pbRelative --manifest-sha256 $pbManifestHash --output $pbIndex
& $pbPython scripts/analysis/formal_analyze.py run --delivery $pbDelivery --index $pbIndex --output $pbAnalysis --rscript $pbRscript --r-library $pbRlib
& $pbPython scripts/analysis/formal_statistics.py --delivery $pbDelivery --index $pbIndex --analysis $pbAnalysis --output $pbStats
```

使用原Windows环境时不加跨平台放宽选项；失败保存，不为使分析通过修改原数据。随后取得 `$pbStats/SHA256.json` 的实际哈希，传给：

```powershell
& $pbPython scripts/analysis/formal_report.py --statistics-directory $pbStats --manifest-sha256 <统计清单实际SHA256> --output $pbReport
```

不要使用 `--fixture`。原始读取每次仅一任务；不能为速度把全部轨迹载入内存。完成后针对相同analysis加 `--resume`核验零新分析，保存原文件不变证据。分析异常单列reader error/evidence gap，不能改称采样失败或排除其任务。Mac独立重建仍是另一项验收，不能拿Windows自重建替代。

统计按128次原四链重复，主/cache框架、失败分母、成对共同有效集合、原参考及MCSE/未定项、9999次整体BCa和退化区间规则均不变。有限预算误差点不改称精确time-to-accuracy；局部缓存加速不改称后验推断加速。全失败或全减速也按协议交付。

最终推送独立交付分支的报告、协议/源码身份、全部任务状态、原始文件清单、恢复/失败记录、分析摘要/图表及依赖锁；大数组/环境/私有技能不入Git。完整证据及Git bundle用校验和绑定到原草稿。列明41472和9216各状态、数值失败/资源/基础设施中断/未执行/证据缺失、缓存调用资格、归档完成范围和实际活动进程观察时点。

本任务完成条件是按已冻结四批研究与诚实交付，不是“所有任务valid”或“出现加速”。若受存储或环境阻挡，保留已完成工作、给出具体外部需求并继续独立工作；不得无限重复旧验收。F5全部原始证据独立重建、F6最终论文及公开/投稿保留后续，不自动宣布研究全部完成。
