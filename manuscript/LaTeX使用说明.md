# LaTeX 与 PDF

当前为论证审查后的中文综述修订稿。含八章正文、两个附录、五张表、两张原创矢量图、十二个编号公式和27项参考文献，PDF共20页。

- [LaTeX主稿](中文综述.tex)
- [编译后的PDF](../output/pdf/parallel-bayes-review-zh.pdf)
- [排版检查记录](latex-validation.json)
- [论证审查与修订记录](../review/manuscript-audit-2026-10-03/synthesis.md)
- [图件及生成说明](figures/README.md)

后续修改以同一LaTeX主稿为准。原Markdown初稿保留为历史版本，不自动与LaTeX互相覆盖。不要运行历史转换脚本覆盖主稿。

## 文件与编译

使用UTF-8、ctexart、Fandol中文字体和A4单栏版式。参考文献嵌入thebibliography；两张图以相对路径加载，因此编译或搬移项目时需同时保留 `figures/fig01-mechanisms.pdf` 和 `figures/fig02-evidence-workflow.pdf`。

内置编辑器可以继续编辑主稿，但其单文件编译器当前不加载外部图件。本次已实际确认其在图件路径处失败，不能声称内置实时预览编译通过。完整PDF使用现有bundled Tectonic 0.17.0导出成功，没有安装TeX Live或MacTeX。新增graphicx等资源由Tectonic自动缓存。

在独立环境中从主稿目录运行：

~~~sh
cd /Users/haku/Workspace/ParallelBayes/manuscript
tectonic -X compile 中文综述.tex --outdir ../output/pdf
~~~

或用已有且包含中文宏包的XeLaTeX，在相同目录连续编译两次解析引文与交叉引用。默认输出名是中文综述.pdf；本次交付副本使用 `parallel-bayes-review-zh.pdf` 作为稳定文件名。

本机本次导出的完整命令、退出状态和日志位于 `tmp/pdfs/latex/audit-revision-compile-online.json`。旧的失败日志保留为过程记录，不代表当前PDF失败。20页已逐页查看，图页和参数表另放大检查；最后一轮只有附录A两处underfull hbox留白提示，无越界、缺失引用或字体替代字符。详见验证JSON。

本稿保留“中文初稿”页眉和2026-10-02文献截点，未添加作者、机构或目标期刊信息。
