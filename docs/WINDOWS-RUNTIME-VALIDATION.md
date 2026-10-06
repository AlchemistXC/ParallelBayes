# Native Windows runtime technical validation

Starting integration: `6f02f3735d0b534b0915a4732c31625ef6ba6bcb`, descended
from `52fdfd0446768033ffd975bc52ea8036c420880d`. Independent worktree branch
`codex/windows-runtime-validation` merges the sealed F2 receipt at `9187bcb`.
The original mechanism checkout, all historical data, frozen Python environment
and its marker remain unchanged. This does not authorize a formal grid.

## Ownership and cost boundaries

The explicit `scripts/windows/` adapters retain the scientific kernels and
portable cost semantics. Windows ownership uses atomic process creation with
`PROC_THREAD_ATTRIBUTE_JOB_LIST`, restricted handle inheritance, nested Job
Objects and `KILL_ON_JOB_CLOSE`. Kernel job membership and active count, rather
than PID disappearance, provide lifecycle evidence. All descendants, including
ordinary workers, four NUTS spawn workers and R, must stay in that job.

Microsoft references: [job objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[nested jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs),
[process attributes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute).
The new schema is `windows-owned-runtime-v1`; it makes no Mac process-group claim.

The shared cooperating-host lease rejects contention and unknown activity;
creation FILETIME protects process identity. Only the owned job is terminated.
There is no experiment duration cutoff. Sampled RSS can miss peaks and count
shared pages repeatedly. The kernel job commitment limit measures committed
host memory, distinct from RSS, and from CUDA allocator/free-memory snapshots.
Disk guards refuse before sampling or stop the owned job, retaining evidence.
Unrelated programs are outside this cooperative lock and resource accounting.

Ordinary inference exits before its independent NumPy audit. Phase and sampler
clocks are nested, not additive. External invocation, terminal verification and
batch preparation/archive costs are separate; missing clocks remain null.
Numerical/resource/unclassified failures cannot be retried as interruptions.
Posterior infrastructure interruption permits at most one explicit retry with
unchanged identities and proven old-job termination; cache interruption is not
retried. Cache measurement is never posterior-eligible.

## Engineering checks, before freezing

Current native checks: **16 passed, 0 failed, 0 skipped**. Earlier failures and
their logs are retained: an exact process-count expectation overlooked Windows
Python launcher processes; registry events initially aliased mutable details.
The fixes change runtime bookkeeping, not numerical source or tolerances.
Checks cover child/grandchild ownership, manager death, safe recovery, lock
contention, failure isolation, retry limits, changed input/source/task refusal,
memory observation failure, low artificial memory budget, impossible disk
budget, actual CUDA float64 synchronization and recoverable resource refusal,
terminal zero-recompute and single-input cache summaries.

A separate hidden persistent fixture continued registering after its launching
PowerShell process ended. Its normal release sealed seven observed processes,
kernel active count zero, measurement available and samples ineligible. This
does not establish reboot recovery or a statistical repetition.

Requested private codebase-design/TDD skills and the private migration ZIP are
absent. No private skill was guessed from a public source. Tests and interface
separation proceed using repository requirements; no skill is claimed used.

## Bounded protocols

Planned main scope is 27 four-chain tasks: G1/L1 retain 64 steps, G2 dimension
64 retains 16,384; each has CPU/CUDA sequential RWM, Picard RWM, sequential MALA,
quasi-DEER MALA, plus CPU four-spawn NUTS. MH discard 512, window 32,
quasi-DEER max 2048/window; NUTS warmup 1024, depth 8, accept .8, diagonal mass,
four processes with one thread each. Existing selected geometry/steps remain.
Three actual master inputs are generated once before freeze; file and array
hashes are shared across devices and paired executors.

A separate 24-probe cache protocol reuses those inputs, four MH combinations
on both devices, one initial plus three prepared calls per probe (at most 96).
It includes failed configurations and adds no independent input. Single-input
summaries give descriptive times and null intervals. No NUTS cache probe.

The new batch marker binds the original venv marker and complete pip lock; it
does not edit that frozen environment. Frozen source explicitly includes
`cached_execution.py`. The read-only archive analyzer has separate provenance
and is excluded from numerical source identity; it never samples or generates
inputs. Main/cache protocols and source identity must be saved before launch.

Actual technical task receipts and delivery are still pending at this commit.
Formal F3 inference, F5 platform installation and F6 manuscript gates remain
open. A technical fit or favorable timing is not a convergence or speed claim.


## 2026-10-07 native Windows technical result

Frozen source 2ddcea970cf0ed78501b53f504d7230e9c2695ec; execution HEAD 6c04eb9782695ef4e600074fa36473cde5e249e8. Main protocol 8abed79661a077b8b7a1746f1ee90b506187b79f4bf81b1c7872ec0ad3481f9c, cache protocol 350189ba8526c2020d1887aa98b9289e30ea0eb12d2eb2fbd8436cbb51ec80ab. All 27 main tasks valid, 24 cache measurements available, 96 cache calls; numerical/resource/infrastructure/unclassified failures and not-run counts all zero. Cache samples_eligible always false. No retry was needed.

All 12 same-kernel actual-array pairs pass with zero acceptance mismatch; maximum path difference 3.6082914434132363e-10. Three NUTS tasks include four observed owned spawn workers each, saved initial states/RNG/warmup/adaptation/diagnostics. G2 maximum retains 16,384 steps in four chains at dimension64. CPU/CUDA MH arrays remain float64; actual CUDA records are cuda:0. All task jobs sealed active count0.

Actual terminal resume executes 0 new tasks and preserves 831 main plus 828 cache files. Current behavior suite is 17 passed / 0 failed / 0 skipped, including real CUDA grandchild ownership and manager termination while a separate test CUDA context survives. Earlier failed test/ancillary launch attempts are retained. The read-only original-bundle audit reconstructs 27 function binaries and 90 modern R diagnostic rows exactly. Default native rebuild is exact; explicit receiver cross-platform mode preserves both binaries and uses frozen output tolerances for receiver calculations, without changing MH acceptance/path criteria.

Evidence summary: benchmark/analysis/outputs/windows-runtime-technical-v1. Raw arrays, all attempts, commands, locks, Job observations, source snapshots and dependency freeze are separate. Archive relocation/delivery remains pending at this commit. This closes only finite technical execution checks; it does not establish formal inference, convergence, general acceleration, reboot recovery, or arbitrary workload resource safety. F5 installation and the formal F3/F4/F6 gates remain open.


Resource-counter qualification: a bounded 128 MiB allocation is denied under a 64 MiB JobMemoryLimit and succeeds under 256 MiB (2 checks passed). The denied case nevertheless reports raw PeakJobMemoryUsed=147,828,736 bytes, above its limit. Therefore archived field kernel_peak_job_commit_bytes must be interpreted as the raw Windows counter, not a proven maximum of successful commitments. G2 NUTS raw counter 45,916,721,152 bytes is retained; its exact internal cause is not identified. Maximum sampled job RSS is 3,636,400,128 bytes, distinct from VRAM and not a no-missed-spike bound. Low RSS, observer error, lifecycle and CUDA resource refusal remain separately tested. Current distinct checks are 17 behavior/summary plus 2 matched allocation checks, all passed, no skips. No failed scientific task was removed or retried.
