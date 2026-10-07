# Native Windows development evidence

2026-10-07 原始结果读取后继（`62b7268`）：新增独立 `scripts/analysis/formal_science.py`，接入 v2 历史/费用、实际输入、独立 NumPy 路径重放、原坐标函数、原始 R 诊断重建及缓存失败保留。11项不同新检查通过，旧3份真实 NUTS 数值布局读取通过、原件不变；人工 v2 文件不构成 Windows 实测。执行源码、冻结协议和旧结果未改。完整研究框架索引、统计汇总、正式实验及论文仍待完成；现有 Windows 适配提示词继续有效，无需增加或重跑旧提示词。详见 docs/FORMAL-RAW-READER.md。

Branch: `windows-native-dev`. Baseline: `a774d83` (0.1.1 JAX/BridgeStan).
New version: `0.2.0.dev1`. Local date: 2026-10-04 (Asia/Tokyo).
Historical 1920 main tasks, 320 SBC tasks, 72 mechanism tasks, L2 uncertainty and all frozen identities remain unchanged.

| Work package | Actual status | Evidence |
|---|---|---|
| S | Blocked only on private ZIP transfer; independent work continues | `skills-status.json`; 30 private directories absent; system skills and plugin catalog checked. Expected `downloads/parallelbayes-user-skills-2026-10-04.zip`. |
| W0 | Framework validation passed | `bootstrap-20261004T071136-c8621336/`: pip reports, check, freeze, GPU probe; torch 2.13.0+cu130, native Python 3.12.14 x64, RTX 5080 sm_120, driver 616.56. |
| W1 | Initial CPU and CUDA correctness passed | NumPy-only oracle and optional imports; all native target families; `torch-cpu-02.xml`, `torch-cuda-01.xml`. |
| W2 | Eager executors correctness passed | Final CPU suite 65 passed; CUDA 63 passed, 0 skipped. 72 positive raw-array comparisons passed; failed/replayed/fallback negative arrays saved. Explicit clipping, shortened final windows and resume-tampering checks added. |
| W3 | Completed within stated baseline scope | R 4.6.1 and libraries in D:\Tools; 8 R batch checks passed. Pyro 1.9.2 CPU NUTS verified on normal targets. SBC: 12 data sets, 60 fits completed, all modern diagnostics saved; analytic/MCMC coverage 9/12, endpoints and moments separately compared. GPU NUTS and native Stan compilation remain unverified. |
| W4 | 96/96 pilot tasks completed | `pilot-01`, `pilot-analysis`: G1/G2/L1 × chains 1/4 × windows 8/16 × CPU/CUDA × four workflows. Actual arrays, timings, host scalar waits, maps/JVP, allocator peaks retained. Both speedups and slowdowns retained. |
| W5 | Frozen before formal results | Source `0c9325e98f2bc7dcd75d344c01c2e50a62801c90`; protocol SHA256 `1d233dd09956c4575fc5775082310e5edca65407db5fcef40bc2ce329e6f5898`; 512 tasks, actual input files, Python/R locks, device/runtime and venv freeze marker saved. |
| W6 | Completed; computational checks passed, inference limitations retained | 512/512 completed, 0 terminal failures/fallbacks; 256 CPU/CUDA array pairs checked, 0 event mismatches. Modern diagnostics for all 512 fits. Resume added no attempts. `windows-native-v1/final-identity-audit.json`; formal analysis in `benchmark/analysis/outputs/windows-native-v1`. |
| W7 | Completed within documented scope; first full export verified | First archive `windows-native-20261003T233726Z.tar`: 5862 files checked; SHA256 `87cae2da96035ab76a04880b04b56e59fbed29aae2fec1e6085c247ca5213b56`; `return-verification-initial.json`. Final archive adds this receipt and final status commit. Wheel lazy/NumPy import and actual CUDA shortened-window audit passed. Revised manuscript PDF remains uncompiled. |

Actual commands are recorded in logs and will be consolidated in `docs/WINDOWS-NATIVE.md`.
Python 3.12.10 installer signature passed but per-user MSI returned 0x80070003;
`python-install.log` preserves the attempt. The existing bundled Python 3.12.14 is
used only as the base interpreter of the isolated `.venv-win-torch`; its packages are not modified.
Initial CPU suite: 59 passed / 2 failed due to an incorrect exact-boundary test
fixture involving sqrt(2). Changed to binary-exact h=.5; rerun 61/61 passed.
No failure logs were overwritten. Eager Python scalar synchronization is counted;
no efficient device-side loop or Windows CUDA compiler claim is made.

