# 原生 Windows 资格运行交接

研究决议为 `docs/prospective-first-use-v1/DECISIONS.md`。先核对源提交、当前身份、任务清单和本机剩余空间。所有路径使用 Windows 原生 Python 与 PowerShell。

在 Windows Codex 中粘贴 [接力提示词](CODEX-PROMPT.md) 的全文，可从检出研究分支和环境预检开始。

## 环境检查

在项目工作树中打开 PowerShell，使用本机已验证的独立 Python 环境：

```powershell
.\handoff\prospective-first-use-v1\preflight.ps1 -Python 'D:\workspace\ParallelBayes\.venv-win-torch\Scripts\python.exe' -Rscript 'D:\Tools\R-4.6.1\bin\Rscript.exe' -Output 'D:\workspace\ParallelBayes\output\prospective-preflight-01'
```

入口仅检查本机环境、CUDA 框架操作和元数据任务清单，不启动采样。输出目录必须为新目录。保存命令、源码 commit、驱动、CUDA、Python、PyTorch、设备、主机 RAM 与 GPU 显存、各磁盘可用空间、环境探针退出码、实际清单及 SHA-256。环境探针通过只是框架资格，需继续完成下述工作。生成的 `qualification-inventory.json` 列出 880 个唯一任务和六个阶段的预定数量，用于核对任务覆盖；其列表顺序不是运行顺序。实际放行顺序按研究决议分批编排并记录。

`dependencies.json` 检查 Pyro、NumPy、SciPy、PyTorch、psutil 和 R 的 posterior/jsonlite 版本。两个可用状态明确供 NUTS 及 R 诊断资格核查。编译接口可导入只说明符号存在，CUDA 编译须另行实测。

## 开发域稠密高斯检查

`scripts/prospective_torch/gaussian_cost.py` 实际执行稠密矩阵与残差计算；独立解析充分统计量用于核验。下列命令只生成开发维度 8 和 128 的四档行数，不生成或访问留出的 32 维输入。输出包含各条件的实际矩阵、响应、测试点和 SHA-256，每设备约需 80 MiB 以上的输出空间，另需运行内存。每次使用新的输出目录：

```powershell
& $Python -B tests/prospective_reference/validate_torch_gaussian_cost.py (Join-Path $Output 'gaussian-static-cpu') --device cpu
& $Python -B tests/prospective_reference/validate_torch_gaussian_cost.py (Join-Path $Output 'gaussian-static-cuda') --device cuda
& $Python -B tests/prospective_reference/validate_gaussian_cost_paths.py (Join-Path $Output 'gaussian-static-cpu') (Join-Path $Output 'gaussian-path-cpu') --device cpu
& $Python -B tests/prospective_reference/validate_gaussian_cost_paths.py (Join-Path $Output 'gaussian-static-cuda') (Join-Path $Output 'gaussian-path-cuda') --device cuda
```

每一步记录退出码、资源、实际输入和回执。路径检查只覆盖两个开发成本端点、四链三步、W=2 尾窗和固定压力提议；它不等于 24 次演练、880 次资格或性能结论。CUDA 不可用不得用 CPU 代替。Mac CPU 已通过八个静态条件及两个端点的四种短路径对照，Windows 须重新实测。

## 候选 logistic 静态对照

Mac 已生成候选输入交接包。将 ZIP 复制到 Windows，核对单独传递的 SHA-256 `281d00e3ea05071c30ca208f08ac00319ca7e02e01955ae14f6a61d23a0096f4`，解包到新目录。输入包包含候选模型数据和参考链分层起点，应按留出数据管理。

```powershell
& $Python -B scripts/prospective_plan/input_transfer.py unpack $Archive '281d00e3ea05071c30ca208f08ac00319ca7e02e01955ae14f6a61d23a0096f4' $Candidate
```

程序验证外部包哈希、文件清单及数据和初值的内层哈希，拒绝覆盖已有接收目录。Windows 采样资格用例使用独立合成探测输入；参考链初值只用于参考链准备。

