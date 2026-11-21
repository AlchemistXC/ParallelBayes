"""Write the 880 prespecified qualification calls without generating random arrays."""
import argparse
import hashlib
import json
from pathlib import Path


COMBINATIONS = (("cpu", "rwm"), ("cpu", "mala"), ("cuda", "rwm"), ("cuda", "mala"))
EIGHT = ("sequential", "w4", "w8", "w16", "w32", "w64", "first_use", "short_race")
THREE = ("sequential", "w32", "first_use")
FOUR = ("sequential", "w32", "w64", "first_use")


def tasks():
    tasks = []

    def add(stage, model, steps, repeats, arms):
        for replicate in range(1, repeats+1):
            for device, kernel in COMBINATIONS:
                for arm in arms:
                    task = dict(stage=stage, model=model, steps=steps, replicate=replicate,
                                device=device, kernel=kernel, arm=arm,
                                input_set="qualification", chains=4)
                    raw = json.dumps(task, sort_keys=True, separators=(",", ":")).encode()
                    task["task_id"] = hashlib.sha256(raw).hexdigest()
                    tasks.append(task)

    for d in (8, 128):
        for m in (256, 65536):
            add("gaussian_corners", f"gaussian_d{d}_m{m}", 1024, 3, EIGHT)
    for d, m in ((8, 2048), (128, 16384)):
        for steps in (256, 4096):
            add("gaussian_intermediate", f"gaussian_d{d}_m{m}", steps, 3, THREE)
    add("logistic_proxy", "logistic_proxy", 1024, 3, FOUR)
    for model in ("ode_normal", "ode_fast"):
        add("ode_1024", model, 1024, 5, FOUR)
        add("ode_4096", model, 4096, 3, THREE)
    for model in ("gaussian_d8_m256", "gaussian_d128_m65536", "ode_fast"):
        add("longest", model, 16384, 3, ("sequential", "first_use"))
    if len(tasks) != 880 or len({task["task_id"] for task in tasks}) != 880:
        raise AssertionError("qualification inventory identity/count mismatch")
    return tasks


def main(output):
    records = tasks()
    counts = {}
    for row in records:
        counts[row["stage"]] = counts.get(row["stage"], 0)+1
    expected = {"gaussian_corners":384, "gaussian_intermediate":144,
                "logistic_proxy":48, "ode_1024":160, "ode_4096":72, "longest":72}
    if counts != expected:
        raise AssertionError(f"qualification strata differ: {counts}")
    # Metadata contains no generated tapes or performance measurements.
    with output.open("x", encoding="utf-8") as file:
        json.dump({"identity":"prospective-first-use-v1", "scope":"qualification plan only",
                   "planned":len(records), "counts":counts, "tasks":records}, file, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.output)
