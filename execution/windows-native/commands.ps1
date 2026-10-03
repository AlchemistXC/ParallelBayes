# Actual commands used on 2026-10-04; audit record, not an unattended reinstall recipe.
# Native PowerShell only. .venv-win-torch becomes immutable after protocol freeze.
# Signature-verified Python312 MSI failed with 0x80070003; see python-install.log.
# Existing native bundled Python 3.12.14 used as isolated venv base.

# git switch -c windows-native-dev
# .\scripts\windows\bootstrap.ps1 -PythonExe C:\Users\chenh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -TorchVersion 2.13.0 -CudaIndex https://download.pytorch.org/whl/cu130
# .\.venv-win-torch\Scripts\python.exe -m pip install -e . --no-build-isolation --report execution/windows-native/package-install.json
# .\.venv-win-torch\Scripts\python.exe -m pip install pyro-ppl --report execution/windows-native/pyro-install.json
# .\.venv-win-torch\Scripts\python.exe scripts/windows/audit_skills.py
# .\.venv-win-torch\Scripts\python.exe -m pytest tests/windows -q --junitxml=execution/windows-native/windows-cpu-final.xml
# $env:PB_TORCH_DEVICE='cuda'
# .\.venv-win-torch\Scripts\python.exe -m pytest tests/windows/test_torch_backend.py -q --junitxml=execution/windows-native/torch-cuda-final.xml
# .\.venv-win-torch\Scripts\python.exe scripts/windows/validate_backend.py --output execution/windows-native/validation-01
# .\.venv-win-torch\Scripts\python.exe scripts/windows/run_study.py pilot
# .\.venv-win-torch\Scripts\python.exe scripts/windows/analyze_study.py --run execution/windows-native/pilot-01 --output execution/windows-native/pilot-analysis --pilot
# .\.venv-win-torch\Scripts\python.exe scripts/windows/statistical_check.py --output execution/windows-native/sbc-01
# & D:\Tools\R-4.6.1\bin\Rscript.exe scripts/windows/install_r_packages.R
# & D:\Tools\R-4.6.1\bin\R.exe CMD INSTALL --library=D:/Tools/R-library-4.6 r-package
# $env:LC_ALL='C'; $env:LANG='C'
# & D:\Tools\R-4.6.1\bin\Rscript.exe scripts/windows/validate_r.R
# & D:\Tools\R-4.6.1\bin\Rscript.exe scripts/windows/modern_diagnostics.R execution/windows-native/sbc-01 execution/windows-native/sbc-01/modern-diagnostics.json
# .\.venv-win-torch\Scripts\python.exe scripts/windows/summarize_sbc.py --run execution/windows-native/sbc-01
# .\.venv-win-jax-regression\Scripts\python.exe -m pytest tests/python tests/safety -m 'not stan' -q --junitxml=execution/windows-native/jax-regression-01.xml
# .\.venv-win-torch\Scripts\python.exe -m pytest tests/handoff -q --junitxml=execution/windows-native/handoff-final.xml
# .\.venv-win-torch\Scripts\python.exe scripts/windows/archive_draft_sources.py
# Source commit then: scripts/windows/run_study.py freeze; scripts/windows/run_study.py formal
# .\.venv-win-torch\Scripts\python.exe scripts/windows/run_study.py formal *> execution/windows-native/formal-resume.log
# .\.venv-win-torch\Scripts\python.exe scripts/windows/analyze_study.py --run execution/windows-native/windows-native-v1 --output benchmark/analysis/outputs/windows-native-v1
# & D:\Tools\R-4.6.1\bin\Rscript.exe scripts/windows/modern_diagnostics.R execution/windows-native/windows-native-v1/diagnostic-inputs execution/windows-native/windows-native-v1/modern-diagnostics.json
# .\.venv-win-torch\Scripts\python.exe scripts/repair-windows-pilot-summary.py
# .\.venv-win-torch\Scripts\python.exe scripts/summarize-windows-delivery.py
# .\.venv-win-torch\Scripts\python.exe scripts/verify-windows-frozen.py
# .\.venv-win-torch\Scripts\python.exe -m pip wheel . --no-deps --no-build-isolation --wheel-dir execution/windows-native/distribution
# Direct wheel import (including a CUDA 9-transition shortened-window audit) recorded in distribution/verification.json.
# git bundle create output/windows-return/windows-native-dev-2111a0f.bundle windows-native-dev
# git bundle verify output/windows-return/windows-native-dev-2111a0f.bundle
# .\.venv-win-torch\Scripts\python.exe scripts/windows/export_results.py --run execution/windows-native --include benchmark/protocols/windows-native-v1.json --include environment/locks/windows-native-v1-pip-freeze.txt --include environment/locks/windows-native-v1-r-packages.csv --include environment/locks/windows-native-v1-replay-requirements.txt --include benchmark/analysis/outputs/windows-native-v1 --include docs/WINDOWS-NATIVE.md --include docs/WINDOWS-RESULTS.md --include scripts/verify-windows-return.py --include scripts/verify-windows-frozen.py --include scripts/summarize-windows-delivery.py --include scripts/repair-windows-pilot-summary.py --include manuscript/software/windows-native.generated.tex --include output/windows-return/windows-native-dev-2111a0f.bundle
# .\.venv-win-torch\Scripts\python.exe scripts/verify-windows-return.py output/windows-return/windows-native-20261003T233726Z.tar --output output/windows-return/verification-initial.json
# Final status commit is bundled and exported again; exact commands in output/windows-return/final-commands.ps1.
