# H1四函数路径差补充结果

2026-10-10。S1已完成。既有80条任务（42失败、38配对有效输出）全部重放和比较，共检查1,130,496个转移位置；原13个输入标签及其设备/预算配对不新增独立重复。接受事件、符号函数均未出现失配，参数变换复算与保存结果的最大差为0。

## 主要结果

下表为剔除原512步后，在全部80项中取得的最大值。逐点差和均值差的最大值不一定来自同一任务；完整任务ID和四链明细在源表中。

| 原参数函数 | 最大逐点绝对差 | 最大四链合并均值绝对差 | 最大单链均值绝对差 |
|---|---:|---:|---:|
| v/3 | 0.00190956 | 1.07757e−7 | 4.35023e−7 |
| tanh(v/3) | 0.00145182 | 4.68970e−8 | 1.90353e−7 |
| I(x1>0) | 0 | 0 | 0 |
| cos(x1 exp(−v/2)) | 0.00326872 | 3.07812e−7 | 1.23163e−6 |

最大采样坐标差仍为0.00572867。结果说明，在这批指定轨迹上，局部差与函数均值差的量级不同；较小均值差既可能受局部差出现次数影响，也可能包含符号抵消，因此一并保留RMS与平均绝对差。不据此宣布数值失败在所有推断任务中无关紧要；NumPy为浮点参考，42项原失败继续排除，旧主网格及参考文件保持原样。

## 图与完整数据

[配对与平均差图](../benchmark/analysis/outputs/h1-function-path-companion-v1/h1-function-pairs.pdf)：左图为40组相同输入/设备/预算的顺序与quasi-DEER配对；右图分开显示逐点最大差和四链平均差。三个连续函数均显示全部任务，符号函数在所有完整路径上差为0，另列完整CSV。坐标使用保留真实0的symlog，虚线为两轴数值相等。没有置信区间或显著性检验。

[位置图](../benchmark/analysis/outputs/h1-function-path-companion-v1/h1-function-locations.pdf)：完整路径含原剔除前缀，每任务划为128个连续区间，颜色为区间内全部链/位置的最大绝对函数差。80任务全部保留；横轴是相对路径位置，不是相同转移数。两图观察性选择见各contract.json；完整四函数、全程/保留段、每链/合并3200行在[差异表](../benchmark/analysis/outputs/h1-function-path-companion-v1/function-differences.csv)，行号见task-index.csv。

## 验证与资源

5项资格检查通过，0失败/跳过；另直接从保存差数组重新汇总全部3200行，与JSON逐项一致。恢复核验复用80项、新增0，162件既有分析资产哈希不变。两图对齐检查通过；PDF最小字号8.5 pt，碰撞检查0失败/警告，已逐面板视觉检查。

原分析约31.19秒，进程抽样观察RSS峰值约365.27 MiB；该时间只记录本次分析作业，不是采样加速证据。新原始差数组及记录约46.34 MiB，低于1 GiB工作配额。原调用和新验证都没有启动采样后端。

## 身份与复现

冻结实现提交`d901e21`；协议[h1-function-path-companion-v1.json](../benchmark/protocols/h1-function-path-companion-v1.json)，SHA256 `4d46fad516b277962b2dbb23cb7eaa644c4e832b3526b936e0f41555f7e4c3a6`。原Windows执行3a37a89及交付94bebec不变。运行需要已校验的原formal目录与外部manifest；其获取边界仍见[紧凑复现文档](COMPACT-REPRODUCTION.md)。

从仓库根目录运行：

```sh
python scripts/analysis/h1_function_paths.py \
  --protocol benchmark/protocols/h1-function-path-companion-v1.json \
  --evidence "$PB_FORMAL_EVIDENCE" \
  --manifest "$PB_FORMAL_MANIFEST" \
  --selection execution/targeted-followups-v1/selection.json \
  --output "$PB_H1_OUTPUT"
python scripts/analysis/report_h1_function_paths.py \
  --source "$PB_H1_OUTPUT" --output "$PB_H1_REPORT"
```

三个PB变量由使用者设为本机证据/输出绝对路径。原件与输出目录必须分离；再次运行第一命令逐项校验并复用结果，报告器则要求新目录，防止覆盖图表版本。依赖版本在协议内，绘图另需matplotlib。归档校验与实际命令见本目录对应delivery.json。

S2 Windows故障定位和S3 W1/L2参考改进仍未完成，不能由S1结果替代。论文的统一增补待其余工作结项后进行；本报告可作为独立补充材料。
