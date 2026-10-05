# Windows第二轮交接：外部目标核验与机制pilot

2026-10-05后继：F4等就绪回执已经接收；F2在输入哈希处停止，现应使用[原输入续跑提示词](CODEX-PROMPT-F2-RESUME.md)。下文保留原交接过程，勿再按种子重建机制输入；分析器新增必需`--inputs`参数。

请在我的原生Windows 11／AMD CPU／RTX5080电脑继续ParallelBayes。严格使用原生PowerShell、原生Windows Python和CUDA，不使用WSL2、Linux虚拟机或容器。当前授权为F1诊断回执、F4水井目标核验和已经冻结的F2开发性机制pilot。不要重跑历史512项网格，不更改旧环境、协议和结果，不自动合并main或发布Release、CRAN、期刊。

先读取AGENTS.md、docs/RESEARCH-COMPLETION-PLAN.md、execution/COMPLETION-WORK-PACKAGES.md、docs/MECHANISM-PILOT.md及docs/WELLS-TARGET-VALIDATION.md。新代码在origin/codex/windows-return-audit。保留原工作区，可从交接提交新建独立开发分支codex/windows-completion-v2及worktree。记录实际HEAD；若后续提交改变冻结源码，检查会拒绝运行，不能修改哈希使其通过，应使用交接时的提交或回报差异。

## 环境与检查

复用原生Windows已验证的Python3.12环境（torch2.13.0+cu130、NumPy2.2.6、SciPy1.15.3、psutil、pytest）及原R4.6.1、posterior1.7.0、jsonlite、reticulate。先记录实际版本与路径；缺件时先回报具体缺项，不能为满足新实验而升级/覆写原冻结venv。可以在独立新环境重建同版依赖，但记录安装命令和差异。无需新增Stan编译、JAX GPU、Pyro GPU或torch.compile。私有技能按原SKILLS-SETUP单独安装，缺少私有ZIP不阻止下列检查，不把技能放入Git或回传归档。

所有命令从新worktree根运行；根据真实路径修改以下变量，不复制venv到worktree：

```powershell
$PB_PYTHON = 'D:/workspace/ParallelBayes/.venv-win-torch/Scripts/python.exe'
$PB_RSCRIPT = 'D:/Tools/R-4.6.1/bin/Rscript.exe'
$env:R_LIBS_USER = 'D:/Tools/R-library-4.6'
$env:PYTHONDONTWRITEBYTECODE = '1'
$PB_BATCH = 'output/completion/windows-completion-v2-attempt01'
$PB_PLAN = 'benchmark/protocols/mechanism-windows-pilot-v1.json'
```

PB_BATCH须为新目录。目录已存在时先判断是已完成、失败还是活动任务，核验后使用相应恢复入口；不能覆盖。仅首次启动时用New-Item -ItemType Directory -Path $PB_BATCH -ErrorAction Stop创建目录；恢复时不重复此步。创建目录后保存命令stdout/stderr、nvidia-smi、版本输出以及开始/结束状态。逐条检查退出码和JSON，不把终端无报错等同于科学核验通过。运行GPU计时时不要并发CPU基准或其他GPU任务；不按负载删除不利测量。

```powershell
& $PB_PYTHON -m pytest tests/handoff/test_windows_wells_plan.py tests/handoff/test_mechanism_runner.py -q --junitxml "$PB_BATCH/handoff-tests.xml"
& $PB_PYTHON scripts/completion/windows_wells.py inspect
```

Mac有6项可移植检查通过；Windows应实际执行，其中“非Windows拒绝执行”一项在Windows跳过，记录真实passed/failed/skipped。尤其确认原生msvcrt互斥行为。测试不更改数值核心，也不等同于CUDA采样通过。若不通过，保留差异和完整日志；兼容性修复须提交并对受影响范围核验，科学参数/方法更改必须新建协议身份，不能改原冻结文件。

## F1：仍未完成时先做小型诊断回执

按handoff/windows-completion/CODEX-PROMPT.md运行12KiB的Rhat固定样例；若已存在真实回执，核对提交和哈希后复用，不重做。保存Windows原生中位数、两种明确中心的Rhat、机器浮点信息及二进制回写，不强行使结果吻合Mac。可将输出直接放在PB_BATCH/rhat-windows。该步骤不启动GPU。

## F4：水井目标的原生CPU／CUDA与R接口

```powershell
& $PB_PYTHON scripts/completion/fetch_wells.py --output "$PB_BATCH/wells-source"
& $PB_PYTHON scripts/completion/windows_wells.py run --device cpu --source "$PB_BATCH/wells-source" --output "$PB_BATCH/wells-cpu"
& $PB_PYTHON scripts/completion/windows_wells.py run --device cuda --source "$PB_BATCH/wells-source" --output "$PB_BATCH/wells-cuda"
& $PB_RSCRIPT --vanilla examples/external_wells.R (Get-Location).Path "$PB_BATCH/wells-source" "$PB_BATCH/wells-r-cuda" $PB_PYTHON benchmark/fixtures/wells-validation-v1/inputs.npz benchmark/protocols/wells-windows-validation-v1/cuda.json
& $PB_RSCRIPT --vanilla scripts/completion/diagnose_wells_example.R "$PB_BATCH/wells-r-cuda/draws.rds" "$PB_BATCH/wells-r-diagnostics.json"
& $PB_PYTHON scripts/completion/verify_windows_wells.py --source "$PB_BATCH/wells-source" --cpu "$PB_BATCH/wells-cpu" --cuda "$PB_BATCH/wells-cuda" --r-return "$PB_BATCH/wells-r-cuda" --output "$PB_BATCH/wells-return-verification.json"
```

