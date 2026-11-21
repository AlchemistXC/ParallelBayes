"""Independent fixed-point validation of candidate targets and ODE Hv."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"scripts/prospective_reference"))
sys.path.insert(0, str(Path(__file__).parent))
from run import jax, jnp, np
from models import Logistic, ODE
from validate_models import direct_hv, fd_gradient


def validate(inputs):
    meta = json.loads((inputs/"manifest.json").read_text())
    with np.load(inputs/"data.npz") as a, np.load(inputs/"initials.npz") as init:
        logistic = Logistic(a["trials"].copy(), a["successes"].copy())
        ode = ODE(a["ode_log_observations"].copy(), np.log(meta["ode"]["center"]), prior_scale=.5)
        start = init["ode"].copy()
    center = ode.center
    points = [center, *(center + row for row in .1*np.eye(8)),
              *(center - row for row in .1*np.eye(8)), *start[:4]]
    directions = np.array([[1,-1,1,-1,0,0,0,0], [0,0,0,0,1,-1,0,0], [1,1,-1,1,-1,1,1,-1]], float)
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    hvps = direct_hv(ode, points, directions)
    evaluate = jax.jit(jax.value_and_grad(ode.log_density))
    trajectory = jax.jit(ode.trajectory)
    reference0 = ode.oracle(center)[1]
    candidate0 = float(evaluate(center)[0])
    results = []
    for index, point in enumerate(points):
        ref_states, ref_value, ref_gradient = ode.oracle(point)
        states, success = trajectory(point)
        value, gradient = evaluate(point)
        _, tighter_value, tighter_gradient = ode.oracle(point, rtol=4e-13, atol=4e-15)
        tighter_states = ode.oracle(point, rtol=4e-13, atol=4e-15)[0]
        offset = abs(float(value)-candidate0-(ref_value-reference0))
        state_error = float(np.max(np.abs(states-ref_states)))
        grad_budget = 1e-6 + 1e-5*np.abs(ref_gradient)
        grad_ratio = float(np.max(np.abs(gradient-ref_gradient)/grad_budget))
        ref_ratio = max(float(np.max(np.abs(tighter_states-ref_states))/1e-6),
                        float(np.max(np.abs(tighter_gradient-ref_gradient)/grad_budget)),
                        abs(tighter_value-ref_value)/1e-5)
        hv_ratio = 0.
        for direction, hv in zip(directions, hvps[index], strict=True):
            oracle = lambda q: ode.oracle(q)[2]
            ref = fd_gradient(oracle, point, direction, 1e-4)
            refined = fd_gradient(oracle, point, direction, 5e-5)
            budget = 1e-5 + 1e-4*np.abs(ref)
            hv_ratio = max(hv_ratio, float(np.max(np.abs(hv-ref)/budget)))
            ref_ratio = max(ref_ratio, float(np.max(np.abs(ref-refined)/budget)))
        good = bool(success and state_error <= 1e-6 and offset <= 1e-5 and
                    grad_ratio <= 1 and hv_ratio <= 1 and ref_ratio <= .1)
        results.append(dict(index=index, passed=good, state=state_error, offset=offset,
                            gradient_budget=grad_ratio, hv_budget=hv_ratio, reference_budget=ref_ratio))
    return {"status": "passed" if all(r["passed"] for r in results) else "failed",
            "scope": "candidate fixed-point validation, independent SciPy sensitivity oracle",
            "manifest_sha256": __import__("hashlib").sha256((inputs/"manifest.json").read_bytes()).hexdigest(),
            "results":results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = validate(args.inputs)
    with args.output.open("x") as file:
        json.dump(report, file, indent=2, allow_nan=False)
    if report["status"] != "passed":
        raise SystemExit("candidate fixed-point checks failed")
