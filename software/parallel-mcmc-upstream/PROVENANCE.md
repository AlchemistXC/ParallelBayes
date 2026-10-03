# 固定上游来源

仓库：https://github.com/lindermanlab/parallel-mcmc
提交：5e5b637b1214580d0be4e495215e0e5ed6eb2688
获取日期：2026-10-03
文件：qdeer.py、samplers.py、LICENSE（BSD 3-Clause），未经修改归档。

qdeer.py 文件头另注明继承 Machine Discovery DEER 的提交 17b0b625d3413cb3251418980fb78916e5dacfaa。上游版权和许可保留。

`execution/upstream-reproduction.json` 记录该求解器在本项目独立定义的固定噪声 MALA 映射上的轨迹复现；不代表复现原论文完整性能实验。`scripts/upstream-reproduction.py` 为复现入口。

本项目执行器采用相同类别的对角仿射扫描机制，新增硬递推残差、失败输出隔离、明确回退和成本记录；采用非重叠块，不等同上游滑动窗口。上游状态裁剪/NaN 归零未用于本项目实现。Online Picard 根据 Grazzi 与 Zanella 论文独立实现，没有再分发 ParallelMH 源码。
