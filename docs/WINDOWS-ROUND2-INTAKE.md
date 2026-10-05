# Windows 第二轮的 Mac 独立接收与后续工作

2026-10-05。接收分支 `codex/windows-completion-v2`，提交 `ced54ef6ce945198339a138142dcdfede84f06bc`；执行源码为 `f5148ee`。已快进接入审查开发分支，main不变。原回执见 [Windows报告](WINDOWS-COMPLETION-V2-RESULTS.md)，本报告区分它与接收端新增验证。

## 已验证证据

原归档 `windows-native-20261005T113131Z.tar` 为76,267,520字节，SHA256：
`bfd55d442fbb4137c54e573031781a95d75e0a86f20ccd4c8a994d338746efb9`。
逐成员948文件通过校验后解压到独立目录；没有覆盖活动工作区或历史结果。

六份协议的规范身份、逐文件冻结源哈希及归档协议与仓库的一致性已核对。另核对369项任务资产、95份小型证据、命令日志及恢复前后状态；接收分析前后674个原批次文件保持不变。NUTS的126个终态文件、两设备MH各135个终态文件与Windows恢复前快照吻合；归档恢复调用各新增任务0。这里没有在Mac假装运行Windows恢复。

| 范围 | 独立接收结果 | 证据边界 |
|---|---|---|
| F1固定诊断 | 输入/回写字节一致；Windows原生中心和5个秩变化与预期对照吻合 | 已有数值机制及实际构建回执，不声称特定底层库根因已证明 |
| 水井F4 | 12工作流重新以独立NumPy重放通过；接受事件零失配；R-CUDA字节回写一致 | 原短链不良Rhat保留，非收敛证明 |
| 已选MH | 108份保存路径均在原容差内、接受事件零失配；54组CPU/CUDA保存路径配对通过 | 跨系统原尺度逐位检查有60份失败，详见下文 |
| CPU NUTS | 九目标×六类串行/spawn数组逐字节一致；36条子链适应步长与串行对应记录一致；初值/种子/进程元数据核对 | 每目标一份配对技术输入；不增加统计重复，也不证明后验精度 |
| R诊断 | 18份原二进制往返一致；Mac对同一二进制重新计算72行函数诊断，有限Rhat完全一致、NA位置一致 | 原探索不足和不可判定项保留 |

## 跨系统末位差没有改写成“全通过”

原 `audit_selected_mh.py` 同时要求路径容差、零接受事件差及变换输出逐位相同。在Mac对Windows结果调用该原审计器时，两台设备的 `saved_array_replay_passed` 都为false；108份中48份满足原尺度逐位一致，另60份涉及G2/A1/L1/L2/H2。

重新评价保存的同一无约束状态后，原尺度输出最大绝对差为8.881784197001252e-15；以 `max(1,abs(output))` 标准化后的最大差5.329070518200751e-15。这是伴随量化，不是新增通过容差，不删除原失败、不改变正常样本的原验收标准。Windows本机原严格审计通过与Mac跨系统逐位失败是两个不同命题。路径/接受事件本身仍满足原冻结检查。

NUTS的18份函数输入中，Mac从保存样本重算有8份逐位一致，另10份最大差2.220446049250313e-16；收到的18份Windows二进制及其R回写哈希则全部一致。为隔离重算差异，新增R伴随分析直接读取收到的原二进制，而不是先改写函数值。

同二进制R结果：Rhat和tail ESS完全一致；bulk ESS最大绝对差1.0231815394945443e-12，均值/标准差/MCSE差在约1e-15及以下。34个不可判定指标条目的位置一致。Windows使用R4.6.1/ucrt、Mac使用R4.6.0，均posterior1.7.0。没有对原诊断取整、覆盖或挑选较好结果。

## F2尚未执行：已定位并补齐输入传递

六份Mac原始冻结NPZ均匹配协议的文件哈希及实际数组哈希。与回传的Windows拒绝候选逐元素对照：所有noise和directions完全相同，六份log_uniform合计82/49152个元素不同，最大差4.440892098500626e-16。这只定位了差异分量，尚未定位到特定数学库/编译器实现；同版NumPy和同seed不保证派生浮点数组逐位一致。

