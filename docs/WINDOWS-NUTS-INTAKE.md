# Windows NUTS定位结果的Mac接收

2026-10-11。此流程对应S2独立接收；目前原生结果尚未回传。新增接收器通过17项合成证据检查，0失败、0跳过；它不证明Windows采样、轨迹资格或故障归因。Windows执行器、固定输入、协议和48次总调用上限均未改变。

## 获取与完整性

只接收本轮结果tar、外部SHA256回执、源码分支/提交及Windows最终报告，不重复下载旧29.31 GB主证据。保持原Windows草稿未发布。收到明确的归档名和SHA后，再下载对应附件；不要把输入包当作结果包。

在研究工作树根目录，使用Python 3.12及新目录。以下路径和SHA必须换成实际回传信息：

```sh
python scripts/analysis/audit_nuts_return.py unpack \
  --archive <新结果tar> --sha256 <回传的64位SHA256> \
  --output <新接收目录>/received
python scripts/analysis/audit_nuts_return.py audit \
  --root <新接收目录>/received \
  --report <新接收目录>/identity-audit.json
```

接收器先核对外部归档哈希，拒绝越界、重复、别名、链接和清单不一致的成员。解包前检查归档加解包副本不超过20 GiB，并保留4 GiB可用空间。原件解到新目录；不覆盖源码工作树或历史实验。后续报告置于原件目录之外。

只读身份核验包括：固定输入清单、原目标和初值、保存RNG、环境要求、冻结基线源码、各版本归档源码、SQLite身份和请求指纹、逐调用文件、原生Job测试的XML/回执、资格轮数、主计划和配额、分析分母及失败类别。旧式Windows反斜杠校验键只读解释，不改写原校验文件。

失败或因资源保护而不完整的研究可作为完整交付的技术证据接收。`identity_audit_passed=true`不表示36项主体均完成；读取`all_main_calls_registered`和各阶段计数。它也不声称通过数值资格，更不能从归档状态推断远端当前没有活动进程。

## 实际轨迹与分析重建

身份通过后，用已检查的本地便携分析器重建，而不是执行压缩包里的任意脚本。选择包含NumPy/psutil的既有报告环境：

```sh
python scripts/followups/analyze_nuts_localization.py \
  --study <新接收目录>/received/study \
  --output <新接收目录>/rebuilt-analysis
```

该程序读取实际保存的预热与采样数组、阶段事件、实际RNG快照与Job日志，重新计算资格、共同前缀和资源记录；不调用采样器或Windows恢复。逐文件比较新报告与`received/analysis`，列出所有差异。浮点数、缺失、截断事件与路径分隔符的差异须分别定位，不能为得到“完全一致”改写原件。资格轮的轨迹未通过、完整四条件缺失或仅部分主体完成，都在终态说明中保留。

同时从回传分支取得相关Git对象，逐个核对`study/bindings/*.json`中的source_commit及source_files与`git show <commit>:<path>`的字节SHA。归档身份核验器仅检查归档源码与绑定哈希，未替代Git对象验证，也不自动合并Windows分支。

确认调用还须依据冻结的模型/条件优先级，使用36项主体的实际阶段差异重算选择，核对`confirmation-selection.json`；仅验证已保存选择和注册调用相符不足以证明选择规则被遵守。保留注册失败和所有资格重试；诊断作业不计入48次四链配额，但应另列9项。核对Windows提供的两次零新增恢复与受管理进程终态证据；Mac不声称自己查询了Windows内核。

## 科学审阅与论文

对九输入四条件报告成功、阶段失败、资源停止及缺件。工作进程数同时影响并发和进程复用；持久化插桩改变对象生命周期与I/O。旧诊断旁路后成功只支持阶段关联，ESS根因还需保存轨迹的独立ESS重放和阶段/资源证据共同支持。未复现保留为未定，不称已修复。

旧105项失败、42项路径数值失败和主实验分母均不变；新轨迹不计入正式后验样本或独立重复。完成独立接收后才更新S2结果、论文/SI、计划状态及最终可重建归档。可用的结论包括未复现、有限定位或资源终止，不要求制造成功或确定根因。

检查依据：`execution/targeted-followups-v1/qualification/nuts-return-receiver-v1.json`。接收器仅位于`scripts/analysis`，未进入Windows运行器绑定的`scripts/followups`等执行目录，无需为这项Mac工具重启或重新冻结Windows任务。
