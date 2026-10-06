# Windows 后续：使用原始冻结输入完成 F2 机制 pilot

> 状态更新（2026-10-07）：本提示词已执行并完成独立接收，保留作历史复现说明。不要再次提交给Windows Codex启动相同任务。当前证据与下一阶段见[接收报告](../../docs/WINDOWS-FOLLOWUP-INTAKE.md)。

请继续 ParallelBayes。第二轮 `ced54ef` 已由 Mac 接收；F1、水井、九目标 NUTS 与 CPU/CUDA MH 就绪核验无需重跑。本次只完成尚未执行的 F2：原生 Windows CPU/CUDA 共192个工作流。不要启动尚未冻结的正式推断网格。

先读取 `docs/WINDOWS-ROUND2-INTAKE.md`、`docs/MECHANISM-PILOT.md`、`handoff/windows-completion/CODEX-PROMPT-F2-F4.md` 与 AGENTS.md。本文件更新 F2 的输入传递和分析命令；其余科学约定不变。

## 代码与环境

拉取 `origin/codex/windows-return-audit` 的最新提交；保留原分支、结果和未提交修改。没有活动实验且工作区干净时，可从它新建 `codex/windows-mechanism-completion`；否则建立独立 worktree，不切换活动实验源码。记录实际 HEAD。

只使用原生 Windows、既有冻结 Python/torch CUDA 环境及实际 RTX5080。不要升级依赖、改成 WSL2、将 CUDA 任务静默替换成 CPU，或改写协议哈希。本轮修复只改变非冻结的分析器输入方式，`mechanism_runner.py`、`mechanism_probes.py` 及冻结数值源码没有改变。

```powershell
$PB_PYTHON = 'D:/workspace/ParallelBayes/.venv-win-torch/Scripts/python.exe'
$PB_PLAN = 'benchmark/protocols/mechanism-windows-pilot-v1.json'
$PB_BATCH = 'output/completion/windows-mechanism-original-attempt01'
$PB_DOWNLOAD = 'downloads/mechanism-windows-original-v1'
$PB_INPUTS = "$PB_BATCH/original-inputs"
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONUTF8 = '1'
```

按实际环境修改 Python 路径；不要复制或改造冻结 venv。PB_BATCH 必须是新目录；恢复时使用原目录，先检查活动进程与原身份，不重复创建、解压或覆盖。

## 取得已核验的原文件

Mac 原文件已经补入同仓库现有草稿 `windows-completion-v2-20261005`。草稿需用有权限的 GitHub 账号读取。不要公开发布草稿。

```powershell
gh release download windows-completion-v2-20261005 --repo AlchemistXC/ParallelBayes --dir $PB_DOWNLOAD --pattern 'mechanism-windows-pilot-v1-original-inputs.tar*'
if ($LASTEXITCODE -ne 0) { throw 'Download failed; preserve existing files and inspect access' }
$PB_ARCHIVE = "$PB_DOWNLOAD/mechanism-windows-pilot-v1-original-inputs.tar"
$PB_EXPECTED = '2b46eedc58067c920c8519cb4f99965bf944202f57392514d4643b847f9b9e5a'
if ((Get-FileHash -Algorithm SHA256 $PB_ARCHIVE).Hash.ToLowerInvariant() -ne $PB_EXPECTED) { throw 'Archive checksum differs' }
New-Item -ItemType Directory -Path $PB_INPUTS -ErrorAction Stop
tar -xf $PB_ARCHIVE -C $PB_INPUTS
if ($LASTEXITCODE -ne 0) { throw 'Extraction failed' }
& $PB_PYTHON scripts/completion/mechanism_runner.py prepare --plan $PB_PLAN --inputs $PB_INPUTS
if ($LASTEXITCODE -ne 0) { throw 'Original input verification failed' }
```

文件已下载时核对而非覆盖；目录已解压时只执行双重哈希核验。包大小10,823,680字节，只含六份原始NPZ：G1/G2/L1各r0、r1。清单见 `benchmark/fixtures/mechanism-windows-pilot-v1/transport.json`。

协议身份必须仍为 `9d8985f579a64df95ebbb22ce0a607020261e5a66516efc80edcf9c956894b2c`。现有 `prepare` 对已存在文件检查原文件哈希，`run`还会检查实际数组哈希。

