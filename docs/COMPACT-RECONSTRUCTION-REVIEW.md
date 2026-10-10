# 紧凑研究：跨平台重建汇总与正文输入

2026-10-10。完整接收已经结束，独立4144项NumPy/R重建仍在运行。本页描述新汇总工具及其已完成的检查，不宣布F3/F5/F6完成，不授权重跑Windows采样。

## 跨平台差异汇总

`review_compact_reconstruction.py`读取SQLite中已经提交的逐任务记录，核对记录、FRAME、科学结果和R诊断JSON的哈希。原始数组完整性与逐数组重放由正式读取器负责；最终汇总还要求其真实恢复证明，不能把这个汇总脚本当作再次读取全部原始字节。

汇总分别记录：MH主轨迹、缓存调用的转移数/接受事件/路径差；NUTS输出契约；重新提取函数与原二进制差异；同一原始二进制在Mac R重算的诊断差异。未定义诊断必须保持未定义，并显式列出跨越`Rhat > 1.01`的条目。阈值和数值容差不变，原Windows统计不被替换。

当前固定快照覆盖2178项，全部成功读取，其中2009项有效主任务、23项原数值失败、82项原未分类失败、64项缓存探测。1847份主MH轨迹和256次缓存调用接受事件均零失配；162份NUTS检查契约，未重跑NUTS。8054个所选函数诊断的未定义状态一致，未发现跨越1.01阈值的条目。该快照不是完整结果，也不增加正式重复。

快照来源和12项新增测试的证据见`benchmark/analysis/outputs/compact-reconstruction-preparation-v1/`。测试7项针对跨平台汇总的缺失状态、阈值、输入损坏及完成边界，5项针对正文生成的独立重建身份要求；全部通过，0失败/0跳过。后组保留14条既有matplotlib/pyparsing弃用警告。

完整读取和恢复结束后，运行：

```text
python scripts/analysis/review_compact_reconstruction.py \
  --analysis ANALYSIS \
  --resume-proof ACTUAL_ZERO_REANALYSIS_JSON \
  --output NEW_COMPLETE_REVIEW
```

查看中间进度可显式使用`--snapshot`，其结果始终标为`partial_snapshot`，不能满足正文最终生成条件。输出目录必须不存在。真正的恢复验证由`formal_analyze.py run --resume`执行，不从文件数量推测。

## 正文表格与数值的可复建入口

`write_compact_manuscript.py`直接读取校验过的完整统计包，输出：

- `compact-scalars.generated.tex`：总状态、诊断数和四类普通费用对照范围。
- `compact-wells.generated.tex`：W1在4096步下的全部九工作流，普通费用及alpha/beta参考平方差、原条件BCa区间。
- `compact-outcomes.generated.tex`：九目标全部主任务的成功/失败和函数诊断计数。
- `claims.json`：完整未舍入数值、选择规则、来源记录；`SHA256.json`绑定全部生成文件。

正文只选W1两个回归系数作为应用表，其他五函数与两个预算仍在完整36函数结果附录；没有生成新估计量、改变函数尺度或补齐缺失区间。W1区间条件于非认证数值参考，不包含其不确定性。72组普通同核费用对照均保留，未按比值方向筛选。

```text
python scripts/analysis/write_compact_manuscript.py \
  --statistics-directory MAC_STATISTICS \
  --manifest-sha256 VERIFIED_MAC_STATISTICS_SHA \
  --review NEW_COMPLETE_REVIEW/SUMMARY.json \
  --review-sha256 VERIFIED_REVIEW_SHA \
  --output NEW_MANUSCRIPT_INPUTS
```

生成器要求完整Mac汇总的身份与统计包`analysis_identity_sha256`相同，并有4144项全部读取和恢复依据。原Windows统计可用`--preview`检查版式，但不通过这一最终门槛。当前两页表格预览已编译并逐页审读，尚未替换正文；它不是新论文版本。

## 下一步

等待现有原始重建进程真实退出，先完成恢复和全模型统计/差异核对，再生成最终主表图。R前端有限计时只在接收与重建停止后执行。最后将主文等待句改为实际结果，并从原始证据、统计、图表到论文构建记录关闭F5；预览、原件接收和LaTeX编译各自不能替代这一步。
