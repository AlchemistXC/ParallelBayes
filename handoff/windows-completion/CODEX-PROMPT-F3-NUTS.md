# Windows F3前置核验：九目标CPU NUTS

请继续ParallelBayes已经授权的原生Windows研究。先读AGENTS.md、docs/RESEARCH-COMPLETION-PLAN.md、execution/COMPLETION-WORK-PACKAGES.md和docs/NATIVE-NUTS-READINESS.md。本提示词新增F3的成熟CPU基线核验，不替代handoff/windows-completion/CODEX-PROMPT-F2-F4.md。若已有活动的CPU/CUDA实验，先确认其真实进程/句柄状态并让其完成，不并发基准、不因观察超时重启任务。不要重跑历史512项网格。

所有操作使用原生PowerShell、原生Windows Python和R；不要使用WSL2、Linux虚拟机或容器。这里只测试CPU NUTS，安装CUDA版torch不使它成为GPU NUTS。

## 源码与环境

保留原工作区、冻结环境和所有结果。从origin/codex/windows-return-audit取得本提示词与新协议，可沿用第二轮独立开发工作树；先查看状态再更新，不重置或覆盖未提交修改。数值/运行器源码冻结于b7791e08e03449bd34ee764dc560bd3934044aeb，协议为benchmark/protocols/nuts-native-readiness-windows-v1.json，规范JSON身份为6c6aadaed20f792715ab9b8b3a3bbb02181f74ecbe259aa1bb3302e370c78220。此身份不是原始JSON文件的SHA256。

运行器逐文件核对源码。若较新分支改变冻结源码，不能改哈希让它通过；使用匹配源码并保留协议/固定输入，或记录差异并在新身份下修复。固定输入在benchmark/fixtures/nuts-native-readiness-windows-v1，无需重新生成。**不要执行freeze覆盖这些文件。**

复用原Windows .venv-win-torch中已验证的Python3.12.14、torch2.13.0+cu130、NumPy2.2.6、SciPy1.15.3、Pyro1.9.2及pytest/psutil；原锁见environment/locks/windows-native-v1-replay-requirements.txt。记录实际pip freeze、pip check、解释器路径、CPU/RAM与线程环境。缺件/版本差异先记录，不能安装或升级进已冻结venv。确需重建时用单独具名原生Windows环境和原锁，不修改旧环境；驱动/GPU并非本CPU核验的依赖。

R沿用实际已安装的4.6.1、posterior1.7.0、jsonlite及其独立库。无需新装Stan、JAX GPU、CUDA Toolkit、编译工具或新算法。私有技能按原SKILLS-SETUP迁移；缺ZIP不阻止本检查，私有内容不得入Git/归档。

## 执行

从开发工作树根目录开始；下面路径按本机实际安装调整。PB_F3必须是新目录；若它已有记录，先核查是活动、完整终态或中断，再使用匹配恢复，不覆盖。

```powershell
$PB_PYTHON = 'D:/workspace/ParallelBayes/.venv-win-torch/Scripts/python.exe'
$PB_RSCRIPT = 'D:/Tools/R-4.6.1/bin/Rscript.exe'
$env:R_LIBS_USER = 'D:/Tools/R-library-4.6'
$env:PYTHONDONTWRITEBYTECODE = '1'
$PB_F3 = 'output/completion/windows-nuts-readiness-v1-attempt01'
$PB_NUTS_PLAN = 'benchmark/protocols/nuts-native-readiness-windows-v1.json'
$PB_NUTS_INPUTS = 'benchmark/fixtures/nuts-native-readiness-windows-v1'
New-Item -ItemType Directory -Path $PB_F3 -ErrorAction Stop
```

保存所有命令、stdout/stderr和退出码；每一步核对结果后再继续。pytest先运行新整批接口检查和已有两项多进程重放/隔离检查；不要把测试数加到历史65/63。测试缓存关闭仅为避免无关目录写入，不关闭系统安全策略。

