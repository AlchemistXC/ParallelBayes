# H1与L2补充结果的论文整合

2026-10-10，targeted-paper-companion-v1。本文档只记录已完成的S1和S3B进入论文；S2原生Windows定位、S3A W1完整包络及其最终合并仍未完成。原紧凑研究3888任务、3741有效、42数值失败、105未分类失败及全部冻结协议保持不变。

## 论证与内容安排

- 正文4.1用80项H1函数差比较替换只描述42失败的段落。最大逐点函数差约3.27×10⁻³、最大四链均值差约3.08×10⁻⁷，各自极值不必来自同一任务。NumPy是浮点参照，结果不恢复42项原失败资格。
- 正文4.4增加L2的概率尺度解释：两套重要性估计约1.57×10⁻⁹和1.76×10⁻⁹，全部414份旧有效拟合的事件估计仍为0；较小绝对平方差与100%相对参考误差同时出现。
- SI第2.5节列提议构造、固定预算、分子/分母联合协方差MCSE、两套质量表以及全部八批结果。第二套提议权重更集中，两套结果均保留。
- SI第4.2节列H1四函数逐点、合并均值及单链均值极值，完整3200行及两图保留仓库。
- 原参考表保留历史状态；新参考单列。讨论用函数/初始化/误差尺度串联H1、M1、L2，不重复全部数字。摘要的主网格结论未改变。

使用nature-writing、latex-compile及PDF检查流程。两份中文PDF编译成功：正文18页、SI37页；新增表格按正常字号排版，查看全部页面缩略图并放大检查新增页。最终编译无未解析引用，文字未越过页边界。旧完整结果附录67页保持原样。

## 从来源重建新增文字和表格

从仓库根目录执行，输出目录必须不存在：

```sh
python3 scripts/analysis/write_targeted_followups_tex.py \
  --root . \
  --manifest manuscript/software/targeted-inputs.json \
  --templates manuscript/software \
  --output output/targeted-paper-rebuild
```

程序校验9个固定输入文件的SHA256、已通过的独立核验及其摘要绑定，重新汇总H1极值，并从L2独立复算保存的八批分子/分母重新计算比率与MCSE。它生成四份LaTeX片段和来源清单，未调用采样器。修改文字应改`targeted-*.template.tex`后重新生成；不要只编辑生成文件。新协议和分析原件不因文字修改而变化。

5项有针对性的检查通过、0失败、0跳过：搬移输入后逐字节重建、源表改动拒绝、错误MCSE拒绝、原失败晋升拒绝和未定义模板值拒绝。数值原始数组的独立核验仍以S1/S3B交付为准；这一小型报告检查不代替原计算验证。检查日志、论证对应和字数变化见`benchmark/analysis/outputs/targeted-paper-companion-v1/`。

本版新增[Owen的在线书稿](https://artowen.su.domains/mc/)作为自归一化重要性采样和delta近似依据；具体混合配比、八批误差估计和计算预算来自本项目冻结协议。没有将近似MCSE写成认证误差界。

## 交付与待办

论文输入便携包用于重新编译；新增汇总重建包用于重建四份新片段。这两类包都不等于完整原始实验复现包。旧主证据不重复复制；H1/L2新增原始归档留在本地，未自动发布。

S2仍需Windows原生资格与有限定位；S3A仍在原会话计算，完成后还需独立检查误差包络及排序敏感性。现稿据此保留105次NUTS失败阶段未定和W1未认证的表述。

## 本次文件

- [正文PDF](../output/software-paper/软件与基准研究-定向补充v1.pdf) · [正文TeX](../manuscript/software/软件与基准研究.tex)
- [补充材料PDF](../output/software-paper/补充材料-定向补充v1.pdf) · [补充材料TeX](../manuscript/software/补充材料.tex)
- [便携论文包](../output/software-paper/parallelbayes-targeted-paper-v1.tar)：17,346,560字节；159个输入逐项校验，另附清单。含旧完整结果附录的编译输入，原67页PDF哈希不变。
- [新增汇总重建包](../output/software-paper/parallelbayes-targeted-summary-v1.tar)：798,720字节；26个文件逐项校验，另附清单，五个生成文件搬移后逐字节相同。
- [交付清单与完整SHA256](../benchmark/analysis/outputs/targeted-paper-companion-v1/delivery.json)。

上述链接指本地交付；归档未上传或公开。论文输入来自源码`1de637b`。两份PDF在独立解包目录重编译，全部55页的文本及72 dpi像素相同；编译使用同机缓存Tectonic 0.17.0，未将这一结果写成异机复现。历史主证据与原始H1/L2计算归档没有修改。
