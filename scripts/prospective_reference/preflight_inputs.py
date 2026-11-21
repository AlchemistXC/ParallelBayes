"""Numerical checks of candidate model identity and stratified chain starts."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

os.environ["JAX_PLATFORMS"] = "cpu"
os.environ["JAX_ENABLE_X64"] = "true"

import jax
import numpy as np

from models import Logistic, ODE


def hash_file(path):
    return sha256(path.read_bytes()).hexdigest()


def main(root, result):
    meta = json.loads((root / "manifest.json").read_text())
    for name, key in [("data.npz", "data_sha256"), ("initials.npz", "initials_sha256")]:
        if hash_file(root / name) != meta[key]:
            raise ValueError(f"hash mismatch: {name}")
    with np.load(root / "data.npz", allow_pickle=False) as inputs:
        logistic = Logistic(inputs["trials"], inputs["successes"])
        ode = ODE(inputs["ode_log_observations"],
                  np.log(meta["ode"]["center"]), prior_scale=.5)
    with np.load(root / "initials.npz", allow_pickle=False) as positions:
        starts = {name: positions[name].copy() for name in positions.files}
    checks = {}
    for name, model, shape in [("logistic", logistic, (10,130)), ("ode", ode, (10,8))]:
        if starts[name].shape != shape:
            raise ValueError(f"invalid starting positions: {name}")
        jax_eval = jax.jit(jax.value_and_grad(model.log_density))
        center = np.zeros(130) if name == "logistic" else ode.center
        def oracle(q):
            if name == "logistic":
                value, grad, _ = model.oracle(q, np.ones_like(q))
                return value, grad
            _, value, grad = model.oracle(q)
            return value, grad
        base_value, base_grad = oracle(center)
        base_jax, base_jax_grad = jax_eval(center)
        rows = []
        for i, point in enumerate(starts[name], start=1):
            value, gradient = jax_eval(point)
            reference, ref_gradient = oracle(point)
            delta = abs(float(value-base_jax) - (reference-base_value))
            abs_gradient = np.abs(gradient-ref_gradient)
            limit = np.full_like(ref_gradient, 1e-7) if name == "logistic" else 1e-6 + 1e-5*np.abs(ref_gradient)
            rows.append({"chain": i, "finite": bool(np.isfinite(value) and np.isfinite(gradient).all()),
                         "density_delta_error": delta,
                         "gradient_max_ratio": float(np.max(abs_gradient/limit))})
        bound = 1e-8 if name == "logistic" else 1e-5
        checks[name] = {"rows": rows, "passed": all(r["finite"] and r["density_delta_error"] <= bound
                                                    and r["gradient_max_ratio"] <= 1 for r in rows)}
    report = {"scope":"candidate-only preflight", "inputs_manifest_sha256":hash_file(root/"manifest.json"),
              "data_sha256":hash_file(root/"data.npz"), "initials_sha256":hash_file(root/"initials.npz"),
              "checks":checks, "formal_sampling_started":False}
    with result.open("x") as file:
        json.dump(report, file, indent=2, allow_nan=False)
    if not all(c["passed"] for c in checks.values()):
        raise SystemExit("candidate preflight did not pass")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.inputs, args.output)
