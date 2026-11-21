"""Integration check for the synthetic, four-process NUTS smoke only."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("pyro")

ROOT = Path(__file__).resolve().parents[2]


def test_four_spawned_chains_preserve_evidence(tmp_path):
    out = tmp_path / "smoke"
    result = subprocess.run(
        [sys.executable, "-B", str(ROOT / "scripts/prospective_torch/nuts_smoke.py"), str(out)],
        cwd=ROOT, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads((out / "summary.json").read_text())
    assert summary["status"] == "completed"
    assert summary["inputs_sha256"] == hashlib.sha256((out / "inputs.npz").read_bytes()).hexdigest()
    assert [row["chain"] for row in summary["results"]] == list(range(4))
    assert len({row["pid"] for row in summary["results"]}) == 4
    assert len({row["initial_rng_sha256"] for row in summary["results"]}) == 4
    for row in summary["results"]:
        chain = out / f"chain-{row['chain']}"
        assert row["status"] == "completed" and row["potential_calls"] > 0
        assert not row["legacy_mcmc_diagnostics_called"]
        assert set(row["kernel_diagnostics"]) >= {"divergences", "acceptance rate"}
        assert row["draws_sha256"] == hashlib.sha256((chain / "draws.npy").read_bytes()).hexdigest()
        assert np.isfinite(np.load(chain / "draws.npy", allow_pickle=False)).all()
        assert (chain / "rng.json").is_file() and (chain / "rng.npz").is_file()
