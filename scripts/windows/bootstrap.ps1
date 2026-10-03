param(
    [string]$TorchVersion = "2.7.1",
    [string]$CudaIndex = "https://download.pytorch.org/whl/cu128",
    [string]$VenvName = ".venv-win-torch",
    [string]$PythonExe = ""
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($env:OS -ne "Windows_NT") { throw "Run this bootstrap on native Windows, not WSL or macOS." }
if ($CudaIndex -notmatch '^https://download\.pytorch\.org/whl/cu[0-9]+/?$') { throw "Use an official stable PyTorch CUDA wheel index." }
if ($TorchVersion -notmatch '^\d+\.\d+\.\d+$') { throw "Pass an explicit stable torch version; record changes before freezing." }
if ($VenvName -notmatch '^\.venv-win-torch(?:-[a-zA-Z0-9-]+)?$') { throw "Use a project .venv-win-torch[-candidate] name." }
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Push-Location $ProjectRoot
try {
    New-Item -ItemType Directory -Force -Path "execution/windows-native" | Out-Null
    if (Test-Path (Join-Path $VenvName "PARALLELBAYES-FROZEN.json")) { throw "This environment is frozen. Create a new named candidate environment." }
    $Attempt = "execution/windows-native/bootstrap-" + (Get-Date -Format "yyyyMMddTHHmmss") + "-" + ([guid]::NewGuid().ToString("N").Substring(0,8))
    New-Item -ItemType Directory -Path $Attempt | Out-Null
    $Python = Join-Path $ProjectRoot "$VenvName/Scripts/python.exe"
    if (-not (Test-Path $Python)) {
        if ($PythonExe) { & $PythonExe -m venv $VenvName }
        else { & py -3.12 -m venv $VenvName }
        if ($LASTEXITCODE -ne 0) { throw "Python 3.12 x64 venv creation failed." }
    }
    & $Python -c "import sys,struct; assert sys.platform=='win32' and struct.calcsize('P')==8; assert sys.version_info[:2]==(3,12)"
    if ($LASTEXITCODE -ne 0) { throw "Expected native Windows Python 3.12 x64." }
    # Existing torch is never silently upgraded; bootstrap dependencies are pinned.
    & $Python -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('torch') else 1)"
    if ($LASTEXITCODE -ne 0) {
        & $Python -m pip install "torch==$TorchVersion" --index-url $CudaIndex --report "$Attempt/torch-install.json"
        if ($LASTEXITCODE -ne 0) { throw "Torch installation failed; no CPU fallback was attempted." }
    } else {
        & $Python -c "import torch,sys; print(torch.__version__);sys.exit(0 if torch.__version__.split('+')[0]==sys.argv[1] else 1)" $TorchVersion
        if ($LASTEXITCODE -ne 0) { throw "Existing torch differs. Preserve it; create a new named environment for a version change." }
    }
    & $Python -m pip install -r handoff/windows-native/requirements-bootstrap.txt --report "$Attempt/bootstrap-install.json"
    if ($LASTEXITCODE -ne 0) { throw "Bootstrap requirements failed." }
    & $Python -m pip check | Tee-Object -FilePath "$Attempt/pip-check.txt"
    if ($LASTEXITCODE -ne 0) { throw "Dependency conflict." }
    & $Python -m pip freeze | Set-Content -Encoding utf8 "$Attempt/python-observed.txt"
    & $Python scripts/windows/probe_environment.py --require-windows --require-cuda --output "$Attempt/environment.json"
    if ($LASTEXITCODE -ne 0) { throw "Device probe failed. Inspect environment.json before any sampler work." }
    & $Python -m pip freeze | Set-Content -Encoding utf8 "$Attempt/python-observed.txt"
    Write-Host "Framework probe passed. The PyTorch MCMC backend still needs implementation and validation."
} finally { Pop-Location }