原 Windows 候选与原文件仅在82个 `log_uniform` 值上有末位差异；noise和directions相同。保留旧 `mechanism-rejected-inputs/` 及准备失败日志；**不得**通过重新生成、取整或替换协议哈希放行。原文件不含个人信息或观测数据，只有固定种子的合成随机输入。

## 执行、分析与恢复

先运行本次修复涉及的检查，使用新的 pytest 临时目录，保存 stdout/stderr、JUnit、退出码及实际版本：

```powershell
& $PB_PYTHON -m pytest tests/handoff/test_mechanism_analysis_inputs.py tests/handoff/test_mechanism_runner.py -q --basetemp "$PB_BATCH/pytest-temp" --junitxml "$PB_BATCH/tests.xml"
```

这5项接口检查不等同于192个科学工作流。测试失败先保留并定位；不得修改冻结算法或容差来通过。执行以下命令时分别保存日志、命令、开始/结束时间、退出码、源提交和环境；不要复用硬编码旧批次路径的 `run_windows_completion_step.py`。

```powershell
& $PB_PYTHON scripts/completion/mechanism_runner.py run --plan $PB_PLAN --inputs $PB_INPUTS --output "$PB_BATCH/mechanism-cpu" --device cpu
& $PB_PYTHON scripts/completion/analyze_mechanism_pilot.py --plan $PB_PLAN --inputs $PB_INPUTS --run "$PB_BATCH/mechanism-cpu" --output "$PB_BATCH/analysis-cpu"
& $PB_PYTHON scripts/completion/mechanism_runner.py run --plan $PB_PLAN --inputs $PB_INPUTS --output "$PB_BATCH/mechanism-cuda" --device cuda
& $PB_PYTHON scripts/completion/analyze_mechanism_pilot.py --plan $PB_PLAN --inputs $PB_INPUTS --run "$PB_BATCH/mechanism-cuda" --output "$PB_BATCH/analysis-cuda"
```

逐条检查退出码及 JSON，再决定后继动作。CPU/CUDA按顺序计时，不与其他基准并行。数值失败、减速、低接受率和常量函数保留；一台设备的故障不阻止另一台可独立执行的任务。分析器现在必须显式传 `--inputs`，它核对冻结主文件后才核对各组前缀，不再按种子重建期望输入。缺文件时应报错，不能退回旧分析器。

已启动的设备运行只在确认原进程结束且身份/哈希一致后，用相同 `run` 命令追加 `--resume`。已成功或失败的终态不重算；不要删除状态绕过失败。观察超时不是停止证据。无总时长截止；数值迭代和内存保护保留。分析输出使用新目录，旧分析不得覆盖。

每设备36组、96个工作流。每工作流的首次审计、3次缓存重放、探针后重放是技术测量，不是5个独立MCMC重复。独立主输入每模型只有2份，不据此输出一般加速或稳定排序声明。不要将重叠操作探针耗时相加制造总时间分解。

## 验收与回传

报告两设备全部组/工作流的 completed/failed/pending、接受事件和路径核验、实际GPU/精度、缓存及API计时、映射/JVP/前缀、主机等待与进程CPU占用。没有加速同样交付；不靠选择性删除获得优势。

终态后保存逐文件快照，并实际执行一次 `--resume`；核对新增组为0、所有终态资产保持不变。不要把终态恢复验证说成中途恢复或Windows进程集合保护已验证。

更新工作包和小型摘要；将源码、测试、修复分析器、原协议身份和摘要提交并推送自己的开发分支，不合并main。大原始输出、六份原输入、环境锁、全部命令/失败记录及源码bundle另行归档，使用 `scripts/windows/export_results.py` 并用 `scripts/verify-windows-return.py` 逐成员核验。保留旧第二轮包；新包可作为现有草稿的新增附件，不使用覆盖选项、不公开发布、不包含私有技能或凭证。

回报提交号、归档名称/大小/SHA256、完整状态及明确未完成项。F3正式推断、Windows长期任务进程/资源保护与最大任务、F5两平台干净安装、F6论文仍是后续门槛；不要把本次机制pilot标为整个研究完成。
