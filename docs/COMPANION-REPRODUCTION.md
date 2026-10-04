# F1/F2伴随分析的重建入口

这是一批2026-10-05的只读伴随分析。它不增加正式MCMC任务、不改变Windows-v1协议、样本或原诊断。入口与收尾状态见`execution/COMPLETION-WORK-PACKAGES.md`。

## 只克隆Git即可做的小检查

```text
python scripts/completion/run_rhat_case.py --case benchmark/fixtures/rhat-midpoint-v1 --output output/completion/rhat-new --rscript Rscript
python -m pytest -q tests/handoff/test_completion_fixture.py
python scripts/completion/write_completion_tex.py --output output/completion-rebuilt.tex
```

第一个命令需要原生R、posterior 1.7.0、jsonlite；Python包装器只用标准库。第二个需要pytest。第三个只用标准库和Git内保留的小型结果，重建`manuscript/software/completion-companion.generated.tex`，可以逐字节比较。它不替代从完整原始证据重新核算。

## 从原始证据重算

先按回传说明下载、校验并解压Windows归档到独立`EVIDENCE`目录。不得覆盖开发检出。准备NumPy 2.2.6，然后运行：

```text
python scripts/completion/prepare_rhat_case.py --evidence EVIDENCE --output NEW_OUTPUT/rhat-case
python scripts/completion/analyze_windows_mechanisms.py --evidence EVIDENCE --output NEW_OUTPUT/accounting
```

原始NPZ、任务与协议均进行身份/哈希核查；输出目录必须全新。固定样例与既有样例比较；机制JSON/CSV与`benchmark/analysis/outputs/completion-f2/`比较。映射计数不含独立核验，也不是FLOPs；原技术重放不增加独立重复数。原Windows草稿Release尚非公开下载资源，这仍是最终外部复现需要关闭的问题。

## 论文与历史身份

当前新增伴随稿PDF为`output/software-paper/软件与基准研究-收尾修订.pdf`，共21页。完整输入仍为`manuscript/software/软件与基准研究.tex`及其局部输入/图件。用支持中文的XeLaTeX或Tectonic从该目录编译；本轮使用已有Tectonic 0.17.0，二次排版后交叉引用全部解析，检查了新增第18–20页。

原20页回传审查PDF`output/software-paper/软件与基准研究.pdf`保留。`benchmark/analysis/outputs/windows-return-audit/SHA256SUMS`仍对应提交`38894409004dd9ebceb978755dc246fcb3418d01`的审查产物，不用新分析回写旧回执。本批伴随产物使用`benchmark/analysis/outputs/completion-v1/SHA256SUMS`；哈希清单校验文件完整性，不等于结果真实性或算法正确性证明。

论文仅补充已实测伴随结果，整体F3–F6尚未完成，不能视为最终投稿稿。Windows执行提示词见`handoff/windows-completion/CODEX-PROMPT.md`；无需重跑512项。
