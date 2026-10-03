# 软件研究稿的主张与证据定位

CPU主实验采用0.1.0／protocol-v1；发布候选与正式SBC采用0.1.1。原生Windows GPU后端尚未实现且不属于本轮范围。

| 正文主张 | 证据来源 | 主要位置与边界 |
|---|---|---|
| 目标、变换和路径核验可执行 | `execution/logs/python-reviewed-stage.xml`、`r-reviewed-check.txt`、`r-stan-end-to-end.json` | 验证节；有限测试，不是一般证明 |
| 正式任务完整且没有事后删组 | `benchmark/protocols/protocol-v1.json`、全部`state.json`、`analysis-provenance.json` | 设计节、结果开头；独立单位为24次重复，不是全部配对任务数 |
| 同核执行的成本收益 | `paired-speedups.json/csv` | 成对成本图；缓存重放不计为统计重复，失败配对保留在任务表 |
| 给定配置后的函数精度与成本 | `formal-summary.json`、`run-metrics.json` | 误差表、误差—成本图；只涉及预声明函数和两个预算，不是自动停止或算法最优排名 |
| L2参考精度未确定 | `reference-summary.json`及来源、参考原始样本 | 方法、表注、结果边界；不删掉全零符号函数，不把零经验方差写成零误差 |
| 数值成功与诊断问题不同 | 逐任务`diagnostics`、发散/积分上限计数 | 结果；有限样本输出仍可能有发散或探索不足 |
| 正式SBC及依赖数据测试量 | `statistical-v4`、`sbc-functions-v1`、`execution/statistical-v4/` | 生成式验证；有限功效、相关秩、并列处理，不宣称一般校准通过 |
| CPU范围及能力边界 | `docs/CAPABILITIES.md`和源码capabilities | Stan仅顺序RWM/MALA；JAX为明确目标，GPU未实现 |

结果分配：核心证据为完整成本与共同函数误差；实现检查作为必要支持；参考问题、发散和版本差异作为正文限定。逐任务成本、每函数误差、秩直方图和原始随机数组保留在机器可读材料，不逐条抄入正文。

论证顺序：定义同一计算对象 → 验证实现 → 固定比较任务 → 展示执行成本 → 展示推断误差及失败边界 → 限定硬件与应用外推。

编辑记录：用实际生成结果替代占位段落；计时口径集中在方法节，图注只提供读图所需定义；参考全零问题在方法说明其原因，在结果限制精度判断，在图表用符号标记。重复出现承担不同功能，不增加新的首次或性能优越性声明。

审查后证据：64组解析SBC配对见sbc-analytic.json；1928拟合现代诊断见output/cpu-revision/modern；72项机制任务见cpu-mechanism-v1及mechanism-summary.json；40组版本对照见version-replay/summary.json。所有补充均区别原预声明主协议，不为得到正结果改写原网格。独立复现见docs/PORTABLE-REPRODUCTION.md。