```powershell
& $PB_PYTHON -m pytest tests/external/test_nuts_readiness_run.py tests/external/test_inference_parallel.py -q -p no:cacheprovider --junitxml "$PB_F3/tests.xml"
& $PB_PYTHON scripts/completion/fetch_wells.py --output "$PB_F3/wells-source"
& $PB_PYTHON scripts/completion/nuts_readiness_run.py run --protocol $PB_NUTS_PLAN --inputs $PB_NUTS_INPUTS --source "$PB_F3/wells-source" --output "$PB_F3/run"
```

水井数据若已由F4取得，可使用已完整校验的原目录作为--source，不需要重复下载。运行会尝试全部九目标，每目标一次顺序四链与一次最多四worker的CPU NUTS，各128预热、64保留步。实际PID和线程数有记录；请求四worker不等于独占四物理核。只有串行/多进程的初值、原/无约束样本、预热轨迹及初始/最终torch随机状态逐字节一致才标记该目标completed。它不是跨Mac/Windows逐字节要求，也不是与MH同轨迹比较。

summary中的completed/failed比进程退出码更重要。某目标失败时保留两种执行、部分子链、traceback和全部耗时，继续独立目标；不重抽初值、改树深、改步长目标、改容差或把失败变为通过。最大树深和内存保护保留，没有总时长截止。失败比较的结果不进入正常推断样本。

全部目标终态后保存run/summary.json副本与每个目标目录的所有文件SHA256，再实际执行相同run命令追加--resume。验收为newly_executed_targets=0、全部目标文件逐字节不变；根summary及invocations允许新增恢复调用记录。保存恢复前summary和对比回执。中断恢复也使用相同--resume入口，但仅在真实进程/句柄已结束、源码/环境/输入匹配时执行。

## 保存数组诊断

```powershell
& $PB_PYTHON scripts/completion/nuts_readiness_run.py collect --protocol $PB_NUTS_PLAN --run "$PB_F3/run" --output "$PB_F3/diagnostics"
& $PB_RSCRIPT --vanilla scripts/completion/posterior_diagnostics.R "$PB_F3/diagnostics"
& $PB_PYTHON scripts/completion/nuts_readiness_run.py verify-diagnostics --output "$PB_F3/diagnostics"
```

diagnostics必须是新目录；中途R失败时保留该尝试，另建目录重新collect，不覆盖旧roundtrip或回执。完成目标各有两份诊断，共最多18份；逐字节核验R输入/回写，保留rank/folded Rhat、bulk/tail ESS及不可判定函数。两份是配对技术执行，每目标仍只一份验证输入，不能宣称18个独立统计重复。

短链不是正式精度验证。Mac同设计九目标均完成六类数组重放，但七目标至少一个有限Rhat>1.01，L2/M1/W1包含不可判定函数。Windows如出现相同或更差诊断，仍原样报告；不为得到理想诊断换模型或延长该冻结任务。发散计数按目标和执行方式分开，不能把两个相同重放相加当作独立事件证据。Pyro未提供的完整树深命中数仍为未提供，不填零。

## 回传与后续界限

更新execution/COMPLETION-WORK-PACKAGES.md，记录分支/提交、协议身份、环境、真实passed/failed/skipped、九目标状态、工作进程及诊断。小型摘要和校验回执入自己的开发分支；完整原始数组、预热、随机状态、子进程元数据、日志和锁文件在PB_F3归档，不入Git。

按第二轮既有export_results.py和verify-windows-return.py导出并逐文件核验。可与F1/F2/F4同批回传，但各协议身份分开。若另开草稿Release上传大包，保持草稿；不要覆盖历史资产、合并main或自动公开发布。最终回报实际tar路径/大小/SHA256及缺项，不能只交截图。

本任务通过只补齐Windows九目标CPU NUTS基线的实现/资源就绪证据。正式CPU/CUDA推断协议、误差/重复规模和主实验另行冻结；不要把这里的64步短链或Mac预算pilot直接改称正式结果，不开发GPU NUTS或自动选择器。
