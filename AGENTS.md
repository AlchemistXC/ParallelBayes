# ParallelBayes project instructions

## Current work

As of 2026-10-04, the user has authorized the native Windows 11 / AMD CPU / RTX 5080 phase. Read `handoff/windows-native/README.md`, `CODEX-PROMPT.md` and `SKILLS-SETUP.md`. The user also authorized skill migration; use the separately transferred private ZIP, never publish it. Use native PowerShell and native Windows Python; do not substitute WSL2, a Linux VM or a Linux container. The historical handoff describes the 0.1.1 JAX core. The received `windows-native-dev` branch at `3a51f98` implements the optional 0.2.0.dev1 PyTorch backend and includes native Windows CPU/CUDA evidence. Consult `docs/WINDOWS-RESULTS.md` and `docs/WINDOWS-RETURN-AUDIT.md` for verified scope; do not restart completed experiments from the old handoff prompt. Older CPU documents that say GPU work is deferred describe the historical CPU milestone, not the current authorization.

Current execution entry: `docs/RESEARCH-COMPLETION-PLAN.md` and `execution/COMPLETION-WORK-PACKAGES.md` (F0–F6). The unified development entry is `codex/research-integration`. Windows follow-up starts at `handoff/windows-completion/README.md`. As of 2026-10-07, F2, the bounded v1 runtime and isolated package installation have returned and passed independent intake (`docs/WINDOWS-FOLLOWUP-INTAKE.md`); do not rerun those prompts. Formal driver development is current: `docs/FORMAL-PERSISTENCE.md` records full-count metadata checks, and `docs/FORMAL-FREEZE.md` records the implemented preparation interface with eight portable checks. Full native input sealing, v2 adapter/worker integration, execution and complete analysis remain unverified or unfinished. No new executable Windows prompt has been issued. Original F1 and migration prompts are historical; do not restart completed work. Continue independent Mac work while awaiting actual Windows receipts.

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
