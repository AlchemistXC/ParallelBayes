# CPU审查修订结果（cpu-review-v1）

本轮按四个有限工作包收敛：范围/版本、既有结果再分析、72项CPU机制实验、可移植复现及论文改写。数值内核仍为0.1.1，源码SHA256为`d8cb2fc2bf950fbe6b47841f3feb449d553e5f2a7c78d140811c6b2f2ba51ec7`。原1920项主实验、负结果和协议不覆盖。GPU与选择器继续暂缓；原生WindowsGPU后端未实现。

## 主要修订与发现

| 审查问题 | 已完成工作 | 结果与边界 |
|---|---|---|
| Stan入口是否能时间并行 | 软件说明、摘要、支持表和架构图统一 | Stan仅CPU顺序RWM/MALA；时间并行要求明确实现的原生JAX目标 |
| 0.1.0与0.1.1衔接 | 40组原输入新旧源码独立调用、保存原始输出 | 最大路径差1.99e-13，事件零失配；不能据此视性能相同 |
| SBC覆盖偏低 | 同64组数据的解析区间及配对端点/后验矩分析 | 解析覆盖54/64；MALA/RWM/NUTS分别有4/3/3个数据集覆盖判断分歧，不能只比总百分比 |
| NUTS总诊断缺少定位 | 全1920任务及8次参考拟合补充posterior现代Rhat/bulk ESS/tail ESS | 2358发散、6861上限命中全部在H1；M1无发散但最大Rhat约1.73；L2常量符号仍不可判定 |
| 审计是否造成全部减速 | 缓存、正常内存口径估计、研究审计三列；新增直接audit=False测量 | 去独立审计后的历史估计仍无组中位加速；正常估计不含未分离的建模/R转换/写盘，非完整实测工作流 |
| 重复工作为何抵消批处理 | 新协议3目标×2链数×2窗口×2核×3随机数组=72项任务 | 全完成，所有组中位缓存速度比<1；固定状态批量吞吐组中位最高2.46，前向工作2–45.5次/输出转移，JVP另列 |
| 软件能否扩展 | 完整Poisson目标Python/R示例 | 密度/梯度差约2.84e-14，MH事件零失配；公开Python Model入口，非任意R闭包注册 |
| 是否可独立核验 | 新依赖环境、非editable安装、迁移目录、独立重建 | 58项Python测试通过（57初次＋1补齐测试依赖后）；R显式3项集成测试15断言通过；主摘要逐字节重建 |

机制举例：G1四链Picard从W16增到W64，首链平均确认推进的组中位保持约5.57步/轮，前向工作由5.50增到20.88次/转移，缓存速度比从0.402降到0.170。更宽窗口没有增加确认推进，却增加了重复工作。G2单链quasi-DEER平均每窗口轮数11→22.25，速度比0.051→0.027。它们是有限网格内的观测，不是CPU普遍不适用的结论。

分段回放记录批量求值/JVP、扫描、事件复核、控制及其他成本。分段插入同步/Python控制，测得控制部分很高；这暴露探针扰动，不能当作融合生产程序的精确瓶颈分解。生产缓存计时与分段探针分开，保存每轮残差/确认前缀及全部原始随机数组。没有为获得正加速重新挑选配置。

## 可查证入口

- 范围：`docs/CAPABILITIES.md`、`docs/VERSION-BRIDGE.md`。
- 扩展：`examples/custom-poisson-target.py`、`.R`、`docs/EXTENDING-TARGETS.md`。
- 解析SBC：`output/cpu-revision/sbc-analytic.json`，含逐数据集分歧、端点、均值及标准差误差。
- 现代诊断：`output/cpu-revision/modern/`、`grouped-diagnostics.json`、`nuts-by-model-budget.csv`、`reference-modern.json`。
- 成本：`output/cpu-revision/cost-tiers.json`；机制：`mechanism-summary.json`、`mechanism-groups.csv`。
- 新实验：`benchmark/protocols/cpu-mechanism-v1.json`；原始记录：`execution/cpu-revision-v1/cpu-mechanism-v1/`。
- 验证日志：`execution/cpu-revision-v1/relocated-check.log`、`relocated-repair.log`、`r-integration-explicit.log`、`relocated-rebuild.log`；R包检查：`execution/logs/r-reviewed-check.txt`。
- 论文：`manuscript/software/软件与基准研究.tex`及两个generated.tex，PDF：`output/software-paper/软件与基准研究.pdf`。
- 三个独立归档及整体SHA256：`output/reproduction/`；使用：`docs/PORTABLE-REPRODUCTION.md`。

本轮“独立环境”仍在同一Mac上，共享OS、R库和编译器；不声称已由外部团队或另一硬件平台复现。昂贵似然/真实应用、分散初始化、生产XLA精确剖面尚未完成。论文为CPU审查修订稿，尚非投稿终稿；署名与维护者信息仍待研究者确认。原综述保持独立。

归档验收：在新临时目录完整解压三个包，根目录verify、analysis、diagnostics、figures、paper五阶段全部exit_code=0。1928项现代诊断强制重算，排除诊断耗时后逐项一致；不是仅重画已生成图片。最终归档校验与候选科学输入一致性见output/reproduction/validation.json。
