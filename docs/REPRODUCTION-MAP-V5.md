# v5正文、证据与重建命令映射

身份submission-v5-rc1，2026-10-12。旧41组件完整保留，新增paper-v5与v5-R-technical，共43组件。组件字节数、SHA及获取状态以`execution/submission-v5-rc1/COMPONENTS.json`为准。原数据访问许可未改变。

| 论文对象 | 证据/身份 | 本版重建入口 |
|---|---|---|
| 正文16页，补充A47页、B67页 | paper-v5，原v5 TeX/图文输入216文件 | 包内BUILD.py；三PDF逐页文本/像素对照 |
| 正文方法/核验，约5445万MH转移、零接受失配 | compact-formal等21原组件；执行3a37a89、交付94bebec | 原COMPACT-REPRODUCTION流程；本候选继承已完成的原完整重放，不启动新网格 |
| 主实验表图，九目标36函数及失败 | mac-final，3888+256保存分析 | v4完整表图/重聚合验收保留；源码/组件相同，旧失败不替换 |
| 费用分解、三边界表，正文5.2 | compact-formal的216份W1阶段记录，mac-final的W1统计，源码cache.csv | review5_evidence.py；阶段和闭合，四缓存输入只作描述性对照 |
| L1尾ESS差异，正文5.4及补充A | 原重复21的两fit.npz与原Mac统计 | review5_evidence.py导出二进制，review5_diagnostics.R重算；原两值保留 |
| 误差—成本图 | mac-final原统计，72保存点和区间 | plot_review5_error_cost.py，仅展示编码改变 |
| Picard前缀示意图 | 概念图，无经验样本 | plot_review5_schematic.py |
| R完整使用示例，正文3.2 | v5-R-technical，4既有技术调用/1采样前环境停止 | export_saved_v5.R、audit_v5_saved_api.py；3旧完成路径重放，1旧失败排除，最终20诊断数值重算 |
| 历史CPU、首轮Windows、机制、SBC | 原cpu-*、windows-*组件 | 原版本和原复现软件保留；不同实验身份不合并独立重复 |
| H1函数差、L2重要性参考、W1数值区间、NUTS有限定位 | 原h1-companion/l2-reference/w1-reference/nuts-localization | 继承v4固定协议、完整证据及已完成核对；本轮没有新积分或随机参考点 |

## 字段及单位

- 正式独立单位是一份四链实际输入。原每格计划24份；链、同核执行副本、设备副本和缓存回放不增加独立n。新R示例不纳入主实验。
- `valid`指满足对应数值契约，仍需评估探索。`numerical_failure`和`output_failure_unclassified`保留轨迹/成本/分母。诊断`null`保留未定，不改为理想收敛。
- 预算1024/4096为每链保留步数。秒是墙钟时间；缓存、普通批量工作流、研究核验时间为嵌套口径，不相加。
- v5阶段CSV的`startup_gaps_exit`为普通总时间减四阶段的余量，含导入、间隙、日志及退出，不是单独测得的纯启动费。NUTS采样段含内部旧诊断。
- L1导出为little-endian float64；R技术导出为R列主序float64及uint8接受数组，JSON保存形状。原RDS在v5-R-technical组件内。恢复随机数组必须匹配原tape SHA，不能只比较整数seed。
- 参考类别、浮点阈值、所选函数、坐标和缺失区间规则全部沿用对应冻结身份。新展示不追溯修改原统计或将42失败晋升。

## 版本与访问

软件仍为Python0.2.0.dev2/R0.2.0.9002，17数值模块与原已安装候选逐字节一致；新代码限复现、运输与输出工具。版本详见`execution/submission-v5-rc1/VERSIONS.json`，候选最终commit/tag及传输哈希在外部SEAL.json。

first-party源码沿用MIT；第三方数据与软件使用其适用条款。Windows草稿与本地补充原件仍需作者落实访问。内部能读取这些组件不代表匿名审稿下载通过。
