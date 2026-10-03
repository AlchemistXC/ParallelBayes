# 原创方法与证据示意图

两图均为本文的概念综合，使用nature-figure技能、保存的Python后端和matplotlib绘制。图形没有实验数据、速度曲线、外部图片或装饰图标。

| 图 | 科学用途 | 文件 |
|---|---|---|
| 图1 三种链内并行机制 | 预取、多提议、固定随机输入的MH/Picard增量与连续前缀 | [PDF](fig01-mechanisms.pdf)、[SVG](fig01-mechanisms.svg)、[PNG](fig01-mechanisms.png) |
| 图2 误差连接与比较协议 | 数值残差到MSE之间的条件，以及完整成本的证据要求 | [PDF](fig02-evidence-workflow.pdf)、[SVG](fig02-evidence-workflow.svg)、[PNG](fig02-evidence-workflow.png) |

见[绘制源码](make_schematics.py)和[绘图合同](figure-contract.md)。原文依据及概念/数据界限写入图注。图1c的增量匹配模式是教学示例，未声称实测；不能把未确认轨迹作为最终样本。

## 尺寸与检查

最终宽度162mm，与本文版芯一致；图1高168mm，图2高96mm。PDF为正文使用的矢量版，SVG保留文字对象，PNG为300dpi预览。最小文本7.4pt；中文使用Arial Unicode MS，面板字母使用DejaVu Sans粗体，PDF嵌入字体。

两图的原技能面板对齐审计均PASS；原PDF文本审计无低于5pt字形；最终渲染碰撞审计均0 FAIL、0 WARN。填色框内的文字被审计器识别为有意包含关系，已目视确认。PDF第8和14页检查实际缩放后的可读性。

[source-audit.json](source-audit.json)记录源代码预检18 PASS、3 WARN、0 FAIL。三条警告已人工核对：没有TIFF、预览为300dpi而非默认600dpi，以及正则检查器把 `162/25.4` 的第一个数字误当英寸，报成4114.8mm。实际PDF MediaBox宽459.2126pt，即162mm，已独立确认。当前没有指定期刊，矢量PDF是正式图件，PNG不是投稿栅格图，因此这些警告不构成当前交付缺陷。

## 本机再生成

运行依赖为临时matplotlib环境与原技能对齐模块；不需要重装TeX或修改技能。

~~~sh
PYTHONPATH=/tmp/parallelbayes-figure-deps:/Users/haku/.codex/skills/nature-figure/scripts /Users/haku/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 /Users/haku/Workspace/ParallelBayes/manuscript/figures/make_schematics.py
~~~

临时依赖若被清理，需在可用Python环境配置matplotlib，并将原技能scripts目录加入PYTHONPATH。导出后重新运行原 `audit_pdf_text.py` 与 `audit_figure_collisions.py`，再编译主稿。不同机器若缺中文字体，需显式指定可用字体并重新检查字符。
