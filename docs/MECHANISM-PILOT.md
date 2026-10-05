# 时间并行机制 pilot 与双机执行边界

2026-10-05｜F2开发性试验已冻结；第二轮在输入校验处停止，192工作流未执行。六份原始输入现已补传，按[续跑入口](../handoff/windows-completion/CODEX-PROMPT-F2-RESUME.md)继续。原输入/协议不变；分析器现在必须传入`--inputs`，不按种子重建。

本次冻结源码97e6835，新增协议mechanism-windows-pilot-v1。它不修改windows-native-v1或历史Mac结果，不是F3正式推断基准。所有192个工作流配置都保留，包括失败、减速和低接受率；2份实际随机输入只足以作开发性、描述性分析，不形成一般加速或稳定排序声明。

## 设计

- 主要网格：G1（8维独立高斯）、G2（64维相关高斯）、L1（256观测、8参数logistic）；MALA/RWM；1或4链；每链128步；顺序执行与窗口4、16的对应时间执行器。每模型2份主随机输入。
- 步长对照：保留G2/RWM的历史尺度1.0，同时预先加入0.25；这用于检查确认前缀、移动和执行成本的联系，不称为优化后的推断配置。其他核参数复用原定义，不依据pilot结果改写历史网格。
- 等输出量对照：G2/RWM（0.25）和L1/RWM（0.1）比较1链×512步、4链×128步、16链×32步。时间执行分别使用1×16或4×4的批次，另有16条顺序链；均为512个输出转移，包括拒绝自环。批次宽度16是软件层的工作组织，不代表占满16个物理核心。不同链分配产生不同路径，只能比较同机吞吐，不视为相同推断任务。
- 总计每设备36组、96个工作流，原生Windows CPU/CUDA共192个工作流。主机torch线程数固定为4，记录实际物理/逻辑CPU数、进程CPU占用和CUDA环境，不声称资源独占。

每个模型/重复保存16链×512步的实际Philox主数组；各配置读取同一数组的链/时间前缀。不同核、设备和窗口共享对应实际输入。主数组的科学哈希和NPZ文件哈希都已冻结，Windows生成后须逐一吻合，整数种子本身不构成核验。底层采样config的默认seed字段在外部tape传入时不参与随机数生成；本实验的输入身份由主数组、前缀和实际哈希确定。

## 测量

每组先执行独立NumPy审计，再交错运行3轮计时重放；轮换执行器的次序，记录实际次序。随后做独立操作探针，再对每个工作流重放一次，检查路径/接受事件及探针对后续计时的敏感性。技术重放不增加独立重复数。

主测量包括：同步后的sample时间、Python API墙钟、process CPU时间及占比、输入/传输/审计/变换成本、归档成本、求解轮次、前向映射/JVP次数、确认前缀、标量读取等待、失败和原始数组。CUDA峰值取分配器记录；CPU RSS只有端点快照，不冒充峰值。初次调用不是全新进程的冷启动；本pilot不提供完整最终用户推断成本，后者属于F3。

探针使用顺序轨迹前部的固定状态，分别测逐点/批量密度、逐点/批量MH映射、surrogate JVP、仿射扫描及前缀标量读取。先与独立NumPy或逐点计算核对数值，再进行3个计时块、每块5次调用。前缀探针使用明确记录的合成一致性布尔数组；真正的确认前缀来自执行器逐轮记录。

这些操作在完整执行中重叠、复用并受上下文影响，**不能相加为总耗时分解，也不能将固定状态的探针时间视为全部求解状态的代表**。探针后的时间变化是敏感性记录，不是可直接相减的因果开销估计。CUDA墙钟显式同步，process CPU占比仅指主机进程，可能超过100%。

## 正确性和恢复

保持原数值标准：atol/rtol各1e-10，独立轨迹误差门槛沿用核心规则，配对路径绝对差1e-7，接受事件零失配。每窗口/执行器的数值迭代上限2048；数组工作区估计上限2048MiB，不当作严格分配器限制。没有总实验时长截止。

失败数组与逐轮记录保留，失败不返回普通样本。每组先完成记录与哈希，再原子写入终态。`--resume`仅在协议、源码、运行时和全部文件哈希吻合时跳过终态；成功和失败均不自动重跑。中断尝试保留，新尝试使用独立目录。运行目录另有OS互斥锁，Mac使用flock，Windows使用msvcrt；锁元数据不是活动进程证据。实际锁不可取得时拒绝第二个执行器。

## 当前验证证据

Mac专用mechanism-smoke-pilot-v1单独冻结，3组、9个工作流全部通过；含独立审计、3轮交错重放、6组成本探针及探针后重放。实际CLI恢复后126个终态文件逐字节不变，未创建新尝试。源码测试4项通过；另有Windows水井交接入口2项通过。它们不扩充历史采样器测试计数，也不验证Windows msvcrt或CUDA执行。

Mac证据见`benchmark/analysis/outputs/mechanism-smoke-v1/`。18条torch.jit.script弃用警告已保留，未据此切换到未经核验的torch.compile。当前数值核心39份文件不变。

## 可重建入口

```text
python scripts/completion/mechanism_runner.py prepare --plan benchmark/protocols/mechanism-windows-pilot-v1.json --inputs NEW_INPUT_DIRECTORY
python scripts/completion/mechanism_runner.py run --plan benchmark/protocols/mechanism-windows-pilot-v1.json --inputs NEW_INPUT_DIRECTORY --output NEW_CPU_OUTPUT --device cpu
python scripts/completion/mechanism_runner.py run --plan benchmark/protocols/mechanism-windows-pilot-v1.json --inputs NEW_INPUT_DIRECTORY --output NEW_CUDA_OUTPUT --device cuda
python scripts/completion/analyze_mechanism_pilot.py --plan benchmark/protocols/mechanism-windows-pilot-v1.json --inputs VERIFIED_ORIGINAL_INPUTS --run COMPLETED_OR_PARTIAL_OUTPUT --output NEW_ANALYSIS_OUTPUT
```

`run`完成网格不等于所有配置成功，应读取summary.json中的成功/失败数量。恢复时在原run命令末尾加`--resume`；不要删除状态文件来强制重跑。Windows协议在非Windows主机会被拒绝。原始主数组不放进Git，prepare按冻结哈希重建；汇总从实际输入、路径、接受事件及逐文件哈希生成。归档时包含原始主数组、全部尝试、环境、源码bundle、协议和汇总。

下一步接收Windows回执，检查计时波动、操作吞吐与额外工作的关系，再决定F2需要的有限补充。F3的独立调参、预算/重复数设计、成熟基线和正式推断比较仍须另立协议；本pilot不替代它们。
