# Windows Codex 技能迁移

2026-10-04用户要求同步现有技能。本机有30个用户自定义技能目录，已生成**私下转交的完整ZIP**（777个文件，约30.7 MB）；公开仓库只保存清单、哈希和安装工具，不分发技能正文、插件缓存、账号配置或凭证。

## 自定义技能：一次转交，校验后安装

在Mac取得`output/windows-skills-private/parallelbayes-user-skills-2026-10-04.zip`，通过你自己的文件传输方式放入Windows仓库的`downloads/`目录。这个ZIP不在GitHub Release中，单独转交一次即可。完整清单及固定SHA256见[skills-inventory.json](skills-inventory.json)。

Windows Codex先检查当前可发现的技能及同名目录。按当前[官方技能目录说明](https://learn.chatgpt.com/docs/build-skills)，用户技能放在`$HOME/.agents/skills`；部分既有安装及内置skill-installer使用`$CODEX_HOME/skills`（未设置时为`$HOME/.codex/skills`）。以目标机实际识别的目录为准，**同一技能只安装一份**，不要同时写两个目录，不覆盖系统技能或已有不同版本。

```powershell
# 默认目的地：当前Windows用户的 .agents/skills
py -3.12 scripts/windows/install_local_skills.py --archive downloads/parallelbayes-user-skills-2026-10-04.zip
# 只有目标机实际使用其他技能目录时，追加 --dest "已确认的技能目录"
```

脚本先校验整个ZIP、内部逐文件哈希及安全路径，然后复制完整目录；不会执行技能中的脚本。已有完全相同技能跳过；同名不同内容会在复制前报错，保留原文件，让Codex说明差异后选择迁移位置或备份方案。若此前安装产生了额外缓存，也会视作差异，需要核对，不能强制覆盖。

原样迁移包括：

- 项目开发：`codebase-design`、`domain-modeling`、`tdd`、`improve-codebase-architecture`、`triage`、`frontend-design`、`find-skills`、`grilling`及两个旧别名。
- 科研：本机全部`nature-*`目录，包括`nature-paper-card`、`nature-statistics`、`nature-figure`、`nature-writing`、`nature-reviewer`、`nature-experiment-log`、`nature-data`、`nature-shared`等。目录`nature-proposal-writer`的调用名称为`researchwrite`，按SKILL.md实际name识别。

安装后在下一轮核对技能是否出现；未出现时重启Codex。文件安装成功不等于脚本在Windows通过测试：清单的`portability_review_markers`标记可能存在的Mac路径、shell命令等，只是静态排查线索。使用前读取所需技能，按Windows环境修正实际调用路径/命令并留痕；不把整个技能集机械改写或批量执行。

本项目优先验证`codebase-design`、`tdd`、`nature-paper-card`、`nature-statistics`、`nature-experiment-log`、`nature-figure`、`nature-writing`、`nature-reviewer`。按实际脚本需要安装Windows可用Python/R依赖；文档/PDF处理用独立工具环境，避免改变已冻结的GPU实验环境。论文检索账号、API、机构权限和连接器需在新机重新配置，不复制Mac密钥或浏览器会话。

## 系统技能与插件附带技能

- `skill-installer`、`skill-creator`是系统技能；`openai-docs`、`imagegen`等以Windows会话实际提供情况为准，先检查，不从Mac复制`.system`。
- 如需公开仓库中的缺失技能，使用Windows本机`$skill-installer`，按它的SKILL.md运行安装辅助脚本；必须有明确仓库/路径。不要假定这里的私有`nature-*`都存在于openai/skills，也不要下载未经核实的同名替代品。
- 插件提供技能、工具和运行时的组合，**复制SKILL.md不能安装其工具**。在Windows Codex插件目录搜索并安装当前账号可用的对应插件；不能安装或需要人工授权的项记录为待处理。依据：[官方插件架构](https://developers.openai.com/plugins/concepts/plugins)。

本Mac会话可用插件技能的迁移核对表（不表示这些插件在Windows已安装或全部兼容）：

| 插件/能力 | 本项目用途 | Windows处理 |
|---|---|---|
| Data Analytics | 数据质量、统计结果核验与绘图 | 检查同名插件及其实际工具 |
| PDF、Documents、Presentations、Spreadsheets | 阅读PDF与导出文稿、演示、表格 | 用Windows提供的插件/运行时，不复制Mac二进制 |
| LaTeX | 多文件TeX项目编译 | 先查本机工具；单文件可用内置编辑器；不复制MacTeX |
| Google Drive、Pages | 云端文档/资料 | 需要时重新连接账号，技能迁移不迁移授权 |
| Sites、Visualize | 网页/交互演示 | 核对账号提供能力；当前实验不依赖 |
| Work Pets、Plugin Management | 其他已有技能 | 核对可用性；不影响实验验收 |
| Computer Use 等Mac应用控制能力 | macOS专属工具 | 无法因复制技能获得Windows支持，记录不适用 |

无需因为可选插件暂不可用停止数值开发。不要为复现技能而改成WSL2。

## 给Windows Codex的技能验收要求

在`execution/windows-native/skills-status.json`记录每项的名称、来源、版本/哈希、安装目录、发现状态、所需依赖和一次适用的小型检查。区分：文件已复制、Codex已发现、脚本/工具已验证、需账号或平台限制。不能只写“所有技能已安装并可用”。安装日志和适配差异保留在本机，不把私下技能正文加入公开仓库。
