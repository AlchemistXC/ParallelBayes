# 安装、使用与复现

当前安装候选为 Python **0.2.0.dev2** / R **0.2.0.9002**，位于
`codex/research-integration`；原安装来源 `codex/release-candidate-0.2` 保留。
这是本地研究候选，未发布到 PyPI、CRAN 或公共 Release。
实测安装与版本差异见 [候选核验记录](RELEASE-CANDIDATE-0.2.md)。
下列命令创建新的环境；不要更新已冻结实验的环境，也不要用此版本继续旧协议。

## 选择提供方式

| 入口 | 包内支持 | 限制与证据 |
|---|---|---|
| `backend="torch"`，明确原生目标 | CPU 顺序 RWM/MALA、Picard RWM、quasi-DEER MALA | 候选安装在 Mac CPU 实测；Windows CPU/CUDA 的既有证据属于 0.2.0.dev1，新安装候选尚待该平台核验 |
| `backend="jax"`，明确原生目标 | 对应四种 MH 工作流、BlackJAX NUTS | 沿用 JAX 路线，需单独安装可选依赖 |
| Stan/BridgeStan | CPU 顺序 RWM/MALA | 不支持 CPU 时间执行、torch 转译或 GPU；Windows 原生编译未核验 |

调用 `pb_capabilities(model)` 查看组合。torch 包内没有 NUTS；项目研究脚本的
Pyro CPU NUTS 是独立入口，不能写成 `pb_sample(..., kernel="nuts", backend="torch")`。
完整边界见 [CAPABILITIES.md](CAPABILITIES.md)。

## Mac CPU：独立 torch 环境与 R 库

在新候选检出目录运行。已验证的版本为 Python 3.12.14、R 4.6.0、
torch 2.13.0、NumPy 2.2.6、reticulate 1.47.0、posterior 1.7.0。
锁文件描述本次验证环境，不是最新版推荐或任意平台兼容性承诺。

```sh
python3.12 -m venv .venv-package
.venv-package/bin/python -m pip install -r environment/locks/mac-release-candidate-v1.txt
# 将已核验的安装候选三个归档放入 dist/；使用非 editable 安装。
.venv-package/bin/python -m pip install --no-deps dist/parallelbayes-0.2.0.dev2-py3-none-any.whl
.venv-package/bin/pb --help
.venv-package/bin/pb environment --backend torch --output execution/package-environment.json
mkdir -p environment/R-package-library
R CMD INSTALL --library=environment/R-package-library dist/parallelbayes_0.2.0.9002.tar.gz
```

安装 R 包前，其依赖应已位于该 R 库：reticulate、posterior、jsonlite，
测试还需要 testthat。项目提供 `environment/locks/renv.lock`，可用已安装的 renv
恢复到**新库**（例如 `renv::restore(lockfile="environment/locks/renv.lock",
library="environment/R-package-library", prompt=FALSE)`）。
需要先安装 renv 时，在该库内执行 `install.packages("renv", lib=...)`，
不要覆盖历史 `environment/R-library`。

只有源码检出、没有预构建包时，可在另一个构建环境中执行
`python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .`
（已安装锁定的 setuptools），以及 `R CMD build r-package`。
安装候选附有 Python sdist、由该 sdist 构建的 wheel 和 R 源码包；
核验清单中的 SHA256 后再安装。

在启动 R **之前**设置 Python 与 R 库：

```sh
R_LIBS_USER="$PWD/environment/R-package-library" \
RETICULATE_PYTHON="$PWD/.venv-package/bin/python" \
Rscript --vanilla examples/installed-torch.R execution/package-example-01
```

示例要求输出目录不存在，运行四种工作流并检查两组实际随机输入哈希、
接受事件与轨迹，将 R 对象、现代诊断、审计和计时写入目录。
64 次转移只验证接口，不证明收敛或性能。R 使用安装包内自带的 Python 模块；
如果会话已载入不同版本，应重启 R，而不是绕过版本检查。

交互式最小示例：

```r
library(parallelbayes)
m <- pb_model("gaussian", dimension = 2L, backend = "torch")
pb_capabilities(m)
stopifnot(pb_validate(m)$passed)
fit <- pb_sample(m, kernel = "mala", executor = "quasi_deer",
                 device = "cpu", draws = 64L, chains = 4L,
                 window = 8L, audit = TRUE)
fit$record$status
fit$record$audit
posterior::summarise_draws(fit$draws)
```

