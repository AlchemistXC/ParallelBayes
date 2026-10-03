# ParallelBayes

时间并行MCMC的可核验实现、R控制接口与单机CPU基准。当前数值内核 **0.1.1**；CPU主实验使用独立归档的 **0.1.0**。软件与论文均为研究候选，尚非投稿终稿。

## 从Windows电脑接手

2026-10-04：开始原生 **Windows 11＋AMD CPU＋RTX 5080** 阶段，不采用WSL2。

1. 克隆仓库，在原生Windows Codex中打开项目。
2. 阅读[环境与操作说明](handoff/windows-native/README.md)。
3. 将[Windows Codex完整提示词](handoff/windows-native/CODEX-PROMPT.md)粘贴给目标机Codex，让它按[工作包](handoff/windows-native/WORK-PACKAGES.md)开发并执行。

**当前没有PyTorch MCMC后端或已验证GPU能力。** 交接含PowerShell环境准备、实际CUDA/float64/导数探针和结果打包工具；目标机先完成移植及正确性核验，再冻结新协议开展实验。JAX无法直接提供原生Windows NVIDIA GPU路线；历史`handoff/gpu`仅是WSL/JAX归档。

## 当前支持范围

| 模型提供方式 | 顺序RWM/MALA | Picard RWM / quasi-DEER MALA | NUTS |
|---|---|---|---|
| Stan/BridgeStan CPU | 支持 | 不支持 | 不支持 |
| 明确实现和核验的原生JAX目标 | 支持 | 支持相应组合 | BlackJAX |
| 原生Windows PyTorch/CUDA | 待开发和目标机验证 | 待开发和目标机验证 | 待评估接入 |

完整[能力矩阵](docs/CAPABILITIES.md)、[计算契约](docs/COMPUTATION-CONTRACT.md)、[Mac安装与使用](docs/INSTALL-AND-USE.md)、[新增Poisson目标示例](docs/EXTENDING-TARGETS.md)。当前包初始化及pyproject仍依赖JAX，不能将`pip install -e .`误认为完成torch后端安装。

## 已完成的CPU研究

- 1920项正式任务、320次正式SBC拟合、72项补充机制任务全部留档，负结果保留。
- 两条时间执行路线的所有模型—预算组中位缓存速度比均未达到1；这不是CPU普遍无收益的证明。
- 同64组数据的解析SBC覆盖54/64；完成1928次拟合的现代Rhat/ESS诊断。NUTS发散集中于H1，M1无发散仍有探索问题，L2参考符号事件保持不可判定。
- 40组历史随机输入的版本对照接受事件零失配；不据此宣称0.1.0/0.1.1性能等价。
- 独立Python环境、迁移目录及完整归档重建通过；仍共享同一Mac、R库和编译器，不声称外部团队或异构平台已复现。

阅读[17页软件论文PDF](output/software-paper/软件与基准研究.pdf)、[LaTeX与完整输入](manuscript/software/软件与基准研究.tex)、[CPU审查修订报告](docs/CPU-REVIEW-REVISION.md)、[版本衔接](docs/VERSION-BRIDGE.md)。原[中文综述](manuscript/中文综述.tex)独立保留，文献结果不与新实验混同。

## 原始证据与复现

Git包含源码、完整测试、冻结协议、分析摘要、论文/图件及历史内核源；**不把5GB原始数组放进Git历史**。完整三部分复现包在[cpu-review-v1 Release](https://github.com/AlchemistXC/ParallelBayes/releases/tag/cpu-review-v1)，大证据tar按512MiB分块；用仓库内SHA256清单重组，见[交接说明](handoff/windows-native/README.md#数据与证据)。新模型和后端开发无需等待下载全部历史证据。

解压完整CPU复现包到独立目录后，按[独立复现说明](docs/PORTABLE-REPRODUCTION.md)从根目录运行`reproduce.py`；校验、分析、1928项诊断重算、绘图和论文编译均有实际记录。仅克隆Git并不包含全部原始证据，不能跳过缺失输入继续声称完整重建成功。

## 许可与发布范围

本项目源码采用[MIT](LICENSE)，上游quasi-DEER比较源码保留BSD许可，详见[第三方说明](docs/THIRD-PARTY.md)。本仓库不分发第三方论文/书籍PDF、全文提取、私有技能源码、虚拟环境或缓存。文献引用、研究摘要和本项目原创稿件另保留。

R包作者/维护者元数据仍是项目占位，不是正式CRAN发布。GPU支持及论文结论只有实际Windows测试后才能更新；没有自动配置选择器、任意Stan转GPU或通用加速声明。

自定义技能迁移见[Windows技能安装说明](handoff/windows-native/SKILLS-SETUP.md)。30个技能的正文以私下ZIP转交；公开仓库仅含清单、校验和及安装脚本。
