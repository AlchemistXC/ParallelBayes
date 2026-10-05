# 新增原生目标：安装版完整示例

当前入口为 `examples/installed_custom_target.py` 和 `examples/installed-custom-target.R`。
它们调用已安装的 Python 0.2.0.dev2 / R 0.2.0.9002，无需修改包内数值源码，
也不要求从项目根目录运行。已在同一 Mac 的既有隔离安装环境核验 torch CPU
与 JAX CPU；[实际记录](INSTALLED-CUSTOM-TARGET.md)包含范围、失败注入和原始证据位置。
Windows/CUDA 的这个新示例尚未实测。

## 模型与接口

模型是二维 Poisson 回归：`log(lambda)=X beta`，两个系数独立服从 `N(0,4)`。
`prepare` 生成一次 32 个合成观测，并将实际 `X/y` 写进 `model.json`。
系数采用恒等坐标，log-Jacobian 为 0；省略 `sum(log(y!))` 不影响同一后验。
这不是水井真实数据案例，也没有向内置模型注册表新增 kind。

`make_target(spec, backend, device)` 展示用户需要提供的内容：

| 内容 | 本例实现 |
|---|---|
| 目标身份、数据、先验、坐标和参数顺序 | 完整 JSON spec；不得只以函数名称代替模型身份 |
| 可微密度 | torch 或 JAX 原生 float64 运算，按所选提供方式延迟导入 |
| 独立参考密度与梯度 | NumPy 密度、解析梯度，不调用待检验的框架密度或自动微分 |
| 参数变换 | NumPy 恒等映射；torch 另给设备映射 |
| 导数与轨迹检查 | 五个确定坐标点；四链各 128 次转移，含拒绝自环；固定实际随机数组 |

当前 torch 使用 `parallelbayes.reference.Model`，JAX 使用
`parallelbayes.models.Model`。两个类并非同一 Python 类型，必须按提供方式选择。
`parallelbayes.sample()` 和 `validate_model()` 接受对应的外部模型对象。
`pb_model()` 仍只接受已注册的内置/Stan 描述，不能传入任意 R 闭包，
也不能把本例 `kind` 直接传给 `pb_model()` 或内置 `make_model()`。
R 通过 reticulate 整批调用外部 Python 模型，再转为 `posterior::draws_array`。

## 运行步骤

先按 [安装说明](INSTALL-AND-USE.md) 安装候选。以下路径都是使用者指定的新目录；
`prepare` 只运行一次，后续提供方式和 R 使用同一输入目录。不要跨机器按种子
重建 `log_uniform` 来代替已保存的 NPZ。

```sh
# 在仓库或任意工作目录中，PYTHON 指向已安装 wheel 的环境。
PYTHON=/absolute/path/to/venv/bin/python
EXAMPLES=/absolute/path/to/ParallelBayes/examples
INPUTS=/absolute/path/to/new-poisson-inputs
"$PYTHON" -I "$EXAMPLES/installed_custom_target.py" prepare --output "$INPUTS"
"$PYTHON" -I "$EXAMPLES/installed_custom_target.py" run --backend torch \
  --inputs "$INPUTS" --output /absolute/path/to/new-python-torch

# 必须在启动 R 之前指定环境；不在示例中修改 .libPaths 或绑定作者目录。
R_LIBS_USER=/absolute/path/to/installed-R-library \
RETICULATE_PYTHON="$PYTHON" \
Rscript --vanilla "$EXAMPLES/installed-custom-target.R" \
  torch "$INPUTS" /absolute/path/to/new-r-torch cpu
```

JAX CPU 使用安装了 `[jax]` 可选依赖的独立环境，把上述后两条的 `torch`
换成 `jax`，使用两个新的输出目录；无需安装 torch。
普通 Python 调用导入 wheel；R 调用先由 `pb_environment()` 载入安装 R 包自带
Python，再显式核对 `__file__`。两者都记录实际来源和版本。

原生 PowerShell 对应调用如下（环境须已按 Windows 安装说明核验）：

```powershell
$py = 'D:\work\ParallelBayes\.venv-package\Scripts\python.exe'
$examples = 'D:\work\ParallelBayes\examples'
$inputs = 'D:\evidence\new-poisson-inputs'
& $py -I "$examples\installed_custom_target.py" prepare --output $inputs
& $py -I "$examples\installed_custom_target.py" run --backend torch --device cpu `
  --inputs $inputs --output 'D:\evidence\new-python-poisson-cpu'
$env:RETICULATE_PYTHON = $py
$env:R_LIBS_USER = 'D:\work\ParallelBayes\environment\R-package-library'
Rscript --vanilla "$examples\installed-custom-target.R" `
  torch $inputs 'D:\evidence\new-r-poisson-cpu' cpu
```

在候选 CUDA 环境已核验后，可另用新输出目录将设备参数改为 `cuda`。
代码拒绝 CUDA 不可用时切换到 CPU；此说明不是 Windows/CUDA 实测证据。
现有冻结实验完成/封存后再运行示例，不切换正在实验的工作树或环境。

## 输出与判断

- 输入目录保存模型、实际 noise/log_uniform/directions、初值、核验点、配置和哈希。
- 每个工作流保存全部返回数组的 NPZ 和对应 JSON，含审计、残差/停止原因及计时。
  返回失败的轨迹仍存档，`draws` 为空，R 不转换为普通后验对象。
- R 另存 RDS、float64 小端字节和现代 Rhat/bulk ESS/tail ESS；不可判定值为 null，
  短链不良诊断不会改成“收敛”。本例没有预热或正式推断误差评价。
- 已存在输出目录、校验和不匹配、不支持组合会明确拒绝。
  采样器异常按工作流保存并继续其他项；输入读取/环境构建错误由进程日志保留。
- `audit=True` 检查独立 NumPy 路径和接受事件，同核配对另检验顺序/时间轨迹。
  通过有限输入下的数值检查，不构成一般正确性、收敛或加速证明。

如将四次调用分别放在同一归档根目录的 `python-torch`、`r-torch`、
`python-jax`、`r-jax`，并将输入放在 `inputs`，可从任意目录只读核验：

```sh
"$PYTHON" -I /absolute/path/to/ParallelBayes/scripts/release/verify_custom_extension.py \
  /absolute/path/to/evidence-root --output /absolute/path/to/new-verification.json
```

核验不重新采样、不调用 R，也不访问回执中的作者安装路径。
历史 `custom-poisson-target.py/.R` 保留为 0.1.1 开发环境示例；其中的相对环境路径
不是当前安装版入口。
