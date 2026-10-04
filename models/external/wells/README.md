# 外部案例：公开水井转换数据的距离logistic模型

2026-10-05｜F4输入选择，尚未运行本项目采样或性能实验

选用posteriordb的`wells_data-wells_dist100_model`，固定上游提交`91027f9cdd13b7e76283fec3f2898f59d4b83ec4`。数据包含孟加拉国3020户家庭的换井选择；该模型仅使用是否转换与距离，参数为截距alpha和每100米距离的系数beta。它来自Gelman与Hill的ARM教学案例。这里评价计算方法，不作新的公共卫生因果结论。

选择理由：它未用于ParallelBayes历史开发；数据、Stan实现、预处理、参考抽样和生成记录可公开核对；二维参数适合用独立数值积分进一步核查有限MCMC参考。没有依据ParallelBayes的速度结果挑选案例，也不把它称为昂贵似然或GPU有利案例。此前检查了同数据增加arsenic的三参数模型，因没有库内参考而没有作为首例；未比较其运行性能。

## 必须保持的目标

原模型将距离除以100，使用Bernoulli-logit似然，**没有显式正态先验**。因此不能直接调用当前内置`logistic`目标：后者会加入N(0,2.5²)先验，改变目标。新示例必须显式实现原始平坦先验、alpha/beta顺序和恒等变换，并验证后验可积性。参数无关常数可以不同，目标与梯度必须一致。

实施顺序：核对数据/模型与参考哈希；检查可积性及数据秩；新增独立NumPy密度/解析梯度、原生torch目标和Stan密度对照；核验实际随机数组下两对执行器；在同一公开模型上准备有限参考误差和数值积分对照；再通过R整批运行。性能任务及函数集合另行冻结，不沿用Windows-v1身份。

## 已检查的参考来源与范围

上游提供10链×1000个保存样本；元数据记录每链20000次迭代、10000次预热、thin=10，Stan 2.36.0。元数据报告两参数Rhat约1.0005/1.0003、零发散。这些是上游报告，目前只检查了归档结构，不能当作本项目已复算的诊断或解析真值。后续应从原数组重新计算所选函数及参考误差，保留不同包版本的影响。

模型元数据标明BSD3，上游仓库为BSD-3-Clause；数据元数据未列单独许可，保留其原始来源链与仓库许可，不擅自加上新的授权声明。模型和数据出处为[固定版posterior条目](https://github.com/stan-dev/posteriordb/blob/91027f9cdd13b7e76283fec3f2898f59d4b83ec4/posterior_database/posteriors/wells_data-wells_dist100_model.json)、[Stan模型](https://github.com/stan-dev/posteriordb/blob/91027f9cdd13b7e76283fec3f2898f59d4b83ec4/posterior_database/models/stan/wells_dist100_model.stan)及[参考生成信息](https://github.com/stan-dev/posteriordb/blob/91027f9cdd13b7e76283fec3f2898f59d4b83ec4/posterior_database/reference_posteriors/draws/info/wells_data-wells_dist100_model.info.json)。

## 可移植获取

`source-manifest.json`列出8个固定文件的大小和SHA256，包含许可、模型、数据、参考及元数据。Git不保存这批上游原始数据副本。用原生Python标准库即可下载到独立目录：

```text
python scripts/completion/fetch_wells.py --output downloads/posteriordb-wells-91027f9
```

已有文件逐一校验，不覆写不同内容。首次获取和后续缓存核验分别记录。下载成功不是目标/采样器验证；当前F4仍在准备阶段。
