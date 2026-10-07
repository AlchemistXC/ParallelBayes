# 人工报告规模检查证据

这些文件来自完整九模型任务身份下的**人工标量夹具**。没有调用 MCMC、Windows 或 CUDA；计时字段是人为设定的测试输入，不可引用为算法性能。

`SUMMARY.json` 记录执行源码、实际报告过程耗时/内存和测试范围。`run-01.log` 保留首次在自然比值区间处失败的记录；已完成统计原件保留，修复后通过公开报告 CLI 继续。`compile-02.json` 保留长表排版问题；`compile-03.json` 是修复后的实际编译。

`ARTIFICIAL-report.pdf` 是85页版面检查快照，非论文终稿。45张图逐面板目检及字体/碰撞/对齐检查在 `figure-qa/` 和 `manual-panel-review.csv`。`source-*-SHA256.json` 与 `source-report-receipt.json` 是本地完整来源目录的身份回执，**不是本精简目录的文件清单**；约300 MB的完整人工表和重复图件未加入Git。本目录文件由自身 `SHA256.json` 覆盖。

复现入口：从项目根目录运行 `python tests/handoff/run_formal_report_scale.py --output NEW_DIRECTORY`，需要现有Python分析环境（NumPy、SciPy、Matplotlib）及至少2 GiB空闲磁盘。设置 `PB_ALIGNMENT_QA` 为本机已安装 nature-figure 的 `scripts/audit_panel_alignment.py` 可重做技能对齐检查；私有技能代码不在本仓库。报告含图，应保留目录结构并用已有XeLaTeX或Tectonic编译 `NEW_DIRECTORY/report/report.tex`。依赖实测版本见 `environment.json`。

这条复现入口不需要Windows、显卡、重新调参或正式协议冻结。真实数据替换人工数据后必须重新核验表图，不能复用本目录来证明正式研究完成。
