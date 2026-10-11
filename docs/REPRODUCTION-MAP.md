# 论文结论与证据组件、重建入口

| 内容 | 组件/来源 | 重建与核验 |
|---|---|---|
| 当前正文18页、SI45页、原完整结果附录67页 | paper-v4、固定源码 | TeX包全部依赖；编译与科学统计分开 |
| 历史Mac1920任务、解析SBC | cpu-software/experiments/evidence-paper | 归档reproduce.py及docs/REBUILD-RESULTS.md历史部分；0.1.0/0.1.1界线保留 |
| 首轮Windows512工作流及后继机制 | windows-first、windows-round2、windows-mechanism | 原冻结源、全数组及报告；独立样本数不按软件/设备复制增加 |
| Native运行/安装/适配检查 | windows-runtime及补充、windows-package及补充、windows-adapter-v2及伴随/运输 | 仅验收软件，不作为新增正式后验重复 |
| 主要3888+256记录、调参、成本及全部失败 | compact-* 21组件及compact-catalog | 冻结执行3a37a89、交付94bebec；逐块接收；formal_analyze/formal_statistics |
| 九目标36函数、45图、72组成本、R使用费用 | mac-final | 完整原件的独立Mac统计；rebuild_submission.py重建全部保存统计；R64次保存调用另核对 |
| H1函数误差与旧路径标准 | h1-companion及compact-formal旧数组 | 80旧任务，不晋升原失败；report_h1_function_paths.py |
| L2稀有概率 | l2-reference | 两固定提议/各八批；audit_l2_importance.py、report_l2_importance.py；近似MCSE不是包络 |
| W1七函数确定数值包络 | w1-reference及mac-final统计 | audit_w1_enclosure.py对全部保存单元、有理端点及敏感性重建；不等于再次认证全部导数/尾界代码 |
| NUTS有限资源定位 | nuts-localization、固定源码与小型重建依据 | scripts/analysis/audit_nuts_return.py及docs/WINDOWS-NUTS-MAC-REVIEW.md；105原故障未全部确定 |
| v4稀有事件说明与公开API | 当前源码/小型证据 | review3_numerics.py重建；examples/paper-api.R短例不并入正式网格 |

## 数据字典

- 独立实验单位是24份四链实际输入中的一次；链、设备副本、顺序/并行配对和缓存重放不增加独立n。
- `main`为主任务，`cache`为准备后执行探测。缓存256项/1024调用不是后验统计重复。
- 状态`valid`仅指通过对应数值契约；`numerical_failure`保留候选轨迹；`output_failure_unclassified`表示未取得完整合格输出，不能填入正常样本。
- `null`或未定诊断表示没有可解释的有限值，不能改为Rhat=1、ESS=0或零参考误差。失败分母使用全部计划重复。
- 原始噪声、log-uniform、导数探针和接受事件随各任务保存；恢复按实际数组及来源SHA验证，不重新从整数seed猜测原输入。
- 参数坐标、约束映射、函数、尺度见正文及SI。H1/H2为不同坐标；G2/A1白化后几何重合。预算1024/4096为保留步数，不包括丢弃/适配。
- 秒为墙钟成本；缓存、普通工作流、研究审计为不同口径。R前端补测与Windows主比较分开。成本未知保留未知，不作0。
- 主要CSV定义和原始契约以冻结协议/报告中的字段为准。新的入口文件不更改原字段或旧协议。

## 许可和访问

源码MIT不自动覆盖posteriordb数据、第三方软件或全部生成数组。数据提供者与数据分享许可待作者确定；不附第三方论文全文、私有技能、环境目录、缓存或凭证。公开源代码并不等于可以匿名下载私有原数组。可用性声明中的具体入口须在作者确认后替换，不能凭本候选制造DOI或审稿链接。
