你正在原生 Windows 11 / AMD CPU / RTX 5080 上接手 ParallelBayes 的新 v2 适配验收。请实际执行以下完整流程，最后提交报告和完整证据。这份提示词一次全文提供，按阶段顺序执行。它是新任务；F2、原 27/24 技术批次及候选安装已经由 Mac 接收通过，无需重跑旧提示词。

一、源码、环境和范围

先读 AGENTS.md、docs/FORMAL-NATIVE-VALIDATION.md、docs/FORMAL-DISPATCH.md、docs/FORMAL-NATIVE-EVIDENCE.md、docs/WINDOWS-FOLLOWUP-INTAKE.md。当前统一分支为 origin/codex/research-integration，必须包含执行提交 06e75c113e3ea6ea5a2a4275d7341595eefd7191。若该分支有后继文档提交，使用包含该提交的最新版本，记录实际 HEAD。

检查当前工作树和分支。保留既有冻结工作树，在短路径 SSD 目录建立或复用合适的独立开发工作树，分支可用 codex/windows-formal-adapter-validation；不要重置旧工作树或覆盖未提交工作。保持 Git 规范 LF 字节，源码/测试必须提交且工作区干净才能 prepare。不要把旧受限技术入口 technical_batch.py 扩网格。

使用上一轮实际通过且已冻结的原生 Windows Python / torch CUDA / NumPy / SciPy / Pyro / psutil / pytest 环境，以及实际 Rscript 和 posterior 所在 R 库。先从上轮回执确认路径，不猜测环境名；不在冻结环境内升级、重装包或运行 bootstrap。命令会核对完整 Python 包版本、驱动/设备、原 venv 标记、R 和 posterior。缺依赖时保存错误，再建立明确命名的新候选环境，重新核验后冻结新目录，不混用环境续跑。

继续使用原生 PowerShell；不使用 WSL2、虚拟机或 Linux 容器。当前验收不需要安装新的模型语言、GPU NUTS、Stan 工具链或编译后端。可以使用已安装且适用的 codebase-design、tdd、nature-experiment-log 等技能；读取后按实际作用使用。私有技能 ZIP 缺失时记录，不阻塞本任务、不从公开仓库猜测替代内容。

独立验证身份固定为 windows-formal-adapter-validation-v1。三目标为 G1、G2、W1；27 主任务、24 缓存探测。G1/W1 每链保留64步；G2每链保留16,384步；MH另有512步，NUTS预热1024步。与正式方案共用数值参数。输入、坐标、接受事件、容差、停止和失败资格均不得改动；正式统计重复数为0。不要启动41,472主任务或9,216缓存探测，Mac还在完成正式原始结果分析入口。

二、准备路径并冻结

由你核对并设置下列 PowerShell 变量的真实路径，用户无需手填：

- `$pbPython`：上轮原生环境中的 python.exe。
- `$pbRscript`、`$pbRlib`：已通过的 Rscript.exe 和 R 库。
- `$pbExternal`：已核验 posteriordb 快照根目录；应包含 `LICENCE.md` 和 source-manifest.json 列出的 posterior_database 相对路径，共八文件。使用既有本地快照；缺件按 models/external/wells/source-manifest.json 的固定上游提交补取，逐件校验，不用更新的随机版本替代。
- `$pbLock`：此前全项目科学运行共用的绝对主机锁路径。读取旧回执确认，不另设一个锁绕过其他活动任务；该路径须在本轮证据目录之外。
- `$pbBundle`：新短路径工作树下 `output/formal-adapter-validation-v1` 的绝对路径，首次必须不存在。父目录先建立，SSD/RAM/显存实际可用资源记录清楚。
- `$pbTar`：另一个结果目录内全新的 `.tar` 路径，不能在 `$pbBundle` 内。

在新工作树根目录逐条执行并检查退出码：

```powershell
& $pbPython scripts/windows/validate_formal_adapter.py prepare --output $pbBundle --external $pbExternal --host-lock $pbLock --rscript $pbRscript --r-library $pbRlib
```

此步骤只生成三份新身份实际输入，保存源码、测试/夹具、水井数据、依赖及地址，并封存协议。旧环境标记和历史输入不改。磁盘保护仅表示当前准备/任务边界的储备，不是整个运行必定装得下的保证。

若准备中断，保留目录，按同一源码/环境加 `--resume`。只有报出某个输入未完成、且你已查明原因时才加 `--recover-input 完整输入文件名 --recovery-reason 明确原因`，它保留原件；已封存输入不得重建。部分协议封存失败也不覆盖，先报告/留档再处理。

三、运行实际原生行为测试

```powershell
& $pbPython scripts/windows/validate_formal_adapter.py test --bundle $pbBundle
```

