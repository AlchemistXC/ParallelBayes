# Windows收尾第一步：诊断最小复现

本文件是F1专用提示词；现已准备的F2/F4、NUTS及已选MH入口见[收尾导航](README.md)。正式41,472项设计仍为草案，不可直接启动。

请在我的原生Windows电脑继续ParallelBayes研究，先完成这个已准备好的F1核查。不使用WSL2，不重新运行512项采样，不修改已冻结的torch/Python/R环境或原始结果。

1. 拉取仓库最新远程引用，阅读`docs/RESEARCH-COMPLETION-PLAN.md`、`execution/COMPLETION-WORK-PACKAGES.md`和`docs/DIAGNOSTIC-MIDPOINT.md`。当前代码在`origin/codex/windows-return-audit`。工作区有修改时保留；可从该远程分支新建`codex/windows-completion-f1`及独立worktree。不要重新执行历史首次移植提示词。
2. 确认本机原实验R 4.6.1、`posterior`1.7.0及`jsonlite`仍可用。记录实际路径和版本；不用升级包来获得一致结果。如果原库位于`D:/Tools/R-library-4.6`，按实际情况设置`R_LIBS_USER`。Python包装器只用标准库，可以使用原生Python3.12，GPU无需启动。
3. 从仓库根运行下面命令，将Rscript路径替换为本机实际路径，输出使用未存在的目录：

```powershell
$env:R_LIBS_USER = 'D:/Tools/R-library-4.6'
.\.venv-win-torch\Scripts\python.exe scripts/completion/run_rhat_case.py --case benchmark/fixtures/rhat-midpoint-v1 --output output/completion/rhat-windows-01 --rscript 'D:/Tools/R-4.6.1/bin/Rscript.exe'
```

若独立worktree不含venv，用原项目venv的绝对Python路径；不要复制或改造冻结venv。脚本已校验12KiB输入的SHA256，并会核对R回写字节。它记录native/bulk/folded Rhat、原生中位数、两个明确中心的结果、5个秩变化、`.Machine`、R版本及函数文本。它只分析既有数据，不替换任何正式诊断。

4. 检查`receipt.json`和`result.json`。比较本机原生中位数是否为`0x1.7701bac434f11p-10`、Rhat是否重现归档的1.40822237244096；Mac原生中心低一个ULP，得到1.4085688369053788。报告实际值，不强行令其符合预期。读取`.Machine$sizeof.longdouble`和对应精度字段，保留完整构建信息。不能仅因显式中心能重现Windows值就宣称Windows原生中位数已实测一致。
5. 如结果意外，保留完整失败输出、版本和差异；新尝试使用新目录。不要改采样器、容差、样本或默认posterior实现。必要时制作进一步的最小诊断，但记录为新伴随分析。
6. 将整个小结果目录（`result.json`、`receipt.json`、`R.log`、`roundtrip-f64le.bin`）保存到`benchmark/analysis/outputs/completion-f1/windows-01/`，生成/核对SHA256，更新工作包的Windows回执状态。提交到自己的开发分支并推送同一用户仓库；不合并main、不发布草稿Release。回报分支和提交号，使Mac端能直接拉取核验。

本次没有GPU性能任务。F2/F3的新实验需要独立协议，等待主项目后续准备；不要沿用windows-native-v1身份扩充采样。私有技能ZIP仍可按原授权单独迁移，但其缺失不阻止本检查。报告中区分文件安装、Codex发现和实际运行验证，不声称缺失技能已经可用。
