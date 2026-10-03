# 安装、使用与复现

本项目为本地研究发布候选 0.1.1，非 CRAN 发布。本轮验证及锁定环境为 Python 3.12、R 4.6.0；其他 R 版本尚未验证；原生 JAX CPU 路径不需要 C++，Stan 路径需要编译器与固定 BridgeStan 源。

从项目根目录运行：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r environment/locks/build-tools.txt
.venv/bin/python -m pip install -r environment/locks/python-runtime-transitive.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
Rscript --vanilla scripts/install-r.R
```

R 的 reticulate Python 应在首次 Python 调用前设置。所有高频计算整批传入 Python，不逐步往返 R。

```r
.libPaths(c(file.path(getwd(), "environment/R-library"), .libPaths()))
Sys.setenv(RETICULATE_PYTHON = file.path(getwd(), ".venv/bin/python"))
library(parallelbayes)
m <- pb_model("gaussian", dimension = 8L)
pb_capabilities(m)
fit <- pb_sample(m, kernel = "mala", executor = "quasi_deer",
                 draws = 256L, chains = 4L, window = 64L,
                 step_size = 0.1, seed = 2026L, audit = TRUE)
fit$record$status
fit$record$audit
posterior::summarise_draws(fit$draws)
```

短例用于检查接口，不保证后验均衡。正式分析必须遵循冻结预算、预热和独立重复方案。`failure='record'` 默认保留失败对象，失败时 draws 为 NULL。若需要相同噪声顺序回退，显式指定 `on_failure='sequential'`；计入所有已花时间。

`examples/quickstart.R`演示原生目标，`examples/stan-end-to-end.R`演示Stan正值参数，`examples/logistic-paired.R`演示共享数据的Stan/JAX核对与R中成对执行。`pb_benchmark()`用于组织给定配置列表并保存R结果；正式研究的协议冻结、检查点和原始随机数组由Python协议CLI管理，重建命令见`docs/REBUILD-RESULTS.md`。短例的单次计时不是正式基准结论。

能力矩阵见 `docs/CAPABILITIES.md`：Stan只支持CPU顺序RWM/MALA；CPU时间并行目前要求明确实现的原生JAX目标。新增目标示例见 `docs/EXTENDING-TARGETS.md`。

标准 Stan 入口：

```r
s <- pb_model(stan_file = "models/stan/lognormal.stan",
              data = list(mu = 0, sigma = 1))
n <- pb_model("lognormal", mu = 0, sigma = 1)
pb_validate(s, matrix(c(-12, -1, 0, 1, 5), ncol = 1), reference = n)
f <- pb_sample(s, kernel = "mala", draws = 64L, step_size = .05)
```

先下载并解压 BridgeStan 2.7.0 到 environment/bridgestan-2.7.0，或设置 BRIDGESTAN。macOS arm64 构建明确传入 TBB arch=arm64，关闭 Stan 线程。模型编译库依赖该源码树的动态库路径，因此复制项目到新机器后必须重新编译 .stan，不要复制 Mac 的 .so 当作 Linux 产物。

基础验证：

```sh
.venv/bin/python -m pytest tests/python tests/safety -q
R_LIBS_USER="$PWD/environment/R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" PB_RUN_INTEGRATION=1 Rscript --vanilla -e 'library(testthat); library(parallelbayes); test_dir("r-package/tests/testthat")'
```

JAX 的编译缓存和首次设备初始化会影响计时。本项目的 compile 是单次任务显式 lower/compile 开销，进程导入/安装是单列环境成本；完整任务时间包含模型建立、执行、审计和结果输出，不称为全新操作系统进程冷启动。当前跨后端结果属于完整软件工作流比较。

冻结协议 CLI 在任务开始前验证源码指纹。复制新代码不能继续旧协议；历史 pilot 源码快照存于 execution/source-snapshots。正式结果由分析脚本读取原始结果重新生成。GPU已暂缓；原生Windows后端尚未实现。历史handoff/gpu归档不属于当前可执行安装路线。

直接调用 MH 时，`draws` 返回全部指定转移，包括拒绝自环；`warmup` 字段仅用于 NUTS 自适应，MH 用户需自行确定并显式丢弃初始段。正式基准在任务内记录 `discard`。`on_failure='sequential'` 只处理执行器停止失败；独立审计失配或变换错误保留为失败，不再静默回退。
