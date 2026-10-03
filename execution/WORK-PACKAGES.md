# 执行登记

> 2026-10-03 后续硬件路线更新：用户不采用WSL2；未来台式机目标改为原生Windows 11＋RTX5080，拟新增PyTorch/CUDA后端。该后端尚未实现或验证；现有JAX/WSL交接包不适用原生Windows。当前仍仅进行Mac CPU工作，全部GPU任务继续暂缓。

> 2026-10-03 用户范围更新：当前仅执行本机 Mac CPU 工作；所有 GPU 环境检查、测试、探测、正式实验及回传任务暂缓，恢复须用户再次明确要求。GPU 不作为当前阶段完成条件，状态仍为未验证。既有源码、冻结协议、原始结果及交接归档保持不变。

2026-10-03。研究计划 v1.0；CPU 正式采样冻结在 0.1.0，当前本地发布候选为审查修订版 0.1.1。本机工作已完成；GPU 支持及结果等待台式机原始证据回传。

| 工作包 | 状态 | 产物、版本及验证 |
|---|---|---|
| WP00 | CPU 完成；GPU 暂缓（用户要求） | M4/16GB，environment/macos.json；R/Python 独立环境；33 项 Python 传递依赖锁、15 项 CUDA 候选锁、renv.lock；上游源码固定提交及许可归档 |
| WP01 | CPU 完成 | G1/G2/L1/L2/T1；独立 NumPy 密度/解析梯度/顺序核；错误注入；Stan 三目标交叉核验 |
| WP02 | CPU 完成；GPU 暂缓（用户要求） | 固定上游 quasi-DEER 复现与窗口适配；残差、接受事件、停止、修复、失败及回退记录；数值核验不称位级证明 |
| WP03 | CPU 完成；GPU 暂缓（用户要求） | 依据论文独立实现 Online Picard；批处理/确认前缀；固定随机输入和回退测试；实际 GPU 执行仍需实机证据 |
| WP04 | 完成 | 192 项 CPU 开发探测，0 输出失败；12 组生成数据×5工作流=60次开发拟合；正式 SBC 另用64组新数据、独立种子 |
| WP05 | CPU 完成 | 0.1.1：58 项 Python 测试通过，R CMD check Status: OK；安装后的高斯和 logistic R/JAX 示例、R→BridgeStan→posterior 示例通过；成熟 NUTS 为 BlackJAX；无需 CmdStan |
| WP06 | 协议冻结 | CPU protocol-v1：8目标×5工作流×2预算×24重复；独立参考8拟合；statistical-v4：64新数据集；拟合前冻结 sbc-functions-v1 伴随分析；GPU protocol-v3 |
| WP07 | CPU 完成；GPU 暂缓（用户要求） | 1920/1920正式任务、320/320正式SBC拟合完成，0输出失败；全部原始数组/状态/校验和保留；80组及768个配对比较从原始输出重建通过 |
| WP08 | 可选，未实现 | 不提出自动配置或模型外泛化声明；后续须新增未见模型族 |
| WP09 | CPU审查修订完成；GPU不在范围 | R 0.1.1 源码包；17页中文软件论文PDF/LaTeX；5幅矢量图；安装与重建说明；GPU 0.1.1-rc2交接包；旧综述独立保留；无公共发布 |

## 验证证据

- `execution/logs/python-reviewed-release.xml`：58 项通过；`r-reviewed-check.txt`：Status: OK；`r-release-install.txt`：安装通过。
- `execution/logs/r-release-quickstart.txt`、`r-release-logistic-paired.txt`：安装后示例通过。logistic 目标梯度差 1.07e-14，配对路径最大差 3.59e-10；短示例不用于收敛声明。
- `execution/logs/r-stan-end-to-end.json`：R→BridgeStan→posterior，固定输入样本差0。
- `execution/final-evidence-audit.json`：原始输出重建的数值摘要逐字节一致；任务网格、成本、配对比、参考未确定标记及SBC算术均核对。
- `execution/logs/software-paper-compile.json`、`output/software-paper/qa/QA.md`：初版Tectonic 编译13页，逐页视觉检查完成；图件检查见 `figures/software/qa/QA.md`。
- `execution/source-snapshots/release-0.1.1.json` 保存源码版本、历史补丁；CPU旧版本结果没有覆盖。

## 实测结论与边界

CPU 所有模型—预算组的中位数均未获得时间并行加速。缓存执行速度比（顺序/并行）范围：quasi-DEER 0.0192–0.174，Picard 0.0503–0.809；完整工作流比为0.0715–0.739和0.226–0.814。个别重复不受这条组中位数结论约束。最大独立数值路径差2.36e-8，接受事件失配0。

输出有效不代表探索充分：NUTS在46个有限输出任务中共有2358个保留转移发散，另有6861个保留转移达到积分步数上限，全部保留。L2符号事件在262144个参考样本中全零，参考精度保持未确定，不宣布全部函数达标。正式SBC覆盖率点估计低于90%，其二项区间均包含90%；不能证明校准，也不能据此认定系统性覆盖不足。

## 恢复与交接

GPU交接为历史归档，当前不执行。原生Windows GPU后端未实现，当前工作不等待回传。

恢复以冻结协议、源码指纹和状态文件为准。校验和匹配的已结束任务自动跳过，失败不自动重跑；中断后的新尝试保留旧记录。兼容性修复留补丁并核验，科学变更须新协议。

独立审查见 `review/software-implementation-2026-10-03/` 的三份冻结报告及综合。历史日志保留，包括已修复的R示例解释器符号链接问题；最终成功日志另存。未通过的历史尝试不删去。

## CPU审查修订 cpu-review-v1

见 `execution/cpu-revision-v1/WORK-PACKAGES.md` 与 `docs/CPU-REVIEW-REVISION.md`。新增72项CPU机制任务、1928拟合现代诊断、64数据集解析SBC配对、40组版本衔接与独立环境重建；原1920任务及0.1.1内核指纹不变。论文改为17页、5图，范围仅单机CPU。独立复现归档在output/reproduction，校验另登记。
