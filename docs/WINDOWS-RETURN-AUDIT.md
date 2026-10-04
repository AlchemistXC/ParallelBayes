# Windows 结果回传复核

2026-10-04；接收提交 `3a51f98fc8d10187b8f71e477aaff56d86ea50cd`，复核分支 `codex/windows-return-audit`。

**结果包完整，512 项正式任务的数值结果与主要速度结论得到独立复核；现代诊断存在跨平台读取敏感性，不能宣称逐项完全重现。** 本次在 M4 Mac 上校验并重算已保存的证据，没有重新运行 CUDA 采样或测量 GPU 性能。Windows CPU/CUDA 的 65/63 项测试数来自已校验的原始 JUnit 日志；本机实跑检查另列。

## 接收身份与保存方式

- 从 GitHub 的 `windows-native-dev` 取得源码；`windows-native-v1` Release 的附件已下载。复核时 Release 仍为草稿，没有替用户发布。
- `windows-native-20261003T234021Z.tar`：680,366,080 字节；SHA256 `86ad93de87bae4ad11cf5b4b8c4cc7de2f61cc184bc37514d76da0cd1f5e3812`。
- 归档整体及内部 **5,866 个文件**全部通过校验，Git bundle 校验通过且完整分支历史的末端对应 `3a51f98`。
- 科学源码身份为 `0c9325e98f2bc7dcd75d344c01c2e50a62801c90`；协议规范 JSON 身份为 `1d233dd09956c4575fc5775082310e5edca65407db5fcef40bc2ce329e6f5898`。
- 原始归档解压在独立证据目录，所有再分析写入另一目录。没有覆盖历史 Mac 数据、Windows 冻结源码、协议、随机数组、尝试日志或诊断文件。

## 实际复核结果

| 检查 | 结果与边界 |
|---|---|
| 冻结身份 | 39 份源码、Python/R 依赖锁、64 份实际随机输入及 512 项终结状态/校验和通过 |
| 独立 NumPy 重放 | 128 组四链参考配置与全部 512 项保存轨迹比较；接受事件失配 0；最大无约束差 `5.211515663461341e-10` |
| CPU/CUDA 配对 | 256 对实际数组数值一致、接受事件一致；不是在 Mac 上重跑 CUDA |
| 普通 API 重放 | 保存的 512 份普通执行数组与对应核验执行逐值一致 |
| 同设备执行收益 | 64 个模型/设备/核/预算组的中位数及 bootstrap 区间重算一致 |
| 固定预算误差 | 128 个分组逐函数结果重建；解析目标的 MSE 与区间复算一致；L1/L2 参考未确定状态保留 |
| 小型 SBC | 12 个生成数据集、60 份实际样本的区间/均值重算一致；解析及各工作流覆盖均为 9/12 |
| 现代诊断 | 512+60 份拟合重新计算；分类及主要计数一致，但见下述读取敏感性 |
| Mac JAX 回归 | 51 通过、7 个 Stan 测试未运行；没有借此声称 Windows Stan 或 GPU NUTS 通过 |
| R 包 | `R CMD check --no-manual` 为 `OK`；`PB_RUN_INTEGRATION=1`，15 个断言通过、失败/警告/跳过均为 0 |
| 论文 | Tectonic 编译成功，20 页；最终轮次无未解析引文/引用，检查了首页及 Windows 表图/复核页 |

R 检查时联网包索引不可访问，但所需依赖已安装，检查和实际集成测试完成；本次没有检查 PDF 帮助手册。主论文首次用精简 TeX Live 编译因缺少 `zhnumber.sty` 失败，随后使用已有 Tectonic 成功，没有安装或修改全局 TeX。

复算的 warmed 组中位速度比范围如下（同设备顺序时间／时间执行器时间）。每组仍只有 4 份独立数组；技术重放不增加统计重复数。

| 设备 | quasi-DEER/MALA | Online Picard/RWM |
|---|---:|---:|
| CPU | 0.101–0.359 | 0.774–3.560 |
| CUDA | 0.164–0.505 | 1.097–5.230 |

**32 项 A1/RWM 全拒绝、480 项至少一个有限 Rhat >1.01、108 项含常量变量/函数的事实均保留。** 这支持指定实现的路径执行比较，不能提升为可靠推断加速或收敛证明。

## 发现及处理

### 1. 冻结源码的 CRLF 与 Git 检出的 LF

冻结 `reference.py` 的字节哈希为 `964d3a1b3084e18eac7748e3e6d9c9ae93ab5e3563e2f0a54fd5f32271900544`；Git 检出为 `4b38a2d481ea1e204ca1a47b7b5b6955a6b810f0978ba0d8baad4db6c5fb9fc1`。39 份源码仅该文件有差异，逐字节比较确认只有 CRLF/LF 区别。