原文件已打包为 `mechanism-windows-pilot-v1-original-inputs.tar`（10,823,680字节），SHA256为
`2b46eedc58067c920c8519cb4f99965bf944202f57392514d4643b847f9b9e5a`，补入同仓库既有草稿 `windows-completion-v2-20261005`。没有公开发布或覆盖原资产。包内只有六份合成随机数组，无观测、私有技能或凭证。传输清单见 `benchmark/fixtures/mechanism-windows-pilot-v1/transport.json`。

还修复了非冻结分析器 `analyze_mechanism_pilot.py`：必须通过 `--inputs`读取原文件，先检查完整主输入清单的双重哈希，再核对各组前缀；删除按seed重建期望值的路径。冻结采样器、数值参数和协议身份均不变。新输入接口测试先失败后通过，与受影响机制接口合计5项通过；旧Mac smoke的9工作流分析表逐字节重建一致，无新采样。

Windows下一步只执行 [F2续跑提示词](../handoff/windows-completion/CODEX-PROMPT-F2-RESUME.md)。192工作流仍为未执行；补齐输入包不等于实验完成。F1/F4及NUTS/MH就绪任务无需重新执行。

## 本机批次与其余门槛

Mac的15项批次/最大形状技术协议已冻结，首项G2四链NUTS在终态封存前中断。旧进程组实际不存在后，按原策略进行了唯一一次显式重试；该重试也在终态封存前停止，进程组缺席由协调器重新确认。原因未确定，没有可验收的输出，不能计为完成或数值失败；两个中断调用没有完整计时回执，成本保持未知。原目录保留，未创建第三次尝试。后续观测确认重试后发生过主机重启，未确定重启原因；其余14项已按原协议完成，并通过零重算及搬移归档重建，详见[本机批次验收](BATCH-MAXIMUM-VALIDATION.md)。

该事实不改变Windows已取得的就绪证据，但最大任务验收仍未关闭。后续继续完善中断后队列推进及原生Windows进程集合/资源保护；不能用仅终态 `--resume`检查替代它们。正式设计41,472拟合仍是草案，未冻结/执行；两平台干净安装、完整论文图表重建与中文稿整合仍未完成。

## 重建入口

小型接收证据在 `benchmark/analysis/outputs/windows-round2-intake-v1/`。大归档位于同仓库Windows第二轮草稿，先下载、运行 `scripts/verify-windows-return.py` 并解压到独立目录。以下均从项目根运行；`BATCH`为解压所得原批次目录，`INTAKE`为新的接收目录。

1. 对CPU/CUDA分别运行 `scripts/completion/audit_selected_mh.py`，传入各自冻结协议、`benchmark/fixtures/selected-mh-readiness-v1`、BATCH的wells-source与mh-*-run；输出INTAKE/mac-mh-*-audit。必须读取JSON通过标志，当前原脚本的退出码不能代替科学判断；本接收的跨系统严格结果为false。
2. 运行 `scripts/completion/verify_windows_wells.py`，读取BATCH三个水井工作流目录，另存复核回执。
3. 运行 `scripts/completion/audit_windows_round2.py --batch BATCH --prior-audits INTAKE --output INTAKE/independent-receipt`，只读核对原始资产、数组、恢复快照和跨系统变换，并复制原诊断二进制到新目录。
4. 用R/posterior1.7.0运行 `scripts/completion/posterior_diagnostics.R INTAKE/independent-receipt/same-binary-mac-diagnostics`；不得覆盖旧诊断。
5. 以 `scripts/completion/compare_mechanism_inputs.py --plan benchmark/protocols/mechanism-windows-pilot-v1.json --original ORIGINAL_NPZ --rejected BATCH/mechanism-rejected-inputs --output INTAKE/mechanism-component-differences.json` 重建输入分量比较。将归档验证回执保存为INTAKE/archive-verification.json，再运行 `scripts/completion/summarize_round2_intake.py --batch BATCH --intake INTAKE --output INTAKE/summary.json` 汇总，保留R版本及所有不一致。

接收端没有重跑Windows采样，没有新增独立统计重复，也没有从短链结果推导推断加速结论。
