# 本轮交接状态

源码、执行器、14项Mac便携检查及提示词已推送到 `codex/research-integration`；实现提交为 `66e9d85`，完整环境绑定修订为 `4ae52af`。Windows原生Job与采样资格尚未执行。

固定输入包已在Mac制作并独立解包校验：

- 文件：`windows-nuts-localization-inputs-v1.tar`
- 大小：21,544,960字节（约20.55 MiB）
- SHA256：`3b97a221ea8a5a61644f3394474e2ceaf8f0b981803456181a012a99d26f5b12`
- 内容：27个输入/记录文件，九个模型案例及三套既有四链诊断轨迹；不含完整主研究原件。
- 本地位置：主工作目录 `output/windows-nuts-localization-handoff/`，同目录包含 `.tar.receipt.json`。

2026-10-11用户明确授权后，已将上述tar及 `.tar.receipt.json` 追加上传到[原Windows草稿](https://github.com/AlchemistXC/ParallelBayes/releases/tag/untagged-a38d1dfe63e5584ac2ef)。实际tag为 `windows-completion-v2-20261005`，草稿仍未发布；附件从215增至217，原215件的ID、名称、大小、摘要和更新时间均未改变。两份新附件的GitHub SHA256与本地文件一致。此前上传审批拒绝已由本次具体授权解决。

上传核验记录见 [github-upload-receipt-v1.json](github-upload-receipt-v1.json)。在已登录且可访问该草稿的Windows GitHub CLI中下载：

```powershell
gh release download windows-completion-v2-20261005 --repo AlchemistXC/ParallelBayes --pattern 'windows-nuts-localization-inputs-v1.tar' --pattern 'windows-nuts-localization-inputs-v1.tar.receipt.json' --dir downloads/windows-nuts-localization-v1
```

下载到新目录；如已存在文件，先核对，不加 `--clobber`。这次只追加交接输入，没有运行新的采样，也没有收到Windows原生定位结果。

收到输入后使用README中的校验解包工具，再整份提交CODEX-PROMPT.md。输入缺失时只准备环境和源码，不生成替代输入或开始正式定位。