`backend` 默认仍为 `jax`，torch 用户必须明确选择。
`failure="record"` 保留失败记录，此时 `draws` 为 NULL；`failure="error"`
在完成失败记录后抛错。`on_failure="sequential"` 为显式执行器回退，保留已花成本，
不同后端的触发范围见计算契约；约束输出错误不得成为正常样本。
MH 的 `draws` 包括拒绝自环，包内 MH 不自动自适应或丢弃初始段。

## 原生 Windows

不使用 WSL2。已收到的 torch 2.13.0+cu130、Windows 11、RTX 5080
证据见 [WINDOWS-NATIVE.md](WINDOWS-NATIVE.md) 与 [WINDOWS-RESULTS.md](WINDOWS-RESULTS.md)。
既有 `.venv-win-torch` 及 F2/F3 协议保持不变。
新候选另建环境，按 [候选安装核验提示词](../handoff/windows-completion/CODEX-PROMPT-PACKAGE.md)
完成原生安装、CPU/CUDA 与 R 检查后，才能登记该版本的 Windows 安装通过。
这是后续独立工作包，不要求中断正在运行的机制或运行器验收。

在原生 PowerShell 中，Python 可执行文件路径使用
`.venv-package\Scripts\python.exe`，设置 R 入口例如：

```powershell
$env:RETICULATE_PYTHON = (Resolve-Path .venv-package\Scripts\python.exe).Path
$env:R_LIBS_USER = (Resolve-Path environment\R-package-library).Path
Rscript --vanilla examples/installed-torch.R execution/package-example-01
```

安装依赖与 GPU 探针成功不等于候选采样通过；不要用 Mac 锁文件安装 CUDA 版本，
不要把 CPU 回退当 GPU 检验。完整 Windows 依赖及驱动按既有已核验环境另行锁定。

## JAX 与 Stan

JAX 是可选提供方式。使用独立环境及 `environment/locks/python-runtime-transitive.txt`；
源码构建或 wheel 安装时附带 `[jax]` 可选依赖，依赖锁优先。
历史详细步骤保留在 [0.1.1 安装说明](history/INSTALL-0.1.1.md)，
其中“Windows 后端尚未实现”等段落仅描述历史状态。
`examples/quickstart.R`、`stan-end-to-end.R`、`logistic-paired.R` 是该路线的历史案例，
运行前检查其环境路径，不把它们当跨平台自动安装器。

Stan 需要 C++ 编译器与 BridgeStan 2.7.0 源码树（或正确设置 `BRIDGESTAN`）。
Mac arm64 编译沿用已有工具链记录；换机器必须重新编译模型，不能复制 Mac `.so`
当作 Windows 动态库。torch 提供方式不接收 Stan 文件。

## 检查与复现边界

```sh
# 在已安装 wheel 的 Python 环境测试，-I 排除 PYTHONPATH 和当前目录导入。
.venv-package/bin/python -I -m pytest --import-mode=importlib -p no:cacheprovider \
  tests/release/test_installed_cli.py tests/windows/test_torch_backend.py -q
R CMD check --no-manual dist/parallelbayes_0.2.0.9002.tar.gz
```

`R CMD check` 默认跳过需要 Python 的集成测试，不能拿它替代真实集成证据。
显式开启 torch 检验：

```sh
R_LIBS_USER="$PWD/environment/R-package-library" \
RETICULATE_PYTHON="$PWD/.venv-package/bin/python" PB_RUN_TORCH_INTEGRATION=1 \
Rscript --vanilla -e 'library(parallelbayes); testthat::test_file("r-package/tests/testthat/test-torch-installed.R")'
```

JAX 集成使用独立 Python 环境和 `PB_RUN_INTEGRATION=1`，运行
`test-end-to-end.R`。必须分别记录通过、失败和跳过；窗口/路径短测不是统计有效性证明。

`pb environment --backend torch` 只记录环境。`pb run` / `pb recover`
仍是 **JAX 历史协议**入口，不能据此运行 torch 的 Windows 或 F3 协议。
现行研究运行器位于项目 `scripts/completion/`；`pb_benchmark()` 只运行配置列表并可保存 R 对象，
不负责冻结协议、全机资源归属、恢复登记或完整归档。

软件安装包、研究脚本与原始证据是不同交付物。重建历史主表图需要对应版本的
完整原始归档，见 [REBUILD-RESULTS.md](REBUILD-RESULTS.md)；
新候选不宣称可以跨版本接续任何冻结实验。安装结果与方法性能结果分别报告。
