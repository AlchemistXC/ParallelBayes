# 原生 Windows GPU 后端路线

2026-10-04：用户已恢复原生Windows阶段，交接入口为handoff/windows-native/。状态仍为后端未实现、GPU未验证；由Windows Codex按分阶段任务完成。应用codebase-design技能，将不同设备实现放在明确的后端接口之后，保留共享模型规格、实际随机输入、核参数与结果契约。

## 判断和来源

原生Windows可以运行PyTorch CUDA；JAX的官方NVIDIA GPU支持不包括原生Windows。因此该需求需要新的数值后端，不能通过在Windows安装CUDA使当前JAX内核直接可用。[PyTorch](https://pytorch.org/get-started/locally/)、[JAX](https://docs.jax.dev/en/latest/installation.html)

PyTorch提供grad、vmap和jvp，可作为本项目MALA与quasi-DEER的实现工具；具体组合仍须核验。[torch.func](https://docs.pytorch.org/docs/stable/func.api.html)

CuPy也发布Windows CUDA wheel，可作为以后专用数组/扫描实现的备选；本阶段选择PyTorch是为了同时覆盖梯度、JVP和批处理，不同时引入两个必需GPU后端。[CuPy](https://docs.cupy.dev/en/stable/install.html)

## 现有代码需要改变的部分

| 当前实现 | 拟议适配与验收 |
|---|---|
| models.py中JAX密度闭包 | 按相同JSON模型规格构建PyTorch模型；与独立NumPy及现有JAX核对密度、梯度、参数变换/Jacobian |
| kernels.py的value_and_grad与接受分支代理导数 | 重现MALA/RWM公式、硬接受分支、非有限失败和quasi-DEER代理导数；不仅比较最终样本均值 |
| executors.py的vmap、scan、while_loop、associative_scan | 实现同样窗口与确认前缀；独立检查仿射扫描组合次序、末窗口、停止/回退。框架GPU可运行不代表这些算子组合已经高效 |
| sampling.py的JIT编译与block_until_ready | 增加PyTorch设备同步、运行/传输/核验/诊断及可选编译成本；CPU循环与主机同步开销进入实测 |
| nuts.py的BlackJAX NUTS | 保留作JAX/CPU工作流；另评估Pyro NUTS等PyTorch候选，重新核对适配、诊断和成本，不声称同核等价 |
| R的reticulate与结果格式 | 同一R控制接口选择后端；批量调用Windows原生Python，保持posterior样本与独立记录 |
| Bash交接、依赖锁与恢复 | 新建PowerShell流程、Windows路径处理、设备/驱动清单、恢复检查及完整结果导出 |

Pyro官方具有HMC/NUTS接口，但本项目尚未接入，也没有验证其5080性能。[Pyro MCMC](https://docs.pyro.ai/en/stable/mcmc.html)

不假定torch.compile或第三方Triton在目标Windows环境中可用或提供净收益。先获得可检查的正确实现；若增加编译或专用CUDA扫描，再独立核验并计入构建成本。不用每步搬到CPU来伪装GPU时间并行。

## 验收顺序

1. 不影响已冻结的0.1.0/0.1.1与现有Mac结果，另建开发版本；只有开始实际移植时才添加后端代码和新依赖。
2. 在Windows CPU上首先核对PyTorch模型、顺序RWM/MALA及两种执行器；复用保存的实际noise/log-uniform/directions，而不要求跨框架同整数seed产生相同随机数。
3. 审计尾部/约束、接受临界值、停止、失败及原随机输入回退，保留新旧实现差异；用完整基准目标复核后冻结迁移版本。
4. 用户已恢复GPU任务；在原生Windows RTX5080上完成float64、实际设备执行、密度/导数、轨迹/接受事件、错误注入、SBC、同步计时与资源核验。
5. 新后端使用新的协议身份；Windows上的顺序PyTorch和时间并行PyTorch是核心成对比较。Mac/JAX对Windows/PyTorch只能描述完整工作流差异，不能把全部差异归因于显卡。
6. 通过小型探测后才能开展新冻结正式基准；预热、编译、失败、负结果及参考不确定性继续完整保留。

原生Windows的支持与性能均不在本次文档更新中标记通过。Mac CPU阶段已完成；新Windows阶段通过实际证据独立验收。
