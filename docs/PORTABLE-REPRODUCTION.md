# 独立CPU复现包

版本：cpu-review-v1；内核仍为0.1.1。主实验0.1.0历史源和协议原样保留。软件归档、实验/分析源码归档、原始证据/论文归档必须一起解压，合并到同一个`parallelbayes-reproduction`根目录。先校验下载文件的SHA256SUMS，再解压；不要只安装R包便声称拥有论文复现材料。

三个归档分别包含：

1. `software-0.1.1-cpu-review-v1.tar.gz`：R/Python源码、R安装包、模型/例子、完整Python测试、依赖锁、上游比较源和许可、0.1.0历史源码和版本补丁。
2. `experiments-cpu-review-v1.tar.gz`：全部相关冻结协议、分析与绘图脚本、根目录`reproduce.py`、安装及复现文档。
3. `evidence-paper-cpu-review-v1.tar`：1920正式任务、8参考拟合、320SBC拟合及72机制任务的原始数组/状态/校验和；现代诊断和版本对照；验证日志；全部LaTeX输入、矢量图及PDF。NPZ已经压缩，该归档不再gzip。

各包自带同一bundle_id的逐文件SHA256清单。路径均相对于合并根目录；日志中的历史本机路径只是证据，不是复现前提。包中不包含原论文版权PDF、私有技能文件、环境二进制或本机编译的Stan库。下载依赖仍需网络；原Stan模型须用目标机器的编译器重新编译。

## 安装与运行

已验证Python 3.12、macOS arm64；不是Windows GPU软件。先按`docs/INSTALL-AND-USE.md`配置Python和R。Stan测试另执行`python scripts/setup-bridgestan.py`（检查脚本记录的2.7.0源和下载校验）；macOS需要Xcode命令行工具。图件重建依赖锁内的matplotlib。论文用已有Tectonic或XeLaTeX（ctex与Fandol），首次构建可能需要下载标准字体。

从解压根目录：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r environment/locks/build-tools.txt
.venv/bin/python -m pip install -r environment/locks/python-runtime-transitive.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps .
.venv/bin/python scripts/setup-bridgestan.py
Rscript --vanilla scripts/install-r.R
.venv/bin/python reproduce.py verify
.venv/bin/python reproduce.py example
.venv/bin/python reproduce.py tests
.venv/bin/python reproduce.py analysis
.venv/bin/python reproduce.py diagnostics
.venv/bin/python reproduce.py figures
.venv/bin/python reproduce.py paper
```

`verify`应在重建前执行；重建可能更新机器环境或耗时元数据，不能将这些变化误判为原包损坏。`analysis`不重新采样，读原始数组，保留原始诊断计时并逐字节比对主摘要。现代指标的逐拟合值已经保存；`diagnostics`强制在新目录重算全部1928个拟合，并比较排除诊断耗时后的内容。两者是不同验证范围。

R CMD check可另外执行`R CMD check --no-manual output/release/parallelbayes_0.1.1.tar.gz`。其默认集成测试会跳过；`reproduce.py tests`显式启用PB_RUN_INTEGRATION=1，二者日志必须分开。论文PDF的二进制字节可因字体、TeX发行版和时间戳变化；科学表格的数值、源输入和图件数据应保持一致。

重跑历史主实验须按`docs/REBUILD-RESULTS.md`选择归档0.1.0内核，另建输出目录；`analysis`绝不会自动启动1920项采样。机制实验入口为`scripts/revision/mechanism.py`，核对其冻结代码哈希，完成/失败均可恢复登记；要在新机器重新测量，应先复制到独立目录并移走该目录中的已有机制输出，保持原包不变。不要混合机器计时、重写旧协议或覆盖原证据。

## 本次验证边界

另建锁定依赖环境，安装非editable Python轮子，迁移源码目录后验证58项Python测试。初次遗漏上游比较源导致1项失败，补齐后仅复查失败项通过；日志完整保留。迁移目录重建使用本机原始数据的文件关联，主数值摘要逐字节一致；这验证目录和Python环境独立性，但仍共享Mac、R库和C++编译器。它不是异构机器/另一研究团队复现声明。

正式SBC、机制实验、版本对照及现代诊断的原始记录与所有失败尝试保留。可选分散初始化、昂贵似然、真实应用及精确XLA剖面未完成，不作为本轮验收要求；GPU和自动配置选择器继续暂缓。所有交付为本地研究候选，署名与投稿尚需研究者决定。
