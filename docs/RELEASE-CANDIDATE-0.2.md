# 0.2 安装候选：版本衔接与本机验收

日期：2026-10-06。分支 `codex/release-candidate-0.2`，基于研究审查提交
`52fdfd0446768033ffd975bc52ea8036c420880d` 单独建立。
Python 版本为 **0.2.0.dev2**，R 版本为 **0.2.0.9002**。
原研究工作树、所有冻结协议、原始数组和历史版本均保留。
这是 F5 的安装里程碑，正式研究 F2/F3、Windows 候选安装和最终论文仍未完成。

## 修正内容与可观察证据

| 问题 | 原行为 | 本候选 |
|---|---|---|
| 可选依赖 | 安装 torch 而没有 JAX 时，`pb --help` 导入 JAX 后失败 | 先解析命令；帮助页不导入数值提供方式 |
| 环境查询 | CLI 只有 JAX 路径 | `pb environment --backend torch`；默认 JAX 保留，缺依赖有明确错误 |
| R 环境元数据 | Python 内存字节数 17179869184 经 reticulate 转换后成为 0 | 在转换前对环境字典进行 JSON 序列化，R 保留 17179869184 |
| 版本与说明 | 安装说明仍称 0.1.1 且未实现 Windows | 独立候选版本、能力与安装说明、无本机绝对路径的安装后 R 示例 |

CLI 和 R 元数据均保留失败先于修正的检查日志。
转移核、执行器、密度/梯度、参数变换、独立 NumPy 参考以及研究运行器没有改动。
`capabilities()` 中的 `validation_evidence.version=0.2.0.dev1` 仍归属原 Windows 证据，
不会改写成新版本已在 Windows 核验。版本桥接的逐文件 SHA256 另存。
数值模块相同不等于跨版本/跨环境计时相同；没有用旧结果给候选增加性能结论。

## 安装与检查

在同一 M4 Mac mini / 16 GiB 主机建立两个新 Python 虚拟环境，
分别安装固定 torch 和 JAX 依赖及非 editable wheel。
Python sdist 先独立解压再构建 wheel；R 从 `R CMD build` 产物安装，
显式核查 R 加载安装包内的 Python，而不是开发目录副本。
运行位置在项目外，Python 测试使用 `-I --import-mode=importlib`。

| 检查 | 实际结果 |
|---|---|
| torch CPU 安装 wheel：原后端测试 | 63 通过，无失败/跳过 |
| CLI 安装后行为 | 3 通过，无失败/跳过 |
| JAX/安全测试 | 55 通过；3 个 Stan 测试首次因未配置 `BRIDGESTAN` 失败 |
| 配置已有 BridgeStan 2.7.0 后的三项测试 | 3 通过，新工作树的三个模型重新编译；上述 55 项未重复运行 |
| `R CMD check --no-manual` | OK；默认 7 个集成测试全部跳过，不能计作通过 |
| 显式 torch R 集成 | 4 个测试、56 断言通过，无失败/跳过 |
| 显式 JAX R 集成 | 3 个测试、15 断言通过，无失败/跳过 |
| 安装后四工作流 R 示例 | 4 次成功返回，2 组同核随机输入哈希/接受事件/路径检查通过；原 R 对象、现代诊断和计时保留 |

Python torch 检查保留 18 条 `torch.jit.script` 弃用警告及 1 条工作树缓存权限警告；
JAX 保留 1 条 JAXopt 维护状态警告。不把测试日志中的警告删除。
R 示例只有每链 64 次转移，RWM 的 Rhat 明显偏高；它用于接口验收，
不是后验收敛、SBC 或正式性能实验，也不增加正式研究的独立重复数。

### 独立环境的实际边界

Python 3.12.14 使用同一个已安装解释器的标准库，虚拟环境不继承旧 site-packages。
torch 环境没有 JAX/Pyro，JAX 环境没有 torch；锁文件及实际发行包位置随记录保存。
离线缓存缺包和最初的缓存目录权限错误均保留，按相同版本下载安装后完成。

R 仍使用本机 R 4.6.0 发行版。初次 `renv::restore` 虽报告同步，实际复用了系统
posterior/jsonlite，故没有把它当作完整独立库验收。
之后在新库安装了 47 个锁定包；Matrix 1.7-5（R 规范化版本号为 1.7.5）
复用同一 R 发行版的二进制并复制到新库。其强制源码构建曾因缺少 `libintl.h`
失败，该日志保留，没有修改系统编译器或工具链。48 个锁定包的位置和版本均检查。
最终 reticulate、posterior、jsonlite、testthat 从新库载入。

这证明在本机新库/虚拟环境中可以安装和运行，不是不同操作系统或外部研究团队复现。
Stan 复用了已有固定源码工具链，未做全新编译器安装。Windows 候选尚待实际回执。

## 交付与使用

- 当前步骤：[INSTALL-AND-USE.md](INSTALL-AND-USE.md)。历史 0.1.1 说明单独保留。
- 安装示例：`examples/installed-torch.R`；要求显式 `RETICULATE_PYTHON` 和新输出目录。
- 公开测试：`tests/release/test_installed_cli.py`、R 包内的两项 torch 测试文件。
- 紧凑证据：`benchmark/analysis/outputs/package-candidate-v1/`，含检查日志、版本桥接、环境及构建索引。
- 本地交付包包含 wheel、sdist、R 源码包、测试/安装日志、失败尝试、源码快照、
  原始示例对象和逐文件校验清单；不包含环境、第三方论文或私有技能。
- [Windows 安装候选提示词](../handoff/windows-completion/CODEX-PROMPT-PACKAGE.md)
  排在现有 F2/F3 任务之后，使用新工作树和新环境。

`pb run/recover` 仍是历史 JAX 协议入口；研究运行器不随 wheel/R 包完整分发。
`pb_benchmark()` 不是协议冻结/资源管理/检查点工具。
旧协议源码身份与候选不同，不能绕过核查接续旧运行。
作者维护者元数据仍为占位，未公开发布或合并主分支。


## 封存身份

候选源码提交 `0e3841353b85a9827aff1b596a74fc4917202306`。
17个Python文件在最终wheel、R包与已测试wheel中逐字节相同；其中15个文件与
52fdfd0基线相同，仅CLI及版本入口改变。R源码和测试与安装包相同；DESCRIPTION
仅增加R构建工具的标准字段与换行。最终wheel的三项CLI检查再次通过，不累计为新测试。

本地 `package-candidate-v1.tar` 为59,842,560字节、130个文件，129项清单资产
逐项验证；SHA256为 `4bf32475466ca4c1aa91fa69f2d7ab0d03bdc47ec482e49cf963a02ad46570c7`。
归档及三个安装产物的校验索引见紧凑证据目录。未上传为公共Release。
