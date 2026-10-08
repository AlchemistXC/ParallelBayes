# 2026-10-09 论文与研究计划修订

本轮完成不依赖紧凑实验回传的改稿。使用 nature-writing、nature-statistics、nature-figure、latex-compile 工作流；没有启动采样或改变正在运行的 Windows 协议。全文仍是研究中稿，最终推断比较尚待实际数据。

## 本次交付

- [正文 LaTeX](../manuscript/software/软件与基准研究.tex)与[13页 PDF](../output/software-paper/软件与基准研究-问题导向修订.pdf)：按研究问题重组为五节。补充确定递推、quasi-DEER 更新及有限轮恢复条件、硬前向与代理 Jacobian、实际门控/探针/截断、Picard 连续前缀；增加真实 R 扩展示例、能力矩阵、实验身份和36函数表。
- [补充材料 LaTeX](../manuscript/software/补充材料.tex)与[22页 PDF](../output/software-paper/补充材料-问题导向修订.pdf)：水井二维正规化证明、完整历史结果、安装/恢复及诊断定位。原七份生成段和其生成器均保持字节不变，旧PDF保留。
- [研究收尾计划](RESEARCH-COMPLETION-PLAN.md)：当前任务为接收紧凑研究、误差/成本分析、有限R前端计时和最终复现。旧计划完整保存在[历史文件](RESEARCH-COMPLETION-PLAN-through-2026-10-08.md)。不改变3888主任务/256缓存设计，不新增16384预算或选择器。
- [图件和数值来源](../figures/software-revision/figure-contract.json)：全部512行组成256个配对，分CPU/CUDA展示每格4个实际输入及中位数，不再以小样本bootstrap区间承担主要性能结论。原图和区间仍保留。架构图三条入口都连接执行层。
- 综述源码中三处 ODE 描述修正为时滞微分方程定义的昂贵似然；[修正后的20页综述PDF](../output/pdf/parallel-bayes-review-zh-dde-correction.pdf)亦已编译；本轮不重写原综述。

## 验证范围

1. 新图256个速度比及64组中位数与原汇总一致（数值容差1e-14），零排除。三图最小名义字号8.5 pt；文字和碰撞检查通过，最终尺寸目检通过。静态检查18通过、3提示、0失败：提示分别为PNG预览而非TIFF、160毫米匹配本文版心而非固定期刊宽度，以及已有显式正值检查未被启发式识别。
2. 主文及补充材料由现有Tectonic 0.17.0成功编译。独立构建包17项输入逐项校验；在搬移目录编译，35页的文本和渲染逐页与原构建相同。内置单文件编译器不支持项目依赖；基础XeLaTeX缺包，故采用已有Tectonic，所需标准字体资源按需缓存。
3. 修改构建工具以遍历正文和补充材料。重新核对历史CPU归档哈希，从62项保存摘要/源码/图件输入运行七个生成器，七份结果段全部与预期字节一致。初次使用历史目录的父层导致缺件，失败目录及日志保留，改用正确输入目录后通过。这不是重新分析原始轨迹或GPU计时。
4. 冻结数值代码、协议及历史生成结果不变。本轮新增采样和R诊断调用均为0；Python源码语法及Git空白检查通过。

[机器可读核验](../benchmark/analysis/outputs/manuscript-revision-v1/verification.json)保存产物哈希；[主要主张来源](../manuscript/software/CLAIM-EVIDENCE.md)连接结果和方法依据。图形生成器为`scripts/analysis/render_revision_figures.py`；独立论文构建入口为`scripts/completion/build_paper_bundle.py`。完整本地构建归档名为`paper-bundle-delivery.tar`，大小389120字节，哈希见[构建回执](../benchmark/analysis/outputs/manuscript-revision-v1/paper-build-archive.json)。仓库中的TeX与首方图件也可直接构建；构建包不等同完整原始实验复现包。

## 尚待完成

Windows紧凑研究当前只有用户进度报告，未取得本轮冻结清单、完整结果和独立接收结论。最终摘要、推断贡献和水井误差—成本结果须等回传；R前端墙钟另设有限技术批次，不回填历史采样。最终公开原始证据及投稿由研究者确认。本轮Git推送仅包含源码、文档、图件和PDF，不含私有技能、环境或第三方论文。
