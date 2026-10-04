# 当前研究收尾登记

2026-10-05。用户已授权沿F0–F6持续推进；[执行依据](../docs/RESEARCH-COMPLETION-PLAN.md)。历史Mac、Windows-v1及回传审查证据保留，旧GPU暂缓或待开发措辞只属于历史记录。

| 工作包 | 当前状态 | 实际证据与下一门槛 |
|---|---|---|
| F0 状态与版本 | 当前入口已统一；最终发布整合留在F5 | CURRENT-SCOPE、README、能力矩阵及历史文件后继指针更新；稿件数据声明区分公开CPU Release和Windows草稿；旧scope有快照 |
| F1 诊断差异 | Mac数值机制已复现，待Windows实际回执 | 12KiB固定样例；一ULP折叠中心差改变5个秩，重现两种历史Rhat；`docs/DIAGNOSTIC-MIDPOINT.md`及`completion-f1/mac-02`；Windows提示词已准备 |
| F2 机制 | 已完成原512项的只读工作量核算；新小网格未冻结 | 所有映射/JVP/前缀及技术重放工作量核对通过；`docs/WINDOWS-MECHANISM-ACCOUNTING.md`；仍需独立控制窗口/链数与成本探针 |
| F3 推断比较 | 未完成 | 合格参考、独立调参试验、预算/重复精度设计、成熟基线及新冻结协议待完成；不沿用4重复短链宣称可靠推断加速 |
| F4 外部案例 | 未完成 | 选择有来源和参考的外部模型/数据，并完善torch/R可扩展示例 |
| F5 发布与复现 | 未完成 | 统一版本候选、两平台干净安装、原始证据到全部表图/PDF的完整重建、公开材料状态核对 |
| F6 论文 | 修正数据声明和新增伴随发现；整体重构未完成 | 新证据齐备后统一论证、文献更新、作者审阅、期刊/语言及复现材料准备；不自动投稿 |

## 本轮实际命令

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
