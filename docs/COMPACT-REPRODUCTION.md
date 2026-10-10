# 从紧凑研究原件重建结果

本入口用于**读取保存的Windows结果**，不启动新MCMC、CUDA计时或Windows任务。完整Mac4144项重建、真实恢复、统计比较及最终论文构建已经完成，见[交付报告](RESEARCH-COMPLETION-REPORT.md)。既有Windows原件、Mac接收树及失败记录均不覆盖。

## 需要取得的材料

1. Windows交付源码`94bebec95177b03f0497d748cbc9f54a45492ce4`，或已验证的Git bundle；其中冻结采样源为`3a37a891896faedc62c0d6af185bfad77696054f`。从独立源码目录运行原始读取器，不能用最新版源码绕过其身份检查。
2. 完整21组件交付中的`formal`原件，以及其外部分块清单和接收回执。[有界接收指南](WINDOWS-COMPACT-RECEIVE.md)解释逐块校验，不需要再生成完整tar。原始正式组件为180582文件，外部分块清单SHA256为`38e68557b03e4e153a2321fe6b8e5210c99557500746c86f855480edc81ab75e`。
3. 当前研究分支中的展示层源码、第一方图件、历史结果输入和论文文件。读取器与展示层使用不同、明确记录的源码身份，不能将新版TeX模板冒充旧采样源码。

正式组件接收后产生的`WINDOWS-RETURN-MANIFEST.json`的SHA256为`81590d6e3cc07452ce46e9668222dcbe9b347cc33278396836e39992b0c3dc57`。这是归档读取器的输入；它和外部分块清单是两个不同文件。先用外部已确认的哈希核验，不从尚未校验的文件自身选择信任值。

Windows完整原件目前仍在草稿Release，源码公开不等于原数组已公开。研究者需取得作者提供的同一分块材料或具有草稿访问权限；本流程不自动发布它们。Git只保存小型摘要与第一方代码，不含第三方论文、私有技能或安装环境。

## 只读分析环境

实际Mac环境为Python3.12.14、NumPy2.2.6、SciPy1.15.3、R4.6.0、posterior1.7.0、jsonlite2.0.0。Windows原诊断为R4.6.1；跨平台差异单独检查，不替换原冻结诊断。

- [Python版本清单](../environment/locks/compact-analysis-observed-v1.txt)包括原件分析、绘图和PDF检查所用13个包及其实际传递依赖。
- [R分析锁](../environment/locks/compact-analysis-renv.lock)从已验收的完整R锁中选取20个非基础依赖，另复用R发行版的8个基础包。未另选新版依赖。
- 这些是实际版本清单，未锁定所有平台的wheel字节、系统数学库或字体；不得宣称换平台必然逐位相同。完整接收身份另外记录实际环境。
- 原始读取不需要安装ParallelBayes wheel/R包、torch、CUDA、JAX、Pyro、BlackJAX或BridgeStan。原源码已包含独立NumPy参考。软件使用和性能复现的依赖见[安装说明](INSTALL-AND-USE.md)，与此只读任务分开。

例如，在使用者指定的新环境中安装固定Python分析包：

```text
python3.12 -m venv ANALYSIS_ENV
ANALYSIS_PYTHON -m pip install -r CURRENT_SOURCE/environment/locks/compact-analysis-observed-v1.txt
```

`ANALYSIS_PYTHON`指该新环境的`bin/python`（Windows则`Scripts/python.exe`）；保留虚拟环境路径，不把其符号链接解析为基础解释器。R可复用已核对匹配的库，或使用已有`renv`在新项目/新库恢复上述分析锁：

```r
renv::restore(project = NEW_ANALYSIS_PROJECT, library = NEW_R_LIBRARY,
              lockfile = ANALYSIS_LOCKFILE, prompt = FALSE)
```

`renv`是恢复工具，须已安装；它不参与正式R诊断。本机全局R库没有`renv`，已有隔离安装库提供该工具，这一区别不应写成“全局已安装”。不在运行中的采样/分析环境升级依赖。

可执行以下只读环境检查：

```text
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/release/inspect_analysis_environment.py ARCHIVED_SOURCE NEW_ENVIRONMENT_RECEIPT
```

它明确拦截六类采样后端导入，并核对NumPy/SciPy/绘图/PDF依赖版本闭合。本机实测加载归档读取器、科学检查、统计和报告模块时，后端导入尝试为0。该检查不等于新环境安装、完整数组重建或CUDA测试；记录见`benchmark/analysis/outputs/compact-analysis-environment-v1/`。

## 路径与执行顺序

将`ARCHIVED_SOURCE`、`FORMAL`、`INDEX`、`ANALYSIS`、`STATISTICS`、`REPORT`理解为使用者自己的路径。输出目录必须是新的、位于原件目录之外。科学数据只保留一棵接收树；分析按单任务处理，不把全部轨迹载入内存。设置`PYTHONDONTWRITEBYTECODE=1`和`PYTHONUTF8=1`，不在归档源码中产生字节码。

