# 当前研究收尾登记

2026-10-05。用户已授权沿F0–F6持续推进；[执行依据](../docs/RESEARCH-COMPLETION-PLAN.md)。历史Mac、Windows-v1及回传审查证据保留，旧GPU暂缓或待开发措辞只属于历史记录。

| 工作包 | 当前状态 | 实际证据与下一门槛 |
|---|---|---|
| F0 状态与版本 | 当前入口已统一；最终发布整合留在F5 | CURRENT-SCOPE、README、能力矩阵及历史文件后继指针更新；稿件数据声明区分公开CPU Release和Windows草稿；旧scope有快照 |
| F1 诊断差异 | Mac数值机制已复现，待Windows实际回执 | 12KiB固定样例；一ULP折叠中心差改变5个秩，重现两种历史Rhat；`docs/DIAGNOSTIC-MIDPOINT.md`及`completion-f1/mac-02`；Windows提示词已准备 |
| F2 机制 | 已完成原512项的只读工作量核算；新小网格未冻结 | 所有映射/JVP/前缀及技术重放工作量核对通过；`docs/WINDOWS-MECHANISM-ACCOUNTING.md`；仍需独立控制窗口/链数与成本探针 |
| F3 推断比较 | 参考复用审计完成；正式比较未完成 | L1/L2目标完全一致，8次参考原始数组及均值/MCSE重建通过；L2事件仍未确定。独立调参、预算/重复设计、成熟基线与新协议待完成 |
| F4 外部案例 | 目标与Mac/R扩展核验通过；正式案例未完成 | wells模型的可积性、Stan/NumPy/torch密度梯度、两对轨迹及R逐字节传输通过；短链Rhat不利结果保留。有限参考复算与正式案例实验待完成，见docs/WELLS-TARGET-VALIDATION.md |
| F5 发布与复现 | 未完成 | 统一版本候选、两平台干净安装、原始证据到全部表图/PDF的完整重建、公开材料状态核对 |
| F6 论文 | 修正数据声明和新增伴随发现；整体重构未完成 | 新证据齐备后统一论证、文献更新、作者审阅、期刊/语言及复现材料准备；不自动投稿 |

## 首批伴随分析记录（F1/F2，水井目标开发之前）

从已校验的解压Windows证据`EVIDENCE`出发，写入全新独立输出`NEW_OUTPUT`：

```text
python scripts/completion/prepare_rhat_case.py --evidence EVIDENCE --output NEW_OUTPUT/rhat-case
python scripts/completion/run_rhat_case.py --case NEW_OUTPUT/rhat-case --output NEW_OUTPUT/rhat-mac --rscript Rscript
python scripts/completion/analyze_windows_mechanisms.py --evidence EVIDENCE --output NEW_OUTPUT/accounting
```

Mac解释器为原项目Python3.12/NumPy2.2.6；R4.6.0、posterior1.7.0。样例首次元数据JSON序列化失败已保存；第二次检查通过、读取/回写二进制字节一致。没有安装新依赖、运行新MCMC或改动39份冻结科学源码。

本轮接收端确认`windows-native-v1`仍为草稿（2026-10-05）；不自动公开。Windows实际执行、推断实验及最终发布复现未完成前，不将整体研究标为完成。

固定样例的精确中点、损坏输入拒绝、旧回执防覆盖和样例内写入拒绝四项测试通过（`tests/handoff/test_completion_fixture.py`；JUnit见`completion-f1/fixture-tests.xml`）。这些只检验新伴随工具，不扩充采样器测试通过计数。

伴随稿已编译为21页并检查新增第18–20页；旧20页回传稿单独保留。39份冻结科学源码与接收审查提交逐字节一致。新伴随核算、最小样例和文稿重建入口见`docs/COMPANION-REPRODUCTION.md`。

F3参考身份审计核查8次原始拟合；新增的改变先验/损坏来源/路径越界三项保护测试通过。F4在该来源选择阶段仅完成8个公开来源文件的固定版本与缓存校验，未扩充采样、速度或收敛证据。

## 后续F4目标核验

F4已新增3项手算行为检查，以及v1模型/轨迹与v2 R整批核验。首次R解释器选择失败已修复并保留；两个核验协议仅R兼容代码/协议命名不同，科学字段与实际输入字节一致。原Mac/Windows主实验及39份冻结科学源码未改。新数据只支持Mac CPU接口和数值核验；Picard示例Rhat约3.036/3.817，不支持收敛。

保存的8个工作流又经纯NumPy独立参考重放通过，R二进制传输一致；只有一份随机数组，不增加统计重复数。详细回执与复跑命令见水井核验报告。
