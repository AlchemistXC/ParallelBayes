# 模型—方法支持矩阵（0.1.1）

## Windows 开发分支 0.2.0.dev1（2026-10-04 新证据）

历史 0.1.1 表格保留在下方。开发分支提供独立 torch/NumPy 导入；安装基础包不再强制安装 JAX。

| 提供方式及实测范围 | 顺序 RWM/MALA | Picard RWM / quasi-DEER MALA | NUTS |
|---|---|---|---|
| 原生 Windows torch CPU，明确内置目标 | 已核验 | 已核验，eager Python 控制 | 独立 Pyro CPU 基线，仅 normal/Gaussian 本轮统计核验 |
| 原生 Windows torch CUDA，RTX 5080 float64 | 已核验 | 已核验，未宣称融合设备内控制 | 尚未接入/核验 |
| 原生 Windows JAX CPU | 原入口回归通过 | 原入口回归通过 | 原入口冒烟测试通过 |
| 原生 Windows Stan/BridgeStan | 本轮未编译核验；历史能力仅 CPU 顺序 | 不支持 | 不支持 |

实测组合、命令与边界见 [WINDOWS-NATIVE.md](WINDOWS-NATIVE.md)；原始数组及状态见
`execution/windows-native/`。GPU 基础探针与采样器正确性分别保存。当前 CUDA NUTS 不在能力查询中。
所有 GPU 声明限定于已经返回本项目的真实设备结果，不延伸到任意硬件、模型或数据。

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

新增模型的完整案例见 `examples/custom-poisson-target.py` 和 `.R`：构造公开Python `Model`，给出JAX密度与独立NumPy密度/解析梯度，核对典型及尾部点，再对两组MH工作流使用同一实际随机输入比较。它不是新增`pb_model()`注册机制；R示例通过reticulate调用此公开Python扩展入口，将输出转换为posterior对象。源数据、模型和验证说明见 `docs/EXTENDING-TARGETS.md`。
