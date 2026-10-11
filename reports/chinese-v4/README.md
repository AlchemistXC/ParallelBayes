# 中文研究计划与研究结果报告：v4 一致版

2026-10-12。两个主文件分别是 `研究计划.tex` 和 `研究结果报告.tex`。前者整理研究问题、软件方案、已执行设计、完成状态及投稿安排；后者完整说明方法、主实验、机制、有限补充、R使用和复现证据。均以 `submission-v4-rc1` 的中文 v4 为科学依据，不修改原论文、协议、原数组或主任务资格。

成品PDF位于 `pdf/`：研究计划15页、研究结果报告24页；`validation.json` 保存最终内容/版式/独立目录编译回执。

## 独立编译

该目录自包含，除 LaTeX 发行版外，不需要原项目、R/Python科学依赖或大原始证据。使用 ctex、Fandol 字体及 XeTeX；不需要第三方论文全文。Tectonic 首次运行可能获取其标准 TeX 资源。

安装 Tectonic 后，可在本目录运行：

```sh
python3 build.py --compiler tectonic
```

原生 Windows 可用 `py -3 build.py --compiler tectonic`。也可直接运行：

```sh
tectonic -X compile --outdir build 研究计划.tex
tectonic -X compile --outdir build 研究结果报告.tex
```

使用 TeX Live、MacTeX 或 MiKTeX 中的 XeLaTeX：

```sh
python3 build.py --compiler xelatex
```

脚本会为目录、引用进行三遍编译。生成文件位于 `build/`。也可给 `--compiler` 传编译器的路径。需要支持中文文件名的终端与UTF-8源码；两份文档必须保留全部相对依赖。

## 文件与来源

- `preamble.tex`：字体、页面、公式、表格与代码格式。
- `methods.tex`、`design.tex`、`capabilities.tex`、`terminology.tex`：两文档共用的数学、实验、能力及术语。
- `facts.tex`、`outcomes.tex`、`wells.tex`、`r-timing.tex`：逐字节复用 v4 的数字或结果表。
- `references.tex`：仅抽取 v4 已有文献条目，未宣称新的文献审计。
- `figures/`：三幅不变的第一方 v4 科学图。
- `PROVENANCE.json`：26项科学来源SHA256及7项原样复用关系。
- `QA.md`：内容审核、编译、版式及独立解包重编译记录。
- `sync_v4_assets.py`：仅在完整项目 checkout 中运行，用于重新复制原v4资产；独立编译不需要运行它。

数据和结果复现仍需原完整证据组件。此文档源码包可以重建这两份PDF，不能代替41组件科学复现包；不把重建报告PDF视为重跑研究。

## 当前完成边界

主研究与内部验收完成；作者信息、许可/公开范围、实际审稿访问路线、期刊语言和最终批准待作者确认。新增正式采样、GPU测量、参考随机点均为0。旧封存标签和原私有草稿保持不变。
