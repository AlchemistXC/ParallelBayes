# 紧凑方案的审查与验证

2026-10-08。按researchwrite与nature-statistics流程，先建立事实/证据/论证/节契约，再由统计与计算可行性两个独立只读代理复核。没有人类专家评审或新的采样结果。

## 已处理问题

- 保留CPU/CUDA配对和全部九模型；拒绝把CUDA MH与CPU NUTS对照称作同核执行实验。
- 缓存初稿的“available中位数”措辞已删除：初次和三次prepared必须全部通过完整路径/事件核验且计时齐全，否则该输入中位数和比值未定。n4只描述，不扩成12或16个独立重复。
- 旧采样已经开始，保全尚待回执；元数据将preservation_required与verified分开。新随机输入不能消除启动后修订的披露义务。
- 精确停止driver后登记对账/原生Job快照；旧Ctrl+C可能被吞，旧resume会采样。不声称Mac已停止Windows。
- 验收前绑定干净候选提交；正式冻结不能换源码。有限技术包先在Windows独立目录做接收模拟，Mac独立验收仍待后续。
- 空间51.46GiB是无压缩双副本条件账本；60–75GiB为建议预留。日志/失败/旧网格占用额外，50GiB两机总预算不能直接放行。

## 8项便携检查

[机器回执](../benchmark/designs/windows-compact-inference-v1/validation.json)记录：确定性重建、原目标/核/分析契约不变、全部配对与三批边界、独立任务身份及输入长度、无采样/虚假原生资格、独立聚合字节公式、全调用缓存资格、拒绝覆盖已有输出。8通过/0失败/0跳过；新增采样0，实际正式随机输入0，原生Windows测试0。不是新运行器通过证明。

复算设计/账本：`python scripts/analysis/plan_compact_study.py --output NEW_NONEXISTENT_DIRECTORY`。新设计schema刻意不同于旧正式执行schema；旧运行器拒绝它是正确行为，不能通过取消校验解决。

主代理内部写作自评8.25/10，仅用于内容完整性（问题9、张力8、证据9、逻辑9、方法7、贡献7、风险9、语言8），不作为科学/平台验收。尚需Windows停止证据、新版适配、有限差异验收、实际容量及正式结果，详见[新设计](F3-COMPACT-DESIGN-v1.md)。
