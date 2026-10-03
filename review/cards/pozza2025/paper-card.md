# On the fundamental limitations of multi-proposal Markov chain Monte Carlo algorithms：全文核查卡

> Source coverage: Full paper
> Extraction confidence: Mixed (text reliable; equations/tables checked against PDF where material)
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Targeted external check
> Card completeness: Complete relative to supplied source

输入边界：保存的全文及已提供补充；按正文、附录、图表与结论进行核对，关键推导抽查。**不代表逐行数学重证、全部引文核验或实验复现。** PDF 页码均从文件第一页起计。

## 01 基本信息

- 作者：Pozza, Francesco; Zanella, Giacomo。单位以 [PDF 首页](../../../references/papers/pozza2025.pdf)为准。
- 年份/载体：2025，Biometrika。
- 本地版本：期刊正文，112(2), asaf019；8 页。
- 标识与出版记录：[原始来源](https://doi.org/10.1093/biomet/asaf019)；引用键 `pozza2025`。
- 类型：methods；领域：贝叶斯计算/并行采样相关方法；关键词：多候选方法与理论限制。
- 软件/数据：以论文实验节和来源包中的链接为准；本轮未运行。MEADS 已另存官方软件。
- 阅读日期：2026-10-02；用途：并行加速上限及适用假设，避免把特定核类别的结果推广到全部并行 MCMC。

独立补充：[pozza2025-supplement](../../../references/supplements/pozza2025-supplement.pdf)；补充页码单独计数。

## 02 一句话概括

用 Peskun 比较和谱隙上界约束一类可逆多候选核的收益；强结论依赖核类别、提案分布和目标条件，不能推广成所有并行 MCMC 的通用上限。

## 03 研究问题

每步产生 K 个候选，能把统计效率提高多少，额外计算是否值得？

## 04 背景与发展路线

[External] [Glatt-Holtz 2024](../glattholtz2024/paper-card.md)给出构造与应用；本文从核比较给出限制，两者问题和假设并不相同。

## 05 痛点

| 痛点与表现 | 原因/作者解释 | 证据 |
|---|---|---|
| 并行候选数增加不意味着混合按 K 改善；若忽略成本，很容易夸大收益。[Paper: PDF p. 1, §1] | 见同列原文；不把机制解释视为普遍已证因果 | 原文定位随主张列出 |

## 06 核心思想

与平均边际提案构成的单候选 MH 比较，再从拒绝率及投影跳跃界约束谱隙。[Paper: PDF p. 4, Theorem 1; PDF p. 5, Theorem 2]

## 07 方法概览

输入满足 Algorithm 1 的 π-可逆多候选核，可允许候选相关→构造平均边际单候选核→比较离对角转移→谱隙/ESJD 上界。Supplement §S1 核查 MTM 与 GMH 的适用性，Remark 3 明确把预取排除在该框架之外。

## 08 模块拆解

| 模块 | 功能 | 必要性 | 输入→输出 | 来源 | 移除影响（实验或分析） |
|---|---|---|---|---|---|
| Peskun 比较 | 上界 K 倍收益 | 核级别分析 | 多候选核→单候选比较核 | [Paper: PDF p. 4, Theorem 1] | 不能得到一般 K 比较界 |
| 谱隙投影界 | 获得更紧几何限制 | K 上界可能太宽 | 拒绝/跳跃→谱隙上界 | [Paper: PDF p. 5, Theorem 2] | 特定提案的次线性结论缺依据 |
| 参数优化 | 处理随机游走步长可调 | 固定步长比较可能误导 | σ 扫描→最优上界 | [Paper: PDF p. 6, Theorem 3] | 固定提案界不可直接替代重调参后的界 |

## 09 关键公式与符号

Theorem 1：$\mathrm{Gap}(P^{(K)})\le K\,\mathrm{Gap}(\widetilde P)$。Theorem 3 对 C²、m-强凸、L-光滑势函数及高斯随机游走边际给出 $\sup_\sigma\mathrm{Gap}(P^{(K)})\le c(L/m)(\log K+\log d)^2/d$，$d,K>2$。这里 Gap 是右谱隙，K 不是处理器墙钟收益。[Paper: PDF p. 4, Theorem 1; PDF p. 6, Theorem 3]

以下人工分组目录同时记录自动抽取的误报；编号覆盖不等于逐行证明认证。

| 公式组/抽取标记 | PDF 物理页 | 作用与边界 |
|---|---|---|
| Equation 1 | 2 | 多候选转移核结构。 |
| Equation 2 | 3 | 广义 Metropolis–Hastings 实例。 |
| Equation 3 | 4 | 与平均边缘提议的单候选 MH 核比较。 |
| Equation 4 | 5 | 谱隙与投影跳跃上界；可逆性是关键条件。 |
| Equation 5; Equation 6; Equation 7 | 6 | 矩生成函数及高斯随机游走界；最后的优化界保留维度和条件数，非所有并行 MCMC 的统一 log K 定律。 |

## 10 实验与证据链

| 实验 | 检验主张 | 数据/基线/预算 | 结果 | 支持结论 | 不支持的更强结论 | 来源 |
|---|---|---|---|---|---|---|
| Logistic 回归 ESJD | 候选数增长是否收益有限 | n=d=50，各 K 重新优化步长，随机游走和 Langevin 类 | 随机游走约 log K；Langevin 更弱增长为经验观察 | 为理论边界提供案例 | 不构成 Langevin 普遍谱隙定理 | [Paper: PDF p. 7, Figure 1] |

图表清单（先于卡片起草核对）：

| 证据 | PDF 物理页 | 论证作用 |
|---|---|---|
| Figure 1 | 7 | 调参后 ESJD 与候选数；无主文表格 |
| Equations (1)–(7); Theorems 1–3 | 2–6 | 核定义、比较与谱隙界 |
| Supplement §S1; §S2 | 补充1–5; 补充6–10 | 算法涵盖范围、可逆性与证明；预取排除见 Remark 3 |

## 11 正确理解

不可把摘要中的对数级直觉替代 Theorem 3 的完整假设和 (log K+log d)² 表达式。论文也说明结论不排除某些 HMC 多状态或 K 相关提案具有价值。[Paper: PDF p. 5, §3]

有界结论：用 Peskun 比较和谱隙上界约束一类可逆多候选核的收益；强结论依赖核类别、提案分布和目标条件，不能推广成所有并行 MCMC 的通用上限。

## 12 作者明确承认的限制

| 限制 | 具体表现 | 作者方向/处理 | 来源 |
|---|---|---|---|
| 推广到梯度提案 | 数值实验覆盖 Langevin，但一般理论不在本文完成 | 扩展理论 | [Paper: PDF p. 8, §5] |

## 13 批判分析

[Analysis] Supplement p.9 的一个中间不等式按字面有反例，已图像确认；此反例参数下最终上界平凡，不能据此声称 Theorem 3 已被推翻。适合正式引用时注明常数推导需核对，并优先使用假设清晰的阶结论。

这里是 [Analysis]，不回填为作者自述。尚未执行文中提出的检验。

## 14 知识候选

### Agent-derived knowledge candidates

[Analysis] 算法核效率、单位处理器计算成本和有限处理器加速必须分别计量。

## 15 与已有知识的联系

[External] [Grazzi 2026](../grazzi2026/paper-card.md)保持串行核但并行计算路径；[Mad Props 2026](../../新增文献核查.md#glattholtz2026)研究大候选极限，需进一步区别有限 K 与极限。

## 16 研究候选

### Agent-derived research candidates

Not applicable：本卡不单独宣称新的算法创意。跨论文形成的候选问题及其前作、验证方式、失败条件见[成果与缺口报告](../../截至2026-10-02的成果与缺口.md)。
