# Windows v2 有限原生验收回执（2026-10-07）

独立身份 `windows-formal-adapter-validation-v1` 已完成原生行为、27 主任务、24 缓存探测、终态零重算、封存、逐成员归档核验与新目录搬移核验。正式统计重复数为 **0**；没有启动 41,472 主任务或 9,216 缓存探测。此回执交回 Mac 接收，不代表正式推断、收敛、一般加速或整个研究完成。

## 来源与冻结

- 起始统一分支：`origin/codex/research-integration`，实际 HEAD `6df04793e0cecb2633f5cc3bbdeea5a8b3228145`，包含执行祖先 `06e75c113e3ea6ea5a2a4275d7341595eefd7191`。
- 独立短路径工作树：`D:/workspace/ParallelBayes/v2`；开发分支 `codex/windows-formal-adapter-validation`。原机制分支、旧工作树、未提交状态与全部历史结果保留；原工作树本轮前后均干净。
- 实际冻结/执行源码：`0ba5643a6b580e79b8040f13a5e3165322db0e77`。prepare 时源码/测试已提交且工作树干净，字节与 Git LF 一致；采样期间不切换或修改源码。后继报告提交与该执行身份分开。
- 协议 SHA256：`e3acc02f32ef1cbb8cb88ae50bdf399b20cf8fde8b2f31f2079e5e393adc9baa`。
- freeze-manifest SHA256：`9e338bf821dc86be48b084ebe033e40e4248076787aea051dae83392deddba5c`；FROZEN.json SHA256：`8f7a1b083b3c3eecf9140c55113f6c302cbedfc0416162a40d3dd5f63f1ebb8b`。
- native-acceptance.json SHA256：`1b71fc0809c5019140768778572681f076bfbf8e7810523f2aed92047c1dd173`；内部 gate SHA256：`27dd0d4cc80112b493fbc985fef015f7b2fd9ca39853c304dca5c26cb46e51c4`。

三份新技术主输入 G1/G2/W1 只生成一次，文件与实际数组双重哈希在采样前冻结；各设备/执行器共享原实际数组。G1/W1 保留64步，G2四链各保留16,384步；MH额外512步，窗口32，quasi-DEER每窗口最多2048轮，Picard最多总转移数。NUTS CPU四spawn×一线程、预热1024、树深8、目标接受率0.8、对角质量矩阵。沿用正式参数/仿射坐标/原容差，未改变核或参考。`cached_execution.py` 明确在冻结源清单中。

水井快照复用原已核验目录的八文件，固定上游 `91027f9cdd13b7e76283fec3f2898f59d4b83ec4`；含许可、数据、模型和有限参考。没有更换上游或从种子重建已冻结输入。完整协议、源码/测试、输入意图和回执在原始归档；Git仅保存[小型回执](../execution/windows-native/formal-adapter-validation-v1/)。

## 实际环境和保护边界

原生 Windows11 build26200，AMD Ryzen7 9800X3D（8物理/16逻辑），RAM 33,346,146,304字节；RTX5080 sm120，驱动616.56，显存17,066,033,152字节。prepare实际可用RAM 18,686,197,760字节、CUDA空闲15,488,516,096字节；D盘可用约1.86TB。准备时的储备不保证整个任务永远装得下。

Python为 `D:/workspace/ParallelBayes/.venv-win-torch/Scripts/python.exe`（3.12.14 x64），torch2.13.0+cu130/CUDA13.0、NumPy2.2.6、SciPy1.15.3、Pyro1.9.2、psutil7.1.0、pytest8.4.2；全部34个包版本与完整freeze/check保存。原环境分发元数据parallelbayes0.2.0.dev1保留；执行源码由冻结工作树显式提供，不借分发元数据冒充源码身份。没有升级、重装或bootstrap。

Rscript `D:/Tools/R-4.6.1/bin/Rscript.exe`，R库 `D:/Tools/R-library-4.6`，R4.6.1/posterior1.7.0。原venv标记 SHA256 前后仍为 `5e8ed0b284b1ef83977fcea0ce45c16349bbf8c1f0eb249be238f8aea547999c`。R启动的LC_COLLATE/CTYPE/MONETARY/TIME locale警告原样保存，没有把警告删除或改成静默通过。

共用锁仍为 `D:/workspace/ParallelBayes/output/runtime/windows-shared-host.lock`，位于证据包外。任务保护：8GiB轮询进程集合RSS、12GiB JobMemoryLimit，启动磁盘储备4GiB/运行底线1GiB，准备可用RAM12GiB、CUDA空闲3GiB；没有科学总时长截止。RSS是采样的驻留页总和，可能重复共享页并遗漏峰值；CUDA allocated/reserved/free/allocator峰值另存。main采样RSS峰值3,626,065,920字节，cache为1,522,216,960字节。

