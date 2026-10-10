# S2：Windows 原生 CPU NUTS 有限故障定位

这是三项补充计划中的 S2。复用此前 Windows 原生环境和已固定输入；不启动旧主网格，不运行 GPU 实验。当前源码在 Mac 通过便携检查，Windows Job 测试和四条件 NUTS 资格仍须在台式机实际完成。只有通过后才能冻结本次新协议并开始主体调用。

把同目录 `CODEX-PROMPT.md` **完整一次性**交给 Windows Codex，由它按阶段执行。每阶段的脚本会检查进入条件，不需把旧的四轮提示词重新发送。

## 转交材料

1. 获取开发分支 `codex/research-integration` 的最新代码，另建 `codex/windows-nuts-localization` 工作分支，保留本机现有工作。
2. 单独取得输入包 `windows-nuts-localization-inputs-v1.tar`，校验随附 receipt，再解压到新目录。包约 21 MiB，含九个固定案例、三套旧诊断轨迹及逐文件哈希，不需重新下载 29.31 GB 主证据。
使用仓库校验工具解包：`python scripts/followups/verify_nuts_input_archive.py --archive <输入tar路径> --output <新输入目录>`。它同时验证固定归档SHA、成员集合及每个文件。具体包大小与哈希见同目录`input-package.json`。

3. 输入目录的 `checksums.json` SHA256 必须为 `d92824d78f352295449d80556368fd9ee3bed1e9b7af2d0443c3ffb7bfbc7504`。协调器也会检查这个固定值。

## 环境

选择此前冻结的原生 Windows Python 3.12 环境；要求 numpy 2.2.6、scipy 1.15.3、psutil 7.1.0、pyro-ppl 1.9.2、torch 2.13.0+cu130，以及 R 4.6.1（2026-06-24 ucrt）、posterior 1.7.0、jsonlite 和 pytest。torch CUDA wheel 在本轮只执行 CPU 路径。不要升级冻结环境，也不要使用 WSL、虚拟机或容器。若原环境无法取得，保留差异并停止进入正式定位；另记兼容性方案。

启动可用 RAM 至少 12 GiB。单次 Job 提交内存硬限制 12 GiB，进程树 RSS 每 0.2 秒观察并以 8 GiB 保护。工作文件上限 6 GiB；本轮新增文件加一份归档每机不超过 20 GiB。预留空间检查包括剩余输出、归档和 4 GiB 余量。无总实验时长上限。

## 阶段与命令

先由 Codex 核对本机路径。下例变量须指向实际原生环境与目录，不能照抄为不存在的路径。所有阶段使用同一个旧研究已有的 host lock 路径，以阻止本项目协作程序同时运行。

```powershell
$StudyPython = '已核对的原生冻结环境/python.exe'
$StudyR = '已核对的Rscript.exe'
$StudyRLibrary = '已核对的原R包库'
$StudyInputs = '已解压且校验的输入目录'
$StudyOutput = 'output/nuts-localization-v1'
$StudyLock = '原项目共用的host-lock绝对路径'

& $StudyPython scripts/followups/run_nuts_localization.py prepare --inputs $StudyInputs --output $StudyOutput --host-lock $StudyLock --rscript $StudyR --r-library $StudyRLibrary
& $StudyPython scripts/followups/run_nuts_localization.py check --output $StudyOutput --host-lock $StudyLock
& $StudyPython scripts/followups/run_nuts_localization.py diagnostics --output $StudyOutput --host-lock $StudyLock
& $StudyPython scripts/followups/run_nuts_localization.py qualify --output $StudyOutput --host-lock $StudyLock
& $StudyPython scripts/followups/run_nuts_localization.py freeze --output $StudyOutput --host-lock $StudyLock
& $StudyPython scripts/followups/run_nuts_localization.py run --output $StudyOutput --host-lock $StudyLock
& $StudyPython scripts/followups/run_nuts_localization.py verify --output $StudyOutput --host-lock $StudyLock
& $StudyPython scripts/followups/analyze_nuts_localization.py --study $StudyOutput --output output/nuts-localization-analysis-v1
& $StudyPython scripts/followups/export_nuts_localization.py --study $StudyOutput --analysis output/nuts-localization-analysis-v1 --destination output/windows-return/windows-nuts-localization-v1.tar --host-lock $StudyLock
```

逐条确认退出码后再进入下一条。`qualify` 若失败，不能接着 `freeze`；先保存失败、修正兼容性实现、提交源码，再用同一研究目录进行下一轮资格。每轮四次，最多三轮。每个注册调用立即消耗配额，包括未能启动与中断，不允许删除 registry 重置计数。主体 36 次，技术确认最多 8 次；与资格合计最多 48 次四链调用。

恢复先运行 `verify`。它只核查、或在查询受管 Job 确已结束后记录中断结果，不重新执行任何调用。然后按尚未完成阶段继续；已有任务只校验和复用。资源错误会停止后续启动，应检查现有记录和实际资源，不通过放宽保护或更换输入追求完成。

## 返回

交付完整源码提交、环境记录、原生 pytest 日志、全部调用登记、阶段事件、部分链、诊断返回值、Job/内存/退出记录、同输入条件比较、分析输出和逐成员校验的 tar。报告资格、主体、确认、诊断作业的实际数量及所有失败。最终查询本轮受管理活动进程为零，并执行两次只核验恢复，记录新增执行均为零。

历史 105 项失败保留；新保存的样本是定位证据，不计入正式推断。未复现不等于已修复；诊断旁路后成功不单独证明 ESS 是根因。文稿新增结论等待 Mac 独立接收。