Legacy JAX CPU regression: 51 passed / 7 Stan cases deselected; separate
`.venv-win-jax-regression`, no JAX installed in the torch venv. Portable handoff
utilities: 17 passed / 1 skipped (non-Windows refusal test on Windows).
R locale startup warnings from inherited C.UTF-8 were resolved for later commands
by using `LC_ALL=C`, `LANG=C`; earlier warning logs remain intact.

Development validation/pilot/SBC began in an uncommitted working tree based on
`a774d83`. Their exact source bytes were recovered and verified against the hashes
already recorded at execution: `source-drafts/` (32/33/35 files respectively,
zero missing). These are first-party source snapshots, not private skill code.
Formal work uses a clean source commit and immutable protocol identity.

Formal numerical evidence: maximum independent NumPy path error 5.2116e-10;
CPU/CUDA maximum unconstrained/constrained differences 2.8422e-14/5.6844e-13.
Warmed group-median sequential/time speed ratios: CPU quasi-DEER 0.101–0.359,
CPU Picard 0.774–3.560, CUDA quasi-DEER 0.164–0.505, CUDA Picard 1.097–5.230.
All 32 A1/RWM fits accepted zero proposals: their speed reflects self-transitions.
480/512 fits had a finite Rhat >1.01; 108 had constant variables/estimands.
Numerical completion is not convergence certification. L1/L2 reference remains unresolved.

Post-freeze review explicitly withdrew the pilot's configuration-pooled accuracy
interval; `pilot-analysis/summary.original.json` preserves the original hash
referenced at freeze. The correction does not change formal source, tasks or data.
The initial post-freeze reviewer used full task hashes for folder names; the
FileNotFoundError is retained in `delivery-review.log`. It was corrected to the
driver's 20-character directory convention; `delivery-review-final.log` passed.

Private ZIP remains absent at final file check; 30 user skills including
nature-shared remain uninstalled and have not been runtime-validated. Existing
plugin discovery and account/platform limits are recorded separately. Native
Stan compilation, GPU NUTS, fused device control and full historical CPU random
array replay are not claimed. The frozen venv and all 39 source hashes are intact.

Export includes a verified Git bundle with the complete local branch history,
the exact-byte frozen source snapshot, raw arrays, all attempted tests/runs,
protocol/data/locks, figures and independent archive verifier. No remote push,
CRAN release, private skills, credentials or installed venv is included.
The final archive's own verification receipt is adjacent to it under
`output/windows-return`; an archive cannot contain its own final hash.


## Receiving-machine review, 2026-10-04

The remote branch and final archive are now received at `3a51f98`; 5866 archived
files and the complete Git bundle verified on Mac. See
[`docs/WINDOWS-RETURN-AUDIT.md`](../../docs/WINDOWS-RETURN-AUDIT.md).
Read-only NumPy replay covered all 512 formal tasks with zero event mismatches;
64 paired speed groups, 128 error groups and 60 SBC fits were reanalyzed.
R CSV parsing sensitivity was found: a binary input companion analysis leaves
only two Rhat discrepancies, with major diagnostic classifications unchanged.
Original Windows diagnostic outputs remain authoritative for the original run;
the remaining cross-platform discrepancies are disclosed, not silently replaced.
Mac JAX regression: 51 passed, 7 Stan tests deselected. R CMD check --no-manual:
OK with PB_RUN_INTEGRATION=1 (15 assertions passed, 0 failed/skipped/warnings).
The updated 20-page Chinese PDF now compiles with the existing Tectonic runtime.
Scientific source, protocol and all Windows/Mac raw data are unchanged. Review
changes stay on `codex/windows-return-audit`; no main merge or Release publication.

## Native Windows second-round execution, 2026-10-05

Branch `codex/windows-completion-v2`, isolated worktree from `f5148ee`.
No active Python/R experiment processes or existing second-round receipts were
found before starting. The original project, venv and first-round raw arrays
remain in place. Six new frozen protocol identities and every listed source
hash matched before execution. Actual dependencies match the original frozen
Windows environment; no installation or upgrade was performed.