候选输入交接并校验 SHA-256 后，分别在 CPU 和 CUDA 运行下列命令，使用两个不存在的结果路径。CUDA 不可用时不替换设备。

```powershell
& $Python -B tests/prospective_reference/validate_torch_logistic.py $Candidate (Join-Path $Output 'logistic-cpu.json') --device cpu
& $Python -B tests/prospective_reference/validate_torch_logistic.py $Candidate (Join-Path $Output 'logistic-cuda.json') --device cuda
```

记录两次退出码和回执哈希。该检查使用固定合成测试点。

静态检查通过后，分别对 CPU 和 CUDA 运行固定实际随机数组的四链采样对照。每次使用新路径并保留旁边的 `.tape.npz`：

```powershell
& $Python -B tests/prospective_reference/test_logistic_sampler.py $Candidate (Join-Path $Output 'logistic-path-cpu.json') --device cpu
& $Python -B tests/prospective_reference/test_logistic_sampler.py $Candidate (Join-Path $Output 'logistic-path-cuda.json') --device cuda
```

对每次调用记录退出码、实际随机数组和回执哈希。四种方法均须保留接受事件及独立路径核验结果。该用例仅覆盖 23 个转移及窗口尾部，正式长度和其他目标还需对应的资格记录。

## 四进程 NUTS 技术演练

在预检确认 Pyro 可用后，可使用独立合成 logistic 输入，在新的输出目录执行：

```powershell
& $Python -B scripts/prospective_torch/nuts_smoke.py (Join-Path $Output 'nuts-synthetic-smoke')
$LASTEXITCODE
```

保存 `summary.json`、实际合成输入、各链初始随机状态、样本和哈希，检查四个进程及四条链的状态。此短跑只检查 spawn、数据和 Pyro 诊断交接，不属于六次 NUTS 资格预检，也不证明收敛、性能或跨平台一致性。它明确禁止调用旧的 `MCMC.diagnostics()`；使用 Pyro 已缓存的逐链 kernel 诊断，该私有接口依赖 Pyro 版本，若版本不兼容必须如实记录失败。Mac 的 Pyro 1.9.1 演练仅是 Mac 证据；Windows 环境与正式规模仍需单独验证。此脚本没有正式长链所需的资源保护及恢复机制，不能直接用于正式计算。

## ODE 候选实现边界

`scripts/prospective_torch/ode_candidate.py` 是待验收的 PyTorch 固定步长 RK4 开发候选，支持批量 log 坐标、密度和自动微分。它不是正式求解器：固定有限步长不能检测所有域内积分误差，也尚未实现决议要求的可恢复失败、确定性重算和后备求解器规则。仅凭返回有限值不能判定求解成功；非有限结果不能当作合法 MH 零密度拒绝。必须在各 Windows 设备和真实/代理目标上完成独立状态、密度、梯度、Hv、重算与路径核验后另行确定实现，不能将当前候选直接接入正式采样。

Mac CPU 上合成常规和快动力学按 21 个点、三个方向对照独立 SciPy 的开发结果另存本地。开发中快动力学每年 40 子步的中心点梯度超限；该失败记录保留。80 子步只是在合成点上的开发候选，不是对参数域、性能或原生 CUDA 的保证。

Mac CPU 还使用候选真实数据及既有 21 个固定点（中心、逐参数扰动、四个预定初值），在 80 子步下完成状态、密度差、梯度和三个方向 Hv 的独立 SciPy 静态对照；其回执和点位作为留出材料保存在 Mac 本地。该验证未生成后验样本，不代替 Windows 原生设备上的对照、路径或求解失败处理验收。

Mac CPU 使用合成溢出提议验证四种顺序/并行执行方式均将非有限结果隔离为失败；两个并行方法的顺序回退也保持失败并记录代价。测试代码 `tests/prospective_reference/test_ode_nonfinite_quarantine.py` 可在安装 pytest 的本机 Python 下重放；可先创建空目录并设置环境变量 `PARALLELBAYES_ODE_FAILURE_EVIDENCE` 指向该目录，以保存实际随机数组、失败轨迹及回执。此测试固定使用 CPU 和故意粗化的求解器，只覆盖非有限溢出，不覆盖有限但不准确、可恢复求解失败、重算或 CUDA；这些仍须分别验收。