Windows原始PeakJobMemoryUsed字段仍按原始计数器报告：main最大45,911,351,296字节，不能称为成功commit的无遗漏硬上限，更不能称为显存。有限64/256MiB Job分配拒绝/成功夹具通过，不推导任意负载或重启安全保证。外层CLI witness不增加资源/时间限制；内层科学保护不变。

## 行为、任务与诊断

最终行为尝试 **16通过 / 0失败 / 0跳过**，含真实子/孙进程、锁竞争、管理者异常退出、独立CUDA上下文保留、资源拒绝、实际数组/配置/源码变更拒绝、失败禁止重试、v1衔接、v2登记及缓存资格矛盾拒绝。XML、实际pytest参数、16用例源码/夹具及Job终态均核对；没有用Mac人工文件检查替代。

| 阶段 | 计划 | 合格终态 | 数值失败 | 资源失败 | 基础设施中断 | 未分类失败 | pending | 采样重试 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| main | 27 | valid 27 | 0 | 0 | 0 | 0 | 0 | 0 |
| cache | 24 | measurement_available 24 | 0 | 0 | 0 | 0 | 0 | 0 |

24 MH主任务通过独立NumPy实际数组全路径/约束输出/接受事件核验；12组同核顺序/时间配对的实际tape哈希一致，接受失配0，最大无约束路径差5.58938895167671e-10，最大约束输出差2.17276951985923e-9（描述性差值；原独立oracle标准未变）。12 CUDA主任务均记录cuda:0/torch.float64。三个CPU NUTS各有四个实际owned spawn PID，已在Job观测中逐一找到；初值、种子/随机状态、预热/适应/发散和元数据保留，不宣称与MH固定路径等价。全部27任务均实际观察到R诊断后代。

24缓存探测各1次初始+3次准备后调用，共 **96次有效调用**，全部measurement_available=true，samples_eligible始终false。保存每次完整路径/接受数组、独立审计和实际CUDA同步；不新增统计重复，不按主任务成功筛选配置，不用缓存免费替代普通推断成本。仅每模型一个技术输入，不输出跨重复区间。

保存117行R现代诊断（rank/folded Rhat、bulk/tail ESS、MCSE）。83行有限Rhat>1.01；Rhat/bulk ESS/MCSE各9行不可用，tail ESS27行不可用。所有短链差诊断与常量/不可判定函数保留，不能把数值有效写成收敛或参考精度达标。

main与cache实际只核验恢复各执行一次，新增执行均0，831主任务文件和828缓存任务文件逐项不变。该证据是终态零重算；实际中断行为另由有限夹具提供，不能称为完整科学任务的中途续算或系统重启验收。

普通推断子进程与之后独立审计分开；每项记录启动/导入、初始化、采样、转换/传输、R诊断/输出及审计。CUDA计时显式同步。main完整CLI调用631.8677844秒，cache为1877.7165398秒；外层调用、内层阶段、嵌套采样/探针不能相加。G2 quasi-DEER较长开销、映射/JVP、确认前缀、裁剪、残差与eager Python标量等待均保留；不称为高效设备内控制流或一般GPU加速。额外终态核验、准备、封存、导出/搬移成本独立记录，丢失的内层结束计时保持未知。

## 失败与兼容修复（未删除）

