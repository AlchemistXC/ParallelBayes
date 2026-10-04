# 水井模型的有限参考复核

2026-10-05｜F4参考准备｜wells-reference-audit-v1｜无新增MCMC

冻结分析源码612afdc后，按预先列出的七个函数复算posteriordb固定版参考。全部八个上游文件哈希通过，参数名和链顺序显式对应，Python到R再回写的560000字节完全一致。未导入torch或JAX。两参数的本地Rhat与上游发布值在保存精度下一致，bulk/tail ESS也仅有约1e-11的显示精度差异。

## 参考单位与误差

参考为一次上游Stan生成的10链，每链保存1000个抽稀样本；原设置每链20000次迭代、10000次预热、thin=10。它不是10000次独立实验，也不是10次独立研究。此次未额外丢弃样本。上游的零发散来自元数据，缺少原始能量/发散记录，未独立重算。

每个函数分别计算posterior::mcse_mean、10个链均值标准差除以sqrt(10)、200个非重叠长度50批均值的标准差除以sqrt(200)。表中取三者最大值作为敏感性摘要，不是严格误差上界，也不能排除所有链共有的偏差。诊断使用R4.6.0、posterior1.7.0；上游诊断记录为posterior1.6.1。

| 函数 | 参考均值 | 最大MCSE估计 | Rhat |
|---|---:|---:|---:|
| alpha | 0.6067102479 | 0.0006328 | 1.0005210 |
| beta | -0.622143444 | 0.001035 | 1.0003342 |
| alpha_squared | 0.3717133062 | 0.0007675 | 1.0006511 |
| beta_squared | 0.396531181 | 0.001353 | 1.0003342 |
| p_switch_0m | 0.647068744 | 0.0001445 | 1.0004986 |
| p_switch_100m | 0.4961455494 | 0.0001579 | 1.0009844 |
| beta_positive | 0 | 未确定 | 未确定 |

`beta_positive`的10000个记录全为零。它保持在函数集合中，MCSE、Rhat和ESS均未确定；不能以零样本方差宣布精度达标，也不能对相关链使用独立二项公式产生伪精确上界。六个连续函数可作为带有限MCSE与共同偏差局限的参考；全函数误差评价尚未闭合。

已有可积性证书通过可逆线性变换将似然上界写成二维指数尾。乘任意固定阶多项式仍可积，因此本次一、二阶矩函数存在；这不提供这些MCMC估计量的无偏或收敛证明。下一步对二维目标使用独立数值积分核查连续矩和稀有事件，保留数值截断/离散误差的限制。

## 重建

在当前提交且分析文件与锁定身份一致时，先按来源清单获取数据到SOURCE。锁文件已归档，输出必须为新目录：

```text
python scripts/completion/fetch_wells.py --output SOURCE
python scripts/completion/audit_wells_reference.py run --source SOURCE --lock benchmark/analysis/outputs/wells-reference-v1/analysis-lock.json --output NEW_REFERENCE_OUTPUT --rscript Rscript
```

需要NumPy/SciPy、R、posterior1.7.0及jsonlite；R库可通过R_LIBS_USER选择。运行状态、参数映射、完整统计和全部文件哈希在`benchmark/analysis/outputs/wells-reference-v1/`。未将上游样本或派生二进制复制进Git，原始哈希与重建命令均保留。新工具的3项检查通过：命名/链映射、非有限输入拒绝、R二进制末位及常量事件保护。

这批结果不验证Windows水井采样性能，不改变历史L2的未确定事件，也不替代F3独立调参与正式推断实验。
