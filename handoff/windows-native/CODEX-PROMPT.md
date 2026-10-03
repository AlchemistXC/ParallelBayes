你正在我的Windows 11原生电脑上接手ParallelBayes。硬件为AMD CPU和NVIDIA RTX5080。请实际开发、验证并开展Windows实验，持续推进到本轮可交付状态，不要只回复计划。不要使用WSL2、Linux虚拟机或Linux容器；不要改成CPU后台却把它称为GPU实验。允许建立项目虚拟环境、安装项目依赖、编写源码/测试/脚本、运行实验和提交本地开发分支。驱动安装/重启等需要我操作时说明具体原因；不要重复询问已经授权的常规步骤。

先读仓库AGENTS.md及以下文件：
1. handoff/windows-native/README.md、WORK-PACKAGES.md、SKILLS-SETUP.md和skills-inventory.json；
2. docs/CAPABILITIES.md、COMPUTATION-CONTRACT.md、CPU-REVIEW-REVISION.md、VERSION-BRIDGE.md；
3. manuscript/software/软件与基准研究.tex、revision.generated.tex；
4. r-package/inst/python/parallelbayes/{models,kernels,executors,sampling,reference,output}.py（以实际存在文件为准）、tests/python和tests/safety；
5. benchmark/protocols/protocol-v1.json、cpu-mechanism-v1.json，以及对应分析脚本。

优先核对状态：当前发布内核0.1.1是JAX/CPU＋BridgeStan顺序入口，没有PyTorch后端。Stan仅CPU顺序RWM/MALA；明确原生JAX目标才支持quasi-DEER MALA、Online Picard RWM与BlackJAX NUTS。当前包__init__直接导入JAX，pip安装现有pyproject也会拉JAX；不能只装torch、改backend字符串就宣称移植完成。历史GPU包handoff/gpu属于WSL/JAX归档，禁止作为本轮执行入口。历史文件的GPU暂缓记录是2026-10-04以前的状态；我现在授权原生Windows阶段。

保留MacCPU的原1920任务（0.1.0）、320SBC、72机制任务、全部负结果、L2参考不可判定与源码/协议身份。新开发使用独立分支和版本，如windows-native-dev；不能直接改历史快照、旧协议哈希或原始结果。按当前实际分支状态选用/建立开发分支，不覆盖其他未提交修改。每完成一个工作包，更新execution/windows-native/WORK-PACKAGES.md，附实际证据。我还授权你在这台Windows上安装Mac已有的技能。先按下面S步骤迁移，再选用适合当前工作包的技能；技能迁移不应阻止其他独立开发工作。

依次完成下列工作：

S. 安装与核验技能。
先检查Windows Codex已有技能和插件。按SKILLS-SETUP.md，将我单独转交到downloads/的parallelbayes-user-skills-2026-10-04.zip，用scripts/windows/install_local_skills.py逐文件校验后安装30个用户技能的完整目录（包括nature-shared）。默认使用官方用户目录~/.agents/skills；若本机实际使用CODEX_HOME/skills则指定--dest，同名技能不要装两份或覆盖已有不同版本。ZIP尚未转交时明确告诉我这个文件名，同时继续环境/源码工作；不要从公开仓库寻找不存在的私有技能。迁移包不包含账号凭证、系统技能或插件缓存，禁止将其提交到公开GitHub。

系统skill-installer/skill-creator优先使用本机内置版本；公开技能缺失且有明确来源时使用$skill-installer及其辅助脚本。插件附带的技能按SKILLS-SETUP.md的清单，通过Windows Codex插件目录查找、安装该账号支持的对应插件；需要人工连接或平台不支持时逐项记录，不声称复制SKILL.md就安装了MCP工具。不要安装Mac二进制、复制旧config/auth文件或启用WSL。

下一轮确认技能已被发现，必要时重启Codex。对当前任务优先核对codebase-design、tdd、nature-paper-card、nature-statistics、nature-experiment-log、nature-figure、nature-writing、nature-reviewer。使用前检查Mac绝对路径、bash/Homebrew和脚本依赖，按Windows实际环境适配并记录差异；科研工具依赖放独立环境，不污染冻结的GPU环境。输出execution/windows-native/skills-status.json，分别记录文件安装、发现、运行验证、待人工连接和平台限制。

A. 环境与可运行性。
使用原生PowerShell、Python3.12 x64、独立.venv-win-torch。先核对官方PyTorch Windows CUDA支持和驱动；handoff中2.7.1/cu128只是已有官方构建的起始候选，不是已验证锁或必须坚持的最新版本。运行scripts/windows/bootstrap.ps1和probe_environment.py，若现有驱动/构建不支持5080，记录失败与官方依据，建立新的具名候选环境，不把失败文件覆盖掉。必须实际验证float64设备运算、torch.func.grad/jvp/vmap、架构和显存；保存pip安装报告、pip check、完整pip freeze、Python/驱动/CUDA版本及源码提交。初期不要求CUDA Toolkit/VS/Rtools，只有实际扩展编译或Stan功能需要才追加。不绕过Codex沙盒或系统安全策略。

