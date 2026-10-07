# 有限v2独立接收回执

报告见[WINDOWS-FORMAL-V2-INTAKE](../../../../docs/WINDOWS-FORMAL-V2-INTAKE.md)。本目录为紧凑一方证据；完整归档在原Windows草稿，大小/哈希见download-receipt。diagnostics.tex/pdf为六页技术诊断附件，不是正式研究结论。

使用与冻结来源相容的项目检出及NumPy2.2.6/SciPy1.15.3、R/posterior环境，从项目根目录运行下列入口。OUT、INDEX、ANALYSIS、STATS、REPORT分别为新的独立输出目录；DELIVERY为经安全解压且逐项核验的主包根，GATE为其validation目录。实际命令/路径见analysis-identity及日志，Windows源码见0ba5643，接收源码基线5885c71（数值读取未改）。后继仅formal_report_text.py表格字号修订。

```text
python scripts/verify-windows-return.py MAIN_TAR --output NEW_VERIFY_JSON
python scripts/windows/extract_verified_return.py MAIN_TAR --destination DELIVERY --receipt NEW_EXTRACTION_JSON
python scripts/windows/validate_formal_adapter.py verify --bundle GATE
python scripts/analysis/formal_analyze.py index --delivery DELIVERY --bundle-relative validation --manifest-sha256 ACTUAL_MANIFEST_SHA256 --output INDEX
python scripts/analysis/formal_analyze.py run --delivery DELIVERY --index INDEX --output ANALYSIS --rscript RSCRIPT --r-library RLIB --cross-platform
python scripts/analysis/formal_statistics.py --delivery DELIVERY --index INDEX --analysis ANALYSIS --output STATS
python scripts/analysis/formal_report.py --statistics-directory STATS --manifest-sha256 ACTUAL_STATISTICS_MANIFEST_SHA256 --output REPORT
python scripts/analysis/formal_analyze.py run --delivery DELIVERY --index INDEX --output ANALYSIS --rscript RSCRIPT --r-library RLIB --cross-platform --resume
```

无需torch/JAX/CUDA采样。普通函数/诊断输出采用已声明跨系统比较；MH全路径与接受事件门槛不变。第一次分析51新/0复用，第二次0新/51复用，27次R调用仅在第一次。全部正式统计重复为0；native行为测试是读取实测XML，不是Mac运行Windows测试。

所有source path是原环境身份记录，重建时用实际本地路径替换参数；不要覆盖证据。SHA256.json仅覆盖本目录紧凑产物，不替代完整原始归档manifest。

本地完整派生接收包为output/research-completion/windows-formal-v2-mac-intake-v1.tar.gz，23,315,685字节、496清单文件，SHA256 de64ea0ac4549275eb0fbdbdae8d3f7c8b1ed0e714b163b9b50ef0d8c91c8ad8。它含第一次/恢复分析、所有接收输出、早期/最终排版和源快照；不重复包含Windows原始数组，仍需原主归档重放。本包未上传Release，Git仅保留本目录紧凑回执。
