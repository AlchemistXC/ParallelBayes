# Native Windows development (0.2.0.dev1)

This branch adds an optional PyTorch numerical provider. The frozen 0.1.0/0.1.1
CPU sources, protocols and original evidence are not rewritten. The Windows
study has its own identity. It is an eager research implementation, with Python
round control and measured scalar host waits, not a fused device-loop product.

## Environment and commands

The validated candidate is Python 3.12.14 x64, torch 2.13.0+cu130, RTX 5080
sm_120, driver 616.56, Windows 11 build 26200, AMD CPU (8 physical/16 logical
cores), and about 32 GB host RAM. `nvidia-smi` reports 16303 MiB device memory.
CUDA Toolkit, Rtools, WSL, containers and driver changes were not required.
Full dependency versions and install reports are in the Windows evidence directory.
The CPU's marketing name is AMD Ryzen 7 9800X3D; the observed Windows power plan
was Balanced. No physical-core affinity or exclusive desktop/GPU use is claimed.

```powershell
.\scripts\windows\bootstrap.ps1 -PythonExe <native-python-3.12.exe> -TorchVersion 2.13.0 -CudaIndex https://download.pytorch.org/whl/cu130
.\.venv-win-torch\Scripts\python.exe -m pip install -e . --no-build-isolation
.\.venv-win-torch\Scripts\python.exe -m pytest tests/windows -q
$env:PB_TORCH_DEVICE='cuda'
.\.venv-win-torch\Scripts\python.exe -m pytest tests/windows/test_torch_backend.py -q
.\.venv-win-torch\Scripts\python.exe scripts/windows/validate_backend.py --output execution/windows-native/new-validation-attempt
```

`pip install .` no longer pulls JAX automatically. Install `[jax]` in a separate
environment for the legacy provider, or first install the selected official CUDA
torch wheel for the native provider. Never modify a frozen venv: bootstrap checks
`PARALLELBAYES-FROZEN.json`. Candidate changes require a new named environment.
The bundled Python was used only as the venv base after the signed Python 3.12.10
MSI failed with 0x80070003; its attempt log is retained. The base interpreter's
path and executable hash are included in runtime identity and checked on resume.
For a fresh review environment, the derived
`environment/locks/windows-native-v1-replay-requirements.txt` omits only the
editable project Git URL and adds the official CUDA wheel index. Install those
locked dependencies in a new venv, then install the supplied project source with
`pip install --no-deps --no-build-isolation .`. The full original pip freeze stays
immutable. A different environment may replay for comparison but cannot resume
the original frozen run under its old identity.

```python
from parallelbayes import sample, make_model, capabilities
model = make_model({"kind": "gaussian", "dimension": 8}, backend="torch", device="cuda")
result = sample(model, {"device": "cuda", "kernel": "mala", "executor": "quasi_deer",
                        "draws": 128, "chains": 4, "window": 16, "audit": True})
assert result["status"] == "completed"  # Otherwise inspect failed_trajectory.
```

Explicit torch targets cover Gaussian/correlated Gaussian, logistic, lognormal,
centered/noncentered funnel, Gaussian mixture, normal-mean and the shared Gaussian
A1 spec. Binary **observations** do not imply discrete latent sampling. NumPy
targets and sequential reference import independently of torch and JAX. Validation
compares relative density, analytic gradients, directional derivatives and
constraints. The finite-difference HVP check is a numerical check, not a proof.

MALA uses `q + h*grad(logp) + sqrt(2*h)*noise`; RWM uses `q + s*noise`.
Actual noise, log uniforms and Rademacher arrays are saved. Strict `<` acceptance
and the reverse MALA density correction are retained. quasi-DEER uses a hard
forward/straight-through sigmoid derivative, clipped Rademacher diagonal JVPs,
and ordered affine scans in nonoverlapping windows. The final window is shortened
to real transitions rather than evaluating fictitious steps. Picard uses sliding
windows; multiple chains advance by their minimum confirmed prefix, a documented
torch scheduling choice. Rejections count as transitions. Array shape memory
guards are estimates rather than strict peak-memory bounds.

Failures remain outside posterior output. Explicit sequential fallback reuses the
entire original tape and records primary failed path, diagnostics and cost. Audit
failures also trigger the selected fallback policy. No new noise or selective
replacement is used. The formal protocol disables fallback.

## R and independent statistical baseline

R 4.6.1 lives at `D:\Tools\R-4.6.1`; libraries at `D:\Tools\R-library-4.6`.
Set `RETICULATE_PYTHON` before loading Python. `pb_model(..., backend="torch")`
and `pb_sample(..., device="cuda")` call a complete batch; posterior arrays retain
iteration × chain × variable order. Stan remains CPU-provided and is not translated.
R development version 0.2.0.9001 maps to Python 0.2.0.dev1.

