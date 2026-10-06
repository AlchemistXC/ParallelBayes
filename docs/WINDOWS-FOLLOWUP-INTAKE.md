# Windows 后续证据独立接收（2026-10-07）

**原先缺少 Windows 回执的阻塞已解除。** 已接收并合入 `codex/research-integration`：机制分支 `1cfc83d9f979b0b58e830affc67ac22e277acc7d`、运行器分支 `b0582c33a5ea855c384acc9b15da908dea2999b6`、安装分支 `0e44c2d5f2d5923f3c4ffa1c0700a18aca88b75b`。机制与运行器合并后再合入安装分支，合并点 `d7bfcdd`。保留各来源、历史协议、旧失败、主分支和原始数组。

本次使用 data-analytics:validate-data 的证据与方法核验流程。验收的是这些有限任务和实际收到的产物；不是 Windows 上的重新执行、正式推断完成或整个研究完成。下一工作为正式驱动/冻结/分析接口的规模验收，再形成新的原生 Windows 正式实验协议和交接命令。已完成的 F2、运行器技术批次及候选安装提示词不再执行。

## 收到并核验的证据

五个归档均来自原 `windows-completion-v2-20261005` 草稿附件。逐一核对大小、外层 SHA256、路径安全、完整清单及解压文件，共 **7,658 个清单文件**。科学重建结束后再次核对，全部原件未变。三个 Git bundle 也通过 `git bundle verify`。草稿没有公开，原始数组未纳入 Git。

| 归档时间戳 | 字节数 | 文件数 | SHA256 |
|---|---:|---:|---|
| `20261006T111324Z` 机制 | 186511360 | 3107 | `ec69fd8032cae9198cd1eb7823f903eebb72bcc624a942b7da6373598b3d6ba7` |
| `20261006T170711Z` 运行器 | 1083330560 | 3753 | `6ef0f6e299867d67b27cbd4067a062a30f3593894dc4b34c1da9086f80ae7274` |
| `20261006T171222Z` 运行器伴随 | 33792000 | 191 | `a1f5752ad98b4d69c55a342a4f360d3162f6f35b7e8fc3c2f9156fe14a2a0ddb` |
| `20261006T173502Z` 安装 | 49428480 | 547 | `9b8b805a4f4605541717f3644ff931e385156bf5f4ca009738a5a9f08d6017ce` |
| `20261006T173742Z` 安装伴随 | 286720 | 60 | `53bf0afa96abaf094f6846cd3a0e29a56a96eea8cac0af8b513bd8003703ce8d` |

原回传分支、归档内源提交、冻结数值提交和安装构建提交是不同身份；完整对应记录在下列机器回执与各来源报告中，不将它们替换为合并提交。

## 机制实验：原输入、实际路径与表格均能重建

原冻结协议 `9d8985f579a64df95ebbb22ce0a607020261e5a66516efc80edcf9c956894b2c`、六份原始输入、41 项源码身份保持不变。CPU/CUDA 各 36 组、96 工作流完成；每个工作流五次技术调用，共 960 份保存路径。固定状态探针另列，不增加统计重复。

接收端用独立 `reference.py::numpy_reference` 重新执行保存初值、实际噪声与 log-uniform 的 NumPy 递推，没有导入 torch/JAX 采样器。960 份路径均满足原来的逐链标准，接受事件零失配；最大路径差 `3.844273788189412e-10`。验证使用既有 `100*(atol + rtol*max(1,maxabs(saved_chain)))`，没有放宽阈值。共同输入的参考计算可复用，不能把同一路径的重放当作独立拟合。

Mac 第一次分析因 Windows 状态清单里的反斜杠路径失败，原日志保留。读取端修复 `3320817` 将归档相对路径按 Windows/POSIX 语义读取，并拒绝绝对路径、父目录和越界路径；没有修改原状态文件。5 项定向检查通过（18 条已有 torch 弃用警告保留）。其中原文件测试夹具实际产生 6 次短技术采样调用，不计为正式重复；其余接收重建只读。修复后的分析器与冻结数值源码在单独目录组合，CPU/CUDA 的 workflows/probes **四张 CSV 全部逐字节重建一致**，分别 96/576 行。

