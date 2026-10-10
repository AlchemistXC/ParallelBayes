# 事实、依据与未知

## 已有实验事实
- 42份H1/MALA路径失败：40quasi-DEER、2顺序；接受事件无失配。现有证据仅证明原路径标准超限，未给四函数差。[review/WINDOWS-COMPACT-FAILURE-AUDIT.md]
- 按同设备/预算/输入匹配另一MALA执行器，共80条已有任务：42失败+38有效，覆盖13个原输入标签；设备与预算不是独立重复。[已校验H1.frame.ndjson，统计清单d928a497…]
- 长预算NUTS105/216失败，全部BrokenProcessPool；部分有效A1/G2旧ESS分配异常，不能认定105根因相同。[review/WINDOWS-COMPACT-FAILURE-AUDIT.md]
- W1采用12组普通浮点求积；现有变化小但未认证。L2在262144相关参考样本中符号事件恒零。[revision-reference.generated.tex]

## 方法依据（已核对原始来源）
- Windows Job通知存在不同保证；没有收到普通completion-port通知不能证明没有超限。https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
- Arb支持带误差包络的计算，但一维积分接口需要正确处理解析性，不能把普通嵌套积分误当认证二维积分。https://python-flint.readthedocs.io/en/latest/acb.html
- 重要性采样需正确计算全提议密度；未知归一化常数采用比率估计，MCSE不是认证误差界。Owen第9章：https://artowen.su.domains/mc/Ch-var-is.pdf

## 未知与禁止断言
不能预期所有H1函数差小、旧ESS必是崩溃根因、W1一定可高效认证、L2新参考必达标。不把固定种子等同实际NUTS轨迹一致；跨设备复制不新增n。S3方法与阈值在后继数据产生前冻结，但设计已知旧结果，不能称全程前瞻预注册。