| Stage | Actual status | Evidence |
|---|---|---|
| F1 | Passed native fixed-input diagnostic | `benchmark/analysis/outputs/completion-f1/windows-01/`; R 4.6.1/posterior 1.7.0, native center `0x1.7701bac434f11p-10`, Rhat 1.40822237244096, five rank changes, identical binary roundtrip. |
| F2 | Blocked before sampling; 192 pending | All six reconstructed actual tapes differ from frozen hashes. Full rejected arrays/component hashes and traceback retained in `mechanism-rejected-inputs/`; original frozen NPZs are needed. No hash or protocol changed. |
| F4 | Passed target/transport validation | 12 CPU/CUDA/R workflows; zero event mismatches; maximum path difference 9.06e-11; R binary replay identical. Rhat 3.036/3.817 retained, no convergence claim. |
| F3 CPU NUTS | Passed readiness and resume | 9 completed, 0 failed; six array classes byte-identical serial/spawn; 18 R binary roundtrips; zero recomputation, 126 terminal files unchanged. Seven targets have finite Rhat >1.01; L2/H1/M1/W1 have undefined functions. |
| F3 CPU/CUDA MH | Passed readiness and resume | Each device: 9 targets, 54 workflows, 36 pairs, 54 independent saved-array NumPy replays; zero event mismatches. Resume: 0 new tasks, 135 terminal files unchanged per device. H1/MALA all-rejection chain preserved. |

Every command has a separate command line, environment, timestamps, exit code
and combined stdout/stderr record under the batch `commands/` directory.
The private skill ZIP remains absent; no private skill contents are archived.
No unfrozen formal inference grid is authorized by this execution record.

F2/F4 handoff checks: initial 2 passed/1 skipped/3 setup errors from an inaccessible
pre-existing pytest temporary directory. The preserved retry uses a fresh batch
temporary directory: 5 passed/1 skipped/0 failed. Windows msvcrt exclusivity passed.
NUTS tests: 3 passed/0 failed/0 skipped. Original attempted logs remain in `commands/`.

MH tests: 3 passed/0 failed/0 skipped, including actual CUDA. Supplementary read-only
CPU/CUDA comparison passed all 54 pairs, with zero event mismatches and maximum
path/output difference 1.084e-12. No sampler source or frozen protocol changed.
Small evidence and SHA256 manifest: `benchmark/analysis/outputs/windows-completion-v2/`.
Full interpretation: `docs/WINDOWS-COMPLETION-V2-RESULTS.md`. The 192 blocked
mechanism workflows remain pending, not passed or deleted. Final export retains
raw arrays, failed input reconstructions, complete logs and source history.

Pre-delivery validation passed: all six canonical protocol/source identities,
unchanged original distributions/pip freeze/frozen marker, 369 raw task assets,
95 curated receipt files, all command log hashes and actual JUnit counts.
Receipt: `benchmark/analysis/outputs/windows-completion-v2-final-check.json`.

## Original-input F2 completion, 2026-10-06

Branch `codex/windows-mechanism-completion`, execution HEAD
`52fdfd0446768033ffd975bc52ea8036c420880d`. Initial workspace was clean and no
Python/R experiment process was active. The existing frozen Windows venv and
its marker/distribution inventory match the prior round; no dependency changes.
All 41 protocol source files match after restoring one pre-existing CRLF
working copy of `reference.py` to the identical frozen Git blob. Previous bytes
and before/after hashes are preserved in the new batch; no semantic change.

The six original Mac-frozen NPZ files were downloaded from existing draft
`windows-completion-v2-20261005`; tar 10,823,680 bytes, SHA256
`2b46eedc58067c920c8519cb4f99965bf944202f57392514d4643b847f9b9e5a`.
All six file/actual-array hashes passed. Comparison to preserved rejected
Windows tapes confirms only 82 log-uniform elements differ; noise/directions
are identical. Old candidates and preparation error logs remain untouched and
are also copied into this batch for complete replay context.

New input/runner tests: 5 passed, 0 failed, 0 errors, 0 skipped; 18 existing
torch.jit deprecation warnings retained. Separate command receipts/logs under
`output/completion/windows-mechanism-original-attempt01/commands/` use the new
explicit-batch `scripts/windows/record_step.py`, not the old hardcoded wrapper.

| Device | Groups completed/failed/pending | Workflows completed/failed/pending | Evidence |
|---|---|---|---|
| CPU | 36/0/0 | 96/0/0 | Explicit original-input analysis passed; actual terminal resume: 0 new groups, 1360 terminal files unchanged. |
| CUDA | 36/0/0 | 96/0/0 | Actual RTX5080 CUDA, float64; original-input analysis and terminal resume passed, 0 new groups and 1360 unchanged files. |

Per device: 480 technical calls, 60 sequential/time path pairs and 64 operation
probe batches passed. Additional 96 CPU/CUDA saved-array pairs passed with zero
events mismatched, maximum path/output difference 8.882e-15. Independent oracle
path differences stay below 3.845e-10. All 2648 task assets and 143 small receipt
files verified. Every first sampling call reports the expected device/float64.

