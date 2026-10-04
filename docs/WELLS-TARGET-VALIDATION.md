# 外部水井模型：目标一致性与R扩展示例

2026-10-05｜F4阶段结果｜Mac CPU核验，尚非正式推断或性能实验

已将公开的`wells_data-wells_dist100_model`接入既有Python `Model`扩展接口。R通过reticulate整批调用示例并得到`posterior::draws_array`。这是显式实现和核验的外部目标；没有新增Stan自动转译，也没有把它注册为`pb_model()`内置kind。当前不应使用内置带正态先验的logistic目标替代它。

## 原模型与可积性

原始数据来自固定版posteriordb，3020个观测；使用`switched`与`dist/100`，参数顺序为alpha、beta。原Stan模型未指定正态先验，本例保留alpha、beta上的平坦先验，约束映射为恒等。来源、版本、许可与8个来源文件哈希见[案例说明](../models/external/wells/README.md)。

数据中有31个距离值同时出现两种结局。选取3.25200009346008米和151.065994262695米；其反向结局观测的0基索引分别为(532,530)及(2883,189)。令两个缩放距离为$x_1,x_2$，相应四条Bernoulli因子给出

\[
L(\alpha,\beta)\leq \exp\{-|\alpha+x_1\beta|-|\alpha+x_2\beta|\}.
\]

其余似然因子均不超过1。由于$x_1\ne x_2$，右式在二维参数空间的积分为$4/|x_2-x_1|\approx2.7061$，有限；似然连续且严格为正，故归一化常数也严格为正。这是本数据平坦先验后验可积的充分证据。代码没有把“找不到这类重复观测”误称为一般后验不适定证明。

## 实际核验结果

| 检查 | 实测结果 |
|---|---:|
| Stan与独立NumPy：相对密度最大差 | 1.2233e-10 |
| Stan与独立NumPy：梯度最大差 | 1.4779e-12 |
| torch与独立NumPy：相对密度最大差 | 1.8190e-12 |
| torch与独立NumPy：梯度最大差 | 7.1054e-15 |
| torch HVP对独立解析梯度中心差分的最大差 | 1.2788e-7 |
| MALA顺序与quasi-DEER：最大路径差 | 9.0510e-11 |
| RWM顺序与Picard：最大路径差 | 6.6613e-16 |
| 两对接受事件失配 | 均为0 |
| R数组与Python对应数组 | 逐字节相同，96×4×2 |

目标检查使用7个预先固定点。轨迹检查使用同一实际Philox数组、4链、每链96步、窗口16；MALA步长0.0005，RWM尺度0.05，无自动回退。两核接受次数分别为360/384和195/384，顺序与时间执行器一致。这些数值只用于正确性检查，不是最优调参或充分混合的证据。R重放复用相同数组，四个工作流的实际样本/接受事件与Python首次运行完全相同；不增加独立统计重复数。

Stan参数名`beta.1`与本例输出名`beta[1]`显式对应，参数位置未重排。torch运行没有导入JAX；实际为Mac CPU、torch 2.13.0、NumPy 2.2.6、SciPy 1.15.3，单一torch CPU线程。R为4.6.0，posterior为1.7.0，reticulate为1.47.0。没有在Mac运行或验证CUDA。

## 失败、协议与诊断

源提交`e171756`冻结了`external-wells-validation-v1`。首次R入口在导入时失败，因为对venv内Python符号链接调用`normalizePath`跳到了基础解释器，找不到SciPy；该次尚未启动R入口的采样，日志保留。

兼容修复只规范化父目录并保留Python文件名，同时允许显式指定协议。为遵守完整源码哈希规则，新建`external-wells-validation-v2`，没有修改v1。v1/v2所有科学字段与实际输入文件字节相同，变更仅为R入口和协议命名器；衔接回执已保存。Stan/torch首次核验属于v1，R成功核验属于v2；不能不加说明地把它们称作同一次协议运行。

另从保存的R Picard样本作事后诊断，未丢弃任何预热：alpha、beta的秩/折叠Rhat分别约3.036、3.817，bulk ESS约4.89、4.68。它们明确没有支持收敛。原始数组、全部逐轮记录与这项不利诊断均保留，未按诊断重新选择初值、链长或步长。

独立重放工具另以NumPy参考重算8条参考链，检查两次运行保存的8个工作流以及R序列化数组；全部接受事件一致，未导入torch或JAX。它复用了同一份实际随机输入，仍只有一份独立随机数组。回执见`benchmark/analysis/outputs/wells-validation/independent-replay.json`。

## 复跑

从项目根使用已安装依赖的Python。固定输入在`benchmark/fixtures/wells-validation-v1/inputs.npz`；公开数据先由fetch脚本按固定哈希获取到`SOURCE`。输出必须用全新目录。

```text
python scripts/completion/fetch_wells.py --output SOURCE
python scripts/completion/verify_wells_arrays.py --source SOURCE --output NEW_REPLAY_JSON
python scripts/completion/validate_wells.py --source SOURCE --output NEW_TORCH_OUTPUT --stage torch --protocol benchmark/protocols/external-wells-validation-v2.json --tape-from benchmark/fixtures/wells-validation-v1/inputs.npz
Rscript --vanilla examples/external_wells.R REPO SOURCE NEW_R_OUTPUT PYTHON_ABSOLUTE_PATH benchmark/fixtures/wells-validation-v1/inputs.npz benchmark/protocols/external-wells-validation-v2.json
Rscript --vanilla scripts/completion/diagnose_wells_example.R NEW_R_OUTPUT/draws.rds NEW_DIAGNOSTICS_JSON
```

R需已有posterior 1.7.0、jsonlite、reticulate；通过`R_LIBS_USER`选择对应库。Python需要NumPy/SciPy/torch，Mac核验依赖锁在`environment/locks/mac-completion-torch-pip.txt`。Stan目标对照另需BridgeStan 2.7.0及可用C++工具链，设置`BRIDGESTAN`后将上方Python命令的stage改为stan，无需`--tape-from`。v2可用于再次核验，但不能把新环境结果标作已保存的v1测量。

保存证据位于`benchmark/analysis/outputs/wells-validation/`，包括首次Stan/torch结果、R成功回执、实际数组和校验清单。Stan编译产物不在Git，按原始源文件重新编译；其原始摘要校验和及编译日志保留，本地原文件未删除。

F4后续仍需复核上游有限参考样本及其不确定性，并以独立协议运行正式案例。F2/F3所需的受控机制实验、独立调参和充分预算比较仍未完成。此示例的接口成功不代替这些研究证据。
