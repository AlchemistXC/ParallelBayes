# 本轮参考精度意见专项审查

结论：意见合理，应补充已存在的逐函数资料和参考敏感性；不需要重采样或改变正式参考。

- **证据**：W1采用预选R=12、每轴96阶Gauss–Legendre值；12个保存组合均保留。加密/扩域变化极小，但不是认证总误差界。
- **证据**：独立posteriorDB Stan样本的MCSE比求积变化大很多。它衡量这份有限MCMC均值的估计误差，不能替代求积误差。
- **衍生分析**：同一24份四链重复、4096预算CPU顺序MALA减CPU Pyro NUTS的六个连续函数点损失差，对12个保存求积点和独立MCMC参考点均保持正号。但在假设±2 MCMC-MCSE偏移范围内六者均可翻转；±1.96范围结论相同。此为事后敏感性，不是假设已知参考置信区间。
- **限制**：固定参考BCa区间没有传播参考不确定性；p(100)的原固定参考BCa已包含零。其余五函数不跨零也不是未校正的全局结论。
- **意见公式**：在相同有效集合、同一尺度下D(c+e)=D(c)−2e(平均估计A−平均估计B)/s²正确。符号e是新增参考减原参考；未知真值误差的符号要按此定义。使用各自归一化集合时共同平方项仍能抵消，但会改变所比较的估计对象，不再是本表指定共同集合上的配对比较。
- **已有分析**：L1/L2主分析原已执行±2MCSE，七个已定函数在4096预算MALA/NUTS点差保持正号；共同有效仅6份，不能给出正式BCa区间。L2事件仍未定。
- **应用解释**：采用预先存在的独立参考全部10链，未选择正式拟合。补充alpha、beta、p(0)、p(100)的后验均值和95%经验等尾区间；后验区间与参考MCSE分列，分位数的计算误差未量化。
- **未改变**：冻结协议、任务状态、MCMC输出、正式误差参考和区间规则。

## 推荐正文一句

W1的MALA与Pyro NUTS损失差在全部已保存求积参考及独立MCMC参考点下保持相同点排序，但对借用MCMC误差尺度的假设参考偏移并不稳健；因此该比较仍限于所用数值参考，不能视为已认证的真值排序。

## 可重复命令

```sh
python scripts/analysis/revision_reference_tables.py \
  --statistics /path/to/formal-statistics \
  --wells-reference-binary /path/to/wells-reference-01/values-f64le.bin \
  --output benchmark/analysis/outputs/manuscript-review-v2 \
  --tex manuscript/software/revision-reference.generated.tex
```

具体来源及所有读取SHA见reference-summary.json；reference-validation.json记录核查项及本脚本SHA。没有新采样调用。
