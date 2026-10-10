# S2 Mac独立接收与科学审阅

2026-10-11。限定NUTS故障定位的接收与审阅已完成；无需续跑Windows提示词或用满48调用配额。全部资源停止和历史未复现情况是交付结果。论文已写入这批证据，其他三项补充保持原结论。

## 接收与独立检查

Windows交付分支`codex/windows-nuts-localization`，提交`1a8759f4faaad85b43fd9ee36bb3c6a7907b4dd2`；执行源`126969036e73b4c077563d6601b030407e7663b8`。Mac将回传提交快进至研究分支，没有合并新的采样器实现。149个执行文件逐项与Git对象、源绑定和归档字节一致；源码bundle完整历史通过Git验证。

完整tar为703,969,280字节、SHA256 `5fffe7f83783651ef58198aab4bad1bfb28be1d2244b9a0738c8f66fbdb88705`，外部回执及GitHub摘要匹配；安全解包后30,044件内容逐项匹配，解出642,074,472字节。后继管理包79件、839,680字节也核验通过。只下载本轮附件，旧约29 GB证据没有重复下载，草稿及旧附件未改。

原生环境仍为Windows Python3.12.14、NumPy2.2.6、SciPy1.15.3、Pyro1.9.2、torch2.13.0+cu130、psutil7.1.0，CPU路径；原R4.6.1/posterior1.7.0。21便携/3原生测试回执均0失败0跳过，Mac核对回执及源码，不冒充在Mac执行原生Job测试。

Mac用可信本地程序重新分析保存的阶段日志、实际预热/采样数组和RNG状态：六份数值分析文件逐字节一致。README仅CRLF/LF差异，校验清单也仅相应README项不同；没有修改Windows原件。四条件二维高斯资格实际重建通过，九模型54对条件/864项共同路径与RNG记录一致。按全部36项主体阶段结果独立重算确认规则，选择恰为G2/A1四worker诊断开/关四次；64项确认记录与原条件一致。

三套旧四链数组另在Mac R4.6.0/posterior1.7.0重算现代诊断。74参数、123数值字段与Windows不同，最大缩放差8.205930873891878e−15；二进制往返、未定位置及Rhat>1.01分类不变。完整差值保留，不以扩大容差覆盖原值。

## 全部终态

|阶段|登记|完成|资源停止|是否新增正式重复|
|---|---:|---:|---:|---|
|旧数组诊断|9|8|1|否，无新增采样|
|四条件资格|4|4|0|否|
|主体|36|34|2|否|
|确认|4|2|2|否，同一输入重复|

44次注册四链调用，低于48上限；全部53个Job有终态。完成表示技术流程完成，不代表收敛。四个采样工作流资源停止均保留每链1024预热及4096样本，诊断前完整数组与钩子分块一致，末事件为legacy_diagnostics_enter，无退出事件。

保存的两次真实Windows终态verify均新增执行0。Mac另核对29,444个当时文件的前后集合/大小/哈希及当前接收字节相同；调用内29308资产检查数与整个研究快照29444是不同范围。53个Job的保存终态均absent，Mac没有查询远端当前内核。对已关闭任务不增加新的Windows恢复或诊断调用。

## 结论的三个层次

**直接观察。** G2/A1的主体及预定确认中，四worker诊断开启条件在采样完整保存后出现Job内存限制消息，整体旁路完成。独立旧G2数组四worker ESS重放进入ESS后触发8 GiB集合RSS护栏。控制仍为查询12 GiB Job限制、0.2秒观察的8 GiB RSS护栏，均未放宽。

**机制解释。** 已冻结Pyro1.9.2 ESS的_cummin用repeat构造2047×2047×64数组：float64为2,145,387,008字节、布尔掩码268,173,376字节/链，另有FFT和运行时对象。源码规模与阶段/资源证据相容；未在失败栈中捕获这一具体分配，不能称独占峰实测或唯一根因。RSS可重复计共享页、轮询可漏尖峰；Job峰计数不能当作显存或成功提交的精确峰，退出码缺失保持缺失。

**仍未确定。** 六个选定旧失败输入在新插桩下全部完成，不能说旧故障已经修复。插桩改变I/O、GC、对象生命周期和进程复用；未定位全部105个历史故障。旧105未分类/42数值失败、正式分母、旧函数估计和失败成本全部不变。技术样本不补回旧结果，也不作为性能/收敛证据。

## 重建入口

从仓库根目录用Python3.12、NumPy和psutil，选择新的接收目录。完整归档只从具有权限的原Windows草稿取得：

```sh
python scripts/analysis/audit_nuts_return.py unpack --archive <tar> \
 --sha256 5fffe7f83783651ef58198aab4bad1bfb28be1d2244b9a0738c8f66fbdb88705 \
 --output <intake>/received
python scripts/analysis/audit_nuts_return.py audit --root <intake>/received \
 --report <intake>/identity-audit.json
python scripts/followups/analyze_nuts_localization.py \
 --study <intake>/received/study --output <intake>/rebuilt-analysis
```

R诊断：对G1/G2/W1各建立新目录`<intake>/r-modern-rebuild/<model>`，仅从`received/study/calls/diagnostic-<model>-modern-w1/`复制draws.bin及transport.json，再分别运行：

```sh
Rscript --vanilla scripts/completion/posterior_diagnostics.R <intake>/r-modern-rebuild/<model>
python scripts/analysis/review_nuts_localization.py --root <intake>/received \
 --rebuilt <intake>/rebuilt-analysis --r-rebuilt <intake>/r-modern-rebuild \
 --output <intake>/scientific-review
```

须取得绑定Git对象；审阅器只执行git读取，不执行归档源码/Windows协调器或采样器。完整原件和接收目录在Git外，小型报告与逐项差值见`benchmark/analysis/outputs/nuts-mac-intake-v1`。修改报告文字改模板，再由`write_nuts_localization_tex.py`生成；不手改派生数值。

接收过程两次工具路径/清单格式假设错误在写原件前失败，修正后通过；记录见qualification/nuts-mac-intake-v1.json。没有Windows兼容性修复、环境升级或重新冻结协议。