Adverse results: all 24 quasi-DEER cells per device were slower; Picard's cached
ratio exceeded one in 20/36 CPU and 32/36 CUDA cells, with all other cells retained.
Each device has 6 zero-acceptance workflows and 21 all-rejection chain records,
which reuse inputs across windows and are not independent event replications.
Initial maps/JVPs/confirmed transitions per device: 158430/51072/33024.
All costs, rounds, prefixes, residuals, clipping and memory records are archived.
Full report: `docs/WINDOWS-MECHANISM-COMPLETION.md`; small evidence and SHA256:
`benchmark/analysis/outputs/mechanism-windows-pilot-v1/windows-20261006/`.

Only terminal resume is tested here. Interrupted recovery, native Windows
process-collection/resource protection, maximum tasks and formal inference
remain separate gates. F1/F4/NUTS/MH and historical 512 tasks were not rerun.


## 2026-10-07 Windows F3 native engineering, before science freeze

Independent branch codex/windows-runtime-validation starts from verified research-integration 6f02f373 and merges the sealed F2 evidence at 9187bcb. Original mechanism worktree and frozen environment are unchanged. Native Windows Job Object lifecycle, shared lock, guarded resources, attempt classification, separate cache eligibility and portable cost receipts are implemented in new scripts/windows adapters; historical Mac runtime files remain untouched.

Current behavior and single-input tests: 16 passed / 0 failed / 0 skipped. Earlier failed test attempts are retained in output/windows-runtime-engineering-v1. A hidden persistent fixture remained registered after its launching shell exited, then sealed kernel active-process count 0 with cache measurement_available=true and samples_eligible=false. Artificial fixtures are not MCMC repetitions. Requested private skills/ZIP are absent; no guessed private code or claimed skill use.

Bounded 27-fit plus 24-cache-probe protocols are pending freeze/execution. No formal grid launched. See docs/WINDOWS-RUNTIME-VALIDATION.md.


## 2026-10-07 native Windows technical result

Frozen source 2ddcea970cf0ed78501b53f504d7230e9c2695ec; execution HEAD 6c04eb9782695ef4e600074fa36473cde5e249e8. Main protocol 8abed79661a077b8b7a1746f1ee90b506187b79f4bf81b1c7872ec0ad3481f9c, cache protocol 350189ba8526c2020d1887aa98b9289e30ea0eb12d2eb2fbd8436cbb51ec80ab. All 27 main tasks valid, 24 cache measurements available, 96 cache calls; numerical/resource/infrastructure/unclassified failures and not-run counts all zero. Cache samples_eligible always false. No retry was needed.

All 12 same-kernel actual-array pairs pass with zero acceptance mismatch; maximum path difference 3.6082914434132363e-10. Three NUTS tasks include four observed owned spawn workers each, saved initial states/RNG/warmup/adaptation/diagnostics. G2 maximum retains 16,384 steps in four chains at dimension64. CPU/CUDA MH arrays remain float64; actual CUDA records are cuda:0. All task jobs sealed active count0.

Actual terminal resume executes 0 new tasks and preserves 831 main plus 828 cache files. Current behavior suite is 17 passed / 0 failed / 0 skipped, including real CUDA grandchild ownership and manager termination while a separate test CUDA context survives. Earlier failed test/ancillary launch attempts are retained. The read-only original-bundle audit reconstructs 27 function binaries and 90 modern R diagnostic rows exactly. Default native rebuild is exact; explicit receiver cross-platform mode preserves both binaries and uses frozen output tolerances for receiver calculations, without changing MH acceptance/path criteria.

Evidence summary: benchmark/analysis/outputs/windows-runtime-technical-v1. Raw arrays, all attempts, commands, locks, Job observations, source snapshots and dependency freeze are separate. Archive relocation/delivery remains pending at this commit. This closes only finite technical execution checks; it does not establish formal inference, convergence, general acceleration, reboot recovery, or arbitrary workload resource safety. F5 installation and the formal F3/F4/F6 gates remain open.


Resource-counter qualification: a bounded 128 MiB allocation is denied under a 64 MiB JobMemoryLimit and succeeds under 256 MiB (2 checks passed). The denied case nevertheless reports raw PeakJobMemoryUsed=147,828,736 bytes, above its limit. Therefore archived field kernel_peak_job_commit_bytes must be interpreted as the raw Windows counter, not a proven maximum of successful commitments. G2 NUTS raw counter 45,916,721,152 bytes is retained; its exact internal cause is not identified. Maximum sampled job RSS is 3,636,400,128 bytes, distinct from VRAM and not a no-missed-spike bound. Low RSS, observer error, lifecycle and CUDA resource refusal remain separately tested. Current distinct checks are 17 behavior/summary plus 2 matched allocation checks, all passed, no skips. No failed scientific task was removed or retried.


