# 原生 Windows 安装候选验收

2026-10-07。F2 与 F3 已终态封存后，独立分支 `codex/windows-package-validation`
从 `codex/research-integration` 的 `6f02f3735d0b534b0915a4732c31625ef6ba6bcb` 开始。
安装包构建源码 `341234ed4341c4c77458a9b352016e1581e4c62e`。后继提交仅增加
只读安装证据工具、日志摘要和说明，不改包内数值实现。

| 验收 | 结果 |
|---|---|
| 已安装 CLI，仓库外 / -I / 无 PYTHONPATH | 3 通过，0 失败/跳过 |
| 已安装 torch CPU | 63 通过，0 失败/跳过，18 弃用警告 |
| 已安装 torch CUDA，RTX 5080 float64 | 63 通过，0 失败/跳过，18 弃用警告 |
| R CMD check --no-manual | 最终 OK，默认 7 集成跳过，0 通过 |
| 显式 R 源码归档中的两测试文件 | 4 测试、56 断言通过，0 失败/跳过 |
| R 原 CPU 示例 / 新 CUDA 短示例 | 各 4 工作流成功；各 2 组同核数组/接受事件/路径通过 |
| CUDA 失败轨迹 | 1 次故意数值迭代耗尽，原对象保存，draws=NULL |
| 原 RDS 只读重建 | CPU/CUDA 全部 8 工作流及失败对象通过；新增采样 0 |

四工作流为顺序 MALA、quasi-DEER MALA、顺序 RWM、Online Picard RWM。
数组为 iteration×chain×variable = 64×4×2。独立 NumPy 审计接受事件失配 0。
现代 Rhat、bulk/tail ESS 和不利短链诊断保留；这只是安装接口验收。

Python 3.12.14、torch 2.13.0+cu130、CUDA 构建 13.0，驱动 616.56，实际设备
RTX 5080 sm120，显存 17066033152 字节。新环境无 JAX，默认 JAX 环境命令明确拒绝
并提示使用 torch；帮助页和 torch 环境查询成功。wheel 来自独立 sdist 解压目录，
Python 模块路径为新 venv 的 site-packages；R 模块路径为新 R 库内包自带 python。
Python/R RAM 字节数均为 33346146304，未截断。

R 4.6.1；44 个依赖下载为原生 Windows CRAN ZIP 后安装新库。非基础包的实际载入路径
另存，发行版自带 base/recommended 包明确复用。没有复制旧库、Mac 动态库或 venv。
完整 Python freeze、安装报告、pip check、R 清单、驱动输出随包提供。

17 个 Python 模块在源码、wheel、安装 Python 和安装 R 包副本中逐字节相同。
与 `52fdfd0446768033ffd975bc52ea8036c420880d` 比较仅 `__init__.py` 与 CLI 不同，
15 个数值模块相同。`validation_evidence.version=0.2.0.dev1` 保留历史证据归属。

失败链：首个长目录 torch 安装 WinError206，改用全新短路径工作树与 venv；
wheel 构建全局缓存 WinError5，下一次使用 `--no-cache-dir`；首次 R check 继承
`C.UTF-8` 导致 1 ERROR/1 WARNING，仅该命令改 locale=C 后在新目录得到 OK。
所有首次失败和部分安装清单保留，没有改种子、目标、容差或系统长路径策略。

所有安装/检查命令由原生 Job Object 管理，共享主机锁串行执行，结束时 active_processes=0。
这复用 F3 已验收的归属 API；辅助命令不是后验或缓存测量任务。
Job 内核 PeakJobMemoryUsed 原字段不解释为成功分配内存的精确峰值；轮询 RSS
可能遗漏瞬时峰值，不能当显存或无遗漏上限。F3 的细节以其独立归档与开发分支为准。

紧凑证据：`benchmark/analysis/outputs/windows-package-candidate-v1/`；工作包：
`execution/package-candidate/WORK-PACKAGES.md`。大包包含 wheel、sdist、R 源码包、
测试源码、示例、原 RDS、失败/命令/归属日志、依赖锁及源码 bundle，不包含私有技能或凭证。

F2 返回分支 `codex/windows-mechanism-completion` 的 `1cfc83d` 已保留。
F3 返回分支 `codex/windows-runtime-validation` 的 `b0582c3` 已保留：27 主任务、
24 缓存探测 / 96 调用通过及终态零重算，不表示正式网格已冻结。
本次候选不验证 JAX/Stan 的 Windows 干净安装、GPU NUTS、外部组织复现或正式推断。
F5 两平台全结果重建与 F6 论文、正式协议接收合并仍是后继门槛。

接收端先运行 `python scripts/verify-windows-return.py ARCHIVE.tar` 验证全部成员，
安全解压到新目录后使用同版 R/依赖库运行：

```powershell
Rscript --vanilla scripts/windows/installed_R_objects.R EXTRACTED/output/windows-package-candidate-v1/R-example-cpu NEW-CPU.json
Rscript --vanilla scripts/windows/installed_R_objects.R EXTRACTED/output/windows-package-candidate-v1/R-example-cuda NEW-CUDA.json
```

这两个命令只读 RDS，无重新采样。不同接收端 R/依赖版本必须另留版本记录，
不能把接收端诊断重建称为 Windows CUDA 重跑。

安装完整主包 `windows-native-20261006T173502Z.tar` 为 49,428,480 字节，SHA256
`9b8b805a4f4605541717f3644ff931e385156bf5f4ca009738a5a9f08d6017ce`，547 个清单文件逐项通过。
归档源码 `0e99453bc7839cba2308f50bdcb0ae4969fada11`，包构建源码仍为341234e。
安全搬移后547文件再核验，8工作流/16现代诊断变量行/1失败对象只读重建一致，新增采样0。
封存/搬移回执作为伴随包另存，主包不再改写。精确身份见紧凑目录的delivery.json。
