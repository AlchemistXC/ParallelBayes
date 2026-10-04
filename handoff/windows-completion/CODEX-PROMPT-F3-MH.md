# Windows F3前置核验：已选MH核、仿射目标与时间执行器

请继续已授权的ParallelBayes原生Windows研究。先读AGENTS.md、docs/RESEARCH-COMPLETION-PLAN.md、execution/COMPLETION-WORK-PACKAGES.md和docs/SELECTED-MH-READINESS.md。本项补F3正式比较的组合核验，不替代F1/F2/F4或CPU NUTS核验。已存在活动实验时先检查实际进程/句柄，让其完成并归档；不并发运行性能任务、不因观察超时重启。

使用原生PowerShell和原生Windows Python，不使用WSL2。保存原分支、冻结环境及结果。从origin/codex/windows-return-audit取得以下新文件，在第二轮独立开发工作树执行；有本地修改时先检查和保留，不重置。采样源码冻结于779b8e4c56ba62939f365f6d723d71319dead221，伴随分析在fc48d76。运行器逐文件核对源码；不能修改哈希绕过检查，兼容性修复必须另存差异和新身份。

## 环境与输入

沿用已验证的Python3.12.14、torch2.13.0+cu130、NumPy2.2.6、SciPy1.15.3、pytest、psutil及NVIDIA驱动。记录解释器路径、完整依赖锁、pip check和nvidia-smi。旧锁为environment/locks/windows-native-v1-replay-requirements.txt。缺件或版本差异先记录，确需重建则建独立环境，不升级原冻结venv。本项不新增JAX、Stan、CUDA Toolkit、R或新算法依赖。私有技能仍按原SKILLS-SETUP处理，缺ZIP不阻止科学核验，私有文件不入Git或结果包。

三份新协议和共同输入已冻结；这里执行两份Windows协议，每设备54工作流：

- benchmark/protocols/selected-mh-readiness-windows-cpu-v1.json；规范身份de1a3bdb35fef84c98fe502cc925574f9092f16da5959f691490b5f1ee55d2e5。
- benchmark/protocols/selected-mh-readiness-windows-cuda-v1.json；规范身份e29d26f2d5836c91001be9bfd5a7c6f156b54c96daf2cbaeaa30fb04d32acf93。
- 共同实际输入：benchmark/fixtures/selected-mh-readiness-v1，九份NPZ；不要运行freeze重新生成或覆盖。

每目标四链256步，精确沿用已选步长和仿射坐标；顺序RWM/MALA，以及窗口8/32的Picard/quasi-DEER。使用实际保存初值和提议/接受/求解随机数组。各执行器、窗口和平台是配对技术验证，不是独立统计重复。短路径通过不能代替正式长路径逐条核验。

## 执行与验收

以下路径按已验证的本机环境调整。PB_MH为全新目录；若已有记录，先检查活动/终态，再使用明确恢复。用PowerShell日志保存每条命令的stdout/stderr与退出码；每步检查结果后继续。

```powershell
$PB_PYTHON = 'D:/workspace/ParallelBayes/.venv-win-torch/Scripts/python.exe'
$PB_MH = 'output/completion/windows-selected-mh-v1-attempt01'
$PB_INPUTS = 'benchmark/fixtures/selected-mh-readiness-v1'
$env:PYTHONDONTWRITEBYTECODE = '1'
New-Item -ItemType Directory -Path $PB_MH -ErrorAction Stop
& $PB_PYTHON -m pytest tests/external/test_inference_targets.py tests/external/test_selected_mh_readiness.py -q -p no:cacheprovider --junitxml "$PB_MH/tests.xml"
```

应有CPU目标、CUDA目标和整批接口三个实际测试案例。Mac中的CUDA跳过不算这里通过；如CUDA测试跳过，记录不可用原因，不将CPU替代为CUDA。弃用和数值警告原样保留。

复用F4或NUTS检查已经取得并完整校验的水井来源目录；没有时才运行下载器取得八份锁定来源及许可：

```powershell
& $PB_PYTHON scripts/completion/fetch_wells.py --output "$PB_MH/wells-source"
$PB_SOURCE = "$PB_MH/wells-source"
$PB_CPU_PLAN = 'benchmark/protocols/selected-mh-readiness-windows-cpu-v1.json'
$PB_CUDA_PLAN = 'benchmark/protocols/selected-mh-readiness-windows-cuda-v1.json'
& $PB_PYTHON scripts/completion/selected_mh_readiness.py run --protocol $PB_CPU_PLAN --inputs $PB_INPUTS --source $PB_SOURCE --output "$PB_MH/cpu-run"
& $PB_PYTHON scripts/completion/audit_selected_mh.py --protocol $PB_CPU_PLAN --inputs $PB_INPUTS --source $PB_SOURCE --run "$PB_MH/cpu-run" --output "$PB_MH/cpu-audit"
& $PB_PYTHON scripts/completion/selected_mh_readiness.py run --protocol $PB_CUDA_PLAN --inputs $PB_INPUTS --source $PB_SOURCE --output "$PB_MH/cuda-run"
& $PB_PYTHON scripts/completion/audit_selected_mh.py --protocol $PB_CUDA_PLAN --inputs $PB_INPUTS --source $PB_SOURCE --run "$PB_MH/cuda-run" --output "$PB_MH/cuda-audit"
```

成功门槛是各设备九目标、54工作流、36组成对检查的真实状态，以及保存数组重放结果；进程退出0不等于全部通过。目标密度/梯度/HVP/Jacobian、接受事件和原路径容差均不放宽。任何失败、非有限输出、全拒绝链、原始失败轨迹和异常堆栈保留。失败不能变为普通后验样本，不重抽随机数，不修改步长/窗口重跑该冻结身份。继续其他独立目标；没有总时长截止，但迭代/内存保护保留。

全部任务终态后，对cpu-run及cuda-run分别保存原summary副本和所有目标目录文件的SHA256，再执行对应run命令追加--resume。验收为newly_executed_targets=0、每个目标终态文件不变；根summary和invocations可以新增恢复调用记录。保存前后比较回执。若运行中断，仅在真实句柄终止后恢复同一身份。

Mac的54/54工作流和36/36配对已经通过，但H1/MALA有一条全拒绝链；不代表探索充分。Mac的G2/A1 slogdet警告返回了有限值，独立三角对角对数核对差≤2.85e-14，原警告保留。Windows如出现警告，不自行屏蔽或改变冻结算法；伴随audit会核对实际坐标目标身份和行列式值。

## 回传

更新自己的开发分支进度，逐项记录源码提交、协议、实际设备、passed/failed/skipped、全部目标/工作流、独立重放及恢复情况。计时保留但不从本次单次验证制作速度排行榜。完整输入、cpu/cuda原始输出、失败、审计、恢复前summary、日志、锁和环境清单统一打包；小型摘要/校验回执入Git，大数组不入Git。沿用第二轮export_results.py与verify-windows-return.py做完整归档校验，保留原有结果，不能只返回成功摘要或截图。

可以与F1/F2/F4/NUTS同批回传，各协议身份保持独立。若上传新草稿Release，保持草稿，不覆盖历史资产、不合并main或自动公开。正式推断实验另有协议；本任务不开发新采样算法或选择器。
