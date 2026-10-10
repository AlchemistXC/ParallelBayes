# 本轮交接状态

源码、执行器、14项Mac便携检查及提示词已推送到 `codex/research-integration`；实现提交为 `66e9d85`，完整环境绑定修订为 `4ae52af`。Windows原生Job与采样资格尚未执行。

固定输入包已在Mac制作并独立解包校验：

- 文件：`windows-nuts-localization-inputs-v1.tar`
- 大小：21,544,960字节（约20.55 MiB）
- SHA256：`3b97a221ea8a5a61644f3394474e2ceaf8f0b981803456181a012a99d26f5b12`
- 内容：27个输入/记录文件，九个模型案例及三套既有四链诊断轨迹；不含完整主研究原件。
- 本地位置：主工作目录 `output/windows-nuts-localization-handoff/`，同目录包含 `.tar.receipt.json`。

上传该tar及回执到GitHub既有草稿的操作被自动审批拒绝，原因是需要用户明确授权这份具体研究输入上传到该目的地。已发出确认请求；截至本记录尚未上传。不能从源码已推送推断输入包也已上传。

拟用目的地为 AlchemistXC/ParallelBayes 的原Windows草稿，实际tag为 `windows-completion-v2-20261005`，历史页面为 `releases/tag/untagged-a38d1dfe63e5584ac2ef`。核对时仍为draft，原215附件不变。用户可以授权上传，或自行把本地输入包转交给台式机。

收到输入后使用README中的校验解包工具，再整份提交CODEX-PROMPT.md。输入缺失时只准备环境和源码，不生成替代输入或开始正式定位。
