# Native Windows development evidence

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
