# Mac 参考实现的合成验收

本阶段使用本地锁定的 Python 3.12.14 / JAX 0.6.2 / BlackJAX 1.2.5 / Diffrax 0.7.0 环境。CPU 使用 float64。程序只接受合成模型，正式启动另须有冻结的模型、数据、先验、分层起点与输入哈希。正式 RWM/MALA/NUTS 的 Windows 执行及计时须在原生 Windows 上取得证据。

## 重放命令

在开发工作树根目录执行。令 `PY` 指向按 `mac-environment/requirements-arm64.lock` 安装的解释器，`RUN` 指向一个存在的空输出目录。重放分别创建各自的报告和数据库。

```sh
"$PY" -B scripts/prospective_plan/inventory.py "$RUN/inventory.json"
"$PY" -B tests/prospective_reference/validate_gaussian.py "$RUN/gaussian-validation.json"
"$PY" -B tests/prospective_reference/validate_analysis.py "$RUN/analysis-qualification.json"
"$PY" -B tests/prospective_reference/validate_models.py "$RUN/model-validation.json"
"$PY" -B tests/prospective_reference/restart.py logistic "$RUN/logistic"
"$PY" -B tests/prospective_reference/restart.py ode-fast "$RUN/ode-fast"
```

每模型的恢复演练比较 2000 步连续输出与 100、300、1000、2000 步的多进程执行。另在未提交的第 200 步注入退出，拒绝错链请求，并复查恢复至既有边界时零新增转移。比较实存的轨迹、梯度、诊断、适应参数与消耗的随机 key 字节。SQLite 文件摘要用于确认各自文件完整性，两路科学内容逐字段比较。

## 当前实测

- 8 个开发域高斯条件复算同维度下四档行数的充分统计量、密度差和梯度。解析设计矩阵使用离散余弦基，似然仍以稠密矩阵计算。未生成 32 维整组留出输入。
- 130 维 logistic 在 9 个测试点对照独立充分统计量、解析梯度和 Hessian–向量积。另验算 128 组等权概率，对 Beta(9,8) 后验均值做求积与 4 条合成链核对。
- 两种 ODE 负荷各 21 点、每点 3 个方向。采样的一阶梯度用 Diffrax 反向模式，二阶核验使用 DirectAdjoint，与 SciPy DOP853 的独立灵敏度方程及五点方向差分对照。另核对平衡态、时间缩放、末年状态与限步失败隔离。
- 分层 logistic 的十条合成链各保留 1000 步，作为 R 诊断与精度验收入口的联调。R 4.6.0 / posterior 1.7.0 检查通过。三个函数相对 MCSE 分别为 1.66%、1.63%、1.17%，概率的绝对 MCSE 为 0.000127。此批合成链共享零向量起点，预热和采样随机流逐链独立。正式分层起点仍依冻结清单。
- 清单生成器只生成条件与任务量，验证 180 个主比较格、36 个预定推荐格、两条联合推荐格、25,856 次主比较和 27,494 次固定项目合计，供后续 Windows 任务清单生成。

合成时间/损失数据通过 31/32 配对覆盖、1.10 速度下限、完整率描述和参考值双端点的分支检验。

两模型的 SQLite 恢复验收通过。2000 步连续组与恢复组的逐字段数组相同。两模型各有 5 次预热发散，保留阶段均为 0 次。快动力学 ODE 保留阶段命中最大深度 2 次。ODE 连续运行含 1024 步预热与 2000 个保留步，实测 260.9 秒，进程峰值 489.3 MiB。logistic 同口径为 0.99 秒、291.9 MiB。该单链合成证据可用于 Mac 机械复盘与参考成本测算，正式后验的收敛和精度须另行验收。

本地原始回执位于项目根目录的 `output/mac-reference-qualification.28JwoF/`。

`SHA256SUMS` 记录用于本阶段验收的原始报告、日志与数据库摘要。执行快照的源码摘要也写入各链的 SQLite 身份记录。
