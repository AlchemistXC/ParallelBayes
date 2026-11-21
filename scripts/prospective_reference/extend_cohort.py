"""Extend a sealed ten-chain reference cohort to its next checkpoint."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

from formal_run import reference_scope, verify_freeze

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/analysis"))
from prospective_reference_diagnostics import read

RUNNER = Path(__file__).with_name("formal_run.py")
DIAGNOSTICS = ROOT / "scripts/analysis/prospective_reference_diagnostics.py"
PREVIOUS = {2000: 1000, 4000: 2000, 8000: 4000}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open("x") as file:
        json.dump(value, file, indent=2, allow_nan=False)
        file.write("\n")


def extend(model, inputs, seal, output, rscript, steps):
    import fcntl  # This scheduler is for the Mac reference environment.

    previous = PREVIOUS[steps]
    _, manifest = verify_freeze(seal, inputs, model)
    meta = json.loads((output / "cohort.json").read_text())
    if (meta["model"] != model or meta["chains"] != 10
            or meta["retained_per_chain"] != 1000
            or meta["seal_sha256"] != digest(seal)
            or meta["input_manifest_sha256"] != digest(inputs / "manifest.json")
            or meta["runner_sha256"] != digest(RUNNER)
            or meta["concurrency"] != (2 if model == "logistic" else 1)
            or meta["rscript"] != str(rscript.resolve())):
        raise ValueError("cohort identity differs")
    with (output / ".extension.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _extend_locked(model, inputs, seal, output, rscript, steps, previous, meta, reference_scope(manifest))


def _extend_locked(model, inputs, seal, output, rscript, steps, previous, meta, expected_scope):
    if (output / "cohort-failed.json").exists() or any(output.glob("cohort-failed-*.json")) or any(output.glob("extension-*-failed.json")):
        raise ValueError("prior failures require classification")
    previous_summary = output / ("first-checkpoint.json" if previous == 1000 else f"checkpoint-{previous}.json")
    previous_diagnostics = output / ("diagnostics" if previous == 1000 else f"diagnostics-{previous}") / "receipt.json"
    report = json.loads(previous_summary.read_text())
    if (report.get("model") != model or report.get("seal_sha256") != digest(seal)
            or report.get("all_chains_complete") is not True
            or report.get("diagnostics_sha256") != digest(previous_diagnostics)):
        raise ValueError("previous checkpoint identity or diagnostic checksum differs")
    receipt = json.loads(previous_diagnostics.read_text())
    if (receipt.get("model") != model or receipt.get("scope") != expected_scope
            or receipt.get("retained_per_chain") != previous or receipt.get("diagnostics_pass") is not True):
        raise ValueError("previous diagnostics failed or require classification")
    quantities = receipt.get("quantities", {})
    if set(quantities) != ({"mu", "tau", "probability"} if model == "logistic" else {"alpha", "hare_20"}):
        raise ValueError("previous estimands differ")
    for item in quantities.values():
        if (not isinstance(item.get("precision_pass"), bool)
                or not isinstance(item.get("mcse"), (float, int))
                or not math.isfinite(item["mcse"]) or item["mcse"] < 0):
            raise ValueError("undefined precision requires classification")
    if all(item["precision_pass"] for item in quantities.values()):
        raise ValueError("reference precision already passed")
    paths = [output / f"chain-{i:02d}.sqlite" for i in range(1, 11)]
    with np.load(inputs / "initials.npz", allow_pickle=False) as archive:
        initials = archive[model].copy()
    manifest = json.loads((inputs / "manifest.json").read_text())
    expected_shared = None
    for index, path in enumerate(paths, 1):
        initial_log = json.loads((output / f"chain-{index:02d}.json").read_text())
        if initial_log.get("exit_code") != 0:
            raise ValueError(f"chain {index} initial run failed")
        identity, _ = read(path, previous)
        if (identity.get("scope") != expected_scope or identity.get("model") != model
                or identity.get("chain") != index or identity.get("seal_sha256") != digest(seal)
                or identity.get("manifest_sha256") != digest(inputs / "manifest.json")
                or identity.get("initial_sha256") != sha256(initials[index-1].tobytes()).hexdigest()
                or identity.get("seed") != manifest["initials"]["formal_random_stream_seed"]):
            raise ValueError(f"chain {index} identity differs")
        shared = {key: value for key, value in identity.items() if key not in {"chain", "initial_sha256"}}
        if expected_shared is None:
            expected_shared = shared
        elif shared != expected_shared:
            raise ValueError("chain runtime identities differ")
        import sqlite3
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
            if db.execute("SELECT MAX(last_step) FROM blocks").fetchone()[0] != previous:
                raise ValueError(f"chain {index} not exactly at prior checkpoint")
    if any(output.glob(f"extension-{steps}-*")) or (output / f"diagnostics-{steps}").exists():
        raise ValueError("extension already attempted; classify existing evidence")
    write_new(output / f"extension-{steps}-start.json", {
        "model": model, "previous": previous, "steps": steps, "seal_sha256": digest(seal),
        "previous_diagnostics_sha256": digest(previous_diagnostics)})

    def chain_call(index):
        command = [sys.executable, "-B", str(RUNNER), model, str(inputs), str(seal),
                   str(paths[index-1]), "--chain", str(index), "--steps", str(steps)]
        proc = subprocess.run(command, capture_output=True, text=True)
        write_new(output / f"extension-{steps}-chain-{index:02d}.json", {
            "command": command, "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
        if proc.returncode:
            return index, False
        try:
            result = json.loads(proc.stdout)
            return index, result["last_step"] == steps and result["new_steps"] == steps - previous
        except (KeyError, ValueError, TypeError):
            return index, False

    completed = []
    with ThreadPoolExecutor(max_workers=meta["concurrency"]) as pool:
        pending = {pool.submit(chain_call, i): i for i in range(1, meta["concurrency"] + 1)}
        next_chain, failed = meta["concurrency"] + 1, False
        while pending:
            future = next(as_completed(pending))
            submitted_index = pending.pop(future)
            try:
                index, success = future.result()
            except Exception as error:
                completed.append({"chain": submitted_index, "exception": repr(error)})
                failed = True
            else:
                completed.append({"chain": index, "success": success})
                failed |= not success
            if not failed and next_chain <= 10:
                pending[pool.submit(chain_call, next_chain)] = next_chain
                next_chain += 1
    if failed or len(completed) != 10:
        write_new(output / f"extension-{steps}-failed.json", {"completed": completed})
        raise RuntimeError("extension incomplete; preserve and classify all chain states")
    command = [sys.executable, "-B", str(DIAGNOSTICS), str(output / f"diagnostics-{steps}"),
               *map(str, paths), "--steps", str(steps), "--rscript", str(rscript)]
    proc = subprocess.run(command, capture_output=True, text=True)
    write_new(output / f"extension-{steps}-diagnostic-process.json", {
        "command": command, "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
    if proc.returncode:
        raise RuntimeError("extension diagnostics failed; preserve evidence")
    diagnostic_path = output / f"diagnostics-{steps}" / "receipt.json"
    result = json.loads(diagnostic_path.read_text())
    summary = {"scope": "reference checkpoint", "model": model, "retained_per_chain": steps,
               "seal_sha256": digest(seal), "all_chains_complete": True,
               "diagnostics_pass": result["diagnostics_pass"], "quantities": result["quantities"],
               "diagnostics_sha256": digest(diagnostic_path)}
    write_new(output / f"checkpoint-{steps}.json", summary)
    print(json.dumps(summary, allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=("logistic", "ode"))
    parser.add_argument("inputs", type=Path)
    parser.add_argument("seal", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rscript", type=Path, required=True)
    parser.add_argument("--steps", type=int, choices=sorted(PREVIOUS), required=True)
    args = parser.parse_args()
    extend(args.model, args.inputs, args.seal, args.output, args.rscript, args.steps)