以下前三步必须使用归档源码版本，Python和R环境也须记录；全部过程没有总时长截止。

```text
ANALYSIS_PYTHON ARCHIVED_SOURCE/scripts/analysis/formal_analyze.py index --delivery FORMAL --bundle-relative "" --manifest-sha256 VERIFIED_RETURN_MANIFEST_SHA --output INDEX
ANALYSIS_PYTHON ARCHIVED_SOURCE/scripts/analysis/formal_analyze.py run --delivery FORMAL --index INDEX --output ANALYSIS --rscript NATIVE_RSCRIPT --r-library R_LIBRARY --cross-platform
```

首次返回后保存`ANALYSIS/SUMMARY.json`及该目录每个文件的SHA256，再原命令追加`--resume`。要求4144项复用、新增分析0、全部原分析文件不变；仅`SUMMARY.json`是可更新的记账文件。禁止在第一次运行仍活跃时启动恢复。当前Mac执行器会生成`formal-first-summary.json`、`formal-analysis-before-resume.json`及`formal-zero-reanalysis.json`作为依据；其他接收者须保存其自身实际记录，不能复制这些成功结论。

```text
ANALYSIS_PYTHON ARCHIVED_SOURCE/scripts/analysis/formal_statistics.py --delivery FORMAL --index INDEX --analysis ANALYSIS --output STATISTICS
```

统计保存原Windows估计和诊断，经Mac核对后继续按冻结规则计算；Mac派生浮点差异另存。完整失败分母、L2未定参考、W1非认证求积、常量诊断和未知费用均保留。

完整Mac统计还要与归档Windows统计逐项比较：

```text
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/analysis/compare_compact_statistics.py --left-directory ORIGINAL_WINDOWS_STATISTICS --left-sha256 VERIFIED_WINDOWS_STATISTICS_SHA --right-directory STATISTICS --right-sha256 VERIFIED_MAC_STATISTICS_SHA --output STATISTICS_COMPARISON
```

该检查保留投影数值、状态/分母、全部bootstrap数组及描述性阈值分类的差异，不以宽容差隐藏变化。冻结bootstrap中空分母造成的NaN位置也逐项比较，不删除或补零。它不重新计算区间；ZIP元数据和重复来源记录不当作统计值。四项针对性检查及完整两平台比较已完成。状态、分母、阈值和NaN位置无变化；浮点末位差全部保留，未将重建声称为逐位相同。

之后使用当前展示层，不修改归档读取器：

```text
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/analysis/review_compact_reconstruction.py --analysis ANALYSIS --resume-proof ACTUAL_ZERO_REANALYSIS_JSON --output COMPLETE_REVIEW
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/analysis/formal_report.py --statistics-directory STATISTICS --manifest-sha256 VERIFIED_STATISTICS_SHA --output REPORT --publication-layout
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/analysis/plot_compact_overview.py --statistics-directory STATISTICS --manifest-sha256 VERIFIED_STATISTICS_SHA --output OVERVIEW
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/analysis/write_compact_manuscript.py --statistics-directory STATISTICS --manifest-sha256 VERIFIED_STATISTICS_SHA --review COMPLETE_REVIEW/SUMMARY.json --review-sha256 VERIFIED_REVIEW_SHA --output MANUSCRIPT_INPUTS
```

这里`VERIFIED_STATISTICS_SHA`为完整`STATISTICS/SHA256.json`本身的哈希；工具会再核对其全部成员。正文生成器要求完整Mac分析身份一致，`--preview`不能通过最终要求。算法图件不依赖私有技能代码；项目自带基础对齐检查，额外作者工具的检查记录与科学输入分开。

## 图文与完整复现的区别

正文数字、W1表、全目标状态表及普通费用图由上游统计投影；完整报告保留9目标、36函数、全部预算/工作流及缺失位置。旧Mac、SBC和Windows首轮采用各自原协议，不能在新统计中混入重复。[历史重建入口](REBUILD-RESULTS.md)与本紧凑入口共同组成研究材料。

`build_paper_bundle.py`仅收集已经生成的TeX与图件，适合将中文正文和补充材料搬到另一目录编译；它本身不重算原始数据。当前论文编辑器不支持此项目的全部外部文件，构建采用已存在的Tectonic或具备ctex/fandol的XeLaTeX，不需要安装Codex私有插件。

最终验收必须分别保存：原件完整性、4144项读取及恢复、统计与原Windows结果的对应、图表源数据、完整PDF版式和便携构建。仅安装成功、汇总通过或PDF能编译，都不能单独关闭研究复现工作包。