CPU/CUDA各有独立新协议。模型保持原平坦先验、dist/100、alpha/beta次序；复用同一实际数组、4链×96步及原容差。要求密度、梯度/HVP、独立NumPy轨迹、接受事件、CPU/CUDA配对、R重放及二进制数组检查。最后的接收核验不导入torch/JAX。

这些短链用于正确性；Mac同样例Rhat约3.04/3.82，不能声称收敛或推断加速。R重放不增加独立重复数。水井有限MCMC参考的符号事件全零，独立积分另给约4.77e-11，参见WELLS-REFERENCE-AUDIT和WELLS-QUADRATURE；不把常量链诊断填成1或零误差。某项F4失败时保留完整输出，继续不依赖它的内置目标F2任务。

## F2：已冻结的192个工作流配置

```powershell
& $PB_PYTHON scripts/completion/mechanism_runner.py prepare --plan $PB_PLAN --inputs "$PB_BATCH/mechanism-inputs"
& $PB_PYTHON scripts/completion/mechanism_runner.py run --plan $PB_PLAN --inputs "$PB_BATCH/mechanism-inputs" --output "$PB_BATCH/mechanism-cpu" --device cpu
& $PB_PYTHON scripts/completion/mechanism_runner.py run --plan $PB_PLAN --inputs "$PB_BATCH/mechanism-inputs" --output "$PB_BATCH/mechanism-cuda" --device cuda
& $PB_PYTHON scripts/completion/analyze_mechanism_pilot.py --plan $PB_PLAN --inputs "$PB_BATCH/mechanism-inputs" --run "$PB_BATCH/mechanism-cpu" --output "$PB_BATCH/mechanism-analysis-cpu"
& $PB_PYTHON scripts/completion/analyze_mechanism_pilot.py --plan $PB_PLAN --inputs "$PB_BATCH/mechanism-inputs" --run "$PB_BATCH/mechanism-cuda" --output "$PB_BATCH/mechanism-analysis-cuda"
```

每设备36组、96个工作流，G1/G2/L1及2份实际主数组；含窗口/链数网格、G2/RWM预设步长对照和512总输出的链分配对照。每工作流有1次审计、3次交错计时重放及1次探针后重放；固定状态探针另计。它们不是5次独立MCMC重复。每台设备的循环完成不代表96项都成功，必须报告completed/failed/pending。

检查点恢复使用完全相同的run命令追加--resume。操作系统锁仍被活动进程持有时不可另开执行器。只有工具句柄/进程确认结束后才恢复；观察超时不等于运行终止。源码、环境、输入、配置或哈希不同则停止该恢复，保留原尝试。不删除慢配置、失败任务或状态文件来重试；无总时长限制，但保持冻结的迭代和内存保护。

计时必须保留设备同步、CPU进程时间、原始数组、接受事件、每轮记录、JVP/映射次数、主机标量等待和内存。探针不是可相加的总耗时分解；同资源更多链也不是同一后验轨迹。保留低接受率与不利结果，不宣称本pilot完成F3正式推断比较，不自行开发选择器或扩展网格。

## 归档、推送和回传

更新execution/COMPLETION-WORK-PACKAGES.md中的实际回执。将小型状态、验证回执、分析CSV和日志索引提交到自己的开发分支；原始大目录及输入留在PB_BATCH，不入Git。记录source/protocol/依赖/设备版本、passed/failed/skipped、所有配置状态和哈希，不覆盖历史CPU/Windows归档。

提交后确保工作区干净，创建源码历史bundle并使用现有通用归档器。以下命令中的PB_BATCH必须只包含本轮实验材料，不能包含私有技能、环境目录或凭证：

```powershell
git bundle create "$PB_BATCH/source.bundle" HEAD
git bundle verify "$PB_BATCH/source.bundle"
& $PB_PYTHON scripts/windows/export_results.py --run $PB_BATCH --include benchmark/protocols/mechanism-windows-pilot-v1.json --include benchmark/protocols/wells-windows-validation-v1 --include benchmark/fixtures/wells-validation-v1 --output output/windows-completion-return
```

归档器沿用windows-native-时间戳命名，但其内部协议必须是本轮新身份。读取工具实际返回的tar路径，运行scripts/verify-windows-return.py TAR_PATH --output VERIFY_JSON，逐文件核验通过后才回报。保留tar、相邻sha256及独立核验回执。

推送开发分支，使Mac端能取得小型结果。大归档可使用同仓库新的草稿Release附件回传，不能公开发布草稿，也不能覆盖cpu-review-v1或windows-native-v1资产。最终报告分支/提交、协议、真实任务状态、包大小及SHA256、缺项和局限。需要兼容修复时保留diff；不要只交截图或成功摘要。
