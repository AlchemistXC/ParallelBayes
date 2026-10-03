# Calderhead 2014｜受限来源卡（不是全文精读完成）

> Source coverage: Abstract and metadata; public figure captions only
> Extraction confidence: Not applicable — no full-text PDF
> Locator mode: source-limited
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Targeted external check — bibliographic record only
> Card completeness: Partial; full paper and supporting information unavailable

## 01 基本信息

[Paper: PubMed metadata] Ben Calderhead，A general construction for parallelizing Metropolis–Hastings algorithms，PNAS 111(49):17408–17413，2014。DOI：10.1073/pnas.1408184111；PMID：25422442。机构：Imperial College London。领域：并行 MCMC。阅读日期：2026-10-03。代码及 SI：未取得。[来源](https://pubmed.ncbi.nlm.nih.gov/25422442/)。本综述用途限于多提议构造的历史归属。

## 02 一句话概括

[Paper: PubMed abstract] 通过并行产生多个候选，再在候选构成的有限状态链上抽样，作者提出保持目标不变分布的 MH 推广。

## 03 研究问题

[Paper: PubMed abstract] 如何在单条链内部利用并行计算？完整的适用条件：Not assessable from supplied material。

## 04 研究背景与发展路径

[Analysis] 此记录可支持该构造在 2014 年已被提出；不能据一篇摘要断言其为所有多提议方法的起点。系统历史优先权未在本卡核查。

## 05 论文指出的核心痛点

[Paper: PubMed abstract] 作者以传统 MCMC 的顺序依赖为计算限制。其定量成本模型：Not assessable from supplied material。

## 06 核心思想

[Paper: PubMed abstract] 多候选生成 → 有限状态转移 → 整体采样过程。所需权重、转移规则及不变性证明：Not assessable from supplied material。

## 07 方法总览

Not assessable from supplied material。仅有摘要流程；没有凭其他论文补写该文算法。

## 08 核心模块拆解

Not assessable from supplied material。待正文与 SI 确认候选生成、辅助变量、逆向概率与候选选择的关系。

## 09 关键公式与符号

Not assessable from supplied material。没有已验证的正文公式或页码。

## 10 实验设计与证据链

Not assessable from supplied material。[Paper: Abstract] 摘要宣称应用于 MALA、自适应 MCMC 和 HMC；完整实验矩阵、成本、消融和公式尚未核查。网页可见图注仅在 [证据目录](evidence-inventory.md) 登记，未据此形成数值结论。

## 11 结论的正确解释

[Analysis] 当前能引用作者提出一种多提议并行构造；不能把摘要中的正确性主张推广为“任意候选按目标密度加权都正确”。正式正文中的细化讨论应由已全文核查的其他原始来源支持。

## 12 作者明确承认的局限

Not assessable from supplied material。摘要未给出完整限制段落，不能把缺失视作作者没有讨论。

## 13 批判性分析

[Analysis] 当前缺口是证据访问范围，不是已发现算法有误。需获得正文与 SI，检查联合分布构造、有限状态链是否运行至平稳、候选相关性与成本计量，再判断细节。

## 14 学到的知识

### Agent-derived knowledge candidates

[Analysis] 题录确认、摘要阅读、全文证据核查是不同状态。本卡保留这些区别，防止后续写作误用。

## 15 与既有知识的联系

[Analysis] 可与本项目 Glatt-Holtz 2024/2026 的已核查构造对照；二者之间具体定理的包含关系仍待本篇正文验证。

## 16 研究创意

不适用。本卡不提出新创意。下一步是补足正文及相关 SI，随后按原技能重建全文来源包、证据目录和完整卡片。
