"""Exercise the formal ODE runner using synthetic data and mock receipts only."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_reference"))
sys.path.insert(0, str(Path(__file__).parent))
from create_freeze import create
from models import ode_fixture
from restart import blocks, same


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open("x") as target:
        json.dump(value, target, indent=2, allow_nan=False)
        target.write("\n")


def main(output):
    output.mkdir()
    inputs = output / "SYNTHETIC-inputs"
    inputs.mkdir()
    model, initial = ode_fixture(False)
    np.savez(inputs / "data.npz", ode_log_observations=model.observations)
    np.savez(inputs / "initials.npz", ode=np.tile(initial, (10, 1)))
    manifest = {"scope": "SYNTHETIC TEST ONLY", "data_sha256": digest(inputs / "data.npz"),
                "initials_sha256": digest(inputs / "initials.npz"),
                "initials": {"formal_random_stream_seed": 8819}, "ode": {"center": np.exp(model.center).tolist()}}
    write_json(inputs / "manifest.json", manifest)
    manifest_hash = digest(inputs / "manifest.json")
    write_json(inputs / "preflight.json", {"inputs_manifest_sha256": manifest_hash,
               "data_sha256": manifest["data_sha256"], "initials_sha256": manifest["initials_sha256"],
               "checks": {"ode": {"passed": True}}})
    write_json(inputs / "ode-points.json", {"status": "passed", "manifest_sha256": manifest_hash,
               "scope": "SYNTHETIC MOCK; not numerical validation"})
    mock_windows, mock_capacity, mock_restart = [output / f"MOCK-{name}.json" for name in ("windows", "capacity", "restart")]
    write_json(mock_windows, {"identity": "prospective-first-use-v1", "status": "passed", "planned": 880,
                             "accounted": 880, "scope": "MOCK TEST ONLY"})
    write_json(mock_capacity, {"identity": "prospective-first-use-v1", "status": "passed",
        "scope": "MOCK TEST ONLY", "resources": {k: {"available": 10, "conservative": 1} for k in
        ("windows_hours", "windows_disk", "mac_disk", "archive")}})
    write_json(mock_restart, {"scope": "MOCK TEST ONLY", "model": "ode-fast", "steps": 2000,
        "position_and_diagnostics_byte_identical": True, "rollback_at_200": True,
        "wrong_chain_rejected": True, "idempotency": True})
    seal_dir = output / "MOCK-seal"
    create(seal_dir, inputs, "ode", mock_windows, mock_capacity, mock_restart)
    seal = seal_dir / "seal.json"
    runner = ROOT / "scripts/prospective_reference/formal_run.py"
    calls = []

    def run(name, database, steps, chain=1, expected=0):
        command = [sys.executable, "-B", str(runner), "ode", str(inputs), str(seal),
                   str(database), "--chain", str(chain), "--steps", str(steps)]
        started = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True)
        record = {"command": command, "exit_code": result.returncode, "stdout": result.stdout,
                  "stderr": result.stderr, "elapsed_seconds": time.monotonic() - started}
        write_json(output / f"{name}.json", record)
        calls.append(name)
        if result.returncode != expected:
            raise RuntimeError(f"{name}: expected exit {expected}, got {result.returncode}")
        return json.loads(result.stdout) if expected == 0 else result.stderr

    split, continuous = output / "split.sqlite", output / "continuous.sqlite"
    assert run("split-1000", split, 1000)["new_steps"] == 1000
    before = blocks(split)
    assert "identity mismatch" in run("wrong-chain", split, 1000, chain=2, expected=1)
    same(before, blocks(split))
    assert run("split-2000", split, 2000)["new_steps"] == 1000
    assert run("split-repeat", split, 2000)["new_steps"] == 0
    assert run("continuous-2000", continuous, 2000)["new_steps"] == 2000
    a, b = blocks(split), blocks(continuous)
    same(a, b)
    assert [(last, first) for last, first, _ in a] == [(0, 0)] + [(n, n-99) for n in range(100, 2001, 100)]
    write_json(output / "receipt.json", {"scope": "SYNTHETIC TEST ONLY; mock qualification and capacity",
        "model": "ode synthetic normal", "steps": 2000, "field_bytes_identical": True,
        "wrong_chain_rejected": True, "idempotent": True, "process_logs": calls,
        "database_sha256": {p.name: digest(p) for p in (split, continuous)},
        "retained_divergences": sum(int(r["divergent"].sum()) for _, first, r in a if first > 0),
        "retained_max_depth_hits": sum(int((r["expansions"] == 8).sum()) for _, first, r in a if first > 0)})
    print("synthetic ODE formal-runner restart: passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output.resolve())
