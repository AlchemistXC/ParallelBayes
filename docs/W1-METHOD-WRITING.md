# W1参考包络的论文方法稿

**2026-10-11更新：** 双规则计算、完整独立核验、零新增恢复及本地归档搬移重建均已完成，七函数全部达到冻结精度，见[最终结果与证据](W1-REFERENCE-RESULTS.md)。方法和结果已纳入当前论文修订。下文保留开发与等待阶段的历史记录，其中“尚未完成”不代表当前终态。

2026-10-10。完成三页可独立编译的方法说明，供最终W1结果通过独立核验后纳入SI。当前正文、SI及其已交付PDF没有据此更新数值结论；两种求积共用目标、导数和尾部实现，其一致性不称完全独立的正确性证明。

## 内容与依据

- `manuscript/software/w1-enclosure-method.tex`：原二进制数据与仿射坐标、七函数、沿事件边界拆分有限域、两点Gauss/Simpson张量余项、球算术与舍入、凹性支持平面尾界、矩尾项、正归一化常数和参考敏感性。
- `manuscript/software/w1-method-references.tex`：NIST DLMF一维求积公式及Johansson的Arb原始论文。公式常数按完整单元宽度换算；期刊元数据与作者预印本分开核对。
- `manuscript/software/w1-method-preview.tex`：独立预览入口。正式整合时只插入方法片段和两条参考，正文仅保留结论所需的参考区间及排序影响。

论文方法与冻结源码逐项对照，8份冻结源文件SHA均未变，未重跑已通过的数值组件测试。当前Gauss规则已因达到目标结束；同一原积分会话继续Simpson规则，尚无完整SUMMARY、最终独立核验及双规则结果表。此状态不等于最终认证完成。

## 编译与版式

使用Tectonic 0.17.0成功编译，最终轮次无未解析引用或超宽警告。全部三页经MuPDF 1.26.5以108 dpi渲染后逐页检查，中文、公式、引用、页眉及页码完整。首次使用的捆绑Poppler缺少Adobe-GB1映射，问题限于该次渲染；未把缺字图作为通过证据，也未改动数值环境。最终PDF为182868字节，SHA256 `6eacd0f4be2d08998be2d18a5605329a762afbeaf892cf3fa1eb7584362ed474`。

本地预览、编译完整记录和页图在主数据工作区的 `output/targeted-followups-v1/w1-method-preview-v1/`；Git只纳入三个TeX源文件、说明及小型核验记录。可从仓库的`manuscript/software`目录使用Tectonic编译`w1-method-preview.tex`，无需原研究数组。

证据索引：`execution/targeted-followups-v1/qualification/w1-method-writing-v1.json`、`w1-method-citations-v1.json`。这一稿件工作不增加MCMC调用或被积函数评价。下一步仍为原积分完成后的独立核验、参考敏感性、恢复零新增、便携归档重建和正式论文整合。
