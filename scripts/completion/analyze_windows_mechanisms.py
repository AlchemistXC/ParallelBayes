"""Post hoc descriptive cost accounting from immutable Windows-v1 outputs.

No sampling, configuration selection, causal regression or runtime modification.
Counts are forward transition maps / JVPs, not density calls or FLOPs.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def summarize(evidence, output):
    if output.exists():
        raise FileExistsError("Choose a fresh analysis output directory")
    if evidence == output or evidence in output.parents:
        raise ValueError("Output must be outside the original evidence")
    root = evidence / "execution/windows-native/windows-native-v1"
    protocol = read(root / "protocol.json")
    unsigned = dict(protocol)
    expected = unsigned.pop("protocol_sha256")
    if identity(unsigned) != expected:
        raise ValueError("Protocol identity mismatch")
    rows = []
    for task in protocol["tasks"]:
        tid = identity(task)
        folder = root / "tasks" / tid[:20]
        state = read(folder / "state.json")
        if state["task"] != task or state["protocol_sha256"] != expected:
            raise ValueError("Task identity mismatch")
        folder = folder / state["attempt"]
        for name in ["result.json", "raw.npz"]:
            if sha(folder / name) != state["checksums"][name]:
                raise ValueError("Changed result or sample file")
        result = read(folder / "result.json")
        config = task["config"]
        d = result["diagnostics"]
        transitions = config["chains"] * config["draws"]
        if state["status"] != "completed" or d["confirmed"] != transitions:
            raise ValueError("This descriptive analysis expects the archived 512 completed tasks")
        rounds = d["rounds"]
        if config["executor"] == "quasi_deer":
            widths = [min(config["window"], config["draws"] - r["offset"]) for r in rounds]
            expected_maps = 2 * config["chains"] * sum(widths)
            expected_jvps = config["chains"] * sum(widths)
            iterations = defaultdict(int)
            for r in rounds:
                iterations[r["offset"]] += 1
            mean_rounds_per_window = float(np.mean(list(iterations.values())))
            mean_prefix = None
        elif config["executor"] == "online_picard":
            widths = [min(config["window"], config["draws"] - r["offset"]) for r in rounds]
            expected_maps = 2 * config["chains"] * sum(widths)
            expected_jvps = 0
            prefixes = [r["confirmed_prefix"] for r in rounds]
            if sum(prefixes) != config["draws"]:
                raise ValueError("Prefix accounting mismatch")
            mean_prefix = float(np.mean(prefixes))
            mean_rounds_per_window = None
        else:
            widths = []
            expected_maps = transitions
            expected_jvps = 0
            mean_prefix = mean_rounds_per_window = None
        if d["forward_evals"] != expected_maps or d["jvp_evals"] != expected_jvps:
            raise ValueError("Map/JVP count disagrees with the saved round trace")
        for replay in result["warmed_eager_replays"]:
            for key in ["iterations", "forward_evals", "jvp_evals", "confirmed"]:
                if replay["diagnostics"][key] != d[key]:
                    raise ValueError("Technical replay work count differs")
        with np.load(folder / "raw.npz", allow_pickle=False) as raw:
            accepted = int(raw["accept"].sum())
        timing = result["timing"]
        row = dict(task_id=tid, model=task["model"], replicate=task["replicate"],
            device=config["device"], kernel=config["kernel"], executor=config["executor"],
            draws=config["draws"], chains=config["chains"], window=config["window"],
            transitions=transitions, accepted=accepted, acceptance_fraction=accepted/transitions,
            forward_maps=d["forward_evals"], jvps=d["jvp_evals"],
            maps_per_transition=d["forward_evals"]/transitions,
            jvps_per_transition=d["jvp_evals"]/transitions,
            rounds=d["iterations"], mean_rounds_per_window=mean_rounds_per_window,
            mean_confirmed_prefix=mean_prefix,
            mean_evaluated_width=float(np.mean(widths)) if widths else None,
            clip_fraction=(d["clips"]/(d["jvp_evals"]*protocol["models"][task["model"]]["dimension"])) if d["jvp_evals"] else None,
            warmed_seconds=float(np.median([r["timing"]["sample"] for r in result["warmed_eager_replays"]])),
            first_sample_seconds=timing["sample"],
            first_scalar_wait_seconds=d["host_scalar_wait_seconds"],
            first_scalar_wait_fraction=d["host_scalar_wait_seconds"]/timing["sample"],
            first_scalar_reads=d["host_scalar_reads"],
            normal_seconds=result["normal"]["wall_seconds"],
            audit_api_seconds=timing["total"], audit_seconds=timing["audit"],
            model_seconds=result["model_seconds"], transfer_seconds=timing["transfer"])
        row["warmed_seconds_per_transition"] = row["warmed_seconds"]/transitions
        rows.append(row)
    index = {(r["model"], r["replicate"], r["draws"], r["device"], r["kernel"], r["executor"]): r for r in rows}
    groups = defaultdict(list)
    for row in rows:
        seq = index[(row["model"], row["replicate"], row["draws"], row["device"], row["kernel"], "sequential")]
        row["paired_warmed_speed_ratio"] = seq["warmed_seconds"]/row["warmed_seconds"]
        key = (row["device"], row["kernel"], row["executor"], row["model"], row["draws"])
        groups[key].append(row)
    metrics = ["paired_warmed_speed_ratio", "maps_per_transition", "jvps_per_transition", "mean_rounds_per_window",
               "mean_confirmed_prefix", "clip_fraction", "acceptance_fraction", "warmed_seconds_per_transition",
               "first_scalar_wait_fraction", "audit_seconds", "normal_seconds", "audit_api_seconds"]
    grouped = []
    for key, values in sorted(groups.items()):
        if len(values) != 4:
            raise ValueError("Expected four independent arrays per formal cell")
        item = dict(zip(["device", "kernel", "executor", "model", "draws"], key))
        item["independent_arrays"] = 4
        item["zero_acceptance_fits"] = sum(r["accepted"] == 0 for r in values)
        for metric in metrics:
            x = [r[metric] for r in values if r[metric] is not None]
            item[metric] = None if not x else dict(median=float(np.median(x)), minimum=min(x), maximum=max(x))
        grouped.append(item)
    ranges = {}
    for device in ["cpu", "cuda"]:
        for executor in ["quasi_deer", "online_picard"]:
            cells = [g for g in grouped if g["device"] == device and g["executor"] == executor]
            ranges[device + "/" + executor] = {}
            for metric in metrics:
                x = [g[metric]["median"] for g in cells if g[metric] is not None]
                if x:
                    ranges[device + "/" + executor][metric] = [min(x), max(x)]
    output.mkdir(parents=True)
    with (output / "task-costs.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report = dict(scope="post hoc descriptive accounting, not causal attribution or new timing", protocol_sha256=expected,
        tasks=len(rows), map_and_prefix_trace_checks=len(rows), groups=grouped, group_median_ranges=ranges,
        limitations=["Map/JVP counts are not density/gradient calls or FLOPs.",
            "Scalar wait includes pending device work; it is not isolated Python overhead.",
            "First audited timing and warmed timing are different observations, not additive buckets.",
            "Pilot configurations share arrays and do not add formal independent replications."],
        source_script_sha256=sha(Path(__file__)))
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(tasks=len(rows), trace_checks=len(rows), ranges=ranges), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summarize(args.evidence.resolve(), args.output.resolve())
