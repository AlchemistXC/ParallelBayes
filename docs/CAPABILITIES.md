# 模型—方法支持矩阵（安装候选0.2.0.dev2；原实验0.2.0.dev1/0.1.1）

安装候选 **0.2.0.dev2 / R 0.2.0.9002** 的数值模块与原开发版本逐文件相同，新增命令入口及R环境元数据修正；[本机安装核验](RELEASE-CANDIDATE-0.2.md)已完成。下列Windows证据仍属于原0.2.0.dev1；新候选Windows安装未验收。

## Windows 开发分支 0.2.0.dev1（2026-10-04 新证据）

历史 0.1.1 表格保留在下方。开发分支提供独立 torch/NumPy 导入；安装基础包不再强制安装 JAX。

| 提供方式及实测范围 | 顺序 RWM/MALA | Picard RWM / quasi-DEER MALA | NUTS |
|---|---|---|---|
| 原生 Windows torch CPU，明确内置目标 | 已核验 | 已核验，eager Python 控制 | 独立研究CLI的Pyro CPU；九目标顺序/spawn就绪核验通过，非正式精度结论 |
| 原生 Windows torch CUDA，RTX 5080 float64 | 已核验 | 已核验，未宣称融合设备内控制 | 尚未接入/核验 |
| 原生 Windows JAX CPU | 原入口回归通过 | 原入口回归通过 | 原入口冒烟测试通过 |
| 原生 Windows Stan/BridgeStan | 本轮未编译核验；历史能力仅 CPU 顺序 | 不支持 | 不支持 |

实测组合、命令与边界见 [WINDOWS-NATIVE.md](WINDOWS-NATIVE.md)；原始数组及状态见
`execution/windows-native/`。GPU 基础探针与采样器正确性分别保存。当前 CUDA NUTS 不在能力查询中。
所有 GPU 声明限定于已经返回本项目的真实设备结果，不延伸到任意硬件、模型或数据。
新协议 512 项（CPU/CUDA 各 256）已完成数值核验，256 对跨设备实际数组接受事件零失配。
大量短链混合不足，A1/RWM 全部拒绝提议；“已核验”不代表推断收敛。
完整解释及未完成范围见 [WINDOWS-RESULTS.md](WINDOWS-RESULTS.md)。
CPU Pyro基线通过独立研究CLI运行，不是`pb_sample(..., backend="torch", kernel="nuts")`的通用选项；torch包能力查询仍将NUTS标为不支持。

2026-10-05第二轮：已选仿射坐标的九目标MH组合在CPU/CUDA各54工作流、36配对通过，
独立NumPy重放及零重算恢复通过；九目标CPU NUTS六类数组串行/spawn一致。
H1/MALA全拒绝链、NUTS不利Rhat与不可判定函数保留；F2机制pilot仍因冻结输入哈希
不匹配而未执行。详见[第二轮回执](WINDOWS-COMPLETION-V2-RESULTS.md)。 Mac独立接收已完成，六份F2原输入已补传；108份路径/事件满足原标准，但其中60份原尺度跨系统逐位检查仍为false，最大差约8.88e-15。此差异与Windows同机核验分开报告，见[接收记录](WINDOWS-ROUND2-INTAKE.md)。

## 历史发布 0.1.1

本版是Stan顺序采样入口与经过核验的原生JAX时间并行实验接口。Stan提供方式尚未连接CPU时间并行执行器，也不自动翻译至JAX或GPU。

| 模型提供方式 | 顺序RWM | 顺序MALA | RWM＋Online Picard | MALA＋quasi-DEER | BlackJAX NUTS |
|---|---|---|---|---|---|
| Stan／BridgeStan CPU | 支持 | 支持 | 不支持 | 不支持 | 不支持 |
| 内置原生JAX目标，Mac CPU | 支持 | 支持 | 支持 | 支持 | 支持 |
| 自定义Python Model，明确提供JAX密度与独立参考 | 按模型核验后使用 | 需梯度核验 | 按模型核验后使用 | 需导数与轨迹核验 | 须另核验，示例未评价 |
| 原生Windows GPU | 未实现 | 未实现 | 未实现 | 未实现 | 未实现 |

`pb_capabilities(model)`返回组合而非声称全部笛卡尔积可用。Picard仅配RWM，quasi-DEER仅配MALA。内置目标包括高斯、logistic、lognormal、漏斗及非中心化漏斗、双峰高斯混合和共轭正态均值；正式潜在AR目标转换为明确高斯后验。

Stan默认没有独立轨迹oracle；传入`audit=TRUE`会拒绝，不能将同一个Stan函数调用两遍称为独立实现。配对示例通过显式原生目标核对共同坐标的密度、梯度与变换。编译某个Stan文件不代表已验证该模型的后验探索。

R例：

```r
native <- pb_model('gaussian', dimension=2L)
pb_capabilities(native)
stan <- pb_model(stan_file='models/stan/lognormal.stan', data=list(mu=0,sigma=1))
pb_capabilities(stan) # combinations仅顺序RWM与MALA
```

`pb_benchmark()`批量运行配置列表并可保存R对象；它不承担正式协议冻结、检查点和完整证据归档。正式研究通过Python CLI和项目协议文件管理。

新增模型的当前安装版案例见 `examples/installed_custom_target.py` 和 `installed-custom-target.R`：按提供方式构造公开Python `Model`，给出torch/JAX密度及独立NumPy密度/解析梯度，保存并共用实际输入，核对两组MH工作流。Mac已安装包的Python/R调用及数组回写通过，短链不利诊断保留；Windows/CUDA本例未测。它不是新增`pb_model()`注册机制或通用Stan转译。说明及证据见 [EXTENDING-TARGETS](EXTENDING-TARGETS.md) 和 [安装版核验](INSTALLED-CUSTOM-TARGET.md)。旧0.1.1示例保留。

## 外部目标扩展的实测例

`examples/external_wells.py`通过公开Python Model接口提供posteriordb水井距离模型，保留其平坦先验；R经`examples/external_wells.R`整批调用。Mac CPU的Stan/NumPy/torch目标、顺序/时间轨迹与R数组字节核验通过，见[报告](WELLS-TARGET-VALIDATION.md)。2026-10-05原生Windows CPU/CUDA及R-CUDA共12工作流、独立NumPy路径/接受事件和二进制回传核验通过，见[第二轮回执](WINDOWS-COMPLETION-V2-RESULTS.md)。它没有注册为pb_model内置kind，不能用带正态先验的内置logistic替换；短链核验不构成正式推断或收敛证据。


2026-10-07后续：F2原始输入机制pilot已完成CPU/CUDA共192工作流，同机独立审计和终态零重算核验通过；旧失败输入与负结果保留，见[机制回执](WINDOWS-MECHANISM-COMPLETION.md)。新Windows原生运行器当前16项人工行为检查通过，27项最大形状技术任务尚待执行；这不是正式推断或候选安装通过，见[运行器验收](WINDOWS-RUNTIME-VALIDATION.md)。

2026-10-07有限技术后继：Windows新协议27主任务（含64维四链16,384步的CPU四spawn NUTS及CPU/CUDA四种MH）及24独立缓存探测/96调用通过；17项原生所有权与恢复行为检查、同机独立审计及终态零重算通过。仅三个模型各一份技术输入，无正式精度/性能结论。详见[原生运行器回执](WINDOWS-RUNTIME-VALIDATION.md)。
