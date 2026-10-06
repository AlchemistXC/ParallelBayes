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
