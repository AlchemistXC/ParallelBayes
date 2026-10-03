> 2026-10-04：用户已恢复Windows实验，当前操作清单、候选安装脚本和Codex提示词见 [原生Windows交接](../handoff/windows-native/README.md)。下文为路线说明；后端尚未实现或验证。

# 台式机依赖：原生 Windows 方案

2026-10-03，根据用户偏好修订。**不采用WSL2或Ubuntu。** 现有Mac/JAX环境继续使用，未来Windows GPU拟采用PyTorch/CUDA新后端。框架支持Windows不等于本项目后端已实现或已在5080验证。

## 可预先准备的基础环境

| 依赖 | 要求与用途 |
|---|---|
| Windows 11 x64 | 现有系统，无需Linux子系统 |
| NVIDIA Windows驱动 | 官方支持RTX5080的驱动；安装时核对适配型号并保存版本 |
| Python 3.12 x64 | 安装Windows原生Python，使用项目独立venv；后续R也连接此Python |
| Microsoft Visual C++ x64运行库 | 当PyTorch/其他二进制依赖要求时安装；它不同于完整Visual Studio编译工具 |
| Git for Windows | 可选，便于记录源码及补丁；不影响直接使用源码交接包 |

由Windows Codex在目标机准备环境并实际验证；在PowerShell建立独立环境的示例为：

```powershell
py -3.12 -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip --version
```

## 未来原生GPU后端依赖

- **PyTorch的官方Windows CUDA构建**：选择明确支持Blackwell的构建；CUDA12.8或更新的对应官方wheel作为核验方向。官方2.7发布已加入Blackwell/CUDA12.8支持，历史安装页列出2.7.1的Linux/Windows cu128构建。这只是已存在的候选依据，不是本项目已冻结或通过的版本。[官方Windows安装](https://pytorch.org/get-started/locally/)、[Blackwell支持发布说明](https://pytorch.org/blog/pytorch-2-7/)、[官方版本安装表](https://pytorch.org/get-started/previous-versions/)
- NumPy、SciPy、pytest、psutil、matplotlib等：现有版本可作为兼容性核验起点；新环境通过后产生独立的Windows锁文件，不把JAX的完整传递依赖直接当作PyTorch环境。
- PyTorch预编译CUDA包路线不以自行编译框架为前提。只有实际需要编译自定义CUDA扩展时，再增加匹配的CUDA Toolkit和Visual Studio C++ Build Tools；不预设所有用户都必须安装完整开发工具链。
- 不需要torchvision、torchaudio；本研究没有图像/音频模型依赖。
- 不使用旧的`jax[cuda12]`、`jax-cuda12-plugin`或`gpu-candidate.txt`来配置原生Windows显卡。JAX官方平台表仍将原生Windows NVIDIA GPU列为不支持。[JAX平台支持](https://docs.jax.dev/en/latest/installation.html)

**目前没有可称为“通过验证”的原生Windows完整环境锁或一键实验安装命令。** 先在Windows CPU上核对PyTorch实现，再用5080验证并冻结驱动、torch/CUDA版本与实际依赖。不会用未验证版本组合覆盖原有科学结果。

## R和Stan（按用途安装）

- 若使用R控制层，在Windows原生安装R x64；当前Mac验证版本4.6.0，Windows平台仍需单独核验。
- R包依赖reticulate、posterior、jsonlite；renv管理依赖，testthat用于核验。reticulate应指向项目`.venv-win\Scripts\python.exe`，不连接WSL Python。
- BridgeStan仍是CPU模型提供方式。需要Windows Stan编译时，再根据BridgeStan说明配置相应编译工具和匹配R版本的Rtools；重新编译模型，不能使用Mac的动态库。它不会把任意Stan模型自动变为PyTorch CUDA模型。
- RStudio可选；当前成熟NUTS为Mac/JAX的BlackJAX。未来Windows GPU NUTS需单独接入并核验PyTorch生态实现，不能将BlackJAX直接改名为PyTorch基线。

## 交接状态

旧`handoff/gpu/parallelbayes-gpu-handoff-0.1.1-rc2.tar.gz`是冻结的历史WSL/JAX包，保持原样以便追溯；**不要用它作为原生Windows GPU执行包**。当前不用其WSL安装脚本或阶段命令。新的Windows源码、PowerShell脚本、锁文件与测试证据须在后端实现后另行交付。

实现分解和验收见[原生Windows后端路线](WINDOWS-NATIVE-ROADMAP.md)。旧WSL清单仅在`docs/archive/`留作历史记录。
