# 已选MH核与显式设备的就绪核验

2026-10-05。此项补正式推断前的一个缺口：Mac预算pilot只运行了已选步长的顺序MH，旧Windows机制pilot也不能替代已选仿射目标与时间执行器组合的核验。新增研究接口明确指定CPU或CUDA，不修改任何旧冻结运行器。

## 身份与设计

采样/运行器源码`779b8e4c56ba62939f365f6d723d71319dead221`，保存数组伴随分析源码`fc48d76`。三个协议分别是：

| 协议 | 规范JSON SHA256 | 当前证据 |
|---|---|---|
| selected-mh-readiness-mac-v1 | 12f3cdcc1c68ffbd48ba8bb1209271f359572979bfc60992cad88ed34424c34b | 实际完成 |
| selected-mh-readiness-windows-cpu-v1 | de1a3bdb35fef84c98fe502cc925574f9092f16da5959f691490b5f1ee55d2e5 | 已冻结，未收到实测 |
| selected-mh-readiness-windows-cuda-v1 | e29d26f2d5836c91001be9bfd5a7c6f156b54c96daf2cbaeaa30fb04d32acf93 | 已冻结，未收到实测 |

共同九目标G1/G2/A1/L1/L2/H1/H2/M1/W1，精确沿用预算pilot的固定仿射坐标与已选RWM/MALA步长。每目标四链、256步；顺序RWM/MALA各一条工作流，Picard和quasi-DEER分别运行窗口8、32，共54工作流、36组成对检查。初值、提议噪声、均匀随机输入和求解方向以九份NPZ保存（合计1550889字节），新Philox命名空间7391000/7392000/7393000。M1首坐标为-5,+5,-5,+5。

同一目标的窗口、执行器和平台共享实际输入，不增加独立重复数；每目标只有一份技术核验输入。没有新调参、正式误差估计或速度比较。保存数据的计时包含同步及原有成本字段，但没有做缓存重放或交错性能测量，不用于效率排序。

原生平台、包版本、源文件和输入哈希在运行前检查，CUDA不可用时拒绝CPU替代。每个目标先验证密度、梯度、HVP和参数变换；每条路径保留接受事件、拒绝自环、求解记录及完整独立NumPy核验，失败不回退、不重抽输入。原容差、最大迭代和2048MiB数组工作区估计守卫不变；没有总运行时长截止。

## Mac实测与局限

54/54工作流满足输出标准，36/36成对检查通过；从保存数组重建独立NumPy参考后，54条工作流接受事件零失配，最大路径差约3.4631e-10，仍按每链原容差判定。126项任务资产哈希通过，实际恢复新执行0目标、135个终态文件哈希不变。恢复前summary保留，匹配伴随重放引用的摘要身份。

H1/MALA第三链（从零计数为2）在256步内接受0次；三个执行配置共享这一结果。这是一条链的同输入重放，不是三次独立失败证据。数值通过不代表充分探索。A1/RWM在这份新输入下四链接受79/82/84/79次；该事实不覆盖或改写历史A1全拒绝实验，也不构成模型已经收敛的证明。

G2的`slogdet`在原日志中发出除零、溢出和无效值警告；伴随分析以`always`捕获时，G2/A1均出现这三类警告。实际返回值有限。对冻结的正对角下三角因子，独立用标量对角对数之和核查，G2/A1与返回值分别相差2.84e-14和1.42e-14，完整坐标目标身份一致。所有九目标检查均通过。警告原样保存；这限定了它在本次行列式数值上的影响，没有声称已完全定位底层库警告的原因，也没有更换因子或关闭浮点检查。

新增行为检查为设备目标接口CPU 1通过/CUDA 1跳过，以及整批采样、失败隔离、恢复和损坏证据拒绝1通过。后者随保存数组分析扩展而重复运行，不能重复累加测试数。18条torch弃用警告保留，不通过更改已冻结核心消除。本Mac结果不能替代Windows CPU/CUDA实测。

## 重放与后续

```text
python scripts/completion/selected_mh_readiness.py run --protocol PROTOCOL --inputs INPUTS --source WELLS_SOURCE --output NEW_RUN
python scripts/completion/audit_selected_mh.py --protocol PROTOCOL --inputs INPUTS --run RUN --source WELLS_SOURCE --output NEW_AUDIT
```

运行恢复使用相同命令追加`--resume`，先确认真实进程已经结束；只允许匹配源码、输入、环境和终态哈希时复用。独立分析支持在CPU上复核保存的CUDA数组，不会替代CUDA性能测量。完整数组在独立本地证据目录，紧凑回执见`benchmark/analysis/outputs/selected-mh-readiness-v1/`。

Windows入口为`handoff/windows-completion/CODEX-PROMPT-F3-MH.md`。下一步仍须接收Windows结果并冻结正式预算/重复与误差处理。256步通过不能保证长路径通过；每条正式路径仍需执行原完整核验。此项不开发GPU NUTS或自动配置选择器。