## 本轮最终输出与R伴随表

统计清单SHA256为`d928a497889e11f6aaf5829bf1ffd807a647a880a5d4ae7cef4acf3046c34bfb`，完整重建审查SHA256为`a04b3b8effc833c29deb93f2555d8161bde725dcd8d0bd0f9e15e0df1aab9ef7`。这些标识供核对本次原件，不应复制为另一环境自己的运行成功标记。

将生成的三个`compact-*.generated.tex`置于当前`manuscript/software/`，普通费用图目录对应`figures/compact-final-v1/`。已签入的原件派生文本与小型图件使普通读者可直接编译主文；完整结果附件由`formal_report.py --publication-layout`生成的`report.tex`单独编译。

R技术原件另按`r_frontend_verify.py --root R_TIMING --reference-file ORIGINAL_REFERENCE_PY --output R_ANALYSIS`只读重建，再用`r_frontend_report.py --analysis R_ANALYSIS --recovery ACTUAL_RECOVERY_JSON --output R_TABLES`生成`r-frontend.generated.tex`。它要求真实32进程恢复证明和64次独立核验，不能用四次技术重放生成统计区间。原R协议含本次安装来源/绝对路径；搬移核验通过显式`--reference-file`指向随证据提供的原`reference.py`，工具要求它与冻结安装文件SHA256完全一致，不重写协议、不伪造路径，也不重新执行计时。实际搬移64次保存调用重放、两份CSV逐字节一致，以及篡改参考文件被拒绝的检查均已完成。R表格也可从随附已核验`calls.csv`检查全部64行，不需新采样。

本次便携论文输入为`output/software-paper/portable-final-inputs-v1.tar`；23文件与清单在新目录验证并使用原Tectonic编译。主文文本和页面像素一致。此包不含完整原始轨迹，仍须与上述原件/源码和分析输出共同使用。


最终派生统计与R技术原件可从作者可访问的草稿Release新增包`parallelbayes-mac-final-research-20261010.tar`取得，校验见[交付报告](RESEARCH-COMPLETION-REPORT.md)。其中`statistics/`是完整Mac统计包，`complete-results/`包含全部45图/源表，`R-timing/`与`R-reference/reference.py`支持上述搬移只读命令。原Windows轨迹仍使用原21组件，未重复塞入此派生包。先校验外部收据和成员清单，再运行工具；不要将已有输出覆盖为新运行。


## 审查修订v2的展示层重建

本轮不重跑MCMC或bootstrap。沿用上面核验过的`STATISTICS`，以及正式证据目录`FORMAL`（包含冻结protocol/catalog/inputs）。以下`NEW_*`均须是尚不存在的目录；`WELLS_REFERENCE_BINARY`是原水井独立参考的`values-f64le.bin`，须与已归档SHA一致。

```text
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/analysis/revision_configuration_tables.py --formal FORMAL --output NEW_CONFIGURATION --tex NEW_CONFIGURATION_TEX
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/analysis/revision_reference_tables.py --project CURRENT_SOURCE --statistics STATISTICS --wells-reference-binary WELLS_REFERENCE_BINARY --output NEW_REFERENCE --tex NEW_REFERENCE_TEX
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/analysis/plot_revision_error_cost.py --statistics-directory STATISTICS --manifest-sha256 VERIFIED_STATISTICS_SHA --output NEW_ERROR_COST
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/analysis/formal_report.py --statistics-directory STATISTICS --manifest-sha256 VERIFIED_STATISTICS_SHA --output NEW_COMPLETE_RESULTS --publication-layout
ANALYSIS_PYTHON CURRENT_SOURCE/scripts/completion/build_paper_bundle.py --root CURRENT_SOURCE --output NEW_PAPER_INPUTS --complete-results NEW_COMPLETE_RESULTS --complete-results-sha256 VERIFIED_REPORT_SHA
```

`VERIFIED_REPORT_SHA`为本次`NEW_COMPLETE_RESULTS/SHA256.json`本身的SHA256，而非统计清单哈希。打包器逐项校验报告PDF、CSV、导航和TeX后复制；不会重新采样或覆盖原目录。新目标/参考表的内容应分别与签入的`revision-configuration.generated.tex`及`revision-reference.generated.tex`比较。本轮实际导出与QA见[审核记录](MANUSCRIPT-REVIEW-V2.md)。

当前便携包`parallelbayes-paper-review-v2.tar`包含正文、SI与完整结果附录所需的全部TeX/图件及附录CSV。解压到新目录，先核对`MANIFEST.json`每项哈希，然后在`manuscript/software`编译两份中文TeX，在`complete-results`编译`report.tex`。这一步只重建已生成的论文；完整原数据分析仍按本页前文执行。旧的23文件输入包和完整Mac派生归档保留，不能将旧包当成本轮新增表/图的源码。