B. 模型与独立顺序参考。
把PyTorch实现放在可替换的数值模块接口后，避免torch后端运行强制依赖JAX。参考NumPy实现也应可独立导入。先实现解析高斯、相关高斯、logistic、正值变换，再覆盖H1/H2、A1、M1等正式模型。共同JSON spec、数据、参数顺序、无约束坐标和Jacobian一致；比较相对log密度、梯度、所需JVP及constrain。不要把支持离散观测写成支持离散潜参数采样。新包能力查询须只列实际通过的组合。

核约定不能改：MALA y=q+h*grad(logp)+sqrt(2h)*z；RWM y=q+s*z；接受规则及正反向MALA提议比沿用计算契约。固定的是实际noise、log_uniform和directions数组，不是两个框架的相同seed。NumPy oracle不得调用待核验torch转移。GPU与CPU比较包括接受事件、路径、非有限及约束输出，不只比较均值。

C. 两条时间执行路线。
先实现顺序MALA与窗口quasi-DEER，再实现顺序RWM与Online Picard；逐项核对硬接受前向、代理导数、Rademacher JVP、对角裁剪、仿射扫描组合次序、残差、非重叠/滑动窗口、末窗口掩码、已确认前缀和拒绝自环。失败/核验失配不进入正常posterior样本；显式回退保留已花成本并复用原实际随机数组，不重抽或删难样本。包含密度/梯度/Jacobian、接受临界值、非有限、迭代耗尽、内存守卫、错误注入和失败重放测试。CPU先验证torch实现，然后同机CUDA核验；不需要等待Mac实施PyTorch移植。

如果torch eager中Python循环、.item()、主机条件判断或重复主机传输成为主要开销，记录同步/传输，不把这种原型称为高效设备内时间并行。可以研究设备内scan/控制流或编译实现，但必须先核对当前Windows官方支持，并单独核验语义与构建成本；不默认torch.compile或Triton可用，不静默回到WSL。数值输出与GPU驻留均通过后才运行性能探测。

D. R入口与统计验证。
用reticulate连接原生Windows Python，整批调用；posterior::draws_array次序仍为iteration×chain×variable。明确Stan仍是CPU提供方式，torch后端不自动翻译Stan。选择并核验成熟PyTorch NUTS候选（例如Pyro，先查官方支持），或明确保留仅CPU的成熟基线及尚未接入的范围；禁止把BlackJAX改名为GPU NUTS。不同核/软件NUTS不能与MH宣称固定同轨迹比较。先做解析统计量与小型SBC；同时比较同数据集的解析区间、端点及矩，不将共享数据的五个工作流当作五份独立证据。保留rank/folded Rhat、bulk/tail ESS及常量函数不可判定。

E. 探测、冻结和正式实验。
首先小网格探测模型、链数、窗口和实际GPU驻留；记录每个确认转移的耗时、映射/JVP次数、求解轮数、前缀、内存及设备同步/控制开销。随后在观察正式结果前冻结新的windows-native-v1协议，写入源码commit、完整依赖锁、设备、数据、实际随机流、坐标、核参数、容差、预算、独立重复、函数集合、参考来源、不确定性及失败规则。原Mac协议仅作设计参考，不借旧身份继续新代码。冻结时在所用venv根目录保存PARALLELBAYES-FROZEN.json，载明协议身份、源码提交与依赖锁哈希，禁止重新运行bootstrap修改冻结环境。

主比较是同Windows、同PyTorch、同目标和精度下的顺序与时间执行，CPU/GPU资源条件分清。Mac JAX对Windows torch只能称完整工作流比较，不能把全部差异归因显卡。计时用torch.cuda.synchronize或正确CUDA events，记录编译/预热/采样/输入输出/传输/核验/诊断/回退；区分缓存、正常推断、完整研究审计。不要以短链ESS替代真实重复误差，或把两个预算点写成精确达标时间。所有失败、负加速和参考未确定均保留；不以出现加速为验收。选择器继续暂缓。无总时长人为上限，但有数值迭代、内存和失败规则；可恢复任务必须核验协议/源码/环境/输出校验和，不能跨环境续算却不留记录。

F. 可核验交付。
提交可用代码、安装说明、测试及实际命令，并更新Windows支持矩阵。执行期间和结束后保存工作包状态、源码版本、完整协议、设备依赖清单、全部任务状态与原始数组、失败及尝试日志、分析脚本、图表和SHA256。用scripts/windows/export_results.py导出指定结果目录并核对清单，不只交截图或成功摘要。结果回传本项目后才能把GPU写为已验证；稿件只根据真实新数据修订。

历史完整证据从cpu-review-v1 Release下载，按README校验分块并解压到独立目录；不覆盖当前Git目录。无需下载5GB就能开始模型/内核开发，但需要旧随机数组做历史重放时必须取得并核验。新开发提交保留在独立分支，先完成可审阅提交和结果包；不要强推main、删除旧结果或自动发布CRAN/期刊。若遇到真正阻塞，保存可重放错误和已完成产物，继续不依赖该阻塞的工作，最终说明未完成项，不把未测试路径标为通过。
