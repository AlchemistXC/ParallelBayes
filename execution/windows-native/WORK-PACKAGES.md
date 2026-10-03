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
| W6 | Running frozen design | 8 models, budgets 128/512, 4 tapes, CPU/CUDA, four MH workflows; all terminal outcomes retained. |
| W7 | In progress | Source, test receipts and all attempts retained; archive after reviewable commits. |

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
