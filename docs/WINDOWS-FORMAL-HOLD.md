# Windows 旧正式研究保全：启动后的资源修订

2026-10-08。用户要求缩减规模后，旧 `windows-formal-inference-v1` 已在任务边界停止。
冻结执行树 `D:/workspace/ParallelBayes/f` 保持
`0ba5643a6b580e79b8040f13a5e3165322db0e77`，源码、环境标记、协议和实际输入未改。
这属于采样启动后的资源修订，不是完全事前预注册；旧结果不会混入新24次重复。

## 停止动作及真实归属

原序列管理者 PID25080 / FILETIME134358637075414703；阶段driver启动PID16636 /
FILETIME134358637584457190，其实际解释器PID10812 /
FILETIME134358637584634970。原命令、父链及成员见 REQUEST.json、original-stage/started.json。
科学入口是固定f树的 `scripts/windows/formal_batch.py --batch 0 --phase main`，
共享锁仍为 `D:/workspace/ParallelBayes/output/runtime/windows-shared-host.lock`。
外围后处理PID1920和发布PID8308按持有原生句柄、精确出生时间与命令行核对后停止，
没有按进程名结束Python或无关桌面程序。

原driver无pause/stop；内层BaseException会处理KeyboardInterrupt，未使用一次Ctrl+C
作为停机证明。核对任务持锁直至Job结束/终态封存、后续export重新取得同一锁后，
用同步LockFileEx排队等待原byte0租约，取得后阻止后续派发，并等待真实管理者句柄
signaled及原生外层Job消失才释放屏障。没有抢占活动锁、删除锁或强杀科学任务。
屏障从00:08:38UTC开始等待，00:08:55取得，00:09:00停止并释放。
此前09:08:38JST控制快照为989 valid、16数值失败、4未分类输出失败、1活动任务。
09:09JST最后任务完成后为990/16/4，全部1010项有终态。

最后任务 `b5bfe17c3371b4fd6db13907` / attempt-0001：H2、rep11、CPU quasi-DEER MALA、
每链16384保留步，valid；独立NumPy路径与接受事件核验通过，失配0。
原任务Job `Local\ParallelBayes-0277d4057e98494fa8ced6e2b4b838ff` 已结束。
原序列Job `Local\ParallelBayes-formal-sequence-c073995f5ec847508a64ff7fceff6616`
及阶段Job `Local\ParallelBayes-formal-stage-42812d425ff148789de12ce82d6e4438` 已结束。
屏障在该任务封存后、阶段export前取得，原progress保留1009，实际终态1010；
原failed.json保留HostBusy及行政停止，不新增科学失败。最后历史从静止副本只读导出，
未改写原progress/state文件。整阶段未封口，completed phases=0。

## 原研究完整状态与费用

|原计划|valid|数值失败|输出失败未分类|任务基础设施中断|活动|未运行|
|---|---:|---:|---:|---:|---:|---:|
|主41472|990|16|4|0|0|40462|
|缓存9216|0|0|0|0|0|9216|

缓存调用0。失败与所有原件均保留，无重试。可见范围是这些任务自身的数组、
独立核验、R诊断和此前失败观察；未完成正式全框架统计/图表，无一般速度或收敛结论。
H1路径失败及W1 NUTS未分类退出保持原分类，不根据停止原因改名。

已登记任务调用费用合计27751.434633秒，
未知调用0；普通子进程已知23936.596103秒，
缺失0。外层阶段27978.129980秒，
序列27981.679094秒，包含内部任务，不能叠加。
独立审计完整逐调用字段和失败费用在原件；本小摘要未读取到的审计时间保持未知，
不以时间戳差补齐，见SUNK-COSTS.json。

## 登记对账与保全

driver结束后实际只调用原源码 `Coordinator(original_lock).task_keys(old_protocol_sha256)`：
1010个key，无run/retry/采样，新recovery sidecar0。随后用最新文档脚本绝对路径、
root=f及原共享锁取得新快照：indexed1061、legacy51、1112个真实原生Job，
indexed_active=0且全部Job absent或active_processes=0。这是登记集合，非全操作系统清空证明。
对应命令/日志/Job结束回执全部保留。快照首次相对路径因cwd=f找不到文档树脚本退出2，
原报错保留；绝对路径后继通过。停止控制第一次出生时间从CIM微秒值转换丢失700ns，
安全拒绝且未行动，错误字样PID reuse不代表实际发生PID重用；原生GetProcessTimes修正
精度后第二次成功。两次控制源码及差异均保存。

全部1152实际主输入保持原文件/数组身份；逐输入哈希见ORIGINAL-INPUT-HASHES.json。
全原件与外层日志41769文件、20644750245字节；其中研究原件41697文件、20507365882字节，
外层72文件、137384363字节。所有原冻结清单资产实际SHA核对未变。
完整逐文件保全清单SHA256：
`3b6bb9544ab14c3d1fd777aa8f1e932bb1d39cb288750948fef3bf045c6bcb83`。
压缩清单只是小型元数据，不是新全量tar；原数组仍在f原目录。
09:15:42JST实际D余量1841881034752字节（1715.39GiB），
C余量1622481690624字节（1511.05GiB），历史占用已包含在内。
源提交0ba5643与协议62ca9db5未改，原完整旧验收保留，Mac完整原始独立接收未完成。

## 回执及后继边界

小型回执根：`execution/windows-native/formal-inference-v1/user-pause-20261008/`。
原登记静止副本及原生观察在rf/output/formal-user-pause-audit-v1；未发布Release或生成全量tar。
旧41472/9216网格不自动恢复，不从成功子集挑选新重复。
已读取最新9eac03f的HOLD、COMPACT提示词与设计；紧凑适配/差异验收使用新的独立分支和身份。
本保全动作新增科学任务0，完整研究仍未完成。
