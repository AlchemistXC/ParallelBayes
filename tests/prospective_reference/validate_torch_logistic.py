"""Compare PyTorch logistic target with an independent analytical NumPy oracle."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"scripts/prospective_reference"))
sys.path.insert(0, str(ROOT/"scripts/prospective_torch"))
from logistic import HierarchicalLogistic


def oracle(q, trials, successes, direction):
    # Independent formulas for the log density, gradient, and Hessian-vector.
    mu, log_scale = q[:2]
    z = q[2:]
    scale = np.exp(log_scale)
    logits = mu+scale*z
    probability = np.exp(-np.logaddexp(0., -logits))
    residual = successes-trials*probability
    value = np.sum(successes*logits-trials*np.logaddexp(0., logits))
    value -= (mu/2)**2/2 + log_scale**2/2 + (z@z)/2
    gradient = np.r_[residual.sum()-mu/4, residual@(scale*z)-log_scale, scale*residual-z]
    dm, dl = direction[:2]
    dz = direction[2:]
    rate = scale*dl
    dr = -trials*probability*(1-probability)*(dm+rate*z+scale*dz)
    hvp = np.r_[dr.sum()-dm/4, dr@(scale*z)+residual@(rate*z+scale*dz)-dl,
                rate*residual+scale*dr-dz]
    return value, gradient, hvp


def main(inputs, output, device):
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no substitution permitted")
    data_path = inputs/"data.npz"
    manifest_path = inputs/"manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if sha256(data_path.read_bytes()).hexdigest() != manifest["data_sha256"]:
        raise ValueError("data identity mismatch")
    with np.load(data_path, allow_pickle=False) as data:
        trials, successes = data["trials"].copy(), data["successes"].copy()
    # Qualification points use fixed synthetic vectors, never formal initials.
    rng = np.random.default_rng(2040)
    points = [np.zeros(130), np.r_[1., -3., rng.normal(size=128)],
              np.r_[-1., 2., rng.normal(size=128)],
              np.r_[0., 0., np.tile([-45., 45.],64)]]
    points += [rng.normal(scale=.3, size=130) for _ in range(5)]
    target = HierarchicalLogistic(trials, successes, device)
    rows = []
    for point in points:
        direction = rng.normal(size=130)
        q = torch.tensor(point, device=device, dtype=torch.float64)
        v = torch.tensor(direction, device=device, dtype=torch.float64)
        value = target.log_density(q)
        gradient_fn = torch.func.grad(target.log_density)
        grad, hvp = torch.func.jvp(gradient_fn, (q,), (v,))
        ref_value, ref_grad, ref_hvp = oracle(point, trials, successes, direction)
        rows.append({"density": abs(float(value)-ref_value),
                     "gradient":float(np.max(np.abs(grad.detach().cpu().numpy()-ref_grad))),
                     "hvp":float(np.max(np.abs(hvp.detach().cpu().numpy()-ref_hvp)))})
    limits = {"density":1e-8,"gradient":1e-7,"hvp":1e-5}
    passed = all(np.isfinite(list(row.values())).all() and all(row[k] <= limits[k] for k in limits)
                 for row in rows)
    report = {"scope":"candidate target static checks; no sampling", "device":device,
              "torch":torch.__version__, "input_sha256":manifest["data_sha256"],
              "source_sha256":sha256((ROOT/"scripts/prospective_torch/logistic.py").read_bytes()).hexdigest(),
              "rows":rows,"limits":limits,"passed":passed}
    with output.open("x") as file:
        json.dump(report,file,indent=2,allow_nan=False)
    if not passed:
        raise SystemExit("PyTorch candidate checks failed")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--device",choices=("cpu","cuda"),default="cpu")
    args=parser.parse_args()
    main(args.inputs,args.output,args.device)