`tests/prospective_reference/validate_ode_synthetic_paths.py` 为 ODE 提供一链三步、W=2（含尾窗）的固定实际数组路径检查；四种执行方式各与独立 SciPy 串行参考对照，并比较同核接受事件与路径。合成压力提议经开发检查选取，旨在覆盖接受和拒绝，不可作为正式输入。Windows 原生环境预检后可分别在新目录运行：

```powershell
& $Python -B tests/prospective_reference/validate_ode_synthetic_paths.py (Join-Path $Output 'ode-path-cpu') --device cpu
& $Python -B tests/prospective_reference/validate_ode_synthetic_paths.py (Join-Path $Output 'ode-path-cuda') --device cuda
```

保留命令、退出码、实际输入数组、各路径、失败及哈希。CUDA 不可用不得改用 CPU 冒充通过；资源超限或异常应保留失败回执。该短检查不等于 24 次四链演练，不验证 ODE 后备求解、完整链或性能。

加 `--chains 4` 可运行四条合成链。Mac CPU 的四链版本已通过四种方法的独立路径和接受事件对照，四链共享合成观测与相同初值，每链噪声数组不同、压力提议固定；其证据不构成四份独立数据重复或正式四链资格。

## 任务与证据

| 顺序 | 工作 | 判定和产物 |
|---|---|---|
| 1 | 复核候选模型、数据、先验、初始值、哈希，以及 PyTorch 密度/梯度和 Mac 独立实现一致性 | 记录实际数组逐项对照、模型参数和数值误差。未过核验的目标不能进入计时。 |
| 2 | 独立一次性输入上完成 24 次四链演练 | 2 输入 × CPU/CUDA × RWM/MALA × 顺序/W32/首次策略。Mac 回放、失败注入、传输校验与步序须通过。 |
| 3 | 高斯四角 384 次与中间条件 144 次 | 先首块 32，后按决议分批。长链启动前保存成本预测。按计划保留错误、残差、实际数组和计时。 |
| 4 | 分层代理 48 次、ODE 代理 160 次、ODE 4096 步 72 次、最长链 72 次 | 880 次资格的所有终态对账；独立回放与资源实测。ODE 零密度和求解失败分别留痕。 |
| 5 | 新增 NUTS 预检 6 次、两目标各 3 份的 profiler 24 次 | 记录运行时进程、Pyro 版本、单链资源、全路径与有效输出、编译覆盖和失败，不把框架编译测试当作采样正确性。 |
| 6 | 更新机时及三项存储用量，准备正式任务清单 | Windows 独占机时、Windows 工作盘、Mac 接收盘和长期归档各自核算；保守用量分别 ≤80% 可用额度。 |

### 资格尝试对账工具

`scripts/prospective_plan/audit_qualification.py` 可以对 880 项计划与逐次尝试台账做机器核对。台账为 UTF-8 JSON Lines，每行是一个已终结的尝试，字段严格为 `task_id`、从 1 开始连续的 `attempt`、`status`（`completed` 或 `failed`）、`reason`、`elapsed_seconds`、`artifacts`（包含相对路径 `path` 和 `sha256` 的非空列表）。失败必须有原因；重复尝试追加新行，不能覆盖首次失败。文件路径使用 `/`，相对于单独的证据根目录。未启动任务不伪造记录，由对账程序列出。

```powershell
& $Python -B scripts/prospective_plan/audit_qualification.py $Ledger $ArtifactRoot (Join-Path $Output 'qualification-accounting.json')
```

