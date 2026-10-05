"""Run against an installed wheel in a torch-only, non-editable environment.

The child uses -I so the checkout and PYTHONPATH cannot satisfy its imports.
"""
import importlib.util
import json
import subprocess
import sys
import pytest


def test_help_does_not_require_an_unselected_numerical_provider(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", "-m", "parallelbayes.cli", "--help"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "environment" in result.stdout


def test_torch_environment_is_recorded_without_jax(tmp_path):
    if importlib.util.find_spec("torch") is None or importlib.util.find_spec("jax") is not None:
        pytest.skip("requires the documented torch-only release environment")
    output = tmp_path / "nested" / "environment.json"
    result = subprocess.run(
        [sys.executable, "-I", "-m", "parallelbayes.cli", "environment",
         "--backend", "torch", "--output", str(output)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(output.read_text())
    assert record["provider"] == "native_torch"
    assert record["dtype"] == "float64"
    assert record["python_executable"] == sys.executable


def test_missing_selected_provider_has_actionable_error_and_no_record(tmp_path):
    if importlib.util.find_spec("jax") is not None:
        pytest.skip("requires the documented torch-only release environment")
    output = tmp_path / "environment.json"
    result = subprocess.run(
        [sys.executable, "-I", "-m", "parallelbayes.cli", "environment", "--output", str(output)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "optional 'jax' provider" in result.stderr
    assert "--backend torch" in result.stderr
    assert "Traceback" not in result.stderr
    assert not output.exists()
