from pathlib import Path
p=Path('manuscript/software/软件与基准研究.tex');s=p.read_text()
s=s.replace('时间并行 MCMC 的可核验实现与资源受限比较\\\\一个 R 接口及跨模型计算研究','ParallelBayes：时间并行 MCMC 的可核验实现与单机 CPU 基准')
s=s.replace('通过R接口组织Stan/BridgeStan CPU目标、原生JAX目标、顺序MALA、窗口quasi-DEER、随机游走Metropolis、Online Picard和四链BlackJAX NUTS','提供Stan/BridgeStan的CPU顺序RWM/MALA入口，并通过R控制接口对明确实现的原生JAX目标组织顺序核、窗口quasi-DEER、Online Picard和BlackJAX NUTS')
s=s.replace('另完成64个新生成数据集的320次拟合及依赖数据的SBC诊断。RTX 5080 GPU证据尚待回传。','另完成64个新生成数据集的320次拟合；审查后解析对照显示，该批数据的解析90\\%区间覆盖本身为54/64，并通过配对端点及现代链诊断定位有限采样偏差。小型CPU机制实验与独立环境复现另行登记。')
s=s.replace('第二，允许不同采样核及合理预热后，获得指定后验函数精度需要付出多少完整成本？','第二，允许不同采样核及合理预热后，在两个预先固定预算下，后验函数误差与完整成本如何变化？本研究没有连续扫描预算以估计精确达标时间。')
s=s.replace('它没有实现任意 Stan 模型到 GPU 的编译器，也没有提供通用新建模语言。','当前Stan入口仅支持CPU顺序RWM/MALA，尚未连接CPU时间并行执行器；原生JAX路径须逐模型实现和核验。软件没有提供新建模语言。')
anchor='\\begin{figure}[htbp]\\centering\n\\includegraphics[width=\\linewidth]{../../figures/software/architecture.pdf}'
matrix=r'''\begin{table}[htbp]\centering\small
\begin{tabular}{lccc}\toprule
模型提供方式 & 顺序RWM/MALA & Picard RWM/quasi-DEER MALA & NUTS\\\midrule
Stan/BridgeStan CPU & 支持 & 不支持 & 不支持\\
明确实现的原生JAX目标 & 支持 & 支持相应组合 & 支持\\\bottomrule
\end{tabular}
\caption{0.1.1的能力边界。并非模型、核、执行器的任意组合均可运行。不支持的请求报错。原生Windows GPU后端尚未实现。}
\end{table}

R函数\texttt{pb\_capabilities()}查询这些组合；\texttt{pb\_benchmark()}只组织配置列表及R结果，正式协议冻结、检查点和完整证据管理依赖Python CLI及项目文件。Stan模型没有默认独立轨迹参考，\texttt{audit=TRUE}明确拒绝。扩展示例通过公开Python \texttt{Model}提供Poisson目标及独立NumPy参考，R经reticulate调用并转换为posterior对象；并非\texttt{pb\_model()}可直接接收任意R闭包。

'''
s=s.replace(anchor,matrix+anchor,1)
s=s.replace('这里计算所选函数的经典split-$\\hat R$，未进行秩正态化，也不能替代全参数和尾部诊断。','原协议计算所选函数的经典split-$\\hat R$；审查后从相同保存样本补充秩正态化/折叠split-$\\hat R$、bulk ESS和tail ESS，后文单列，不替换原分析。')
s=s.replace('GPU allocator 指标在台式机回传后单列。','本研究不评价GPU内存。')
s=s.replace('\\input{results.generated.tex}','\\input{results.generated.tex}\n\n\\section{审查后的伴随分析与CPU机制实验}\n\\input{revision.generated.tex}')
s=s.replace('但还不能排除编译策略、窗口调度和底层矩阵运算的影响。','新增机制测量进一步将批处理吞吐、重复求值与分段调度区分；由于分段执行插入同步，不能把其阶段比例直接当作生产程序的精确剖面。编译策略和底层运算仍限制因果归因。')
s=s.replace('上游算法的硬件、窗口策略、停止规则和计时排除项不同，因此本研究的负例不否定其原有实验结论。','Picard原文在Apple M3 CPU上对昂贵延迟微分方程似然报告约2.52倍墙钟加速\\cite{grazzi}；这与本研究的低成本合成目标不同。上游算法的窗口策略、停止规则和计时排除项亦不同，因此当前负例不能解释为CPU普遍不适合时间并行，也不识别正加速的分界。')
start=s.index('GPU 环境和性能只有在实际');end=s.index('\n\n\\section*{代码',start)
s=s[:start]+'本研究仅评价指定CPU环境。原生Windows GPU后端尚未实现，不属于本版软件能力及实验结论；历史WSL2交接资料仅归档保留。自动配置模块未进入本版贡献，当前没有足够证据支持稳定收益区间。昂贵似然、真实数据应用和分散初始化属于后续研究；本轮不以挑选有利案例扩展结论。'+s[end:]
s=s.replace('R 包发布候选及 Python 内核随项目交付；','软件安装源、实验/分析源、原始证据及论文构建材料分成三个互有关联的本地归档，提供根目录入口与逐文件校验和。独立依赖环境和迁移目录验证已在同一Mac完成，不等同另一研究团队或操作系统的复现。R包检查与显式开启集成测试的日志分开保存。R 包发布候选及 Python 内核随项目交付；')
s=s.replace('\\begin{thebibliography}{9}','\\begin{thebibliography}{99}')
s=s.replace('\\end{thebibliography}',r'\bibitem{posterior} Stan development team. \href{https://mc-stan.org/posterior/reference/rhat.html}{posterior: Rhat, bulk ESS and tail ESS documentation}. 本研究使用posterior 1.7.0；常量链诊断保留为不可判定。'+'\n\\end{thebibliography}')
p.write_text(s)
p=Path('scripts/write-results-tex.py');s=p.read_text().replace("text.append('RTX 5080 的环境检查和正式任务尚无本项目可核验回传记录，GPU性能、显存和跨设备结论保持待验证。上述结果均为Mac CPU实测，不外推为时间并行MCMC的一般硬件结论。')","text.append('上述结果仅为Mac CPU实测；原生Windows GPU后端未实现，处于本轮研究范围之外。')");s=s.replace('完整工作流','研究审计工作流');p.write_text(s)
p=Path('docs/INSTALL-AND-USE.md');s=p.read_text().replace('GPU 流程见 handoff/gpu/。','GPU已暂缓；原生Windows后端尚未实现。历史handoff/gpu归档不属于当前可执行安装路线。');s=s.replace('标准 Stan 入口：','能力矩阵见 `docs/CAPABILITIES.md`：Stan只支持CPU顺序RWM/MALA；CPU时间并行目前要求明确实现的原生JAX目标。新增目标示例见 `docs/EXTENDING-TARGETS.md`。\n\n标准 Stan 入口：');p.write_text(s)
p=Path('docs/REBUILD-RESULTS.md');s=p.read_text().replace('PB_ORIGINAL_PROJECT=/Users/haku/Workspace/ParallelBayes','PB_ORIGINAL_PROJECT="$(cd ../.. && pwd)"');s=s.replace('GPU返回相同统计验证的原始样本后，也可在Mac端运行此分析；没有要求台式机修改已交付的采样协议。','GPU不属于本轮范围；不等待外部回传。');s=s.replace('GPU包是0.1.1／protocol-v3；','历史GPU交接归档为0.1.1／protocol-v3（当前不执行）；');p.write_text(s)
