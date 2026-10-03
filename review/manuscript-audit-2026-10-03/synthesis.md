# 论证、贡献与方法图审查综合

日期：2026-10-03。冻结审查对象为修改前的 15 页 LaTeX/PDF；当前修订稿见 [LaTeX](../../manuscript/中文综述.tex) 和 [PDF](../../output/pdf/parallel-bayes-review-zh.pdf)。

## 审查方式与边界

采用 [nature-reviewer](/Users/haku/.codex/skills/nature-reviewer/SKILL.md)，按其明确要求使用三个相互隔离的代理，预先分配贡献与前作、数学与统计、机制与可读性三个侧重。三者获得相同冻结正文和来源清单，未获得已有精读卡结论、其他报告或主审疑点。最终报告已校验 SHA-256 并冻结，分别见 [Reviewer 1](reviewer-1.md)、[Reviewer 2](reviewer-2.md)、[Reviewer 3](reviewer-3.md)。后续编辑未回传给审查代理。

原文核对与先前 nature-paper-card 研读记录共同用于修改。写作采用 [nature-writing](/Users/haku/.codex/skills/nature-writing/SKILL.md)，配图采用 [nature-figure](/Users/haku/.codex/skills/nature-figure/SKILL.md)，完整项目导出采用 [latex-compile](/Users/haku/.codex/plugins/cache/openai-bundled/latex/0.2.8/skills/latex-compile/SKILL.md)。没有选定目标期刊，Nature-style 只作审查视角，不等于期刊适配结论。

## Cross-review synthesis (post-review; not shown to reviewers)

核心判断得到三份报告支持。轨迹等价、目标不变性和有限时间误差不能互换；降低执行深度不能直接推出达到后验精度的完整成本更低。三份报告均未提出 Blocking Yes 问题。这不代表已重证所有定理或复现实验。

独立报告共提出 5 项 Major、10 项 Minor；按论点合并后，有两项明确的 Major 共识。

| 综合问题 | 独立来源与原严重程度 | 综合判断及修订 |
|---|---|---|
| 综合贡献尚未变成可使用的条件化判断 | R1-M1、R3-M2，均 Major / Blocking No | 明确继承的评价原则与新增综合用途；第6.2节补单卡MALA与昂贵ODE两个判读案例，并区分真值、独立参考、诊断代理三种证据等级。 |
| 理论对照未保留核心参数 | R1-M2、R2-M1，均 Major / Blocking No | 第4.4节补具体比较结论，附录A分列LMC、ULMC、交错Picard的条件、初始化、精度、轮数、宽度和状态存储；解释有限核阈值及高精度下界的oracle边界。 |
| Picard机制不自足 | R3-M1 为 Major / Blocking No，R1-m2 为 Minor | 同一问题的权重有差异，不伪称Major共识。第4.3节加入增量求值、前缀和、连续确认规则；图1c用固定四步窗口示例，明确不同于Jacobi。第4.1节区分HMC转移与leapfrog层次。 |
| Fisher信息对象含混 | R2-m1、R3-m1，均 Minor | 首次定义相对FI，第4.5节明确时间积分、平均边缘与末时刻分布之别。 |
| 定量结果的追踪和聚合口径不足 | R2-m3、R3-m2，均 Minor | 表3澄清LAPS目标；附录B列Newton两个任务、H100/JIT、原有种子区间、LAPS函数及最大/平均聚合、FSM四模型对应。 |

以下单独提出的问题也已保留，没有因缺少重合而删去。

| Minor 项目 | 处理 |
|---|---|
| R1-m1 开放问题的前作归属 | 第7.4节指出原作提出议程的具体章节，再标明本文细化的函数证书、探测/编译成本和共同预算验证。 |
| R1-m3 Mad Props类别身份 | 第3.3节明确 Remark 3.5、Multiple Try Algorithms 3.3/3.4、Slingshot Algorithm 1.1和Proposition 4.10(i)，保留有限提议与核极限的区别。原文导言部分将Remark/Method误称Theorem，修订使用实际条目标题。 |
| R2-m2 TV与MSE之间的缺口 | 式12后补有界函数期望差界，保留基准链混合项；无界函数需附加条件，样本均值方差不能由单时刻边缘差代替。图2a作可视化。 |
| R2-m4 Picard路径失配用词 | 表2和第7.1节改为接受/增量事件失配，区分可观察容忍规则与命题3相对精确增量的概率控制。 |
| R3-m3 LAPS冻结调参 | 第5.2节区分开启MH与冻结群体自适应，并引至原作第2节和5.1节。 |

## 冻结后的内部一致性审计

主审在三份报告冻结后另行完成 [forensic-audit.md](forensic-audit.md) 和 [JSON记录](forensic-audit.json)，没有把这些结果冒充第四份审稿意见或独立共识。

重新计算116/37=3.1351、28/9=3.1111，均支持约3.1倍；50倍仍保留不同配方、质量阈值与硬件配置。式4的MSE恒等式及式11至12在所列条件下成立。冻结稿27个引文均有题录。没有发现需要推翻中心论点的内部算术矛盾。

LAPS、Newton和FSM的部分聚合背景属于 `aggregation_ambiguity`，通过附录B澄清，不能称为已确认数字错误。原始种子数据、全面实现复现和Calderhead全文仍属 `not_assessable`。新图没有性能数据，不涉及凭图推断效应大小。

## 配图与贡献边界

图1解释预取、多提议和增量型MH/Picard的不同计算对象；Newton在正文公式和图注中说明。图2解释数值残差、核误差、分布差、函数期望与MSE之间的条件，以及完整成本的比较步骤。全部由Python原创绘制，交付PDF/SVG/PNG和源码，没有转载原文图，也没有生成虚构的实验曲线。圆点、箭头和状态填充承担必要标记，未额外添加装饰图标。

贡献定位经修订后为“可追溯的条件化综合”：把机制、保证和成本接到具体案例和定理比较。没有声称首篇综述、首次统一、新误差定理、算法普遍最优，或把前作未来工作重新包装成空白。

## Risk / unsupported claims

- 当前修订已由主审逐项核对；未再进行第二轮独立审稿，不能把首轮意见当作对修改稿的独立通过证明。
- 文献截点仍为2026-10-02。本任务依据已有全文、补充材料及精读记录审查，未重新开展穷尽性前沿检索。
- Calderhead 2014正文和SI、Nested R-hat正式SI仍缺；公开稿附录与正式SI不能互换。其他既有预印本/技术报告版本边界保持。
- 本项目未运行新采样性能实验。表3是原文结果，图1的前缀匹配模式是教学示例。不同论文的速度比不能合并成排名。
- 附录A的状态网格存储是按算法状态数计数的量级，不是实测峰值内存；理论查询成本不包含初始化极小点求解、通信和编译。
- 内置编辑器可继续编辑同一tex，但它的单文件编译器无法读取外部图件；完整PDF采用现有Tectonic导出，最终编译与版面状态见 [latex-validation.json](../../manuscript/latex-validation.json)。
