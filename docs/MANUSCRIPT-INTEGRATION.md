# 当前中文稿整合与独立构建核验

2026-10-05；正文/图件/构建源码提交 `6d9029e5e1b979e8d596cfd8f722fbaf7007c8c9`，前继主修订 `ba48a41`。使用nature-writing整理论证和证据范围、nature-figure检查当前架构图、latex-compile构建已有多文件项目。本轮没有采样、重新计时或新增独立统计重复。

## 本次完成

[23页中文PDF](../output/software-paper/软件与基准研究-整合修订.pdf)与[LaTeX源](../manuscript/software/软件与基准研究.tex)统一为“ParallelBayes：时间并行MCMC的可核验实现与成本评估”。摘要围绕同路径执行与推断可靠性，保留Mac CPU负结果、CUDA Picard缓存收益及其全拒绝/混合不足边界。

当前能力表、README及说明书明确：torch CPU/CUDA的对应MH组合已有实测；Pyro CPU九目标串行/spawn是独立研究CLI，尚非通用pb_sample的torch NUTS选项。Stan仍仅CPU顺序；GPU NUTS、Windows Stan编译、融合控制未核验。新架构图单独保存为architecture-current；旧图、原CPU/results/revision和Windows首轮生成输入原字节保留。

正文加入跨系统接收结果：108份MH路径/事件满足原标准，但60份变换输出逐位检查仍失败；F1实际Windows回执补齐；原始输入派生差异使F2的192工作流仍未执行。水井目标/接口已完成与正式应用比较未完成分别写明。新成本接口作为后续协议方法准备，不追溯替换旧bootstrap或计时口径。

[写作契约](../manuscript/software/writing-contract.md)与[主张—证据表](../manuscript/software/claim-map.md)已同步。逐任务日志和开发过程留在仓库，未将技术批次n=1绘成正式性能区间。Pyro文献元数据根据其JMLR原始页面核对。

## 实际验证

- 两份生成文本从各自保存JSON逐字节重建；79个冻结数值文件哈希不变。
- 新图为160×124 mm单幅逻辑示意，7 pt可编辑文字，PDF/SVG及600 dpi PNG。渲染碰撞检查0失败/0警告；对齐为单幅不适用。23个文字与填充框包含关系均为预期。
- 图源检查19通过、2警告：无TIFF但交付矢量PDF与PNG预览；静态检查将160/25.4误读成4064 mm，实际PDF宽160 mm。未指定期刊，不据默认183 mm改动正文宽度。最终图与各改动页已视觉检查。
- 系统TeX Live首次因缺zhnumber.sty退出；没有安装宏包。已有Tectonic 0.17.0使用缓存中文资源成功编译。初稿能力表的Underfull经列格式修正消除；最终编译轮次无未解析引用、Overfull或警告。
- 搬移到新目录的13个输入全部校验，23页提取文本及72dpi逐页像素与活动项目编译一致。PDF文件哈希不同，未声称PDF字节可重现；文本/渲染相同不代表原始实验被重新复算。

最终PDF SHA256：`e66cd300a7044365b346772a859e9b5c67edc686e8c55a215cff1b6e1e7b2f4b`。
核验摘要、构建日志、输入清单及图QA在[`benchmark/analysis/outputs/manuscript-integration-v1/`](../benchmark/analysis/outputs/manuscript-integration-v1/)。未重复运行已通过的数值测试，因为本轮没有改变数值实现。

## 构建与边界

项目根运行：

```text
python scripts/completion/write_completion_tex.py
python scripts/completion/write_intake_tex.py --output manuscript/software/intake.generated.tex
python scripts/completion/plot_current_architecture.py --output figures/software
python scripts/completion/build_paper_bundle.py --output NEW_PAPER_INPUT_DIRECTORY
```

图需要Python/matplotlib及项目自有layout_check；论文编译需要已有Tectonic或具备ctex/fandol的XeLaTeX。从`manuscript/software`目录运行`tectonic 软件与基准研究.tex`即可。旧定量图在仓库中已生成，重算它们须使用对应历史分析/原始证据；此构建器不调用MCMC。

本机`output/research-completion/paper-inputs-integration-v1.tar`含13输入加manifest，共14文件，296960字节，SHA256：`6d84d6ce72cee15968a15f3b0da15fadad42fff1fbbee697704b9b7b12919a37`。这是**独立论文编译包**，不是完整论文结果复现包；没有包含大原始数组或私有技能。可从上述提交重新生成，未自动公开Release。

当前23页PDF、旧21页“收尾修订”和20页回传稿并存，不覆盖历史PDF。F6完成的是当前证据整合与构建，不是投稿终稿。F2原生Windows机制补充、Windows运行器/最大任务、正式共同精度研究、统一候选的双平台干净安装、全部证据独立重建及作者终审仍待完成；F3/F5/F6不关闭。
