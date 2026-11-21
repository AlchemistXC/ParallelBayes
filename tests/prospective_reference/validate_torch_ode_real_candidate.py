"""Numerically check fixed points of the real-data ODE candidate, without sampling."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_torch"))
sys.path.insert(0, str(Path(__file__).parent))
from ode_candidate import OdeCandidate
from validate_torch_ode_candidate import independent, fd_grad


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def validate(inputs, output, substeps):
    manifest_path = inputs / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for key, file in (("data_sha256", "data.npz"), ("initials_sha256", "initials.npz")):
        if digest(inputs / file) != manifest[key]:
            raise ValueError(f"candidate {file} hash mismatch")
    with np.load(inputs / "data.npz", allow_pickle=False) as data:
        observations = data["ode_log_observations"].copy()
    with np.load(inputs / "initials.npz", allow_pickle=False) as data:
        starts = data["ode"].copy()
    center = np.log(manifest["ode"]["center"])
    points = [center, *(center + row for row in .1*np.eye(8)),
              *(center - row for row in .1*np.eye(8)), *starts[:4]]
    directions = np.array([[1,-1,1,-1,0,0,0,0], [0,0,0,0,1,-1,0,0],
                           [1,1,-1,1,-1,1,1,-1]], dtype=float)
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    torch.set_num_threads(1)
    model = OdeCandidate(observations, center, substeps=substeps)
    ref0 = independent(center, observations, center)[1]
    tight0 = independent(center, observations, center, 4e-13, 4e-15)[1]
    value0 = float(model.log_density(torch.tensor(center, dtype=torch.float64)))
    rows = []
    for index, point in enumerate(points):
        start = time.monotonic()
        try:
            q = torch.tensor(point, dtype=torch.float64, requires_grad=True)
            states = model.trajectory(q).detach().numpy()
            value = model.log_density(q)
            gradient = torch.autograd.grad(value, q)[0].detach().numpy()
            expected, reference, refgrad = independent(point, observations, center)
            tightstate, tightvalue, tightgrad = independent(point, observations, center, 4e-13, 4e-15)
            gradtol = 1e-6+1e-5*np.abs(refgrad)
            refbudget = max(float(np.max(np.abs(tightstate-expected))/1e-6),
                            float(abs((tightvalue-tight0)-(reference-ref0))/1e-5),
                            float(np.max(np.abs((tightgrad-refgrad)/gradtol))))
            hv_errors = []
            for direction in directions:
                v = torch.tensor(direction, dtype=torch.float64)
                hv = torch.autograd.functional.hvp(model.log_density, q.detach(), v)[1].detach().numpy()
                ref_fn = lambda z: independent(z, observations, center)[2]
                refhv = fd_grad(ref_fn, point, direction, 1e-4)
                refined = fd_grad(ref_fn, point, direction, 5e-5)
                tol = 1e-5+1e-4*np.abs(refhv)
                hv_errors.append(float(np.max(np.abs((hv-refhv)/tol))))
                refbudget = max(refbudget, float(np.max(np.abs((refined-refhv)/tol))))
            row = {"index":index, "q":point.tolist(),
                   "state_error":float(np.max(np.abs(states-expected))),
                   "density_delta_error":float(abs((float(value.detach())-value0)-(reference-ref0))),
                   "gradient_budget":float(np.max(np.abs((gradient-refgrad)/gradtol))),
                   "hvp_budget":max(hv_errors), "reference_budget":refbudget}
            metrics = [row[k] for k in ("state_error","density_delta_error","gradient_budget","hvp_budget","reference_budget")]
            if not np.isfinite(metrics).all():
                raise FloatingPointError("nonfinite numerical result")
            row["passed"] = bool(row["state_error"] <= 1e-6 and row["density_delta_error"] <= 1e-5
                                 and row["gradient_budget"] <= 1 and row["hvp_budget"] <= 1
                                 and row["reference_budget"] <= .1)
        except Exception as error:
            row = {"index":index, "q":point.tolist(), "passed":False,
                   "error_type":type(error).__name__, "error":str(error)}
        row["seconds"] = time.monotonic()-start
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k != "q"}, allow_nan=False), flush=True)
    report = {"scope":"candidate fixed points only; no posterior samples or Windows qualification",
              "manifest_sha256":digest(manifest_path), "data_sha256":manifest["data_sha256"],
              "initials_sha256":manifest["initials_sha256"], "substeps_per_year":substeps,
              "directions":directions.tolist(), "rows":rows,
              "status":"passed" if len(rows)==21 and all(row["passed"] for row in rows) else "failed",
              "torch":torch.__version__}
    with output.open("x") as file:
        json.dump(report,file,indent=2,allow_nan=False)
        file.write("\n")
    if report["status"] != "passed":
        raise SystemExit("one or more fixed-point checks failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--substeps", type=int, default=80)
    args = parser.parse_args()
    validate(args.inputs,args.output,args.substeps)