对账结果统计首次交付、首次失败、未启动及尝试数，并核对证据文件哈希。它只证明台账形式、分母和文件完整性，不能认定轨迹正确、数值通过、预测封存或科学资格通过，也不自动生成正式封存所需的资格回执。首次运行前先在独立合成台账验证数据格式，再将实际运行产生的原始日志、数组和失败记录纳入；不要将合成结果当作资格数据。

真实候选参考封存需要真实 Windows 资格与容量回执，分别标注 `scope` 为 `prospective_windows_qualification` 和 `prospective_capacity_budget`，并标注 `evidence_kind: actual`；正式身份、状态、数量和四项容量仍须满足封存检查。标签只是避免误把模拟材料当作正式回执，**不能证明内容真实或验收充分**，须先核查原始台账、路径、预测和资源账。模拟参考链使用 `synthetic_test` 身份。

真实 Windows 资格回执还需绑定完整资格台账的 `ledger_sha256`。Mac 封存时须另提供该台账及其原始证据根目录（`--qualification-ledger`、`--qualification-artifact-root`），由封存器重算 880 项覆盖和证据文件哈希；保留首轮失败与后续重试。封存目录复制台账和对账摘要，并绑定相关代码哈希。对账通过不自动签发科学资格，失败轨迹、资源和独立数值验收仍由研究者审查。

方案还包含 24 次技术演练之外的正式 25,856 次主比较、128 次 Windows CPU NUTS 和 576 次编译及预热对照。采样器、模型、预测器、正式输入和容量核验都需要新的实现及回执。已有 `inventory.py` 生成条件规模，不能单凭它启动正式执行。

`scripts/prospective_plan/first_use_policy.py` 是开发阶段的纯计算组件：把 512 步丢弃、样本数相关交付和增量探测计入时间预测，并根据调用者提供的同时预测下界选择窗口或保守顺序回退。它不生成或校验 90% 同时覆盖的校准、不运行探测/采样、不封存预测，也不构成完整首次使用策略。下界必须来自独立开发数据并经验证和冻结；不能把函数接收下界误称为下界已经有效。当前同下界取小窗口是开发期确定性约定，正式规则应在协议冻结前核对。

`first_use_calibration.py` 另提供一个**探索性候选**：以每份独立输入的五窗口最大对数预测误差作单侧 split-conformal 校准，使用 `ceil(0.9(n+1))` 的次序统计量。调用者须提供互不重复、基于实际输入及随机数组的 SHA-256，拟合与校准身份不得重叠；每份输入的五个窗口必须全部记账，未交付结果以最保守分数保留。校准样本不足或所需分位为无穷时，下界为零。哈希不证明输入独立；模型拟合、数据划分和输入来源仍须独立核验。

这一计算只有在固定模型及校准与未来输入的完整误差向量可交换等条件下，才有边际的同时覆盖解释；它不保证单条件覆盖，也不证明留出维度、新模型、设备或预算与开发数据可交换。此方法尚无真实 Windows 开发数据验证、未被纳入冻结协议，不能作为正式 90% 覆盖证据或自动放行规则。

`tests/prospective_reference/probe_gaussian_development.py` 提供四链 64 步的开发期探测演练，记录顺序和五个窗口的推进、执行耗时、同步及独立回放，并保存实际随机数组。它在已初始化进程内对所有窗口都运行完整短链，计时包含模拟预留数组生成及文件写入；这些模拟预留数组与探测数组还放在同一文件中。该脚本不实现规定的正式微测量、正式留出输入封存或总端到端时钟，禁止用它替代正式首次使用策略或据此校准覆盖率。

## 交接边界

正式留出数据与随机数组独立封存。运行流程在持久化每次预测前不得访问该输入的正式基线或轨迹。单次候选提议已知数学密度为零可合法拒绝；ODE 域内数值求解失败走预定重算，持续失败按失败处理。同步设备后计时，记录失败、重试、回退和完整成本。

参考输入候选的生成和校验从 Mac 交接，其清单当前标记为候选。正式封存、采样权限和启动回执以完整科学协议及资格结果为准。旧实验的归档、原始输入和失败记录独立保留。
