# Nested R-hat：公开稿附录补读

2026-10-03。此记录附属于 [正式正文卡](../margossian2025/paper-card.md)，不另计作品或已全文阅读版本。

来源为 [arXiv:2110.13017v6](https://arxiv.org/abs/2110.13017v6)，2024-05-30，41 页。[本地 PDF](../../../references/downloads/margossian2024v6/PDFs/Nested_R-hat_arXiv_v6_appendix_companion.pdf)。SHA-256：3160740b7eb7114fd87c369cb87ebb69407f2adaa33bf0adfdb279668a207d4d。由 nature-downloader 原脚本带 --si 获取，并由 nature-paper-card 原 prepare_paper.py 生成 [来源包](source_bundle.json)，验证为 valid。

本次阅读范围为 p.23–37（讨论与 Appendix A–C），p.37–41 书目只追踪来源。未逐段对齐公开稿正文与正式版；公开稿附录**不能标成已取得 DOI 10.1214/24-BA1453SUPP 的正式 SI**。

| 位置（本公开稿 PDF 页） | 证据与结论 | 边界 |
|---|---|---|
| p.25–27，Appendix A，Lemma 3.3、Corollaries 3.4–3.5，Eq.31–32 | 大数定律沿组数 K，组内条件独立给出 1/M；N=1 时组内时间方差项消失 | 正自相关用于特定平稳下界；共享自适应并不凭此自动满足条件 |
| p.27–29，Theorem 3.8、Corollary 3.9，Eq.33 | OU 显式解联系初值方差、偏差与诊断可靠性 | Gaussian 连续时间特例，不是任意后验的一般证书 |
| p.29–30，B.1、Figure 11 | 标准高斯及双高斯；MALA 步长 0.04，M=16、K=1024，总 16384 链；高斯的初始方差界较准确，混合例界保守 | 大量不同初值可能碰到两模态，不能据此保证模式发现 |
| p.30–34，B.2、Lemma B.1、Theorem B.3、Eq.34–37、Figure 12 | 普通 R-hat 的积分均值可靠性分析 | B/W 单调下降被列为假设 A1（作者猜测总成立）；A2 另约束阈值。不能省掉假设把结论推广 |
| p.34–37，Appendix C | 6 个目标维度为 2、25、10、45、100、501；药代模型参照用 2048 链，各 1000 预热+1000 采样，ChEES-HMC，ESS 约 6–10 万 | 参照仍是 Monte Carlo 估计；并非精确已知真值。双峰均值/方差才可解析计算 |

[Analysis] 对综述的影响：继续保留“诊断不能证明无偏”“初始化设计与目标泛函很重要”的结论。公开稿附录已补足部分证明链和模型设定，但没有消除共享调参下条件独立、正式 SI 版本一致性这两个待核点。未运行代码或重做实验。