| 缓存顺序时间 / 时间执行器时间 | CPU | CUDA |
|---|---|---|
| quasi-DEER MALA | 0.0924–0.3218；0/24 大于 1 | 0.1386–0.4368；0/24 大于 1 |
| Online Picard RWM | 0.6120–3.5743；20/36 大于 1 | 0.7776–4.8047；32/36 大于 1 |

这些是各配置三次缓存调用的中位时间所形成的配对比，只有每目标两份独立输入；不能解释成推断加速、置信区间或一般硬件结论。每设备六个全拒绝工作流保留。固定状态目标、JVP、扫描等探针在真实执行中可能重叠，不能相加为排他的因果成本分解。首方四面板图已检查坐标、计数、说明和布局，见[机制报告](WINDOWS-MECHANISM-COMPLETION.md)。

## 原生运行器：有限执行与资源门槛通过

冻结源 `2ddcea970cf0ed78501b53f504d7230e9c2695ec`，主协议 `8abed79661a077b8b7a1746f1ee90b506187b79f4bf81b1c7872ec0ad3481f9c`，缓存协议 `350189ba8526c2020d1887aa98b9289e30ea0eb12d2eb2fbd8436cbb51ec80ab`。接收端核对封存清单、输入、源码、任务登记、调用账本、所有权观察和资格分离，并重新读取原始数组：

- 27 主任务有效，24 缓存探测可用、96 次保存调用；各失败/中断/未运行计数为零。本批没有重试。
- 24 主 MH 路径和 96 缓存路径重新通过独立 NumPy 完整递推，接受事件零失配，最大差 `3.608271459398793e-10`。加上机制路径，共 **1,080 份记录、42 组唯一参考计算**。缓存路径始终没有普通后验样本资格。
- 12 组同核执行配对通过。3 个 CPU NUTS 任务分别有四个被 Job 实际观察到的 spawn worker、初值、预热和 RNG 记录；其中 G2 包含 64 维、四链、每链保留 16,384 步。NUTS 没有套用 MH 的 NumPy 同路径保证。
- 51 个任务终态 Job active-process count 为 0。原生恢复回执显示零重算、831 主任务文件及 828 缓存文件不变；接收端核对其实际文件及账本，不声称在 Mac 上重新运行 Windows 恢复。
- XML 中 17 个行为/汇总检查和独立 2 个有界内存分配检查通过，无失败或跳过。早先失败日志仍在原包，不与最终检查重复累计。

接收端只读重建 27 份函数二进制和 90 行现代 R 诊断：18 份二进制逐字节一致，9 份有跨平台末位差，最大 `1.1102230246251565e-16`；均值差为 0。R 诊断最大绝对差约 `1.00044e-10`，在显式 `atol=rtol=1e-10` 比较内。使用 Mac R4.6.0 与 Windows R4.6.1、相同 posterior1.7.0，原 Windows 二进制与 Mac 重建结果分开保存。90 行中 **59 行 Rhat>1.01、27 行 tail ESS 不可判定**，不宣称统计收敛。三模型各一份输入不支持正式误差区间。

资源限制也保持原说明：有界 128 MiB 分配在 64 MiB Job limit 下被拒绝、256 MiB 下成功，但 Windows 原始 `PeakJobMemoryUsed` 计数可能超过限制，不能改称成功提交内存的可靠峰值。G2 NUTS 的原始计数 45,916,721,152 字节保留；最大采样 RSS 3,636,400,128 字节是另一口径，不保证捕获瞬时峰值。源码及行为测试支持本批所有权、终止、锁和拒绝处理，不能推广为重启恢复或任意负载的资源保证。NumPy `slogdet` 的已有警告保留，未凭警告擅自更改数值输入。

