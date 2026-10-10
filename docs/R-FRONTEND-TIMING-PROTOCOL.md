# R 前端有限使用成本伴随方案

身份 `mac-r-frontend-timing-v1`，2026-10-10。F4 的技术补充；Windows 正式协议、
历史实验与数值模块不变。本方案形成时已知历史短 Poisson 轨迹和 Windows 汇总结果，
不是整个研究开始前的预注册。尚未测量本方案的费用。

## 问题与范围

测量安装版 R 环境从进程启动到样本和诊断可用的实际延迟，说明最外层 R 使用的费用。
沿用已经验证的外部 Poisson 目标：32 条观测、2 参数、4 链各 128 步；实际随机数组
与旧扩展示例相同，初值、步长和窗口均不改。MALA 顺序/quasi-DEER 与 RWM 顺序/Picard
共四工作流。短轨迹已有不良诊断，因此这不是精度比较或新增统计校准。

使用已安装 R 包内置的 Python 模块和其公开 `Model`/`sample` 扩展接口，R 通过
reticulate 整批调用并转换为 posterior。该扩展目标不是 `pb_model()` 当前内置类型，
不能把辅助脚本写成通用自定义模型的 `pb_sample()` 接口。仅在 Mac CPU/torch 执行；
不推断 Windows/CUDA 或 JAX 的调用成本。

## 固定设计

- 一个实际输入；4 个工作流 × 2 个审计模式 × 4 个技术轮次 = 32 个新 R 进程。
- 每个进程调用两次相同配置，分别记录首次和后续调用，最多 64 次技术采样。
  第二次仍走完整 `sample` 接口，并非直接调用缓存内核；torch 为 eager 实现。
  首次仅指新 R 进程，没有清除操作系统页缓存，也不称为冷机器测量。
- 轮次内工作流循环移位，模式顺序交替；全计划由 `tasks()` 生成并写入不可变协议。
- 普通模式 `audit=False`，审计模式 `audit=True`，均保留执行器自身输出标准、
  float64、原数值容差、1024 轮数上限和 512 MiB 工作区估计保护。
- CPU torch intra/inter-op 及 BLAS 线程均固定为 1；记录实际版本与线程数。
  线程上限不是占用一个物理核心或 CPU 独占的证明。
- 不调参、不重试失败、不按速度选结果。若首次调用失败，保存失败并不执行该进程的
  后续调用；报告已执行/失败/未运行分母。恢复只复用哈希匹配的已结束进程。
- 接收及正式分析确已结束后才执行，保存实际句柄/进程检查；不以检查点文件推定静止。
  保留运行前后系统负载和任务记录，若有干扰则报告，不删除不利耗时。

## 时间边界

父 Python 进程在启动 R 前开启单调时钟；R 完成首次样本转换和现代诊断后立即刷新
`PB_R_READY`，父进程接收这一通知时停止首次可用延迟计时。该直接观测包含 R 启动、
包/Python/torch 载入、输入读取/哈希和目标建立、采样及其内部数据移动/参数变换、
传回 R、posterior 转换和诊断，以及少量通知费用。它不靠相减推算“普通使用成本”。

R 内另记录载入、目标建立、每次调用、传回 R、posterior 转换、诊断和随后归档。
后续调用费用从本次调用开始到诊断结束，已经复用加载与目标；首次归档发生在其前。
父进程完整墙钟还包括两次结果持久化、JSON/RDS/数组写盘和退出，独立列出，不能
再与内部各项相加。`sample` 返回的内部费用属于嵌套分解，不能与外层重复求和。

已有安装、数据/随机数组生成及执行前协议封存不在用户一次调用延迟中；安装来源和
输入仍完整保存。独立数值核验和原始数组归档不包含在普通模式的 ready 延迟中；
审计模式包含 `sample` 的独立路径检查，但额外归档仍在 ready 之后单列。

## 数值与统计呈现

计时后只读核验所有普通调用的完整状态/接受事件，与独立 NumPy 参考比较；审计模式
须保留原独立审计。核对普通/审计、首次/后续和同核两执行器的实际输入及轨迹，
核对 R 回写 float64 字节。失败记录不能当作普通样本。

展示全部四个技术轮次和描述性中位数/范围，不做 bootstrap 置信区间、显著性检验，
不把四次重放当作四份独立随机输入。参数 rank-normalized/folded Rhat、bulk/tail ESS
及未定诊断全部保留；正式推断独立重复新增 0。

## 执行与验收

通过 `scripts/analysis/r_frontend_timing.py freeze` 封存输入、计划、脚本、安装包
及依赖清单；随后 `run --quiet-record ...` 在串行新 R 进程中执行。协议和脚本身份
不匹配即停止，不自动放宽。进程原始日志、错误、状态及未完成目录全部保留。
本方案不设置总执行时限，仅有数值/内存保护和 1 GiB 可用磁盘保护。

验收包括直接 R 调用计时、独立原数组核验、实际恢复新增 0、从保存记录重建表格，
以及文稿明确其技术而非推断性质。测量无论是否加速均交付；不得补测到有利为止。

示例命令（路径由执行者指定；`freeze` 不调用采样器）：

```sh
python scripts/analysis/r_frontend_timing.py freeze \
  --inputs ACTUAL_INPUT_DIRECTORY --output NEW_TIMING_DIRECTORY \
  --rscript /path/to/Rscript --python /path/to/venv/bin/python \
  --r-library /path/to/installed/R-library
python scripts/analysis/r_frontend_timing.py run \
  --root NEW_TIMING_DIRECTORY --quiet-record ACTUAL_QUIET_RECORD.json
python scripts/analysis/r_frontend_verify.py \
  --root NEW_TIMING_DIRECTORY --output NEW_READONLY_ANALYSIS_DIRECTORY
```

`quiet-record` 必须来自实际观察，含 `receiver_active=false`、
`reconstruction_active=false` 和 `actual_handle_observations`；不是预写成功标记。
执行结果仍需由退出记录和原始输出核对。
