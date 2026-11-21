"""Exercise the actual eager sampler with a new target and common random arrays."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"scripts/prospective_torch"))
from logistic_adapter import build
from parallelbayes.torch_backend.sampling import random_tape, sample, settings


def main(inputs, output, device):
    manifest = json.loads((inputs/"manifest.json").read_text())
    data = inputs/"data.npz"
    if sha256(data.read_bytes()).hexdigest() != manifest["data_sha256"]:
        raise ValueError("data hash mismatch")
    with np.load(data, allow_pickle=False) as archive:
        model = build(archive["trials"], archive["successes"], device)
    common = {"device":device, "draws":23, "chains":4, "window":8, "step_size":.0001,
              "max_iter":500, "audit":True, "on_failure":"error"}
    tape = random_tape(settings(common),130)
    tape_path = output.with_suffix(".tape.npz")
    with tape_path.open("xb") as file:
        np.savez_compressed(file, **tape)
    rows = []
    previous = {}
    for kernel, executor in [("rwm","sequential"), ("rwm","online_picard"),
                             ("mala","sequential"), ("mala","quasi_deer")]:
        result = sample(model, {**common,"kernel":kernel,"executor":executor}, tape=tape)
        passed = result["status"] == "completed" and result["audit"]["passed"]
        path_delta = None
        if executor == "sequential":
            previous[kernel] = result
        elif result["status"] == "completed" and previous[kernel]["status"] == "completed":
            path_delta = float(np.max(np.abs(result["unconstrained"]-previous[kernel]["unconstrained"])))
            passed &= np.array_equal(result["accept"], previous[kernel]["accept"]) and path_delta <= 2e-8
        else:
            passed = False
        rows.append({"kernel":kernel,"executor":executor,"status":result["status"],
                     "audit":result["audit"],"path_delta":path_delta,"passed":bool(passed),
                     "tape_sha256":result["tape_sha256"],"diagnostics":result["diagnostics"]})
    with output.open("x") as file:
        json.dump({"device":device,"target_id":model.target_id,"rows":rows,
                   "actual_tape":tape_path.name,
                   "actual_tape_sha256":sha256(tape_path.read_bytes()).hexdigest()},
                  file,indent=2,default=str)
    if not all(row["passed"] for row in rows):
        raise SystemExit("fixed-tape sampler comparison failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--device",choices=("cpu","cuda"),default="cpu")
    args = parser.parse_args()
    main(args.inputs,args.output,args.device)
