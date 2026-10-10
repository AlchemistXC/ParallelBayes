# S2 Mac独立接收与审阅

完整原件保持在Git外的独立接收目录；此目录只含第一方小型核验、重建分析和现代R诊断。`review/SUMMARY.json`是科学审阅结果，`identity-audit.json`只证明归档身份一致。21/3项检查来自保存的Windows回执，不是Mac执行原生测试。

运行可信本地`audit_nuts_return.py`、`analyze_nuts_localization.py`及`review_nuts_localization.py`从对应结果tar重建。R现代诊断另用已有`posterior_diagnostics.R`，具体入口见docs/WINDOWS-NUTS-MAC-REVIEW.md。没有新增采样，原105/42失败、正式分母和随机输入不变。README换行符及现代R浮点差逐项保留。
