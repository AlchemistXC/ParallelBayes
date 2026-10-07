# Windows 研究收尾入口

2026-10-06。当前统一开发入口为 `codex/research-integration`，合入软件候选、测量运行器与失败证据接收。原来源分支及冻结实验均保留；F2 使用其原源码，F3/安装核验在新工作树继续。只使用原生 Windows，不重启第一次移植。

**2026-10-07：F2续跑、原生运行器技术批次、候选安装三项已完成并经Mac独立接收，不要重复执行旧提示词。** 三条结果分支已合入`codex/research-integration`，见[后续接收报告](../../docs/WINDOWS-FOLLOWUP-INTAKE.md)。当前新入口为[有限 v2 原生适配验收](CODEX-PROMPT-FORMAL-VALIDATION.md)：一次全文提供，依次准备、行为测试、27主任务/24缓存、零重算、封存和回传。它尚待Windows实测，未授权从该入口启动正式全网格。Mac继续完整原始结果分析。下方入口与原门槛为历史索引，不改变已完成状态。

以下是原执行入口的保留索引：

1. [F1 诊断最小复现](CODEX-PROMPT.md)：固定二进制输入、R版本和两项Rhat差异核验，无新采样。
2. [F2 机制与 F4 水井](CODEX-PROMPT-F2-F4.md)：按各自已冻结协议执行；水井目标/R接口、CPU/CUDA核验和192工作流机制pilot，保留负结果。
3. [F3 原生 CPU NUTS](CODEX-PROMPT-F3-NUTS.md)：核验九目标串行／四进程、保存数组、R回写及恢复。
4. [F3 已选 MH 组合](CODEX-PROMPT-F3-MH.md)：九目标、已选步长／仿射坐标的CPU/CUDA顺序与时间执行核验；不代替正式长路径逐条审计。

各项回执包括完整原始输出、终态、环境、源提交和哈希，推送开发分支后由Mac独立接收。某项失败按提示词保存、定位并继续其他独立项；不提升为通过，不改变冻结科学参数。测试次数按实际不同检查报告，技术重放不扩充独立统计重复数。

[正式推断设计草案v0.1](../../docs/F3-FORMAL-DESIGN-DRAFT.md)暂定九目标×四预算×九工作流×128次四链重复，共41,472拟合；它**尚未冻结，也没有正式执行命令**。不要将现有pilot直接扩为该网格。运行器已有Mac两目标十任务、合作主机锁、恢复完整性和人工内存保护的有限实测，见FORMAL-RUNTIME-TECHNICAL；已有324项预算pilot的原始数组逐任务重建及配对分析衔接通过（STREAMING-ANALYSIS）；Mac显式单任务中断恢复和全部尝试成本已有限核验（FORMAL-RECOVERY）；共享登记/遗留进程及尝试成本已在有限Mac配置中接入并核验（FORMAL-COORDINATOR）；runtime-v1登记到搬迁归档/有界数组/配对摘要已作有限Mac核验（FORMAL-RUNTIME-ANALYSIS）；原生Windows进程集合与恢复、正式批次驱动/冻结后完整格式验收、三种成本的独立测量及Windows最大任务／资源保护仍未完成。不得在Windows套用Mac进程组实现。Mac实测不代表Windows通过。实际磁盘／内存情况由Windows端记录，主要未压缩数组374.35GiB只是规划值，不能当作足够空间保证。

全部研究完成条件在[总计划](../../docs/RESEARCH-COMPLETION-PLAN.md)与[工作包登记](../../execution/COMPLETION-WORK-PACKAGES.md)。机制回执及运行门槛齐备后仍需正式推断、两平台干净安装、归档到表图/PDF的完整重建及作者终审。无需为本篇新增GPU NUTS、通用Stan转译或自动选择器。


Mac后续计时验证：`docs/MEASURED-WORKFLOW.md`记录独立普通子进程和外层审计调用的五工作流实测、候选隔离及归档重建。它不是Windows验收；Windows后续应维持同样明确的计时边界，并单独核验原生进程生命周期。缓存执行、失败/恢复外层完整成本和正式规模仍待完成，不得将单次技术重放作为新的独立统计重复。


Mac后继：`docs/CACHED-AND-RECOVERY-COSTS.md`给出固定设备输入的原MH执行器计时，以及记录run/retry/拒绝/零重算调用的外层账本。科学源码和原协议未改；`MeasuredCoordinator`依赖当前仅Mac验收的TaskCoordinator，不能直接把Windows调用标为通过。Windows需原生进程/恢复验证及最大任务实测。MALA exit7工作程序为明确人工故障夹具，不得用于正式研究；缓存重放不增加独立统计n。

Mac批次后继：[最大形状/搬移归档报告](../../docs/BATCH-MAXIMUM-VALIDATION.md)14项合格，最大NUTS原调用及唯一重试中断保留，未做第三次尝试；不能替代Windows验收。

Mac 测量任务的有限原生管理验收见 [OWNED-CACHE-RUNTIME](../../docs/OWNED-CACHE-RUNTIME.md)。F3 提示词已纳入产物资格和独立的24项缓存技术探测；不修改正在运行的 Windows 协议。顺序仍为 F2 续跑封存 → F3 原生管理/有限技术批次 → [独立候选安装](CODEX-PROMPT-PACKAGE.md)。最后一项使用统一分支的安装材料；不得改动正在执行的冻结实验工作树。
