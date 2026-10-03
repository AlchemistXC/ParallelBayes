# 台式机环境依赖清单

2026-10-03。当前按用户要求仅在Mac CPU实验，所有GPU任务暂缓。本清单用于以后准备台式机，不表示已经安装、测试通过或需要现在执行。项目现有锁定版本优先于官网最新版；恢复GPU时仍须实际兼容性验证。

## 1 基础环境

| 项目 | 项目使用方式与版本 |
|---|---|
| Windows 11 | 已有系统；台式机Codex负责未来执行，当前不派发任务 |
| WSL2 + Ubuntu 24.04 LTS | 为现有Linux脚本和未来NVIDIA后端准备；已有合适WSL2可复用，不重复安装 |
| Python 3.12 + venv + pip | 安装在WSL内；每项目一个`.venv`。Mac实际为3.12.14；脚本要求3.12系列 |
| 编译/系统工具 | `build-essential`（gcc/g++/make）、`git`、`ca-certificates`；编译器主要用于Stan及R依赖 |
| Python构建工具 | `setuptools==84.0.0`，来自`environment/locks/build-tools.txt` |

如以后准备环境，管理员PowerShell可先检查 `wsl --list --verbose`。缺少发行版时使用 `wsl --install -d Ubuntu-24.04`，按系统提示重启；已有WSL可使用 `wsl --update`。发行版名以 `wsl --list --online` 为准。[Microsoft安装说明](https://learn.microsoft.com/en-us/windows/wsl/install)

Ubuntu基础安装命令（仅准备环境，不运行实验）：

```sh
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip build-essential git ca-certificates
```

项目放在WSL用户目录，例如`~/ParallelBayes`；Windows侧安装的Python/R不会自动成为WSL环境的一部分。当前没有远程安装任何软件。

## 2 Python数值与测试依赖

| 用途 | 锁定版本 |
|---|---|
| 自动微分与执行 | jax 0.6.2、jaxlib 0.6.2 |
| 数值计算 | numpy 2.2.6、scipy 1.15.3 |
| NUTS基线 | blackjax 1.2.5 |
| 算法配套 | optax 0.2.5、chex 0.1.89、jaxopt 0.8.5、fastprogress 1.0.3 |
| Stan模型接口 | bridgestan 2.7.0 |
| 测试、资源、图表 | pytest 8.4.2、psutil 7.1.0、matplotlib 3.10.6 |

完整33项传递依赖见[python-runtime-transitive.txt](../environment/locks/python-runtime-transitive.txt)，不用逐个手装。基础CPU环境的安装命令如下；这些命令不会启动采样，也不安装CUDA依赖：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r environment/locks/build-tools.txt
.venv/bin/python -m pip install -r environment/locks/python-runtime-transitive.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m pip check
```

## 3 R接口和Stan扩展（按用途安装）

只运行Python正式实验不必先安装R。需要R包、R端分析或跨语言测试时，在同一WSL发行版安装R；本机已验证版本为 **R 4.6.0**，其他版本尚未核验。包声明的最低R版本不是完整锁定环境的兼容承诺；Ubuntu默认仓库提供的R不一定等于4.6.0。

核心R依赖：`renv 1.3.0`、`reticulate 1.47.0`、`posterior 1.7.0`、`jsonlite 2.0.0`；测试用`testthat 3.3.2`。其余依赖按[renv.lock](../environment/locks/renv.lock)恢复。安装R及开发工具后，在项目根目录运行 `Rscript --vanilla scripts/install-r.R`；根据R源包的实际编译需要补齐`gfortran`等系统依赖。R调用项目内`.venv/bin/python`，不混用Windows R和WSL Python。

Stan路径另需 **BridgeStan 2.7.0源码、Linux stanc 2.37.0及C++编译工具**。交接包已携带源码压缩包和stanc，通过 `scripts/setup-bridgestan.py` 校验并准备；模型必须在Linux重新编译，不能复用Mac动态库。当前NUTS采用BlackJAX，**不需要CmdStan、RStan或JAGS**。RStudio、Anaconda、Docker和Windows Rtools也不是此WSL方案的必需项。

## 4 GPU附加依赖（全部延期）

| 安装位置 | 以后恢复GPU时所需 |
|---|---|
| Windows | 支持RTX5080及WSL的NVIDIA Windows驱动；安装时从NVIDIA官方选适配版本，并保存实际驱动信息 |
| WSL项目`.venv` | `jax[cuda12]==0.6.2`，`jax-cuda12-plugin==0.6.2`、`jax-cuda12-pjrt==0.6.2` |
| WSL项目`.venv` | CUDA运行库、cuBLAS、cuDNN、cuFFT、cuSOLVER、cuSPARSE、NCCL等15项候选包，完整版本见[gpu-candidate.txt](../environment/locks/gpu-candidate.txt) |

当前官方JAX支持表中，Windows原生NVIDIA后端不支持，WSL2为实验性支持；本项目因此采用WSL2。官方推荐通过pip安装CUDA/cuDNN库。本项目已锁定的0.6.2/CUDA12组合只做过依赖解析，**尚未在5080上通过实测**；官网目前推荐的新版本不能直接替换冻结环境。[JAX安装与平台支持](https://docs.jax.dev/en/latest/installation.html)

驱动只安装在Windows，不在WSL里安装Linux NVIDIA显示驱动。此项目采用pip CUDA库路线，通常不需要另装完整系统CUDA Toolkit或手动复制cuDNN。[NVIDIA WSL指南](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)

GPU安装脚本为`handoff/gpu/01-bootstrap-wsl.sh`，设备检查为`02-check-device.py`，实验阶段为`RUN-STAGES.sh`。**当前均不执行；用户明确恢复GPU后再使用。** 安装成功不等于数值正确或有性能收益，仍需原计划设备/精度、正确性、探测和正式实验。
