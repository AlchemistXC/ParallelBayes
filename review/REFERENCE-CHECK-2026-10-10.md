# 终稿定向引文核对

2026-10-10，采用 nature-ref-verifier。范围为新方法和诊断论述所用的几项出版信息；不是全参考表重新精读或全部元数据已核验的声明。

| 条目 | 原始来源核对 | 处理 |
|---|---|---|
| Modrák等，SBC测试量 | [Crossref](https://api.crossref.org/works/10.1214/23-BA1404)与[出版方](https://doi.org/10.1214/23-BA1404)的标题、作者顺序、2025年20卷2期461–488页一致 | 补齐正式卷期页年；DOI含23不代表卷年2023，出版方另记首次在线2023-11-23 |
| Zoltowski等，序列长度并行 | [NeurIPS正式页](https://proceedings.nips.cc/paper_files/paper/2025/hash/202886ee1c9ca735cb5bff3a00a69883-Abstract-Conference.html)与[Crossref](https://api.crossref.org/works/10.52202/085713-0751)的标题、五作者顺序、2025及DOI一致；页码冲突 | 出版方BibTeX为22242–22277，Crossref为25284–25319。保留当前卷38及可解析正式链接，暂不新增页码；不默选其中一个当成多源一致 |
| Robnik与Seljak，LAPS | [PMLR正式页](https://proceedings.mlr.press/v300/robnik26a.html)正文与BibTeX给2026、300:2719–2727 | 当前字段一致；本轮仅同一出版方，未称两个独立来源核对 |
| Gonzalez等，因果前缀依据 | [作者arXiv记录](https://arxiv.org/abs/2407.19115)可访问；正文引用仍固定v3 | 本轮未改变定理或重做全文研读，沿用10月9日逐式核对记录 |

出版方网页首次抓取及BibTeX工具解析均曾失败，随后通过出版方索引与直接元数据请求取得记录。Crossref两项HTTP 200；原始响应保留本地，提取字段和SHA见`benchmark/analysis/outputs/citation-check-20261010/verification.json`。不把网页抓取失败标成文献不存在。

本轮只补参考字段，未更换采样器、研究函数或实验身份。新增失败机制论述使用Pyro 1.9.2固定版本源码，不能以当前版本行为代替已测版本。

修改后正文13页、补充22页由已有Tectonic编译成功；本轮只补字段，末页均已渲染审读。完整研究的原始数据重建仍在进行。