1. 冻结前首次prepare启动失败（7bbc39d）：Job API在NUL关闭后清除继承标志，SetHandleInformation遇到无效句柄0xc0000008。子进程始终suspended，确认Job active0，验收包及输入均未生成。0ba5643仅延长NUL句柄生命周期、检查API返回值，并补witness异常日志；数值源码、协议参数及16用例无改变。[微软API依据](https://learn.microsoft.com/windows/win32/api/handleapi/nf-handleapi-sethandleinformation)。旧源码/精确patch/失败JSON均归档；修复提交干净后重新prepare。
2. 首次test在受限工具账号下，R库不可见，preflight报找不到posterior，尚未创建行为尝试。按已授权审批在原环境同一原生用户上下文运行后库可见；没有安装依赖或绕过环境身份检查。此错误单独保留。
3. 下一次实际行为尝试15通过/1失败：legacy fixture的就绪文件读取PermissionError；随后同一文件可读，确切触发原因未定。fixture的等待超时不是退出证明，原生观察显示外层Job尚有13成员。仅终止已登记的本次人工外层Job，核验active0，未按进程名称批量杀进程。原XML、所有目录和残缺内层封存保留；明确repeat-reason后用同一冻结源码/依赖/断言再执行16用例，最终16/0/0。未以此重抽科学输入或重试采样。

原私有技能ZIP `parallelbayes-user-skills-2026-10-04.zip` 和所需codebase-design/tdd/nature技能在本机缺失；没有从公开源猜测私有内容，也没有声称使用它们。

## 命令、完整交付与接收

实际参数/开始结束时间/退出码/源提交/Job句柄归属与stdout/stderr见小型[commands回执](../execution/windows-native/formal-adapter-validation-v1/commands/)，完整每秒观察及全部失败在独立commands归档。依次执行的原入口如下（实际绝对路径已记录，未用旧硬编码运行脚本）：

```powershell
$pbPython = 'D:/workspace/ParallelBayes/.venv-win-torch/Scripts/python.exe'
$pbBundle = 'D:/workspace/ParallelBayes/v2/output/formal-adapter-validation-v1'
& $pbPython scripts/windows/validate_formal_adapter.py prepare --output $pbBundle --external 'C:/Users/chenh/.codex/worktrees/windows-completion-v2/ParallelBayes/output/completion/windows-round2-20261005/wells-source' --host-lock 'D:/workspace/ParallelBayes/output/runtime/windows-shared-host.lock' --rscript 'D:/Tools/R-4.6.1/bin/Rscript.exe' --r-library 'D:/Tools/R-library-4.6'
& $pbPython scripts/windows/validate_formal_adapter.py test --bundle $pbBundle # 最终行为尝试另有显式repeat-reason
& $pbPython scripts/windows/validate_formal_adapter.py run --bundle $pbBundle --phase main
& $pbPython scripts/windows/validate_formal_adapter.py run --bundle $pbBundle --phase cache
& $pbPython scripts/windows/validate_formal_adapter.py run --bundle $pbBundle --phase main --verify-only
& $pbPython scripts/windows/validate_formal_adapter.py run --bundle $pbBundle --phase cache --verify-only
& $pbPython scripts/windows/validate_formal_adapter.py seal --bundle $pbBundle
& $pbPython scripts/windows/validate_formal_adapter.py verify --bundle $pbBundle
& $pbPython scripts/windows/validate_formal_adapter.py export --bundle $pbBundle --output <新tar路径>
& $pbPython scripts/verify-windows-return.py <新tar路径>
```

每条通过独立witness原生Job管理CLI生命周期，不持有与内层竞争的科学锁。封存后没有向原包追加执行记录。静止共享锁快照保存51个v2、51个旧v1登记；102个真实Job逐一OpenJobObject核对，没有活动进程。所有CLI/任务Job退出均有实际active0证明；这不是全OS进程普查。

主归档 `windows-formal-adapter-validation-v1-20261007.tar`：**987,596,800字节**，SHA256 **`ceb722b100570972c99684185bbf7cdeec1dd122efc863854d0c9168cbc2de62`**，3167文件逐成员验证。接受文件内部覆盖3166资产，导出另包含接受文件本身。安全解压至全新 `output/v2-relocated` 后3167文件大小/哈希均一致，`validation/` 的verify再次通过。

完整CLI/失败/清理/资源观察、静止注册表、搬移证明、完整描述性汇总和报告另用 `scripts/windows/export_results.py` 导出伴随完整性包，并用 `scripts/verify-windows-return.py`逐成员核对。源码分支另附Git bundle及SHA256。所有归档/sidecar新增到既有草稿 `windows-completion-v2-20261005`，不覆盖旧附件、不公开发布、不合并main；上传清单和远端大小/digest核对见交付sidecar。大NPZ、环境目录、私有技能和凭证不入Git。

实际伴随包 `windows-native-20261007T134451Z.tar`，43,284,480字节，SHA256 `82a830104c39d9bfddb24d5f9783ab650a4a3b98ed3dc174355c933aff882337`，247成员通过。首次13个新资产已全部实际上传，GitHub大小/digest逐项匹配，原27附件不变，草稿与原target不变；见[上传核验回执](../execution/windows-native/formal-adapter-validation-v1/delivery-verified.json)。此后仅追加上传/源码交付证明，不改冻结原件或采样计数。

接收方先核对tar整体SHA及逐成员清单，安全解压到新目录，然后仅运行：

```powershell
python scripts/verify-windows-return.py <归档.tar> --output <新核验JSON>
python scripts/windows/extract_verified_return.py <归档.tar> --destination <新目录> --receipt <新搬移JSON>
python scripts/windows/validate_formal_adapter.py verify --bundle <新目录>/validation
```

本机以上搬移路径已实际通过，Mac端独立接收仍由接收端完成。正式输入/全模型协议冻结和执行、正式统计/精度/费用统一分析、全原始证据到论文与正式研究完成门槛仍未关闭；本轮没有GPU NUTS、Windows Stan编译、自动选择器或新安装验收要求。