## 安装候选：真实 Windows 证据与跨平台对象重建

安装构建源 `341234ed4341c4c77458a9b352016e1581e4c62e`；Python0.2.0.dev2、R0.2.0.9002。读取原始 XML：CLI3、CPU63、CUDA63，共129项通过、0跳过；R 显式4测试/56断言通过。`R CMD check` 最终 OK，其默认7项集成跳过独立列出，不能计为通过。首轮长路径、wheel 缓存、locale 错误均保留。

直接从归档 wheel、sdist、R 源包和收到的源码计算 17 模块哈希，完全一致；安装环境实际载入路径/版本和非 editable 状态由原安装回执支持。没有把接收端读包称作重新在 Windows 安装。15 个数值模块与既有验证版本保持一致；开发版本变化不回改历史实验版本。

Mac 只读载入 CPU/CUDA 的 8 个 RDS 工作流和 CUDA 失败对象，核对形状、样本/失败资格、同核事件及路径，并重算16行诊断。与原 Windows 只读对象结果最大差 `9.947598300641403e-14`，其余类别/NA/状态相同。失败轨迹仍不能作为普通 draws。短链不利诊断保留。GPU NUTS、原生 Windows Stan 及安装版 Poisson CUDA 扩展示例不在本次验收中。

## 复查入口与剩余工作

接收机器回执：`benchmark/analysis/outputs/windows-followup-intake-v1/`，包含五归档校验、原件不变检查、逐路径结果、表格比较、R/运行器重建及读取端测试证据。对应完整原始数据须另取上述五归档并解压至隔离目录，不能覆盖开发检出。

下例中 `RECEIVED/{mechanism,runtime,package}` 分别为对应主归档的解压根目录，`SOURCE` 是已核验的 `b0582c3` Git 源快照；`NEW` 必须不存在。使用记录的 Python/NumPy/SciPy 环境，不生成替代随机数组：

```text
python scripts/completion/replay_windows_followup.py --evidence-root RECEIVED --source-root SOURCE --output NEW
python scripts/windows/audit_technical_batch.py audit --bundle RECEIVED/runtime/output/windows-runtime-technical-v1 --output NEW_RUNTIME --rscript Rscript --r-library R_LIBRARY --cross-platform
Rscript --vanilla scripts/windows/installed_R_objects.R RECEIVED/package/output/windows-package-candidate-v1/R-example-cpu NEW_CPU.json
Rscript --vanilla scripts/windows/installed_R_objects.R RECEIVED/package/output/windows-package-candidate-v1/R-example-cuda NEW_CUDA.json
```

先运行 `scripts/verify-windows-return.py` 校验归档及清单；重放工具是后续科学复核，不替代来源校验。机制 CSV 重建须使用原冻结数值快照与修复后的非数值分析器，步骤在机器回执 `mechanism-reader-rebuild.py` 中记录。首次反斜杠失败、首次接收端把 `execution-*.started.json` 误列为终态记录的失败日志保留；最终读取明确的 execution-0 至 execution-3，不删原件或重复启动设备任务。

当前关闭的是 F2 有限机制实验、Windows 运行器有限技术验收、候选双平台安装证据缺口。F3 正式实验尚未冻结或执行，F4 水井正式比较、F5 全部结果原始证据到表图/PDF的整套重建、F6 最终论文仍待完成。现有 `technical_batch.py` 显式只接收27/24任务，不能直接扩成正式网格。

下一顺序：完成正式分批驱动与有界分析接口 → 根据接收结果核对 v0.2 草案的资源、失败、成本和参考契约 → 在原生 Windows 冻结新身份与实际输入、执行四个预定批次 → 回传并重建正式结果 → 修订图表和中文稿、编译及整套复现。缓存重放不增加独立重复；没有加速、失败和参考未定均可成为最终结果。本轮不新开 GPU NUTS、语言编译器或选择器研究，也不自动公开草稿、合入 main 或投稿。
