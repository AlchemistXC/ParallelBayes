# 原生 Windows 11 / RTX 5080 接力入口

2026-10-04：用户已恢复Windows阶段。目标电脑是AMD CPU＋RTX 5080，不采用WSL2、Linux虚拟机或Linux容器。**此提交提供交接与环境探针，尚未提供PyTorch MCMC后端；GPU实验必须在完成移植和核验后开始。** Mac CPU研究里程碑和原始负结果继续保留。

1. 安装/准备下表的基础环境，克隆本仓库。
2. 在Windows Codex中打开该仓库，粘贴 [CODEX-PROMPT.md](CODEX-PROMPT.md) 的全文。
3. 将Mac上的`output/windows-skills-private/parallelbayes-user-skills-2026-10-04.zip`单独转到Windows仓库的`downloads/`；提示词会按[技能安装说明](SKILLS-SETUP.md)完成迁移。该私下技能包不会上传公开GitHub。
4. Codex按 [WORK-PACKAGES.md](WORK-PACKAGES.md) 完成环境实测、后端开发、正确性核验、探测、新协议冻结和正式实验。阶段失败保留记录，不跳到性能结论。

## 先准备什么

| 环境 | 用途及要求 |
|---|---|
| Windows 11 x64、原生Codex、Git for Windows | 工作区放在本机SSD，如C:\work\ParallelBayes；使用PowerShell；不要放OneDrive同步目录 |
| NVIDIA官方Windows驱动 | 支持RTX5080；记录实际驱动版本及nvidia-smi输出，不能只检查安装了CUDA |
| Python 3.12 x64 | 与Mac的语言版本对齐；使用独立`.venv-win-torch`，不复用Mac venv |
| PyTorch官方Windows CUDA wheel | 初始候选`torch==2.7.1`＋cu128，**不是最新版本推荐、最终环境锁或已验证5080组合**；目标机核对官方支持并实测后冻结 |
| NumPy、SciPy、pytest、psutil、matplotlib | 见`requirements-bootstrap.txt`；完整传递锁在目标机成功后生成 |
| Microsoft Visual C++ x64运行库 | 二进制依赖需要时安装；不同于完整Visual Studio C++工具链 |
| R x64、reticulate、posterior、jsonlite、testthat、renv | 后续R控制/诊断；Mac记录R4.6.0，Windows安装受支持版本并另行记录，不必为了运行GPU先装Stan |
| GitHub CLI（可选） | 下载证据Release、推送开发分支及交回结果；也可浏览器下载 |

预编译torch CUDA wheel的基础路线无需先装完整CUDA Toolkit、VS Build Tools、Rtools或CmdStan。只有需要自定义CUDA扩展、编译Stan/R源码时才按官方说明增加相应工具；不要假定torch.compile/Triton在当前Windows组合上可用。torchvision、torchaudio和WSL均不是本任务依赖。

## 克隆及环境探测

```powershell
git clone https://github.com/AlchemistXC/ParallelBayes.git
cd ParallelBayes
# 安装官方Codex后，在Codex中打开这个文件夹；随后粘贴CODEX-PROMPT.md。
# 以下脚本在Windows运行，不在Mac上冒充验证：
.\scripts\windows\bootstrap.ps1
```

若组织策略阻止PowerShell脚本，让Codex执行脚本中相同的逐条命令或按组织批准方式处理；不要关闭系统安全策略。脚本只建立项目venv和安装Python包，不安装驱动、不改全局环境、不启动正式采样。默认候选固定为已核对有Windows CUDA构建的2.7.1/cu128；升级可传`-TorchVersion`、`-CudaIndex`及`-VenvName .venv-win-torch-候选名`，但须检查官方匹配关系并生成新环境记录，不能覆盖已冻结实验环境。每次安装报告保存在独立bootstrap尝试目录；正式冻结时在所用venv根目录写入`PARALLELBAYES-FROZEN.json`（协议身份、源码提交、锁文件哈希），此后bootstrap会拒绝修改该环境。

```powershell
.\.venv-win-torch\Scripts\python.exe scripts/windows/probe_environment.py --require-windows --require-cuda --output execution/windows-native/environment.json
```

探针做float64 GPU运算、torch.func的grad/JVP/vmap、CPU/GPU数值对照及显式同步，记录设备能力、实际GPU名称、显存、版本、CPU/RAM和峰值分配。它只证明基础框架操作可用，**不证明时间并行采样器已实现、收敛或加速**。失败返回非零码并保存错误；不自动切CPU伪装通过。

当前包`parallelbayes`的初始化直接导入JAX，pyproject.toml仍为Mac/JAX依赖。因此不要在torch环境盲目执行`pip install -e .`并假定完成了原生GPU安装。新后端需在新版本中隔离/延迟JAX导入，并保留旧版源码及Mac回归；具体见提示词。

## 数据与证据

仓库包含源码、测试、冻结协议、摘要、论文、独立NumPy参考以及历史源码快照。重新构造目标和新的共同随机输入不要求先下载5GB历史证据；**跨版本重放/完整旧结果重建**需要Release资产。

[cpu-review-v1 Release](https://github.com/AlchemistXC/ParallelBayes/releases/tag/cpu-review-v1)保存完整三部分复现包；大证据tar按512MiB分块。下载所有资产到独立目录后运行：

```powershell
# gh已登录时可用；也可在浏览器下载所有附件
gh release download cpu-review-v1 --repo AlchemistXC/ParallelBayes --dir downloads/cpu-review-v1
py -3.12 scripts/windows/assemble_evidence.py --directory downloads/cpu-review-v1
```

脚本校验每块及重组tar的SHA256，不自动覆盖已有不同文件。重建整套Mac证据时，将三个归档解压到**独立目录**，不要覆盖当前Git开发分支。独立复现包是历史CPU快照，其中GPU暂缓的历史文字不覆盖本交接的2026-10-04授权。

## 官方依据（2026-10-04核对）

- [PyTorch Windows安装](https://pytorch.org/get-started/locally/)、[2.7.1 Windows/cu128命令](https://pytorch.org/get-started/previous-versions/)、[Blackwell/CUDA12.8支持起点](https://pytorch.org/blog/pytorch-2-7/)。候选不是对未来版本兼容性的保证。
- [JAX平台表](https://docs.jax.dev/en/latest/installation.html)：原生Windows的NVIDIA GPU不受支持；不能把CPU JAX安装成功写成GPU成功。
- [官方Codex配置说明](https://learn.chatgpt.com/docs/config-file/config-basic)：原生Windows沙盒可用。保持标准权限审批；不要开启全权限模式来绕过环境错误。该项目无需为Codex选定特定模型或关闭沙盒。
- [GitHub Release限制](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)：每个资产小于2GiB；分块传输保持整体证据哈希不变。