2026-10-07 delivery: primary archive windows-native-20261006T170711Z.tar, 1,083,330,560 bytes, SHA256 6ef0f6e299867d67b27cbd4067a062a30f3593894dc4b34c1da9086f80ae7274, 3,753 manifest files verified. Safe extraction into a new directory and independently owned read-only analysis rebuilt all 27 planned rows, 24 cache rows, 96 call records, 27 function binaries and 90 R rows; all 12 pairs passed. Reconstruction jobs finished kernel active count0. New reader preserves raw memory counter semantics and explicit cross-platform differences. Initial archive creation clock was not separately recorded and remains unknown; inference/cache invocation and extra verification clocks are preserved. No new sampling during recovery or reanalysis.

Receiver: `python scripts/windows/audit_technical_batch.py audit --bundle EXTRACTED/output/windows-runtime-technical-v1 --output NEW_ANALYSIS --rscript Rscript --r-library R_LIBRARY --cross-platform`. Actual Mac execution of this command remains receiving-side work. Current bounded runtime checks pass; formal scientific freezes remain gated on merged F2/cost/analysis/version intake, not on this pilot alone.


## 新有限 v2 原生验收入口（2026-10-07）

执行源码06e75c1；prepare/test/run/verify-only/seal/verify/export接通，共享既定控制设置，27主任务与24缓存测量固定在独立技术身份。8项新增本地检查及2项受影响检查通过；首轮1个测试异常文字大小写失败保留，最终无失败/跳过。三份测试输入和归档仅用于本地接口/存储检查，无新Windows Job、CUDA、MCMC或正式重复。

Windows新任务入口为handoff/windows-completion/CODEX-PROMPT-FORMAL-VALIDATION.md，一次全文提供，按顺序执行；旧F2/v1运行器/安装提示词不重复。原生16行为用例、51任务、96缓存调用、零重算及封存均尚待实机结果，不把代码准备计为通过。Mac继续完整正式原始结果分析，F3/F4/F5/F6未关闭。详见docs/FORMAL-NATIVE-VALIDATION.md和formal-native-producer-v1回执。

## 新 v2 原生适配验收开始（2026-10-07）

从research-integration 6df04793e0cecb2633f5cc3bbdeea5a8b3228145建立短路径v2独立分支codex/windows-formal-adapter-validation，包含执行祖先06e75c113e3ea6ea5a2a4275d7341595eefd7191。原工作树/旧F2/F3/安装结果保留，不重跑。源码与测试的工作树字节均与Git canonical LF一致。

使用既有冻结D:/workspace/ParallelBayes/.venv-win-torch/Scripts/python.exe，Rscript D:/Tools/R-4.6.1/bin/Rscript.exe，R库D:/Tools/R-library-4.6；实际旧回执确认。共享锁仍为D:/workspace/ParallelBayes/output/runtime/windows-shared-host.lock，位于证据包之外。旧水井快照8文件大小/SHA256全通过；不补取或更换上游版本。原venv标记不修改。

新增witness_formal_stage仅在包外保存CLI命令、原生外层Job/实际句柄/所有后代、日志与外层调用时间；不持有科学主机锁、不增加资源/总时长限制、不改变数值或失败政策。内部原生运行器继续管理任务锁与资源。待依次prepare/16行为用例/27主任务/24缓存探测/终态核验/封存/搬移。正式统计重复0；不启动全网格。

私有技能目录/ZIP缺失（parallelbayes-user-skills-2026-10-04.zip）；未猜测公开替代技能，继续独立执行。完整命令/失败/原始证据保存output/formal-adapter-validation-v1及独立commands目录。

Prepare前首次witness启动失败：7bbc39d的Job API在with NUL退出后才清除继承标志，调用已关闭NUL句柄触发0xc0000008。子进程从未resume，Job active0，validation包不存在、输入生成0。原失败JSON和旧源码保留在包外commands目录。兼容修复仅延长NUL句柄生命周期到SetHandleInformation清理完成，并检查返回值；外层witness追加自身异常日志。微软API依据：https://learn.microsoft.com/windows/win32/api/handleapi/nf-handleapi-sethandleinformation。数值源码、参数和16行为用例不变；修复提交后重新prepare新目录，不续算任何旧冻结输入。