Pyro 1.9.2 CPU NUTS is a separate baseline in `torch_backend.nuts_baseline`.
Chains run sequentially in one native process, avoiding the Windows multiprocessing
path that Pyro documents as not extensively tested. Warmup is additional and timed.
Its development hook ends the warmup timing bucket at the first retained-sample
callback, so that bucket also contains the first retained transition. Total time
is valid; this hook split must not be treated as exact warmup-versus-sampling cost.
The CPU NUTS baseline is not in the frozen paired performance experiment.
This is not a GPU NUTS implementation, not BlackJAX renamed, and not an MH
fixed-tape comparison. Only the normal/Gaussian baseline is statistically checked
in this phase; other NUTS targets require their own validation.

The small SBC uses 12 generated data sets and five workflows sharing each data
set. It compares each fitted interval, endpoints, mean and standard deviation to
the same analytic posterior. It is not 60 independent calibration replications.
`posterior` computes rank/folded Rhat, bulk/tail ESS; constant estimands remain
undefined. Short-chain ESS is never substituted for error across independent runs.

## Study and evidence

`run_study.py pilot` records the 96-task development grid. After the pilot and
source commit, `run_study.py freeze` creates `windows-native-v1`, the full pip
freeze and the venv freeze marker. The formal design contains 8 shared target
specs × 2 budgets × 4 independent tapes × 2 devices × 4 MH workflows = 512 tasks.
Each has 4 chains and window 16. It is a bounded eager implementation study.
Budgets of 128/512 transitions discard their first quarter; they do not estimate
an exact time-to-accuracy. CPU uses 8 torch intra-op threads / 1 inter-op thread;
CUDA uses the same host settings on this shared WDDM desktop.

```powershell
.\.venv-win-torch\Scripts\python.exe scripts/windows/run_study.py pilot
# Commit reviewed source before freeze; never refreeze or overwrite a protocol.
.\.venv-win-torch\Scripts\python.exe scripts/windows/run_study.py freeze
.\.venv-win-torch\Scripts\python.exe scripts/windows/run_study.py formal
.\.venv-win-torch\Scripts\python.exe scripts/windows/analyze_study.py --run execution/windows-native/windows-native-v1 --output benchmark/analysis/outputs/windows-native-v1
& D:\Tools\R-4.6.1\bin\Rscript.exe scripts/windows/modern_diagnostics.R execution/windows-native/windows-native-v1/diagnostic-inputs execution/windows-native/windows-native-v1/modern-diagnostics.json
```

Resume requires identical numerical/script source hashes, runtime identity,
dependency lock, protocol, actual input arrays and previous output checksums.
An interrupted attempt directory is retained; retry is a new attempt. Terminal
failures are not rerun automatically. All attempt costs and failed pair counts are
reported. Timing distinguishes first audited execution, direct ordinary Python
inference, warmed eager execution, transfer, constraints, independent audit,
ordinary output and evidence output. Warmed repeats are technical repetitions.
Modern R diagnostics are a separately measured additional cost. Full process
startup and installation are not per-fit inference costs.
`normal_seconds` includes construction, sampling, transformation and basic
moments but excludes serialization and modern R diagnostics. `audit_api_seconds`
adds the independent oracle inside the API, but also excludes serialization and
R diagnostics. `all_attempt_seconds` retains the whole recorded attempt including
ordinary and technical replay measurements; it is research expenditure, not the
cost of one ordinary fit. These quantities must not be given the same label.

The frozen driver checks each input tape when executing a task. The additional
read-only `scripts/verify-windows-frozen.py` also verifies all 64 input files for
terminal tasks, both dependency-lock files, the R executable, all 39 source
hashes and every audited/ordinary result checksum. Run this before a final export
or when reviewing a completed run.

Logistic formal reference precision is unresolved in this Windows phase. No
accuracy pass claim is made for L1/L2. The historical L2 reference issue remains
unchanged. Mac JAX versus Windows torch is only a full-workflow comparison; no
cross-platform difference is attributed wholly to the GPU. The selector remains
deferred. Private skill ZIPs, virtual environments and raw bulk arrays stay out of Git.

## Actual results of this delivery

All 512 formal tasks completed their numerical output checks: 256 CPU and 256
CUDA, with no fallback or terminal failure. Independent NumPy comparison found
zero acceptance-event mismatches and a maximum absolute path error of
5.2116e-10. Direct CPU/CUDA comparison of 256 matched actual-array pairs found
zero event mismatches/nonfinite values, maximum unconstrained difference
2.8422e-14 and maximum constrained difference 5.6844e-13. Ordinary and warmed
replays passed; a resume checked existing outputs without adding attempts.