原始归档保存的冻结文件完全匹配协议。新增只读审查入口先检查归档源码的精确哈希，再使用这份 NumPy 参考；另行报告 Git 的换行差异。**没有修改冻结哈希，也没有把换行兼容检查用作允许继续原冻结实验的条件。** 原来的正式运行恢复规则保持严格；在新机器重放性能实验需建立新的运行身份。

### 2. CSV 读取影响秩诊断

用 Windows 原 R 脚本在 Mac R 4.6.0、`posterior` 1.7.0 上重新读 CSV，与 Windows R 4.6.1 的记录相比，正式分析有 4,158 个 Rhat/ESS 指标值、SBC 有 31 个指标值超过绝对及相对 `1e-11` 的比较容差。分类未改变，不能把这些差异都称为普通计算舍入。

检查发现：NumPy 从 CSV 读回的全部 512 项参数列与原始 NPZ 逐值一致；Mac R 的 CSV 转换在部分末位上不同。正式输入最大变化约 `2.84e-14`，但接近重复值的秩可能变化，尾部 ESS 最大差达到约 5.57。差异主要集中在 quasi-DEER；它的数值近似轨迹在拒绝自环附近也可能含末位不同的状态。

新增伴随分析以小端 float64 二进制把同一 NumPy 数组传入 R，没有取整、删样本或改变参考轨迹。正式分析仅剩 **2 个 Rhat 指标值**不同，SBC 全部在比较容差内一致。两项剩余 Rhat 都由 `1.40822237244096` 变为 `1.40856883690538`，差约 `0.00034646`；尚不能仅凭这些证据确定剩余的跨平台成因。具体任务身份见 [diagnostics-comparison.json](../benchmark/analysis/outputs/windows-return-audit/diagnostics-comparison.json)。

480 项 Rhat 偏高和 108 项常量输出的计数，在原 Windows、Mac CSV 和 Mac 二进制分析中均相同。保留原 Windows 诊断，将二进制结果作为可重放的敏感性分析；不宣称数值接近的轨迹必然产生逐值一致的秩诊断。下一步可以在原 Windows R 上运行同一二进制入口，隔离剩余差异，**不需要重新采样**。

### 3. R 文档与成本名称

补齐 `pb_model()`、`pb_environment()` 的 `backend` 参数、torch 的 `device` 设置和实际 NUTS 边界，说明 torch 与 JAX 在显式回退时对审计失败的处理差异。R 帮助与函数签名检查通过；没有改动数值实现。

明确普通 API 时间含模型构建及基本矩；独立核验 API 使用已构建模型，另含 NumPy oracle，模型构建单列。两者不是“同一计时桶再加核验”的关系。原始计时数值、速度比与协议没有改写。

## 独立复核入口

先取得 Release 归档和相邻 `.sha256`，再用 `scripts/verify-windows-return.py` 校验；解压到新的独立目录 `EVIDENCE`。下列命令在审查分支仓库根目录执行，`EVIDENCE`/`NEW_OUTPUT` 均替换为实际路径，输出目录不得覆盖原证据。需要 NumPy 2.2.6、SciPy 1.15.3；诊断还需 R、`posterior` 1.7.0 与 `jsonlite`。不依赖 torch、JAX 或 GPU。

```text
python scripts/audit_windows_return.py --evidence EVIDENCE --source . --output NEW_OUTPUT/path-audit
python scripts/review_windows_diagnostics.py --evidence EVIDENCE --output NEW_OUTPUT/diagnostics --rscript Rscript
```

审查脚本不改变原始正式分析。第一个命令拒绝 Python `-O`，以免禁用完整性断言；新输出目录须不存在。第二个命令检查 CSV 参数与 NPZ 完全相等后，分别进行原 CSV 与二进制诊断，并生成差异清单。Win 上使用原生 Python/R 和 PowerShell，设置自己的 R 库路径；不需要 WSL。

本次诊断工具装配后逐项确认 572 份输入及 R 脚本与已完成的 R 计算完全一致，因此复用了已完成输出进行最终比较，没有重复执行已通过的计算。复用回执、审查源码及日志有独立哈希。已跟踪的小型证据见 [审查产物](../benchmark/analysis/outputs/windows-return-audit/)；完整再分析输出保存在本地独立目录，可由上述命令重建。

## 仍未验证的范围

原生 Windows Stan 编译、GPU NUTS、融合设备内控制及更广模型的推断可靠性，仍不在本次通过范围。私有 30 技能尚待单独转交 ZIP，不能从公开仓库取得。`main` 与原 `windows-native-dev` 分支未被覆盖；本轮修订只增加审查工具、说明和更新稿 PDF，不自动合并或公开发布草稿 Release。
