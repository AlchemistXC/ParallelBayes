# 软件研究稿的主张与证据定位

2026-10-05整合稿。历史CPU主实验0.1.0/protocol-v1；CPU修订/SBC为0.1.1；原生Windows0.2.0.dev1使用独立协议。数字只能在其所属设计与计时边界内解释。

| 主张 | 可定位证据 | 正文范围和限制 |
|---|---|---|
| 当前支持组合 | docs/CAPABILITIES.md；各后端sampling.capabilities；r-package/R/interface.R；独立completion NUTS CLI | Stan仅CPU顺序，torch NUTS不能由pb_sample通用调用；GPU NUTS未接入 |
| CPU1920任务、成对执行负结果 | protocol-v1.json；results.generated.tex及write-results-tex.py的原始摘要 | 24次完整四链重复/格；两个预算；不推断精确达标时间或CPU普遍无收益 |
| L2参考未定、NUTS发散和探索不足 | 原formal/reference-summary、run-metrics、revision.generated.tex及生成器 | 保留符号事件，区分特定函数误差与后验可靠探索 |
| 64组SBC解析配对、现代诊断 | revision.generated.tex；CPU修订sbc-analytic/modern分析 | 同64组数据，解析覆盖54/64；不能计作五组独立证据 |
| CPU72项机制与40项版本对照 | cpu-mechanism-v1；version-replay；docs/CPU-REVIEW-REVISION.md | 分段测量有同步扰动，不等于生产剖面；数值一致不证明性能等价 |
| Windows512任务及CUDA缓存速度区间 | windows-native-v1.json；windows-native.generated.tex；docs/WINDOWS-RESULTS.md | 每格4份数组；Picard1.097–5.230、quasi-DEER0.164–0.505为组中位数范围，不是置信区间；A1全拒绝及短链诊断同时呈现 |
| F1折叠中心机制有实际Windows回执 | completion-f1/windows-01/result.json；同Mac固定样例；write_completion_tex.py | 改变中心使5秩变动；两种Rhat均不良，未证明底层库根因 |
| 跨系统MH108路径/事件通过，但60变换逐位失败 | windows-round2-intake-v1/summary.json；independent-receipt-v2及原Mac审计false | 原严格失败保留，不将8.88e-15描述量改为通过容差 |
| CPU NUTS九目标串行/spawn数组及原二进制R诊断 | 同接收summary：54数组对、18传输、72函数行；原始948文件归档 | 技术配对，不增加n；坏诊断和34未判定条目保留 |
| F2原输入补传后192个机制工作流完成 | windows-followup-intake-v1；mechanism-windows-pilot-v1/windows-20261006；followup.generated.tex | 原82/49152差异和启动失败保留；960份路径零事件失配；每模型仅2输入，缓存重放不扩充n |
| 全部机制配置与等输出链数对照 | 同目录两端workflows.csv；write_followup_tex.py | 额外映射/JVP不是等价FLOPs；8个等512输出对照的路径长度不同，不能解释为推断优势 |
| 水井扩展目标成立 | docs/WELLS-TARGET-VALIDATION.md、WELLS-REFERENCE-AUDIT.md、WELLS-QUADRATURE.md；models/external/wells/source-manifest.json | 保留平坦先验及可积性依据；目标/接口与充分推断区分；罕见事件参考未认证 |
| 成本与函数可用集一致的分析接口 | docs/FORMAL-COST-POLICY.md；formal-cost-policy-v1；formal_cost_policy.py | 已测任务/人工样例核验，不是正式研究；未知成本不填零；技术批次n=1不画统计区间 |
| 封存Windows运行器的最大形状/恢复已测 | docs/WINDOWS-FOLLOWUP-INTAKE.md；windows-followup-intake-v1/runtime | 27主任务和24缓存探测/96调用；有限技术批次，后续适配器验收与正式实验另行进行 |
| Windows新环境候选安装 | docs/WINDOWS-PACKAGE-CANDIDATE.md；同接收comparison-summary | CPU/CUDA MH与R入口核验；不包括Windows JAX/Stan、GPU NUTS或第三方全研究复现 |
| 可用性 | README.md；各归档manifest与Release状态 | CPU公开；Windows草稿及部分本机大归档不自动公开；克隆不足以完整复现全部结果 |

## 编辑与证据分配记录

摘要从单纯CPU里程碑改为跨协议共同问题，只保留关键执行结果及推断边界；不将两个平台合成排名。旧architecture图保留，新architecture-current图仅展示当前路线，无数值结果。历史CPU/results、revision和Windows首轮generated输入保持原字节；completion伴随文本只更新已有Windows F1回执，新增intake.generated.tex从只读接收摘要产生。

引言、能力矩阵、限制和可用性对应当前实现；术语和计时口径集中解释。旧版本实际证据按原身份保留，不把前瞻BCa/成本规则追溯套到已发表述的历史统计量。详见本轮docs/MANUSCRIPT-INTEGRATION.md的构建回执与输入哈希。

## 2026-10-06相关工作校正

见[定向检索与引用复核](../../review/文献定位复核_2026-10-06.md)。ParallelMCMC.jl/BayesForge只支持既有软件功能的定位，不提供本项目性能证据；MEADS/LAPS/FSM用于界定未比较方法。BridgeStan正式论文及PPL Bench预印本作者已核对，posteriordb原正式引用不变。核心贡献、历史数值及正式研究未完成状态不变。

## 2026-10-07 实测机制与安装整合

参见docs/WINDOWS-FOLLOWUP-MANUSCRIPT.md。用后继followup生成段替代当前稿过时状态，不覆盖历史completion/intake文本及生成器。新增120配置全量表图、8个等总输出技术对照和有限运行/安装边界。正文增加1161汉字（扩展TeX、去注释，含图注/参考文献），主要用于结果与解释；版本、命令和归档详情留在仓库文档。新增采样/正式重复为0；正式推断及投稿稿未完成。
