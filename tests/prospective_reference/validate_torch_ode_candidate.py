"""Compare experimental PyTorch ODE against independent SciPy sensitivities."""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import solve_ivp
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_torch"))
from ode_candidate import OdeCandidate


def independent(q, observations, center, rtol=2e-13, atol=2e-15):
    alpha, beta, gamma, delta = np.exp(q[:4])
    sensitivity = np.zeros((2, 8))
    sensitivity[0, 4] = sensitivity[1, 5] = 1
    def rhs(_, z):
        x, y = np.exp(z[:2])
        matrix = np.array([[0, -beta*y], [delta*x, 0]])
        derivative = np.zeros((2, 8))
        derivative[0, :2] = alpha, -beta*y
        derivative[1, 2:4] = -gamma, delta*x
        return np.r_[alpha-beta*y, delta*x-gamma,
                     (matrix @ z[2:].reshape(2, 8) + derivative).ravel()]
    result = solve_ivp(rhs, (0, 20), np.r_[q[4:6], sensitivity.ravel()], method="DOP853",
                       t_eval=np.arange(21), rtol=rtol, atol=atol)
    if not result.success or not np.isfinite(result.y).all():
        raise FloatingPointError("independent ODE solve failed")
    states = result.y[:2].T
    sens = result.y[2:].T.reshape(21, 2, 8)
    residual = observations-states
    scaled = residual**2*np.exp(-2*q[6:])
    prior = (q-center)/.5
    density = -scaled.sum()/2 - 21*sum(q[6:]) - prior @ prior/2
    grad = np.einsum("ij,ijk->k", residual*np.exp(-2*q[6:]), sens)
    grad[6:] += scaled.sum(axis=0)-21
    grad -= prior/.5
    return states, density, grad


def fd_grad(fn, q, direction, step):
    return (-fn(q+2*step*direction)+8*fn(q+step*direction)
            -8*fn(q-step*direction)+fn(q-2*step*direction))/(12*step)


def main(output, fast, substeps, npoints):
    torch.set_num_threads(1)
    rng = np.random.default_rng(27103)
    center = np.log(np.r_[np.array([.5,.025,.75,.025])*(2 if fast else 1), [24,12,.2,.2]])
    clean, _, _ = independent(center, np.zeros((21, 2)), center)
    observations = clean + np.random.default_rng(27102).normal(scale=.2, size=(21,2))
    model = OdeCandidate(observations, center, substeps=substeps)
    points = [center, *(center+d for d in np.eye(8)*.1), *(center-d for d in np.eye(8)*.1),
              *(center+rng.normal(scale=.06,size=8) for _ in range(4))][:npoints]
    directions = np.array([[1,-1,1,-1,0,0,0,0], [0,0,0,0,1,-1,0,0],
                           [1,1,-1,1,-1,1,1,-1]], dtype=float)
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    ref0 = independent(center, observations, center)[1]
    q0 = torch.tensor(center, dtype=torch.float64)
    value0 = float(model.log_density(q0))
    rows = []
    for index, point in enumerate(points):
        start = time.monotonic()
        q = torch.tensor(point, dtype=torch.float64, requires_grad=True)
        states = model.trajectory(q).detach().numpy()
        value = model.log_density(q)
        gradient = torch.autograd.grad(value, q)[0].detach().numpy()
        expected, reference, refgrad = independent(point, observations, center)
        tightstate, tightvalue, tightgrad = independent(point, observations, center, 4e-13, 4e-15)
        gradtol = 1e-6+1e-5*np.abs(refgrad)
        refbudget = max(np.max(np.abs(tightstate-expected))/1e-6,
                        abs((tightvalue-independent(center,observations,center,4e-13,4e-15)[1])-(reference-ref0))/1e-5,
                        np.max(np.abs((tightgrad-refgrad)/gradtol)))
        hv_errors = []
        for direction in directions:
            v = torch.tensor(direction, dtype=torch.float64)
            hv = torch.autograd.functional.hvp(model.log_density, q.detach(), v)[1].detach().numpy()
            ref_fn = lambda z: independent(z,observations,center)[2]
            reference_hv = fd_grad(ref_fn, point, direction, 1e-4)
            half = fd_grad(ref_fn, point, direction, 5e-5)
            tol = 1e-5+1e-4*np.abs(reference_hv)
            hv_errors.append(float(np.max(np.abs((hv-reference_hv)/tol))))
            refbudget = max(refbudget, float(np.max(np.abs((half-reference_hv)/tol))))
        row = {"point":index, "q":point.tolist(), "state_error":float(np.max(np.abs(states-expected))),
               "density_delta_error":float(abs((float(value.detach())-value0)-(reference-ref0))),
               "gradient_budget":float(np.max(np.abs((gradient-refgrad)/gradtol))),
               "hvp_budget":max(hv_errors),"reference_budget":float(refbudget),
               "seconds":time.monotonic()-start}
        row["passed"] = bool(row["state_error"] <= 1e-6 and row["density_delta_error"] <= 1e-5
                         and row["gradient_budget"] <= 1 and row["hvp_budget"] <= 1
                         and row["reference_budget"] <= .1)
        rows.append(row)
        print(json.dumps(row), flush=True)
    result = {"scope":"synthetic CPU development only; not formal qualification", "fast":fast,
              "substeps_per_year":substeps, "points":rows, "passed":all(x["passed"] for x in rows),
              "full_21_points":len(rows)==21, "torch":torch.__version__,
              "center":center.tolist(), "observations":observations.tolist(), "directions":directions.tolist()}
    with output.open("x") as file:
        json.dump(result,file,indent=2,allow_nan=False)
        file.write("\n")
    if not result["passed"]:
        raise SystemExit("one or more numerical thresholds failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--substeps", type=int, default=80)
    parser.add_argument("--points", type=int, default=21, choices=range(1,22))
    args = parser.parse_args()
    main(args.output,args.fast,args.substeps,args.points)
