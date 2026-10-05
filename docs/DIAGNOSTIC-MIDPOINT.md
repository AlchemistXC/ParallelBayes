# 二进制输入后的两项 Rhat 差异：折叠中心最小复现

2026-10-05｜F1 新增伴随分析｜没有重新采样或更改原 Windows 诊断

## 新发现

两项剩余差异实际来自同一配置：H2、RWM顺序、512步、重复3，分别在CPU和CUDA运行。丢弃前128步后，q2为384次迭代×4链；两端保存的该数组逐值相同。它们不是两份独立的差异证据。

`posterior` 1.7.0 的 `rhat()`取秩正态化split-Rhat及折叠后split-Rhat的最大值；折叠使用`abs(x-median(x))`。本样例的未折叠值为1.1777201953723706，最终值由折叠分量决定。[版本对应源码](https://github.com/stan-dev/posterior/blob/v1.7.0/R/convergence.R)

| 折叠中心的计算/取值 | float64十六进制表示 | 折叠Rhat |
|---|---|---:|
| 本机Mac R 4.6.0的`median(x)` | `0x1.7701bac434f10p-10` | 1.4085688369053788 |
| 对中间两数求精确有理数均值，再正确舍入到float64 | `0x1.7701bac434f11p-10` | 1.4082223724409619 |

这两个中心只差一个ULP（约`2.1684e-19`）。但折叠后有5个观测的秩改变：4个重复值的平均秩从3.5变为2.5，另一个值从1变为5。固定其他计算，仅切换这个中心，已经能在Mac上重现原Mac与原Windows记录的两种Rhat；第二种与归档Windows值在`1e-11`绝对/相对比较容差内一致。

本机`median()`调用中间两数的`mean()`；`mean(middle)`给出较低的中心，而`(middle[1]+middle[2])/2`给出正确舍入中心。使用Python `Fraction`从原float64位值构造精确中点，避免将NumPy结果未经检查视为真值。R公开实现中均值还包含累加后的修正项，累加精度是需要核对的运行时因素。[R源码镜像](https://github.com/wch/r-source/blob/trunk/src/main/summary.c) 这里引用的是机制背景，不能以trunk代替两台机器的实际构建记录。

## 已确认与尚待确认

已确认：本地存在完整的“中点末位变化→5个秩变化→两种历史Rhat”的数值链条；无须修改样本、接受事件、链次序或统计包即可复现。Mac的二进制读取—写回字节哈希也完全一致。

Windows第二轮已补齐并经Mac接收核验：R4.6.1/ucrt、posterior1.7.0，原生中位数为`0x1.7701bac434f11p-10`、Rhat为1.40822237244096；将显式中心降低一个ULP得到1.40856883690538，5个秩改变；12KiB输入及回写字节一致。`.Machine$sizeof.longdouble=16`、`longdouble.digits=64`。见`benchmark/analysis/outputs/completion-f1/windows-01/`及[接收报告](WINDOWS-ROUND2-INTAKE.md)。这关闭F1的有限复现与平台回执门槛，保留运行时局限；不声称特定底层库/编译器根因已经证明，也不将其归因于CUDA采样器。

这不是把较小的Rhat作为修复目标。两种值均远大于1.01，原来的混合不足判断不变。显式中心计算仅是诊断敏感性实验；原Windows诊断、Mac CSV/二进制复查及本次结果分别保留。没有给所有模型强制取整或替换默认`posterior::rhat()`。

## 小型复现包

`benchmark/fixtures/rhat-midpoint-v1/`保存12KiB的原生float64样例、来源任务、协议身份、原始NPZ哈希、精确中点和预期对照。样例SHA256：

`5fc66d60bb22dbc98e75feb213fe936a912ce0cdd7ff3b21adda0515b324460d`

根目录命令：

```text
python scripts/completion/run_rhat_case.py --case benchmark/fixtures/rhat-midpoint-v1 --output output/completion/rhat-new-attempt --rscript Rscript
```

Python包装器只用标准库；R需要原有`posterior`1.7.0及`jsonlite`，不需要torch、JAX或GPU。包装器先校验样例，R输出诊断分量、5个变化的秩、机器信息和二进制回写；包装器再验证回写SHA256。已有输出拒绝覆盖。完整样例可由`prepare_rhat_case.py`从通过归档验证的Windows证据重建。

Mac正式小样例回执见`benchmark/analysis/outputs/completion-f1/mac-02/`。首次运行因R.version元数据带`simple.list`类而无法序列化；修正为显式去除该类后通过。首次失败日志仍保留，诊断数值计算未变。
