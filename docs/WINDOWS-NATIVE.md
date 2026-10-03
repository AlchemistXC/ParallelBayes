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

Logistic formal reference precision is unresolved in this Windows phase. No
accuracy pass claim is made for L1/L2. The historical L2 reference issue remains
unchanged. Mac JAX versus Windows torch is only a full-workflow comparison; no
cross-platform difference is attributed wholly to the GPU. The selector remains
deferred. Private skill ZIPs, virtual environments and raw bulk arrays stay out of Git.

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
