#!/usr/bin/env python3
"""Read-only reconstruction of the finite R cost companion, including failures."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_path(path, accept, reference, reference_accept, config):
    if path.shape != reference.shape or accept.shape != reference_accept.shape:
        raise ValueError("Saved state/event shape differs from independent reference")
    errors = np.max(np.abs(path - reference), axis=(1, 2))
    limits = 100 * (config["atol"] + config["rtol"] *
                    np.maximum(1., np.max(np.abs(path), axis=(1, 2))))
    mismatches = int(np.sum(accept != reference_accept))
    return dict(passed=bool(np.isfinite(path).all() and np.all(errors <= limits) and mismatches == 0),
                max_abs_error=float(np.max(errors)), limits=limits.tolist(),
                acceptance_mismatches=mismatches)


def verify(root, output, reference_file=None):
    root, output = Path(root), Path(output)
    if output.exists():
        raise FileExistsError(output)
    if sha(root / "protocol.json") != (root / "protocol.sha256").read_text().strip():
        raise ValueError("Frozen protocol changed")
    plan = read(root / "protocol.json")
    for name, expected in plan["inputs_sha256"].items():
        if sha(root / "inputs" / name) != expected:
            raise ValueError("Actual input changed")
    manifest = read(root / "inputs/input-manifest.json")
    target = read(root / "inputs/model.json")
    x, y, sd = np.asarray(target["X"]), np.asarray(target["y"]), target["prior_sd"]
    model = SimpleNamespace(
        reference=lambda q: float(np.sum(y * (x @ q) - np.exp(x @ q)) - .5 * np.sum(q*q) / sd**2),
        gradient_reference=lambda q: x.T @ (y - np.exp(x @ q)) - q / sd**2)
    ref_file = (Path(reference_file) if reference_file is not None else
                Path(plan["package_path"]) / "python/parallelbayes/reference.py")
    if sha(ref_file) != plan["installed_package_sha256"]["python/parallelbayes/reference.py"]:
        raise ValueError("Independent NumPy reference changed")
    spec = importlib.util.spec_from_file_location("frozen_reference", ref_file)
    reference_module = importlib.util.module_from_spec(spec)
    # Dataclasses consult sys.modules while loading this standalone module.
    import sys
    sys.modules[spec.name] = reference_module
    spec.loader.exec_module(reference_module)
    with np.load(root / "inputs/inputs.npz", allow_pickle=False) as saved:
        tape = {k: saved[k].copy() for k in ("noise", "directions", "log_uniform")}
        initial = saved["initial"].copy()
    tape_digest = hashlib.sha256()
    for k in sorted(tape):
        a = np.ascontiguousarray(tape[k], dtype="<f8")
        tape_digest.update(k.encode()); tape_digest.update(str(a.shape).encode()); tape_digest.update(a.tobytes())
    references = {}
    for workflow in manifest["workflows"]:
        if workflow["kernel"] in references:
            continue
        paths, events = [], []
        for chain, q0 in enumerate(initial):
            path, event = reference_module.numpy_reference(model, workflow["kernel"], q0,
                tape["noise"][chain], tape["log_uniform"][chain], workflow["step_size"])
            paths.append(path); events.append(event)
        references[workflow["kernel"]] = (np.asarray(paths), np.asarray(events))
    rows, checks, process_states, diagnostics = [], [], [], []
    for task in plan["tasks"]:
        folder = root / "attempts" / task["id"]
        state = dict(task_id=task["id"], status="not_run")
        process_states.append(state)
        if not (folder / "process.json").exists():
            state["status"] = "interrupted" if folder.exists() else "not_run"
            continue
        process = read(folder / "process.json")
        for name, digest in process["files_sha256"].items():
            if sha(folder / name) != digest:
                raise ValueError("Terminal file changed: " + str(folder / name))
        state.update(returncode=process["returncode"], status="process_failed")
        if not (folder / "R-record.json").exists():
            continue
        r = read(folder / "R-record.json")
        workflow = manifest["workflows"][task["workflow"]]
        if r["workflow"] != task["workflow"] or r["audit"] != task["audit"]:
            raise ValueError("R call identity differs")
        state["status"] = "completed" if process["returncode"] == 0 else "process_failed"
        for label, call in r["calls"].items():
            record = read(folder / (label + ".json"))
            expected_config = dict(manifest["config"], **workflow, audit=task["audit"],
                                   initial=initial.tolist(), device="cpu")
            if any(record["config"].get(k) != v for k, v in expected_config.items()):
                raise ValueError("Call configuration changed")
            row = dict(task_id=task["id"], block=task["block"], **workflow, audit=task["audit"],
                       call=label, status=record["status"], call_seconds=call["call_elapsed"],
                       load_seconds=r["load_seconds"], target_seconds=r["target_seconds"],
                       cold_R_ready_seconds=None, process_wall_seconds=process["process_wall_seconds"],
                       invoke_seconds=call["invoke"], transfer_to_R_seconds=call["transfer_to_R"],
                       posterior_conversion_seconds=call["posterior_conversion"],
                       diagnostics_seconds=call["diagnostics_seconds"], archive_seconds=call["archive_seconds"])
            markers = [m for m in process["markers"] if m["call"] == label]
            if len(markers) != 1 or markers[0]["status"] != record["status"]:
                raise ValueError("Missing or inconsistent direct ready clock")
            if label == "first":
                row["cold_R_ready_seconds"] = markers[0]["seconds_from_process_launch"]
            rows.append(row)
            if record["status"] != "completed":
                state["status"] = "call_failed"
                continue
            if record["tape_sha256"] != tape_digest.hexdigest():
                raise ValueError("Actual random tape changed")
            with np.load(folder / (label + ".npz"), allow_pickle=False) as z:
                q = z[record["unconstrained"]["array"]]
                accept = z[record["accept"]["array"]]
                draws = z[record["draws"]["array"]]
                check = check_path(q, accept, *references[workflow["kernel"]], record["config"])
                check.update(task_id=task["id"], call=label)
                if not np.array_equal(q, draws):
                    raise ValueError("Identity parameter transform changed")
                r_bytes = np.asarray(draws.transpose(1, 0, 2), dtype="<f8").tobytes(order="F")
                if (folder / (label + "-R.bin")).read_bytes() != r_bytes:
                    raise ValueError("R float64 roundtrip differs")
            if task["audit"] and record.get("audit", {}).get("passed") is not True:
                raise ValueError("Audited completed result lacks passing audit")
            checks.append(check)
            for diagnostic in call["diagnostics"]:
                diagnostics.append(dict(task_id=task["id"], call=label, **diagnostic))
    summary = dict(schema="r-frontend-timing-verification-v1", process_states=process_states,
                   rows=len(rows), numerical_checks=checks, formal_repetitions_added=0,
                   actual_input_blocks=1, independent_reference_paths=8,
                   reference_source=dict(sha256=sha(ref_file),
                       explicit_relocation=reference_file is not None),
                   missing_or_failed_processes=sum(s["status"] != "completed" for s in process_states),
                   all_numerical_checks_passed=all(c["passed"] for c in checks) and len(checks) == 64)
    output.mkdir(parents=True)
    for name, values in (("calls.csv", rows), ("diagnostics.csv", diagnostics)):
        if values:
            with (output / name).open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(values[0]))
                writer.writeheader(); writer.writerows(values)
    (output / "SUMMARY.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--reference-file", help="Relocated original NumPy reference; must match frozen installed-file SHA256")
    a = p.parse_args()
    result = verify(a.root, a.output, a.reference_file)
    print(json.dumps({k:v for k,v in result.items() if k not in ("numerical_checks", "process_states")}, indent=2))
