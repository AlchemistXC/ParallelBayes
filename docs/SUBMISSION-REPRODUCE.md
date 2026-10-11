# ParallelBayes 投稿候选复现入口

身份 `submission-v4-rc1`，中文正文v4、SI v4与原完整结果附录。源代码、元数据、论文输入和大证据组件分开封存；这是完整复现材料的索引，不是一份含全部原始数组的小包。第一方源代码为MIT；第三方数据/依赖沿用其适用条款，原数组分享许可待作者确认。

## 获取与完整性

1. 从封存清单取得源码Git bundle及论文输入包，检查外部 `SHA256SUMS`。从bundle克隆固定研究分支到新目录。代码、软件候选和旧研究执行源有不同身份，见 `REPRODUCTION-MAP.md`。
2. 取得 `COMPONENTS.json` 所列全部41组件。历史CPU组件已有公开Release；其余Windows组件在原私有草稿、H1/L2/W1/论文输入在作者本地。先取得真实权限；本入口不自动公开或下载任何私有资料。
3. 为每个组件填写一份本地 `locations.json`。普通文件为 `{"path":"your/archive.tar"}`，紧凑目录为 `{"path":"your/received/component","manifest":"your/component-manifest.json"}`。键必须逐项覆盖清单ID；路径由使用者决定，不依赖作者的 `/Users/haku`。
4. 用**外部记录的清单SHA256**验全部组件：

```text
python SOURCE/scripts/submission/reproduction.py verify --manifest COMPONENTS.json --manifest-sha256 EXTERNAL_COMPONENTS_SHA --locations locations.json --output NEW_INTEGRITY.json
```

外部清单中的块名称和SHA保持原样。Windows 21组件按 `docs/WINDOWS-COMPACT-RECEIVE.md` 流式接收，一次一个块，不另建全量tar。核验可读取现有独立证据树，不复制约29.31GB原件。文件SHA通过只是完整性，并非新的轨迹或收敛证明。

## 两个不同的重建层次

**保存统计/参考到表图。** 首先用 `reproduction.py extract` 将 `mac-final`、`h1-companion`、`l2-reference`、`w1-reference`、`paper-v4` 逐一解包到同一新 `RELOCATED` 目录的同名子目录。每次提供manifest、SHA、locations、component和新output，例如：

```text
python SOURCE/scripts/submission/reproduction.py extract --manifest COMPONENTS.json --manifest-sha256 EXTERNAL_COMPONENTS_SHA --locations locations.json --component mac-final --output RELOCATED/mac-final --max-bytes 8589934592
```

默认每档解包上限8GiB；使用前按清单实测磁盘空间。

例如先 `python3.12 -m venv analysis-env`，再 `analysis-env/bin/python -m pip install -r SOURCE/environment/locks/submission-analysis-v1.txt`（Windows改为该venv的 `Scripts/python.exe`；这是分析环境，不是重测GPU）。以Python3.12建立独立环境，用 `environment/locks/submission-analysis-v1.txt` 安装14个固定包。旧13项锁保留为历史记录，缺少读取器间接依赖psutil，不能作为本候选的完整安装锁。运行：

```text
ANALYSIS_PYTHON SOURCE/scripts/submission/rebuild_submission.py --source SOURCE --relocated RELOCATED --output NEW_REBUILD
```

此入口重新生成九目标全部CSV与45图、72组普通费用概览、主表、H1表图、L2保存点/权重独立复算、W1保存球端点有理重建、64个已保存R调用的NumPy检查，以及v4解释片段。逐项比较CSV和主文TeX；任何差异停止并保留记录。它不重新测量CUDA/R性能，不重新生成重要性随机点，也不替代原4144项完整路径重放。

**原始数组到统计。** 要完整重建原始Windows数组/R诊断，遵循 `docs/COMPACT-REPRODUCTION.md`：从源码bundle取出冻结交付源94bebec，用新索引、新分析、新统计目录，执行index → run → 实际resume验证 → statistics，再接当前展示层。实际R4.6.0和分析R锁/库须记录。原件保持不变；所有3888主任务和256缓存在场，3741/42/105分类不改。无需安装GPU或重新采样。旧实际完整重放、恢复和跨平台差异证据在封存材料内；本次只读验收分别标明复算范围。

## 软件与论文

安装三个原已核验候选产物（wheel、sdist、R tar.gz），按 `docs/INSTALL-AND-USE.md` 设置可选后端。不使用editable安装或开发源码影子导入。新机器安装依赖按锁处理。`examples/paper-api.R` 是短路径使用说明，不是精度/性能实验；正式复现不必重复新采样。已有安装测试与实际开启的R集成测试分别保留，默认跳过不能算通过。

论文输入包包含169个内容文件及清单。`ctex`/Fandol兼容的Tectonic0.17.0或XeLaTeX可编译正文和SI；完整结果附录位于 `complete-results/report.tex`。保存统计重建与TeX重编译是不同层次。PDF元数据/ID可能变化，不要求字节哈希相同；同机验收另核对页数、逐页文本和渲染。

## 终点与未决事项

封存记录包含实际命令、环境、工具SHA、原件校验、复建差异及失败尝试。目录恢复或验收不授权追加科学采样。作者身份、公开/受控入口、数据分享许可和期刊尚待确认；参见 `AUTHOR-DECISIONS.md`。在真实非作者权限测试前，状态始终为“内部可复建候选已验收，外部审稿访问未验收”。
