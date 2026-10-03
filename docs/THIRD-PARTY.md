# 来源与许可

本地研究代码采用 MIT，最终公开作者/维护者身份尚待确认。R DESCRIPTION 的项目名和 example.invalid 地址为本地候选元数据，不是用户真实身份，未提交CRAN。

| 组件 | 锁定来源 | 许可/处理 |
|---|---|---|
| quasi-DEER 来源归档 | lindermanlab/parallel-mcmc, 5e5b637b1214580d0be4e495215e0e5ed6eb2688 | BSD 3-Clause，原许可与版权随文件 |
| BridgeStan | 2.7.0官方源码包 | BSD 3-Clause；依赖Stan/Stan Math/TBB等保留各自许可 |
| Stan stanc3 | 2.37.0官方mac/Linux二进制 | Stan项目许可随上游发行包；本地使用，不改变二进制 |
| JAX / jaxlib | 0.6.2 | Apache-2.0，使用发行wheel |
| BlackJAX | 1.2.5 | Apache-2.0，使用发行wheel |
| NumPy / SciPy | 2.2.6 / 1.15.3 | BSD条款随发行包 |
| R reticulate / posterior | renv.lock固定 | 依赖本身许可保留，不改许可证 |
| Online Picard | Grazzi与Zanella论文算法 | 本项目独立实现；未复制许可不明的ParallelMH代码 |

图表QA脚本由用户已安装的绘图技能提供，仅随本地研究材料用于复核；不将其私有来源视为公共发布授权。正式公共发布前须另核这部分工具的分发范围，或保留为开发依赖。GPU交接在用户自己的两台计算机之间进行，没有公开上传。

CPU审查独立复现包不分发私有技能或图表QA脚本。生产绘图仅依赖matplotlib和项目独立编写的layout_check.py；本地作者QA可经环境变量接入技能检查器，输出报告随证据保留。
