# 完整中文研究计划与研究结果报告

2026-10-12。以封存中文v4和submission-v4-rc1为科学依据，新增两份完整中文PDF及自包含LaTeX；原研究、协议、失败资格和旧候选不变。

| 文档 | PDF | 主LaTeX |
|---|---|---|
| 研究与开发计划，15页 | [研究计划-v4一致版.pdf](../reports/chinese-v4/pdf/研究计划-v4一致版.pdf) | [研究计划.tex](../reports/chinese-v4/研究计划.tex) |
| 研究结果报告，24页 | [研究结果报告-v4一致版.pdf](../reports/chinese-v4/pdf/研究结果报告-v4一致版.pdf) | [研究结果报告.tex](../reports/chinese-v4/研究结果报告.tex) |

全部依赖位于 [reports/chinese-v4](../reports/chinese-v4/README.md)，含共享数学/配置、术语、v4原表、16条原文献、三幅第一方图件及来源SHA清单。编译入口为 `build.py`，支持Tectonic或XeLaTeX；无需原项目绝对路径或科学后端。

[内容与版式QA](../reports/chinese-v4/QA.md)记录独立内容审核、39页图像检查及新目录重编译。重编译全部文本和72 dpi像素一致。文档包只重建这两份PDF，完整科学复现仍依赖原41组件材料。

研究计划为执行后的设计与状态更新，不冒称事前注册；报告分别说明数值核验、成本、固定预算误差、有限参考及探索。新增正式重复/GPU测量/参考随机点均为0。

作者和投稿事项继续以 [AUTHOR-DECISIONS.md](AUTHOR-DECISIONS.md) 为准；本轮没有公开私有草稿或替作者批准投稿。
