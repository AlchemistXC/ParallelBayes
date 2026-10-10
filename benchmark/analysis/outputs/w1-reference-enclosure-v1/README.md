# W1数值包络：完成的汇总与重建输入

2026-10-11。两规则七函数均达到冻结精度；本目录是已核验原件的轻量汇总，不含SQLite积分单元。`source/checksums.json`保留完整原清单，清单所列其余文件需从原始证据包取得；不能把本目录当作全原件。

从仓库根目录，以Python 3.12运行：

```sh
python scripts/analysis/report_w1_enclosure.py --source benchmark/analysis/outputs/w1-reference-enclosure-v1/source --audit benchmark/analysis/outputs/w1-reference-enclosure-v1/audit --output output/w1-report-rebuilt
```

输出目录须不存在。报告生成读取已核验摘要、精确端点与保存的敏感性行；不重新积分或采样。完整独立端点/分区核验还需本地 `w1-reference-evidence-v1.tar`（303360000字节，81个内容成员及MANIFEST）。归档尚未上传；SHA256为 `c1bf12eb937ba57582647c7eb81cea21d01b6f204e1305d459cdc1175bd368d1`。

`archive-receipt.json`记录打包时状态，保留当时portable_rebuild_verified=false；随后实际完成的搬移重建由独立 `portable-rebuild.json` 记录为true。两份回执时序不同，均不覆盖。重建在同一Mac的独立目录完成，不称异机或外部团队复现。
