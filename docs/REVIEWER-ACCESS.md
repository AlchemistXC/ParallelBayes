# 审稿材料访问与受控交付

2026-10-11，v4修订。此文件说明实际材料与交付检查，不构成“外部审稿人已经取得全部原件”的声明。源码/协议/小型证据随研究分支提供；部分大原件仍在权限保护的草稿Release或作者本地。

## 三种独立交付

|材料|内容|实际状态与入口|
|---|---|---|
|软件与分析源码|R包、后端、独立参考、冻结协议、原数据入口、测试、W1球算术与有理累计代码|Git研究分支；固定提交用交付清单绑定。W1源码为scripts/analysis/wells_ball_target.py、verified_cubature.py、checkpoint_cubature.py及run/audit/report_w1_enclosure.py（以实际源码清单为准）|
|论文构建输入|主文、SI、所有input/图件及原67页结果构建材料|本地parallelbayes-targeted-paper-v4.tar；含SHA256清单。只重编译，不重算MCMC。|
|原始科学证据|历史CPU、紧凑Windows原数组/实际RNG、Mac派生统计、R技术原件、H1/L2/W1/NUTS补充|下表逐组件取得；私有草稿需要真实权限，不应向无权限读者展示为直接下载。|

## 必需组件

|组件|包/来源|完整性与重建入口|
|---|---|---|
|历史CPU|cpu-review-v1 Release的原分卷|docs/REBUILD-RESULTS.md及原SHA256清单|
|Windows紧凑正式原件|原草稿中的完整21组件/原始清单，不用成功摘要替代|docs/COMPACT-REPRODUCTION.md、COMPACT-RECONSTRUCTION-REVIEW.md|
|Mac完整统计/45图/源表及R原件|parallelbayes-mac-final-research-20261010.tar，原草稿|docs/RESEARCH-COMPLETION-REPORT.md与COMPACT-REPRODUCTION.md；不再次复制紧凑原数组|
|H1旧轨迹函数伴随|h1-function-path-companion-v1.tar，51,240,960字节，本地|SHA256 b752a879492a15bde59b0efe1cedbc1c8a3027ae36742b5b79058e76a6cb0ff2；docs/H1-FUNCTION-PATH-RESULTS.md|
|L2重要性参考全部点/权重|l2-rare-reference-is-v1.tar，187,627,520字节，本地|SHA256 14e57e7be0f4006534720a2375ed9fe753443a7b5a9195fb4062f0427a1cd8e5；docs/L2-RARE-REFERENCE-RESULTS.md|
|W1全部叶单元/尾界/球端点|w1-reference-evidence-v1.tar，303,360,000字节，本地|SHA256 c1bf12eb937ba57582647c7eb81cea21d01b6f204e1305d459cdc1175bd368d1；docs/W1-REFERENCE-RESULTS.md|
|S2 NUTS定位原件|windows-nuts-localization-v1.tar，703,969,280字节，原草稿；另有源码bundle和行政附件|SHA256 5fffe7f83783651ef58198aab4bad1bfb28be1d2244b9a0738c8f66fbdb88705；docs/WINDOWS-NUTS-MAC-REVIEW.md|
|v4解释与API例|benchmark/analysis/outputs/manuscript-review-v3及examples/paper-api.R|任务计数、保存W1中间界、API摘要/日志均在源码；API完整fits.rds留本地，可用公开示例新建输出复现，不是正式原研究|

## 作者落实访问后的核对顺序

1. 由作者确定公开仓库发布或期刊认可的受控下载入口，提供可实际访问的URL/凭证方式与固定版本；不将GitHub草稿页面当作匿名审稿入口，不在Git中提交凭证。
2. 在一个无原项目绝对路径的新目录，用实际审稿权限下载所有需要的组件；记录外部包哈希和成员清单。只解包到独立证据目录，不覆盖源码。
3. 从小包开始：软件安装及公开R示例、论文包清单核对与重编译；再执行完整原数组/统计/参考重建。W1有理重建核对保存界，不单独认证全部导数和尾界实现；完整重算另按固定协议。
4. 检查失败和未定项全部在场，结果集合与3888+256分母、42/105分类一致。只核验恢复时不应启动采样或把无用额度跑满。
5. 保存外部环境、源码提交、权限实际测试、执行日志、结果差异及全部哈希。只有完成这些真实步骤，才能改稿中的“尚未提供完整访问”状态。

目前第1步尚待作者决定；本轮没有公开私有草稿、上传本地补充原件或宣称匿名审稿访问已经通过。论文中文修订与独立目录编译可以完成，这一访问缺口仍单独保留。
