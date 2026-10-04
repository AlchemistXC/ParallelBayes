# ParallelBayes

时间并行MCMC的可核验实现、R控制接口与单机基准。本开发分支为 **0.2.0.dev1**；历史发布内核 **0.1.1**，Mac CPU主实验使用独立归档的 **0.1.0**。软件与论文均为研究候选，尚非投稿终稿。

## 从Windows电脑接手

2026-10-04：开始原生 **Windows 11＋AMD CPU＋RTX 5080** 阶段，不采用WSL2。

1. 克隆仓库，在原生Windows Codex中打开项目。
2. 阅读[环境与操作说明](handoff/windows-native/README.md)。
3. 将[Windows Codex完整提示词](handoff/windows-native/CODEX-PROMPT.md)粘贴给目标机Codex，让它按[工作包](handoff/windows-native/WORK-PACKAGES.md)开发并执行。

**本开发分支已完成原生PyTorch后端及RTX 5080实测。** 新协议512项CPU/CUDA任务通过数值输出核验，65项CPU和63项CUDA测试通过；详细结果、负例与限制见[Windows实测报告](docs/WINDOWS-RESULTS.md)和[安装/运行说明](docs/WINDOWS-NATIVE.md)。许多短链尚未混合，数值核验通过不等于推断收敛。`handoff/windows-native`保留移植前交接状态；历史`handoff/gpu`仅是WSL/JAX归档。

## 当前支持范围

| 模型提供方式 | 顺序RWM/MALA | Picard RWM / quasi-DEER MALA | NUTS |
|---|---|---|---|
| Stan/BridgeStan CPU | 支持 | 不支持 | 不支持 |
| 明确实现和核验的原生JAX目标 | 支持 | 支持相应组合 | BlackJAX |
| 原生Windows PyTorch CPU/CUDA | 内置目标已实测 | 相应组合已实测，eager Python控制 | GPU未接入；独立Pyro CPU正态基线已核验 |

完整[能力矩阵](docs/CAPABILITIES.md)、[计算契约](docs/COMPUTATION-CONTRACT.md)、[Mac安装与使用](docs/INSTALL-AND-USE.md)、[新增Poisson目标示例](docs/EXTENDING-TARGETS.md)。本开发版本支持torch/NumPy独立导入，JAX依赖移至可选安装；CUDA torch构建须按[Windows说明](docs/WINDOWS-NATIVE.md)安装并验证。

## 已完成的CPU研究

- 1920项正式任务、320次正式SBC拟合、72项补充机制任务全部留档，负结果保留。
- 两条时间执行路线的所有模型—预算组中位缓存速度比均未达到1；这不是CPU普遍无收益的证明。
- 同64组数据的解析SBC覆盖54/64；完成1928次拟合的现代Rhat/ESS诊断。NUTS发散集中于H1，M1无发散仍有探索问题，L2参考符号事件保持不可判定。
- 40组历史随机输入的版本对照接受事件零失配；不据此宣称0.1.0/0.1.1性能等价。
- 独立Python环境、迁移目录及完整归档重建通过；仍共享同一Mac、R库和编译器，不声称外部团队或异构平台已复现。

阅读[CPU与Windows扩展论文PDF](output/software-paper/软件与基准研究.pdf)、[LaTeX与完整输入](manuscript/software/软件与基准研究.tex)、[CPU审查修订报告](docs/CPU-REVIEW-REVISION.md)、[版本衔接](docs/VERSION-BRIDGE.md)。该20页PDF已编译，包含Windows实测及回传复核；历史CPU稿保留于Git历史和CPU复现Release。原[中文综述](manuscript/中文综述.tex)独立保留，文献结果不与新实验混同。

## 原始证据与复现

Git包含源码、完整测试、冻结协议、分析摘要、论文/图件及历史内核源；**不把5GB原始数组放进Git历史**。完整三部分复现包在[cpu-review-v1 Release](https://github.com/AlchemistXC/ParallelBayes/releases/tag/cpu-review-v1)，大证据tar按512MiB分块；用仓库内SHA256清单重组，见[交接说明](handoff/windows-native/README.md#数据与证据)。新模型和后端开发无需等待下载全部历史证据。

解压完整CPU复现包到独立目录后，按[独立复现说明](docs/PORTABLE-REPRODUCTION.md)从根目录运行`reproduce.py`；校验、分析、1928项诊断重算、绘图和论文编译均有实际记录。仅克隆Git并不包含全部原始证据，不能跳过缺失输入继续声称完整重建成功。

## 许可与发布范围

原始构想与历史选题讨论保留在[研究材料](materials/README.md)，属于待核验的历史资料，不是当前操作指令。

本项目源码采用[MIT](LICENSE)，上游quasi-DEER比较源码保留BSD许可，详见[第三方说明](docs/THIRD-PARTY.md)。本仓库不分发第三方论文/书籍PDF、全文提取、私有技能源码、虚拟环境或缓存。文献引用、研究摘要和本项目原创稿件另保留。

R包作者/维护者元数据仍是项目占位，不是正式CRAN发布。GPU声明限于已保存并核对的Windows实测组合；没有自动配置选择器、任意Stan转GPU或通用加速声明。Windows结果包已上传`windows-native-v1`草稿Release并通过接收端校验；未代用户将草稿公开。复核与剩余诊断差异见[回传复核报告](docs/WINDOWS-RETURN-AUDIT.md)。

自定义技能迁移见[Windows技能安装说明](handoff/windows-native/SKILLS-SETUP.md)。30个技能的正文以私下ZIP转交；公开仓库仅含清单、校验和及安装脚本。