The following ranges are the minimum and maximum of 16 **group median** warmed
speed ratios (sequential seconds / time-executor seconds), with four independent
tapes per group. These are not GPU-versus-CPU ratios or time-to-accuracy estimates.

| Resource | MALA / quasi-DEER | RWM / Online Picard |
|---|---:|---:|
| CPU | 0.101–0.359 | 0.774–3.560 |
| CUDA | 0.164–0.505 | 1.097–5.230 |

Every quasi-DEER group median was below one. CUDA Picard had 16/16 medians above
one and 15/16 pointwise bootstrap lower bounds above one; n=4 is small and the
intervals do not provide simultaneous coverage. **All 32 A1/RWM fits rejected
every proposal. Their fast self-transition execution is not useful posterior
exploration.** No task was tuned or removed after observing these outcomes.

Of 512 fits, 480 had at least one finite rank/folded Rhat above 1.01; 108 had
constant parameters or estimands, whose diagnostics remain undefined. The
largest finite Rhat was 4.666 and the minimum finite bulk/tail ESS were 4.085/4.205.
The 1.01 count is a descriptive review, not a new frozen pass rule. Finite-budget
function MSE and n=4 bootstrap intervals are saved for analytic targets. L1/L2
remain without a resolved finite reference. Numerical completion certifies
neither convergence nor accurate posterior inference.

Observed CUDA allocator peaks reached 97,251,328 allocated bytes and 115,343,360
reserved bytes (including already resident allocations). CPU per-fit peak RSS
was not measured; only the array-workspace estimate is available. All formal
attempts took 1790.220 recorded seconds including technical measurements; modern
R diagnostic passes added 28.470 seconds. The initial audited executions recorded
88,406 host scalar reads and 4.206 seconds in their scalar-wait timers. These
timers include pending device work and do not isolate all Python/control cost.

Validation receipts: 65 CPU tests, 63 CUDA tests (no CUDA skips), 72 model/path
cases and 8 R batches passed; separate legacy JAX regression passed 51 tests
with 7 Stan cases deselected. Handoff utilities passed 17 with 1 platform skip.
The 12-data-set SBC completed 60 fits; all five workflows and the analytic
posterior covered 9/12 generating values. The analytic coverage interval was
[0.428, 0.945]. Endpoint and moment errors are retained separately; this small
exercise is not a calibration certification.

See [the Chinese results review](WINDOWS-RESULTS.md),
[the analysis JSON](../benchmark/analysis/outputs/windows-native-v1/delivery-review.json)
and [work-package status](../execution/windows-native/WORK-PACKAGES.md).
The pilot's generic analyzer had pooled configurations sharing tapes for an
accuracy interval. That interval was withdrawn, with the original output and
its frozen hash preserved as `pilot-analysis/summary.original.json`; the
post-freeze correction is explicit and does not alter formal data or protocol.

The private transfer `downloads/parallelbayes-user-skills-2026-10-04.zip` has not
arrived, so the 30 user skills remain pending installation/discovery/runtime
review. GPU NUTS, native Stan compilation, fused CUDA control and broader model
certification are unfinished scopes. Historical CPU evidence was not downloaded
for a full historical random-tape replay; no such replay is claimed.

Export after committing source/protocol/results summaries:

```powershell
.\.venv-win-torch\Scripts\python.exe scripts/windows/export_results.py --run execution/windows-native --include benchmark/protocols/windows-native-v1.json --include environment/locks/windows-native-v1-pip-freeze.txt --include benchmark/analysis/outputs/windows-native-v1
```

## Official support checked on 2026-10-04

- [PyTorch Windows installation](https://pytorch.org/get-started/locally/) and
  [explicit Windows CUDA builds](https://pytorch.org/get-started/previous-versions/).
- [Blackwell support starting in PyTorch 2.7](https://pytorch.org/blog/pytorch-2-7/).
- [NVIDIA driver/CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html).
- [Official Windows compiler tutorial](https://docs.pytorch.org/tutorials/unstable/inductor_windows.html)
  covers CPU/XPU. It is not evidence that this native CUDA sampler can use
  torch.compile/Triton; those paths are not enabled or certified here.
- [Pyro MCMC documentation](https://docs.pyro.ai/en/stable/mcmc.html), including
  Windows multiprocessing limitations.
- [CRAN Windows R distribution](https://cran.r-project.org/bin/windows/base/).
