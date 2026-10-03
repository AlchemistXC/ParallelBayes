# 中文论文写作

写作日期：2026-10-03。前沿文献覆盖截至 2026-10-02。

主稿为专题叙述性综述：**链内与时间并行 MCMC：统计保证、可并行性与推断成本**。以“在给定硬件和后验精度要求下，何时值得加速同一条链内部的计算”为主线，当前修订稿含摘要、八章正文、两个附录、五表、两图和27项参考文献，PDF为20页。

现已转换为 [LaTeX 主稿](中文综述.tex)和 [PDF](../output/pdf/parallel-bayes-review-zh.pdf)。后续论文修改以 LaTeX 文件为准，编译和版本说明见 [LaTeX 使用说明](LaTeX使用说明.md)。

## 阅读入口

- [审查后 PDF](../output/pdf/parallel-bayes-review-zh.pdf)及[LaTeX主稿](中文综述.tex)：当前阅读与编辑版本。
- [论证与贡献审查](../review/manuscript-audit-2026-10-03/synthesis.md)：三份冻结独立报告、综合判断及逐项修订。
- [方法图与证据图](figures/README.md)：原创矢量图、预览、源码及质量检查。
- [原Markdown初稿](中文综述_初稿.md)：历史文字版本，没有同步本轮LaTeX实质修改。
- [文章框架](文章框架.md)：核心论点、章节逻辑、术语表及证据分配。
- [引用定位与写作自查](引用定位与写作自查.md)：关键结论的来源页码、阅读边界、公式说明和待定的投稿信息。
- [本稿 BibTeX](references.bib)：正文实际引用的 27 项文献；不重复计算书章的 2024/2026 版本。
- [引文映射](reference-map.json)：编号、文献键、外部来源及本地全文路径。

正文引用了既有资料库中的 19 个独立作品，以及 8 项本轮核对的背景来源。新增背景来源的题录、用途和核对深度见 [background-references.json](background-references.json)。其中7篇已取得全文并补齐nature-paper-card精读卡，Calderhead仅有受限来源卡；实际版本和SI边界见全文清单。

## 编辑与更新

带稳定文献键的 [source/中文综述.md](source/中文综述.md) 是原 Markdown 版本的源文件。下面的命令仅重新生成 Markdown 阅读稿及其配套文件，不会更新 LaTeX 或 PDF：

~~~sh
python3 manuscript/scripts/build_manuscript.py
python3 manuscript/scripts/check_manuscript.py
~~~

命令在项目根目录运行。构建脚本重新生成阅读稿、BibTeX、编号映射及篇幅统计；检查脚本核对引文、链接、公式编号、表格结构及文件一致性，结果写入 [validation.json](validation.json)。自动检查不验证定理、实验证据或论文创新性。

本稿使用中文和通用学术体例，尚未套用具体期刊模板。没有添加作者、机构或虚构实验。后续可在 LaTeX 主稿基础上修改论证、压缩篇幅，再按目标期刊排版。
