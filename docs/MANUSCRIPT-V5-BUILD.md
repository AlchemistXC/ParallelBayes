# 中文论文v5：修改范围、构建与验收

2026-10-12。v5是v4的后继写作修订，主线为同核执行成本与固定预算的推断误差。106项意见的判断及处理见[逐项审核](MANUSCRIPT-REVIEW-V5.md)。v4封存候选、冻结协议、原始结果、与v4一致的中文研究计划及报告保持原样；v5不追溯更改研究设计为预注册设计，也不替代封存身份。

## 阅读和源文件

| 文稿 | PDF | 源入口 |
|---|---|---|
| 正文，16页 | [v5正文](../output/software-paper/软件与基准研究-审读修订v5.pdf) | [主TeX](../manuscript/software-v5/软件与基准研究.tex) |
| 补充A，47页 | [v5补充A](../output/software-paper/补充材料A-审读修订v5.pdf) | [补充TeX](../manuscript/software-v5/补充材料.tex) |
| 补充B，67页 | [v5补充B](../output/software-paper/补充材料B-审读修订v5.pdf) | 便携包内`complete-results/report.tex` |

[完整TeX输入ZIP](../output/software-paper/parallelbayes-paper-v5.zip)含三份主文件、全部相对路径依赖、第一方图件、来源清单与独立`BUILD.py`。这是图文重编译包，未包含约29.31GB的正式原数组或完整分析环境。

解压到新目录，安装Tectonic或完整TeX Live/MacTeX后运行：

```text
python BUILD.py --verify-only
python BUILD.py
```

也可用`--compiler /path/to/tectonic`指定编译器，或`--output NEW_BUILD`选择新的构建目录。Tectonic首次可能需要网络下载TeX资源。输出目录必须新建，失败日志保留。入口使用Python标准库，不需Codex插件；本轮实测的是Tectonic 0.17.0，未另行验证XeLaTeX路线。

## 本轮新增证据

1. 重读W1每链4096步的216份原阶段计时，绑定接收索引和已核验Mac统计清单；普通费用拆成准备、含转换的采样、写盘、外部R诊断及其余进程费用。NUTS采样段仍包含内部旧诊断。余额并非单独测得的纯启动时间。
2. 三种费用边界采用同四份原W1输入，按输入配对取几何比；缓存每输入四次调用先平均。它是描述性对照，未新增独立重复或四重复bootstrap区间。
3. L1原重复21的两份路径以二进制重算posterior 1.7.0诊断，复现尾ESS 4.80946与31.87691。相同接受事件、4.5e-11路径差及3673步长拒绝段导致5%分位数并列值敏感；舍入仅作额外检查，原诊断不替换。
4. [公开R示例](../examples/paper-api-v5.R)最终两份8192步输出完成，接受事件失配0、路径差约1.14e-14，q1/q2的Rhat约1.00166/1.00042。技术过程共4次采样调用：初次配对1完成/1迭代停止，显式上限后2完成；此前还有1次采样前依赖路径错误。日志、状态与原二进制摘要均保存，未计入正式MSE、速度比或24次重复。

新增正式采样为0。R原样本在独立作者本地技术包，未进入Git；[ATTEMPTS.json](../benchmark/analysis/outputs/manuscript-review-v5/r-technical-example/ATTEMPTS.json)保留其哈希和全部尝试身份。完整正式复现仍遵循[v4复现入口](SUBMISSION-REPRODUCE.md)与[原数组重建说明](COMPACT-REPRODUCTION.md)，原件访问待作者落实。

## 重新执行只读分析

在完整仓库的新副本中，使用已有分析锁与R锁，取得核验过的`FORMAL`、`INDEX`及`STATISTICS`目录，运行：

```text
ANALYSIS_PYTHON scripts/analysis/review5_evidence.py --project . --delivery FORMAL --index INDEX --statistics-dir STATISTICS --output NEW_EVIDENCE
Rscript --vanilla scripts/analysis/review5_diagnostics.R NEW_EVIDENCE
```

输入Mac统计清单SHA256必须为`d928a497889e11f6aaf5829bf1ffd807a647a880a5d4ae7cef4acf3046c34bfb`；每个被读取的正式原件再次绑定字节数和SHA256。原件及已有输出不覆写。R使用posterior 1.7.0。展示层位于`write_review5_tex.py`与两份`plot_review5_*.py`，应在新仓库副本中生成，不覆盖旧封存目录。便携TeX包附带部分脚本供溯源，完整运行需完整仓库的公共辅助模块。

## 验收结果与边界

- 六份新增Python工具语法通过；216条阶段记录闭合，两个原二进制输入和阶段CSV在增加统计清单检查后完全相同，L1原尾ESS重算符合保存值。
- 新误差图的72个数据点与区间源CSV逐字节等于原图，仅改变颜色和图例。两张新图的渲染对齐及碰撞检查通过。字体实际最低字形为9pt/5.95pt（后者为对数指数；主标注8.5–9pt）。PNG为300dpi预览，投稿以矢量PDF/SVG为基础，最终尺寸按期刊决定。
- 源级图检查展开公共配置/导出辅助模块后为18通过、3提醒、0失败；单文件静态检查不解析导入函数，初始提醒及其边界没有作为渲染错误隐藏。剩余提醒为PNG而非TIFF、300而非600dpi以及静态尺寸算式解析；导出文件真实宽度为160mm。
- 三份文稿在源工作树之外仅用便携输入和`BUILD.py`编译成功。PDF页数为16/47/67，无未解析引用、缺失字形或超出版心的编译警告；MuPDF逐页/修改页视觉检查通过。编译不修改清单内输入，日志及PDF哈希见[构建记录](../benchmark/analysis/outputs/manuscript-review-v5/relocated-build-receipt.json)。
- 原v4三份PDF、TeX包以及受保护软件、模型、依赖锁、v4稿源/计划/报告均不变，见[QA记录](../benchmark/analysis/outputs/manuscript-review-v5/QA.json)。本轮未改数值内核，因此没有重跑无关软件测试，也未把语法/排版验收计入历史采样器测试数。

仍待决定的是作者/单位、期刊与原件公开及审稿访问。若拟主张无条件算法排名、昂贵似然交叉点或最优窗口，应另立相应协议；本版采用限定的计算研究论断，无新Windows提示词。本轮不发布私有草稿、不进行CRAN或期刊投稿。
