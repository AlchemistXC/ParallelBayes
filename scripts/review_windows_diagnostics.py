"""Companion sensitivity analysis; never replaces frozen Windows diagnostics.

Requires NumPy, R, posterior and jsonlite. No torch, JAX or GPU is required.
Use --prepare-only, then Rscript review_windows_diagnostics.R inputs.json
binary.json, then --compare-only to separate the stages. Existing output paths
are refused except by the explicitly read-only comparison stage.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(evidence, output):
    output.mkdir(parents=True, exist_ok=False)
    items = []
    root = evidence / "execution/windows-native"
    for run, kind in [("windows-native-v1", "formal"), ("sbc-01", "sbc")]:
        states = {}
        if kind == "formal":
            for path in (root / run / "tasks").glob("*/state.json"):
                state = read(path)
                states[path.parent.name] = (state, path.parent / state["attempt"])
        for csv in sorted((root / run).rglob("diagnostic-input.csv")):
            key = csv.parent.name
            table = np.loadtxt(csv, delimiter=",", skiprows=1)
            if kind == "formal":
                state, folder = states[key[:20]]
                discard = state["task"]["discard"]
                raw_path = folder / "raw.npz"
            else:
                raw_path = csv.parent / "raw.npz"
                discard = 0 if "-nuts-" in key else 256
            with np.load(raw_path, allow_pickle=False) as raw:
                draws = raw["draws"][:, discard:]
                np.testing.assert_array_equal(
                    table[:, 2:2 + draws.shape[-1]].reshape(draws.shape), draws
                )
            binary = output / f"{kind}-{key}.bin"
            table.astype("<f8").tofile(binary)
            items.append(dict(kind=kind, key=key, csv=str(csv), binary=str(binary),
                              rows=table.shape[0], cols=table.shape[1],
                              names=csv.read_text().splitlines()[0].split(","),
                              csv_sha256=checksum(csv), binary_sha256=checksum(binary),
                              raw_sha256=checksum(raw_path)))
    if len(items) != 572:
        raise ValueError(f"Expected 512 formal and 60 SBC inputs, found {len(items)}")
    (output / "inputs.json").write_text(json.dumps(items, indent=2) + "\n")


def compare(evidence, output):
    items = read(output / "inputs.json")
    for item in items:
        for name in ["csv", "binary"]:
            if checksum(Path(item[name])) != item[name + "_sha256"]:
                raise ValueError(f"Changed diagnostic input: {item[name]}")
    binary = read(output / "binary.json")
    result = {"scope": "companion CSV/binary sensitivity analysis; original diagnostics retained",
              "comparison_tolerance": {"atol": 1e-11, "rtol": 1e-11}}
    for run, kind in [("windows-native-v1", "formal"), ("sbc-01", "sbc")]:
        original = {Path(k).name: v for k, v in read(
            evidence / "execution/windows-native" / run / "modern-diagnostics.json"
        ).items()}
        csv = {Path(k).name: v for k, v in read(output / f"{kind}.json").items()}
        mismatches = {"csv": [], "binary": []}
        counts = {}
        for route in ["csv", "binary"]:
            records = csv if route == "csv" else {
                k.split("/", 1)[1]: v for k, v in binary["diagnostics"].items()
                if k.startswith(kind + "/")
            }
            if records.keys() != original.keys():
                raise ValueError("Diagnostic fit identities differ")
            for key, expected in original.items():
                actual = records[key]
                if len(actual["summary"]) != len(expected["summary"]):
                    raise ValueError("Diagnostic variable count differs")
                for a, b in zip(expected["summary"], actual["summary"]):
                    for field in ["variable", "state"]:
                        if a[field] != b[field]:
                            raise ValueError(f"Diagnostic category changed: {key}/{field}")
                    for metric in ["rhat", "ess_bulk", "ess_tail"]:
                        x, y = a[metric], b[metric]
                        if x is None or y is None:
                            if x != y:
                                raise ValueError("Undefined diagnostic state changed")
                        elif not np.isclose(x, y, atol=1e-11, rtol=1e-11):
                            mismatches[route].append(dict(fit=key, variable=a["variable"],
                                metric=metric, windows=x, replay=y, abs_difference=abs(x-y)))
            counts[route] = dict(fits=len(records),
                constant_fits=sum(any(s["state"] == "undefined_no_variation"
                    for s in v["summary"]) for v in records.values()),
                fits_with_finite_rhat_gt_1_01=sum(any(s["rhat"] is not None and s["rhat"] > 1.01
                    for s in v["summary"]) for v in records.values()))
        inputs = [v for k, v in binary["input_comparison"].items() if k.startswith(kind + "/")]
        result[kind] = dict(counts=counts, numeric_disagreements={k: len(v) for k,v in mismatches.items()},
            binary_disagreements=mismatches["binary"],
            csv_largest_disagreements=sorted(mismatches["csv"], key=lambda x:x["abs_difference"], reverse=True)[:10],
            csv_cells_different_from_numpy=sum(v["changed_values"] for v in inputs),
            max_csv_cell_difference=max(v["max_absolute_change"] for v in inputs),
            categories_identical=True)
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rscript", default="Rscript")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare-only", action="store_true")
    modes.add_argument("--compare-only", action="store_true")
    args = parser.parse_args()
    evidence, output = args.evidence.resolve(), args.output.resolve()
    if evidence == output or evidence in output.parents or output in evidence.parents:
        parser.error("Output and original evidence must be separate directories")
    if not args.compare_only:
        prepare(evidence, output)
    if args.prepare_only:
        raise SystemExit(0)
    if not args.compare_only:
        script = Path(__file__).with_suffix(".R")
        subprocess.run([args.rscript, "--vanilla", str(script), str(output / "inputs.json"),
                        str(output / "binary.json")], check=True)
        # The archived, hash-verified script retains the original CSV reader.
        original = evidence / "execution/windows-native/frozen-source/scripts/windows/modern_diagnostics.R"
        for run, kind in [("windows-native-v1", "formal"), ("sbc-01", "sbc")]:
            subprocess.run([args.rscript, "--vanilla", str(original),
                            str(evidence / "execution/windows-native" / run),
                            str(output / f"{kind}.json")], check=True)
    compare(evidence, output)
