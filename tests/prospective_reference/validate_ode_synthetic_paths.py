"""Fixed-array ODE path check, synthetic input only; no formal sampling."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_torch"))
from ode_adapter import build
from ode_reference import states_and_sensitivities
from parallelbayes.torch_backend.sampling import sample


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k,v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def main(output, device, chains):
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable; no substitution")
    output.mkdir()
    torch.set_num_threads(1)
    center = np.log([.5,.025,.75,.025,24,12,.2,.2])
    states, _ = states_and_sensitivities(center)
    rng = np.random.default_rng(763410)
    observations = states+rng.normal(scale=.2,size=states.shape)
    # Development-only stress proposal chosen to exercise rejection under both kernels.
    noise = rng.normal(size=(chains,3,8)); noise[:,1,1] = -1000.
    tape = {"noise":noise, "log_uniform":np.full((chains,3),np.log(.5)),
            "directions":np.where(rng.integers(0,2,size=(chains,3,8)),1.,-1.)}
    with (output/"actual-inputs.npz").open("xb") as f:
        np.savez_compressed(f, center=center, observations=observations, **tape)
    model = build(observations, center, device, substeps=80)
    results, references = [], {}
    for kernel, executor, scale in (("rwm","sequential",.001), ("rwm","online_picard",.001),
                                     ("mala","sequential",1e-6), ("mala","quasi_deer",1e-6)):
        config = {"device":device,"draws":3,"chains":chains,"window":2,"max_iter":30,
                  "initial":center,"step_size":scale,"kernel":kernel,"executor":executor,
                  "audit":True,"on_failure":"error"}
        started = time.monotonic()
        try:
            result = sample(model, config, tape=tape)
        except (RuntimeError, MemoryError, FloatingPointError, ValueError) as error:
            row = {"kernel":kernel,"executor":executor,"status":"exception","passed":False,
                   "error_type":type(error).__name__,"error":str(error),
                   "elapsed_seconds":time.monotonic()-started}
            results.append(row)
            print(json.dumps(row,allow_nan=False),flush=True)
            continue
        path = result["unconstrained"] if result["status"] == "completed" else result["failed_trajectory"]
        name = f"{kernel}-{executor}.npz"
        with (output/name).open("xb") as f:
            np.savez_compressed(f,path=path,accept=result["accept"])
        path_delta, events_match = None, None
        if executor == "sequential":
            references[kernel] = result
        elif (result["status"] == "completed" and kernel in references
              and references[kernel]["status"] == "completed"):
            path_delta = float(np.max(np.abs(path-references[kernel]["unconstrained"])))
            events_match = bool(np.array_equal(result["accept"],references[kernel]["accept"]))
        passed = result["status"] == "completed" and result["audit"] is not None and result["audit"]["passed"]
        if executor != "sequential":
            passed = passed and events_match and path_delta <= 2e-8
        row = {"kernel":kernel,"executor":executor,"status":result["status"], "passed":bool(passed),
               "accept":result["accept"].tolist(), "path_delta":path_delta,"events_match":events_match,
               "audit":result["audit"],"diagnostics":result["diagnostics"],"timing":result["timing"],
               "path_file":name,"path_sha256":sha256((output/name).read_bytes()).hexdigest(),
               "tape_sha256":result["tape_sha256"]}
        results.append(row)
        print(json.dumps(clean(row),allow_nan=False),flush=True)
    report = {"scope":"synthetic three-step fixed-tape CPU/CUDA development check only",
              "device":device,"chains":chains,"torch":torch.__version__,"input_sha256":sha256((output/"actual-inputs.npz").read_bytes()).hexdigest(),
              "rows":results,"passed":all(row["passed"] for row in results)}
    with (output/"receipt.json").open("x") as f:
        json.dump(clean(report),f,indent=2,allow_nan=False); f.write("\n")
    if not report["passed"]:
        raise SystemExit("one or more ODE fixed-tape checks failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--device",choices=("cpu","cuda"),default="cpu")
    parser.add_argument("--chains",type=int,choices=(1,4),default=1)
    args = parser.parse_args()
    main(args.output,args.device,args.chains)