它通过受管理的 ancillary Job 运行16个原生行为用例，包括真实 Job/子进程、CPU/CUDA故障夹具、旧 v1登记衔接、v2登记和终态恢复。验收必须16通过、0失败、0跳过；Mac上的人工文件测试不替代本步骤。保留原 XML、命令日志、所有测试目录及 Job 观察。原测试用例中的等待限时是夹具就绪判断，不是科学任务时限。

失败时先诊断；再次行为测试必须显式给 `--repeat-reason`，旧尝试保留。若需要修改源码、依赖、参数或协议，保存差异和失败包，新提交后在新目录重新冻结，不能修改原包后继续冒充同一身份。

四、依次运行主任务、缓存及零重算核验

行为测试通过后：

```powershell
& $pbPython scripts/windows/validate_formal_adapter.py run --bundle $pbBundle --phase main
& $pbPython scripts/windows/validate_formal_adapter.py run --bundle $pbBundle --phase cache
& $pbPython scripts/windows/validate_formal_adapter.py run --bundle $pbBundle --phase main --verify-only
& $pbPython scripts/windows/validate_formal_adapter.py run --bundle $pbBundle --phase cache --verify-only
```

每条命令结束并检查退出码后才执行下一条，不并行跑其他 benchmark、游戏或 GPU 压力任务。不要人为设置总实验时限；已有数值迭代、RAM/磁盘、Job commit 和显存检查继续生效。跟踪真实进程句柄或原生 Job，不仅凭状态文件或长时间无输出判定进程已停。

27主任务中，24 MH使用独立NumPy全路径及实际随机数组核验；3个CPU NUTS使用四个受管理spawn worker，不作MH同路径声明。24缓存任务保存96次调用，不将缓存重放当作后验样本或新统计重复。保留全拒绝、差诊断、额外工作和慢配置。

进程中断后先确认原任务实际终止，再用同一命令加 `--resume`，继续未启动任务；已结束任务只核验，未知旧耗时不补零。本有限验收入口不重试采样任务。若出现数值失败、资源失败或中断，完整保留并回传；程序可能完成任务框架但不会给出通过的验收文件。不要为了通过而换随机输入、调步长、改容差、删失败或另选模型。

两次 `--verify-only` 必须报告新执行数0，全部原任务文件不变。它不能启动尚未运行的登记项。

五、封存、核对、导出

所有要求满足时：

```powershell
& $pbPython scripts/windows/validate_formal_adapter.py seal --bundle $pbBundle
& $pbPython scripts/windows/validate_formal_adapter.py verify --bundle $pbBundle
& $pbPython scripts/windows/validate_formal_adapter.py export --bundle $pbBundle --output $pbTar
& $pbPython scripts/verify-windows-return.py $pbTar
```

封存会检查实际 pytest 命令/Job终态、全部任务/原始资产、固定任务绑定及额外核验账本，然后才生成 native-acceptance.json。保存 tar、.sha256、.receipt.json 和核验输出。封存后仅做只读核验/导出；不要再往原包写入执行记录。

在新的独立目录安全解压归档，核对 WINDOWS-RETURN-MANIFEST.json 中所有路径、文件大小和哈希，再针对其中 `validation/` 目录运行上述 verify。不要覆盖活动检出或旧数据。记录搬移结果；本轮不必重新采样或重新安装 R 包。

若未通过，仍须交付所有失败日志、冻结/部分冻结资料、实际任务状态与已有原始输出。确认本轮进程已结束后，可以使用现有 scripts/windows/export_results.py 对工作树内 `$pbBundle` 作完整性归档，明确标记“未通过”；它不能生成或替代 native-acceptance.json。不得因为失败而只返回摘要。

六、报告与交回

更新 execution/windows-native/WORK-PACKAGES.md 并新增本轮结果报告，列明源码提交、协议/封存哈希、环境、实际命令、16项测试计数、27/24各状态、96缓存调用、原件不变核验、所有失败及修复差异。清楚区分数值核验、进程结束、诊断和统计收敛；本轮不形成正式性能/推断结论。

源码/小型协议摘要/日志回执在独立开发分支提交并推送，不能强推或合入main。大原始包、原始NPZ、环境和私有技能不入Git。将完整归档及校验材料附到既有 Windows 草稿 Release，保持 draft；若上传受大小限制，分块并保留各块及整体SHA256。另附本分支Git bundle及哈希，方便Mac独立接收源码身份。不要自动公开Release、CRAN或投稿。

最终告诉用户：分支与最新提交、结果包/草稿位置、通过与未通过项、总任务状态、归档哈希、是否还存在真实活动进程。完成本轮即交回Mac；正式全模型实验仍由后续协议和提示词启动，不将有限原生验收报告成整个研究完成。
