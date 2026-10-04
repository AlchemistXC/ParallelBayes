# 主张与依据

项目路径以独立审查工作树 `/Users/haku/.codex/worktrees/windows-evidence-review/ParallelBayes` 为根。

| 主张/判断 | 依据 | 状态 |
|---|---|---|
| 原Mac审查修订已完成 | execution/cpu-revision-v1/WORK-PACKAGES.md | 已有运行证据 |
| Windows执行证据可核验，但推断可靠性仍受限 | docs/WINDOWS-RESULTS.md、docs/WINDOWS-RETURN-AUDIT.md | 已有运行及回传复核证据 |
| 两项二进制Rhat差异已在Mac复现为折叠中心末位敏感性，Windows运行时待回执 | docs/DIAGNOSTIC-MIDPOINT.md、completion-f1/mac-02 | 新伴随分析，不替换原诊断 |
| 512项映射/JVP/前缀计数均可由逐轮记录重建 | docs/WINDOWS-MECHANISM-ACCOUNTING.md、completion-f2 | 新事后描述性核算，不是因果分解 |
| 原计划Q3要求共同精度与资源分配评价 | outputs/researchwrite/parallel-r-package/exports/研究与开发计划.md §1、§8 | 原研究承诺，当前未充分回答 |
| 当前入口已统一并保留历史状态快照 | execution/CURRENT-SCOPE.json、COMPLETION-WORK-PACKAGES.md | F0本轮修订；最终发布整合未完成 |
| 常量链不能机械填成理想Rhat | https://mc-stan.org/posterior/reference/rhat.html （2026-10-05读取；在线文档1.7.1） | 官方文档；不升级实验所用1.7.0 |
| 若投JSS需软件源码及全部论文结果复现材料 | https://www.jstatsoft.org/about/submissions （2026-10-05读取） | 官方投稿要求，不是录用保证 |
| 下一轮采用有限补充实验并设停止条件 | 当前证据缺口、原计划Q1–Q3 | 本次建议，非已冻结协议或已得结果 |
| 独立调参216项均有终态，212完成、4项H1/MALA参考失配隔离 | docs/F3-TUNING.md、qa_logs/progress-check-2026-10-05.json、原始state/fit文件 | 860个任务资产哈希核对；未完成评分重建/原因分析，不是正式推断通过 |
| 最新优先级为失配审计→调参再分析→独立预算pilot→正式推断→复现和论文 | docs/RESEARCH-COMPLETION-PLAN.md最新进度段 | 更新执行顺序，不改冻结协议或历史结果 |
| F3调参评分、诊断及失败机制伴随分析已完成，正式推断仍未完成 | docs/F3-TUNING-RESULTS.md、benchmark/analysis/outputs/inference-tuning-v1 | 212份评分/R回写；24576同前态转移零接受失配；一ULP敏感性；失败不改标 |
| 独立预算pilot提供正式预算/重复设计资料，不能直接作正式推断结论 | docs/F3-BUDGET-PILOT-RESULTS.md、inference-budget-pilot-v1摘要与原始数组 | 323/324有效；单项路径容差失败、H1发散和未判定函数保留；Windows正式比较仍未完成 |
| 预算单项长路径失败有有限数值敏感性证据，原失败仍隔离 | docs/BUDGET-PATH-LOCALIZATION.md、budget-failure-localization-v1 | 18432同前态、实际首差受控后续重放；初值ULP阴性探针保留，非一般正确性证明 |
| 九目标CPU NUTS顺序/spawn可核验，Windows不能由Mac代替 | docs/NATIVE-NUTS-READINESS.md、nuts-native-readiness-v1 | Mac54项数组字节和18份R回写；Windows仅冻结协议，正式推断仍未完成 |
