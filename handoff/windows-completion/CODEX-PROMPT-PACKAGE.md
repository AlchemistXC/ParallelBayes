# 独立安装候选核验（F5；按顺序接续，不中断 F2/F3）

你在原生 Windows 11 / AMD CPU / RTX 5080 上继续 ParallelBayes。
本提示词是安装候选的后续验收；先完成或安全封存正在运行的 F2/F3 工作，
不要把本分支合并到正在执行的冻结实验工作树。无 WSL2、Linux 虚拟机或容器。

读取 `AGENTS.md`、`docs/RELEASE-CANDIDATE-0.2.md`、`docs/INSTALL-AND-USE.md`
与 `docs/CAPABILITIES.md`。安装候选位于远端分支 `codex/release-candidate-0.2`，
Python 0.2.0.dev2 / R 0.2.0.9002。用新的 Git worktree 检出该分支并记录实际提交；
不要切换或更新当前冻结实验的目录、Python 环境、协议或源码。

1. **环境和构建。** 在新目录建立 `.venv-package` 与 `environment/R-package-library`。
   按本机已通过核验的 Windows CUDA 依赖清单安装相同版本，另存完整锁、
   安装日志、驱动和设备信息，不借用 Mac wheel 或把 CPU torch 当 CUDA。
   不要求完整 CUDA Toolkit、Stan、WSL、Triton 或新采样算法。
   构建 Python sdist，再在独立解压目录从 sdist 构建 wheel；构建 R 源码包。
   记录各归档 SHA256，安装实际 wheel 和 R 源码包，禁止 editable 安装。
   R 依赖用新库，记录每个非基础包的实际载入路径；系统自带 recommended 包的
   复用要明确记载。作者/维护者占位信息不替用户填写。
2. **命令入口。** 在仓库外工作目录、去除 PYTHONPATH 后运行
   `python -I -m parallelbayes.cli --help` 和
   `python -I -m parallelbayes.cli environment --backend torch --output <新文件>`。
   记录包的 `__file__`、`__version__`，确认来自安装路径且环境没有 JAX。
   不选 JAX 时不得依赖它；没有 JAX 时默认环境命令应明确拒绝并给出提示。
   `pb run/recover` 仍为 JAX 历史命令，不是 torch 正式实验入口。
3. **CPU 然后 CUDA。** 用安装环境运行
   `tests/release/test_installed_cli.py` 与 `tests/windows/test_torch_backend.py`。
   前者一次足够；后者先设 `PB_TORCH_DEVICE=cpu`，通过后再设 `cuda`。
   使用 `python -I -m pytest --import-mode=importlib -p no:cacheprovider`，
   确认测试导入安装 wheel；保存 XML、通过/失败/跳过和警告。
   不要为通过而换种子、删目标、放宽接受事件或路径标准。
4. **R 安装证据。** `R CMD check --no-manual` 单独留日志；默认集成跳过不是验证通过。
   设置 `RETICULATE_PYTHON` 为新原生 Python、`R_LIBS_USER` 为新库，
   `PB_RUN_TORCH_INTEGRATION=1`，显式运行安装包源码中
   `test-torch-installed.R`、`test-environment-record.R`。
   检查实际环境内存字节数在 Python JSON 与 R 中一致；当前候选修正了大整数截断。
   再运行 `examples/installed-torch.R`，保存四工作流原对象与诊断。
   在 R 中追加同样四工作流的 `device="cuda"` 短验证：数组次序、独立审计、
   同核随机数组哈希、接受事件、失败隔离和 CUDA 设备记录都要保留。
   确认 R 加载的是安装包自带的 Python 模块，不是旧项目副本。
5. **版本与结果。** 比较本分支与 `52fdfd0446768033ffd975bc52ea8036c420880d`
   的数值模块清单；候选修改入口、R 元数据和版本，不改转移核/参考/执行器。
   保留 `validation_evidence.version=0.2.0.dev1` 的历史能力证据归属，
   不直接改成 dev2 冒充新平台检验。不重跑 512、1920 或 F2 正式网格。
   若修正候选源码，独立提交并重新构建受影响包和检查，保留前次失败。
6. **回传。** 输出 `execution/package-candidate/` 工作包、源码提交、
   依赖及设备清单、安装/测试日志、原始 R 对象、环境 JSON、版本桥接和校验和。
   归档须包含用于安装的 wheel、sdist、R 包、测试源码及示例。
   给出全部测试状态和仍未验证项；不只给截图/摘要。
   不发布公共 Release、合并主分支、上传 CRAN 或替换冻结实验结果。

这项验收回答“外部用户能否安装并核验当前包”，不证明统计收敛或加速。
Mac 已核验也不替代本机 CPU/CUDA 与 R 的真实结果。技能按已授权本机安装状态
选用；缺私有 ZIP 时继续此工作，不从公开源猜测私有技能。
