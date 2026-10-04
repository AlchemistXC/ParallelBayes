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
| F3伴随归档可异目录重建，不代表全论文复现 | nuts-native-readiness-v1/archive-receipt.json、rebuild/receipt.json | 240文件哈希；18份R诊断与8份后续递推数组一致；同Mac现有环境，新增拟合0 |
| 已选MH及仿射目标的Mac短路径时间执行组合已核验，Windows待实测 | docs/SELECTED-MH-READINESS.md、selected-mh-readiness-v1 | 54工作流/36配对、独立重放及恢复；H1全拒绝与slogdet警告保留，不是正式推断 |

| 正式重复草案128不依赖“pilot上限246所以充分”的错误推论 | formal-design-planning-v0.1/planning.json；F3-FORMAL-DESIGN-DRAFT.md | 非负数CV解析上界、六规模资源/区间计算；设计决定，不是正式证据 |
| 新输入保持前缀、避免旧目标×100地址重叠，并兼容uint32 NUTS | formal_inputs.py；新增2项行为检查；46,080地址/键及9,216种子检查 | 有限集合核验，不是随机独立性证明或正式输入包 |
| 未定L2事件不能报告零误差 | formal_error_summary.py；3项契约检查；unresolved-reference-companion.json | 九行保存估计伴随纠正；历史文件保持不变，新增拟合0 |
| 原全缓存分析器不适合正式全网格 | formal_design_planning.py；analyze_budget_pilot.py保存路径逻辑 | 输入23.78GiB、最新前缀路径104.06GiB；新流式分析未实现 |
| 共享完整重复索引的损失/成本区间可重建，并保留缺失和失败条件 | FORMAL-UNCERTAINTY.md；formal-uncertainty-v1；SciPy公开bootstrap对照 | 4项新接口检查；315个旧合格点误差差0；四重复全部无BCa区间。非正式推断或覆盖率证明 |

| Mac运行器有限实测支持任务封存与恢复，不支持正式实验已就绪声明 | FORMAL-RUNTIME-TECHNICAL.md；formal-runtime-technical-v1；采样67547a3／核验8e502a1 | 10任务、4配对、10R回写；196文件恢复不变；人工内存保护和3行为测试；29个有限Rhat>1.01保留。Windows及中断恢复未验证 |

| 原始预算证据可以逐任务重建，结果与旧分析保持一致 | STREAMING-ANALYSIS.md；streaming-budget-v1；分析8f3c47c／核验ceb2635 | 323估计／R二进制、1,292诊断行、215前缀、45报告一致；新增拟合0。已有pilot格式通过，不是正式最大规模、Windows或干净安装验收 |

| 显式恢复在已测试Mac场景保留原输入、失败记录与全部已知尝试成本 | FORMAL-RECOVERY.md；formal-recovery-v2；d9890b8／d589678 | 7行为检查；真实MALA四数组字节一致，20原文件不变；未知耗时不补零。非全局调度器、Windows或任意崩溃恢复证明 |

| 共享登记在已测试Mac场景阻止遗留进程与其他输出目录重叠，并保留一次恢复的尝试成本 | FORMAL-COORDINATOR.md；formal-coordinator-v1；6d686de | 新增5行为检查/受影响7检查；实际3工作流、1配对/2MH审计/3R回写；恢复62文件不变。有限Mac配置，非全局OS排他、Windows或任意崩溃恢复保证 |

| 登记尝试和原始数组可在搬迁后的只读证据中连接到函数及完整重复分析 | FORMAL-RUNTIME-ANALYSIS.md；runtime-analysis-v1；872d5d0/22a3b9e | 新增4/相关5检查；三份均值/成本/二进制和10行诊断一致，6个有限Rhat>1.01保留；新拟合0。有限格式验证，不是正式网格、Windows或区间覆盖率证明 |
