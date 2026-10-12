# v5投稿候选的完整复现入口

身份submission-v5-rc1。论文和补充均保持v5结果；v4封存材料及全部历史协议/结果保留。源代码、软件安装包、图文输入和43证据组件分别绑定，不把一份小入口包误称为完整原数组。

## 取得和核对

1. 从候选入口取得外部SEAL.json、SHA256SUMS和entry归档，核对外部SHA后解包。用Git bundle克隆`codex/submission-v5-rc1`；固定commit/tag以外部seal为准。
2. 取得43组件及21原紧凑组件的外部清单。旧41记录逐字保持，另有paper-v5 ZIP和v5-R-technical tar.gz。历史CPU为已有公开入口，Windows草稿与作者本地原件须取得真实权限，不虚构DOI或下载权限。
3. 按`execution/submission-v5-rc1/locations.example.json`填本地路径；位置映射和凭证不提交Git。依赖安装使用原14项`environment/locks/submission-analysis-v1.txt`及对应R锁，Python3.12、posterior1.7.0。
4. 先对外部固定的组件清单SHA核验：

```text
ANALYSIS_PYTHON SOURCE/scripts/submission/reproduction.py verify --manifest COMPONENTS.json --manifest-sha256 EXTERNAL_COMPONENTS_SHA --locations locations.json --output NEW_INTEGRITY.json
```

这一步读取现有文件/证据树，不复制约39.36GB的列示组件。其中历史表示有重叠，列示字节数不等于额外磁盘需求或独立样本量。严格保持原21组件边界，恢复不启动采样。

## 原数组、旧分析和v5新分析

**完整原数组到统计**仍按`docs/COMPACT-REPRODUCTION.md`从冻结交付源94bebec执行index→run→resume验证→statistics，保留4144任务、原失败和未定诊断。GPU及新采样不是只读分析依赖。旧v4完整重聚合/全部表图的实际验收随候选继承，见`execution/submission-rc1/ACCEPTANCE.json`，本轮没有再次运行整个4144路径网格。

从原组件得到`STATISTICS`、`FORMAL`及`INDEX`。STATISTICS使用已核验Mac清单d928a497889e11f6aaf5829bf1ffd807a647a880a5d4ae7cef4acf3046c34bfb。Mac统计可从mac-final组件提取；FORMAL是compact-formal目录；INDEX按原读取流程创建，不要求作者绝对路径。

将新增两个小组件解包到新目录（512MiB上限足以容纳其实际约17.8MB和2.2MB输入）：

```text
ANALYSIS_PYTHON SOURCE/scripts/submission/v5_transport.py --manifest COMPONENTS.json --manifest-sha256 EXTERNAL_COMPONENTS_SHA --locations locations.json --component paper-v5 --output RELOCATED/paper-v5
ANALYSIS_PYTHON SOURCE/scripts/submission/reproduction.py extract --manifest COMPONENTS.json --manifest-sha256 EXTERNAL_COMPONENTS_SHA --locations locations.json --component v5-R-technical --output RELOCATED/v5-R-technical --max-bytes 536870912
```

选定安装R依赖库后运行八阶段入口：

```text
ANALYSIS_PYTHON SOURCE/scripts/submission/rebuild_v5.py --source SOURCE --statistics STATISTICS --delivery FORMAL --index INDEX --paper RELOCATED/paper-v5 --r-evidence RELOCATED/v5-R-technical --integrity NEW_INTEGRITY.json --output NEW_REBUILD --rscript Rscript --compiler TECTONIC_EXECUTABLE
```

它重读216份W1原阶段与2条L1原路径、重算R诊断、生成3个TeX片段、两图，读取3份旧完成R路径并保持1旧失败，最后重编译16/47/67页。R实际数组按保存形状二进制导出；随机输入恢复后须匹配原hash，再独立NumPy重放，未引入新独立随机输入或后验拟合。任何失败停止并保留日志；输出路径必须新建。

图文独立重编译也可只解包paper-v5，在其根目录运行`python BUILD.py --verify-only`和`python BUILD.py`。包内所有依赖相对定位；不需Codex插件。此层不替代完整原数组和数值参考复现。

## 软件与继承验收

入口附原wheel、sdist和R源码包，软件版号不变。新源码的17数值模块、旧已安装Python/R模块与14分析依赖已核对。原新安装/明确开启R集成测试和完整旧分析验收分别保留；本轮使用已验收环境，没有把复用写成又一次新安装，也没有重复无关采样器测试。新ZIP运输工具的10测试只核验安全边界。

## 公开状态和终点

入口包包含源码bundle、软件、paper-v5、三PDF、版本与验收记录，以及约2MiB的完整R技术原件；不包含全部主实验原数组。入口本身仅在作者本地，不自动公开。43组件最终获取方式和数据条款、作者信息、期刊及真实外审权限由`AUTHOR-DECISIONS-V5.md`集中确认。

本候选状态是“内部可复建候选验收并封存，作者决定与外部审稿访问待完成”。只有作者落实入口并完成真实非作者权限下载后，才更新可得性声明。内部重建、完整性核对、外部访问和最终投稿批准是不同事项。
