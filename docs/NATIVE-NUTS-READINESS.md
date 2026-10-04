# 原生CPU NUTS九目标就绪核验

2026-10-05。目的：在原生Windows上核验成熟CPU NUTS的模型重建、明确初值/随机状态、真实spawn多进程和完整成本记录，补正式同机比较的基线门槛。没有GPU NUTS、统计收敛或速度声明。

## 冻结设计与范围

源码b7791e08e03449bd34ee764dc560bd3934044aeb。Windows身份`nuts-native-readiness-windows-v1`，规范JSON SHA256 `6c6aadaed20f792715ab9b8b3a3bbb02181f74ecbe259aa1bb3302e370c78220`；Mac伴随身份`nuts-native-readiness-mac-companion-v1`，SHA256 `7e5c8e60afaaba73d762f7d435d01ec8916c7a4e17df7c5e0dde276ff623a15e`。两份协议和各九份实际输入已保存。

G1/G2/A1/L1/L2/H1/H2/M1/W1，各一份四链初值/种子；同目标顺序四链和最多四worker运行分别保存128步预热、64步保留值、适应记录和初始/最终torch RNG字节。父进程和子进程每进程一个torch计算线程，子进程interop一个；记录实际PID，不宣称独占物理核。对角质量适应、目标接受率0.8、最大树深8、内存守卫2048MiB，无总时间截止。

两种执行共享实际初值/种子，比较六类数组的dtype/shape/字节：原参数样本、无约束样本、预热、初始RNG、最终RNG和初值。跨平台不要求逐字节相同，也不与MH共享轨迹。每目标的一对运行是技术执行比较，不是两个独立统计重复。失败比较不成为正常推断样本；原始输出和部分子链保留。

输入沿用已固定的几何，新的Philox命名空间7381000/7384000，M1首坐标-5,+5,-5,+5。Mac和Windows九份实际输入相同；这只用于配对可移植核验，不新增独立重复。

## Mac已完成的实际检查

九目标均完成顺序/spawn比较，54项数组比较逐字节一致，每目标均观察到4个worker。18份历史函数二进制R输入回写一致，R4.6.0/posterior1.7.0。七目标至少有一个有限Rhat>1.01，L2/M1/W1包含不可判定函数；两种执行的诊断相同但统计问题仍存在。R另报告8条为避免不稳定估计而限制ESS的警告，原日志保留；这些短链ESS不用于正式效率排序。

实际恢复新执行0目标，126个终态文件哈希不变。原summary另存，对应收集器引用的原summary哈希。新整批接口检查先在缺实现时失败，随后在真实顺序/多进程、恢复、损坏证据拒绝及诊断传输上通过；这是同一个测试随两个实现步骤重复运行，不是新增两项独立测试。早期pytest缓存写入警告保留，后续禁用无关缓存；未更改数值环境或系统权限。

新运行器源文件及61个依赖文件按协议逐项核对，精确数量见plan-receipt.json。Windows身份在Mac被原生平台守卫拒绝，这只检查守卫，不证明Windows运行。当前Windows实际核验仍待回传。

## Windows执行及后续

使用[可直接转交的提示词](../handoff/windows-completion/CODEX-PROMPT-F3-NUTS.md)，复用原生Windows已验证的torch2.13.0+cu130、Pyro1.9.2、NumPy2.2.6、SciPy1.15.3与R4.6.1/posterior1.7.0。不得安装/升级进旧冻结环境，也不运行freeze覆盖协议。若已有F1/F2/F4任务活动，先完成并保存，不并发性能任务。

运行器有run/--resume、collect、verify-diagnostics入口；R使用现有posterior_diagnostics.R。完整诊断包括rank/folded Rhat、bulk/tail ESS、常量不可判定；Pyro未提供的完整树深命中数不填零。原始数组、R回写、所有状态/日志、依赖及校验和随新回传包保存。

Windows通过这一门槛后，才把该平台的九目标CPU基线写为就绪。正式推断预算/重复数/窗口/误差和时间口径还需单独冻结；这里的短链不是正式数据。Mac伴随摘要见`benchmark/analysis/outputs/nuts-native-readiness-v1/`。

## 伴随归档与异目录重建

完整本地归档`f3-readiness-localization-v1.tar`为74178560字节，240个文件从TAR内逐项校验通过，Git bundle验证通过；源码快照076fabd90276efdfa99d891690ab1f140ab2acb5。SHA256为`cb5206d2a7c419563b8ee84e5f297be5f1b58272b4665a4984cbe46552d50621`。它包含本次NUTS完整数组、诊断、恢复证据，以及H1失败定位数组、最小原始失败用例和源码历史；没有公开Release。

在新的提取目录使用归档中的源码，从保存数组重建18份诊断输入并运行R；18份输入字节和全部posterior函数结果与归档相同。随后重建受控NumPy后续递推，8份数组的dtype、shape和字节及逐链摘要完全一致。新增MCMC拟合数为0。此项使用同一Mac和现有Python/R环境，仅验证本伴随归档的异目录重建，不是干净安装、外部团队复现或全部论文重建。

回执、四条命令的原始日志及归档校验日志在`benchmark/analysis/outputs/nuts-native-readiness-v1/`。完整首次失败定位仍依赖先前`inference-budget-pilot-v1.tar`；本包保留的最小原用例足以重建后续递推探针。不得将其称为原324项实验的独立完整副本。
