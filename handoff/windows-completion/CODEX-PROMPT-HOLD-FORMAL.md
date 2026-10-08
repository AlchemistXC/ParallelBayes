用户已因资源规模要求缩减ParallelBayes正式实验，旧正式采样已启动。请先执行本条保全任务，不继续派发旧网格，不启动新实验。原生Windows/PowerShell，不用WSL。

1. 记录当前真实执行入口、父命令/driver PID、创建时间、命令行、工作树/提交、正式身份与协议哈希、当前任务/attempt、共享锁和Job名字。停止外围脚本继续发起后续批次。不要先切换或修改正在运行的冻结工作树。
2. 旧scripts/windows/formal_batch.py没有--pause/--stop。formal_owned_runtime.py的BaseException处理可能吞下KeyboardInterrupt，终止当前Job后继续下一个任务。因此不要声称按一次Ctrl+C就已暂停。核对本机实际源码与启动方式后，使用你持有的当前命令执行句柄终止这一明确归属的driver/外层命令Job；必要时按PID＋创建时间＋命令行三重核对后只停止它。保留动作日志。不kill所有python、不删除锁、不结束无关用户进程。若已有可验证的任务边界停止机制，优先使用；没有就有序终止当前所属运行，保留部分证据。
3. 仅在driver确实停止后，用原冻结源码、原shared_host_lock调用formal_owned_runtime.Coordinator(...).task_keys(旧protocol_sha256)，只做登记对账，不调用run/retry。这不会采样，recovery sidecar保留未封口尝试和原失败类别。不要手改state.json，不把此前resource_failure改名伪装成功。
4. 从最新文档工作树调用scripts/windows/snapshot_quiescent_registry.py，参数--root指向原冻结源码、--lock指向原共享锁、--output为新的快照目录。不要把该辅助脚本复制进冻结工作树。该脚本只验证/复制登记；须取得索引active=0且全部已注册Job absent或active_processes=0的回执。若仍有活跃或归属不明的Job，保留等待、报告具体对象；不能运行旧formal_batch --resume做核验，它会派发新任务。
5. 输出旧研究中止清单：修订提出时与停止后的状态时点、已完成/失败/中断/未运行数、已可见的结果摘要范围、实际随机输入数量和哈希、目录字节、每卷余量、已知/未知累计费用。未知不填零。记录本次因用户资源要求中止，保留所有结果及历史尝试，不挑选成功子集、不自动重试、不删文件。不为了打包再生成一份全量tar。
6. 将小型保全报告和源码状态推送开发/交付分支，原始数组留在原目录；不得强推或公开草稿Release。告诉用户旧任务是否真正停止，以及回执路径。随后阅读新的CODEX-PROMPT-COMPACT-STUDY.md；当前保全任务本身不启动新采样。
