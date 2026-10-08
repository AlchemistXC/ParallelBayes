# ParallelBayes project instructions

## Current work

As of 2026-10-04, the user has authorized the native Windows 11 / AMD CPU / RTX 5080 phase. Read `handoff/windows-native/README.md`, `CODEX-PROMPT.md` and `SKILLS-SETUP.md`. The user also authorized skill migration; use the separately transferred private ZIP, never publish it. Use native PowerShell and native Windows Python; do not substitute WSL2, a Linux VM or a Linux container. The historical handoff describes the 0.1.1 JAX core. The received `windows-native-dev` branch at `3a51f98` implements the optional 0.2.0.dev1 PyTorch backend and includes native Windows CPU/CUDA evidence. Consult `docs/WINDOWS-RESULTS.md` and `docs/WINDOWS-RETURN-AUDIT.md` for verified scope; do not restart completed experiments from the old handoff prompt. Older CPU documents that say GPU work is deferred describe the historical CPU milestone, not the current authorization.

Current execution entry: `docs/CURRENT-SCOPE.md`, `docs/RESEARCH-COMPLETION-PLAN.md` and `execution/COMPLETION-WORK-PACKAGES.md` (F0–F6). The unified development entry is `codex/research-integration`; Windows follow-up starts at `handoff/windows-completion/README.md`. As of 2026-10-07, F1/F2, bounded v1 runtime, isolated package installation **and finite native v2 acceptance** have passed independent intake. Do not rerun their prompts. `docs/WINDOWS-FORMAL-V2-INTAKE.md` records 16 actual native behavior tests, 27 main tasks, 24 cache probes/96 calls, all 51 tasks independently read on Mac, 117 R function rows and zero-reanalysis resume. Retain prior failures and undefined diagnostics; these are technical checks, not formal independent repetitions or convergence evidence.

The active design has changed on 2026-10-08 at the user's request: the old formal sampling **has already started** (user-confirmed; its current counts and process state are not yet independently received). The user provides approximately 50–80 GiB additional storage. Stop further dispatch of the old full grid, preserve all completed/failed/partial results and actual inputs, and record a post-start resource amendment. Do not relabel old successful tasks as a new prospective study.

Current Windows sequence: `handoff/windows-completion/CODEX-PROMPT-HOLD-FORMAL.md`, then `CODEX-PROMPT-COMPACT-STUDY.md`. Read `docs/F3-COMPACT-DESIGN-v1.md`. The new design is 9 targets × 9 workflows × 2 budgets (1024/4096) × 24 original four-chain repeats = 3,888 main tasks, plus 256 cache probes (1,024 calls) and 216 fresh input files. Three prespecified batches contain 1,296 main tasks each, with 64/64/128 cache probes. New identity: `windows-compact-inference-v1`. The metadata planner is implemented; the compact freezer/controller/receiver adaptation and native validation are **not yet implemented/passed**. Old fixed-grid CLI cannot consume the new JSON. Do not remove source/identity checks to make it run.

The old accepted commit 0ba5643a6b580e79b8040f13a5e3165322db0e77 and its frozen protocols/evidence remain historical. Do not edit or restart its full grid. That driver has no pause flag and its inner runtime can swallow KeyboardInterrupt; one Ctrl+C is not proof of stopping. The Windows hold prompt requires exact driver/owned-Job identification, native end evidence, registry reconciliation and preservation, without resuming sampling or killing unrelated processes. No live Windows handle exists on Mac.

The compact all-success uncompressed named-array/reserve ledger is 23.95 GiB on Windows, 27.51 GiB for a Mac copy plus receiver derivatives, 51.46 GiB combined before logs/failures/buffers/history. Plan 60–75 GiB combined within the user's approximate upper budget, verify each actual volume, and avoid a third full archive/extracted copy. These are conditional storage scenarios, not capacity or runtime guarantees. Preserve old evidence separately and account its occupied space. No total experiment cutoff; preserve numerical/resource guards.

The source-bound full-frame receiver and downstream tables/Chinese LaTeX report have processed the real finite v2 return. Separate artificial full-scale fixtures from scientific evidence. Formal F3/F4 results, F5 full raw-to-final-paper reproduction and F6 final manuscript remain incomplete. Continue useful local work without pretending to have a live Windows execution handle.

## Scientific invariants

- Preserve archived 0.1.0/0.1.1 sources, all frozen protocols and historical results. Develop Windows support on a separate branch/version with a new experiment identity.
- Separate target/coordinates, transition kernel, execution strategy and resource/measurement policy. Stan/BridgeStan currently supports CPU sequential RWM/MALA only.
- Compare actual random arrays, not merely integer seeds. An independent NumPy reference must not call the implementation being tested.
- Retain rejection self-transitions, acceptance events, residuals, stopping causes, nonfinite failures, fallback cost and invalid trajectories. Invalid outputs cannot become ordinary posterior samples.
- Explicitly synchronize device work; distinguish cached execution, ordinary inference and research-audit costs. Host synchronization, transfer and compilation are not free.
- No post hoc deletion of failure, slow configurations, unfavorable models or constant estimands. Preserve reference uncertainty (including L2) and undefined diagnostics.
- A framework CUDA probe is not sampler correctness, convergence or speed evidence. No claims of general acceleration or precise time-to-accuracy from two measured budgets.

## Work and evidence

Use `execution/COMPLETION-WORK-PACKAGES.md` for current progress; `execution/windows-native/WORK-PACKAGES.md` retains the historical first Windows phase. Record commands, source commit, dependency/device versions, counts of passed/failed/skipped tests and artifact hashes. Continue independent work when one step is blocked. Do not silently overwrite a frozen run; resume only with matching identities and checksums. Numerical iteration/memory guards are required; do not impose a total experiment time cutoff.

Project numerical source lives at `r-package/inst/python/parallelbayes/`; version 0.2.0.dev1 separates optional torch/JAX imports and an independent NumPy reference. Maintain that separation. Audit tools may run on Mac without CUDA; this does not count as rerunning Windows or GPU timing. Preserve Mac tests and the package's truthful capability matrix. Tests added under `tests/handoff/` certify only portable handoff utilities.

## Repository and releases

Git tracks source, tests, protocols, summaries, manuscripts and first-party figures. Complete CPU raw evidence is in the `cpu-review-v1` Release, split into checksum-verified assets. Download/extract historical reproduction bundles into a separate directory, never over the active development checkout. Third-party paper/book PDFs, full-text extractions, private skill code, local environments, caches and credentials are not Git assets. Upstream permissively licensed source retains its license.

Commit new source/protocol changes to a development branch. Do not force-push or overwrite history. Keep large raw outputs outside Git and provide integrity manifests and replayable result archives. No automatic CRAN or journal submission.
