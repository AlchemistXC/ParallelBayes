"""Analytic and independent numerical checks for the Mac synthetic targets."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/prospective_reference"))

from run import diffrax, jax, jnp, np, sampler, warmup
from models import logistic_fixture, ode_fixture, scipy_trajectory, RATES
from scipy.integrate import quad
from scipy.special import expit


def logistic():
    model, q = logistic_fixture()
    q[2:34] = np.log(3)
    np.testing.assert_allclose(model.functions(q), [0., 1., 9/16], atol=1e-14, rtol=0)
    upper = q.copy()
    upper[1] = np.log(4)
    np.testing.assert_allclose((model.functions(q) + model.functions(upper))[1]/2, 2.5, atol=1e-14)
    reverse = replace(model, trials=model.trials[::-1], successes=model.successes[::-1])
    q_reversed = np.r_[q[:2], q[2:][::-1]]
    np.testing.assert_allclose(reverse.log_density(q_reversed), model.log_density(q), atol=1e-12, rtol=0)
    np.testing.assert_allclose(reverse.functions(q_reversed), model.functions(q), atol=1e-14, rtol=0)

    rng = np.random.default_rng(301)
    points = [q, np.zeros(130), np.r_[1., -3., rng.normal(size=128)],
              np.r_[-1., 2.5, rng.normal(size=128)], np.r_[0., 0., np.tile([-45., 45.], 64)]]
    points += [rng.normal(scale=.3, size=130) for _ in range(4)]
    vg = jax.jit(jax.value_and_grad(model.log_density))
    hv = jax.jit(lambda p, v: jax.jvp(jax.grad(model.log_density), (p,), (v,))[1])
    errors = []
    for point in points:
        direction = rng.normal(size=130)
        density, gradient = vg(point)
        ref_value, ref_grad, ref_hv = model.oracle(point, direction)
        errors.append([abs(float(density)-ref_value), np.max(np.abs(gradient-ref_grad)),
                       np.max(np.abs(hv(point, direction)-ref_hv))])
    maxima = np.asarray(errors).max(axis=0)
    assert np.all(maxima <= [1e-8, 1e-7, 1e-5]), maxima

    def integrand(q):
        return np.exp(-9*np.logaddexp(0., -q) - 8*np.logaddexp(0., q))

    normalization = quad(integrand, -40, 40, epsabs=1e-15)[0]
    moments = [quad(lambda z: f(z)*integrand(z), -40, 40, epsabs=1e-15)[0]/normalization
               for f in (expit, float)]
    np.testing.assert_allclose(moments, [9/17, 1/8], atol=1e-9, rtol=0)
    return {"n_points": len(points), "max_errors": maxima.tolist(), "points_errors": np.asarray(errors).tolist(),
            "beta_quadrature_means": moments, "beta_sampler": beta_sampler(moments)}


class BetaFixture:
    def log_density(self, q):
        return -9*jax.nn.softplus(-q[0]) - 8*jax.nn.softplus(q[0])

    def functions(self, q):
        return jnp.stack((jax.nn.sigmoid(q[0]), q[0]))


def beta_sampler(expected):
    model = BetaFixture()
    advance = sampler(model)
    chains = []
    divergences = 0
    for index, initial in enumerate([-1.5, -.5, .5, 1.5]):
        warm_key, key = jax.random.split(jax.random.key(27105+index), 2)
        state, params, _ = warmup(model, np.array([initial]), warm_key)
        samples = []
        for _ in range(40):
            (state, key), record = advance(state, key, params["step_size"], params["inverse_mass_matrix"])
            samples.append(np.asarray(record["functions"]))
            divergences += int(record["divergent"].sum())
        chains.append(np.concatenate(samples))
    values = np.stack(chains)
    mean = values.mean(axis=(0,1))
    batches = values.reshape(4, 40, 100, 2).mean(axis=2).reshape(-1, 2)
    batch_mcse = batches.std(axis=0, ddof=1)/np.sqrt(len(batches))
    between = values.mean(axis=1).std(axis=0, ddof=1)/2
    mcse = np.maximum(batch_mcse, between)
    assert divergences == 0
    assert np.all(np.abs(mean-expected) <= 4*mcse)
    return {"mean": mean.tolist(), "mcse": mcse.tolist(), "retained_per_chain": len(values[0]),
            "divergences": divergences}


def fd_gradient(gradient, q, direction, h):
    return (-gradient(q+2*h*direction) + 8*gradient(q+h*direction)
            - 8*gradient(q-h*direction) + gradient(q-2*h*direction))/(12*h)


def direct_hv(model, points, directions):
    # The reference NUTS trajectory uses reverse-mode checkpointing for its
    # first derivative. DirectAdjoint permits forward-over-reverse for this audit.
    solve = diffrax.diffeqsolve

    def solve_direct(*args, **kwargs):
        return solve(*args, **kwargs, adjoint=diffrax.DirectAdjoint())

    hvp = jax.jit(lambda q, v: jax.jvp(jax.grad(model.log_density), (q,), (v,))[1])
    with patch.object(diffrax, "diffeqsolve", solve_direct):
        return [[np.asarray(hvp(q, v)) for v in directions] for q in points]


def ode(fast):
    model, center = ode_fixture(fast)
    vg = jax.jit(jax.value_and_grad(model.log_density))
    trajectory = jax.jit(model.trajectory)
    rng = np.random.default_rng(27103)
    points = [center, *(center + d for d in np.eye(8)*.1), *(center - d for d in np.eye(8)*.1),
              *(center + rng.normal(scale=.06, size=8) for _ in range(4))]
    directions = np.array([[1,-1,1,-1,0,0,0,0], [0,0,0,0,1,-1,0,0], [1,1,-1,1,-1,1,1,-1]], dtype=float)
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    direct = direct_hv(model, points, directions)
    rows = []
    value0 = float(vg(center)[0])
    reference0 = model.oracle(center)[1]
    loose = dict(rtol=4e-13, atol=4e-15)
    for index, q in enumerate(points):
        expected, density_ref, gradient_ref = model.oracle(q)
        state, success = trajectory(q)
        assert bool(success)
        assert np.all(np.isfinite(state)) and np.all(np.exp(state)>0)
        value, gradient = vg(q)
        err_state = float(np.max(np.abs(state-expected)))
        err_density = abs((float(value)-value0)-(density_ref-reference0))
        grad_tol = 1e-6 + 1e-5*np.abs(gradient_ref)
        err_gradient = float(np.max(np.abs((gradient-gradient_ref)/grad_tol)))
        ref_state, ref_density, ref_gradient = model.oracle(q, **loose)
        ref_error = max(np.max(np.abs(ref_state-expected))/1e-6,
                        abs((ref_density-model.oracle(center, **loose)[1])-(density_ref-reference0))/1e-5,
                        np.max(np.abs((ref_gradient-gradient_ref)/grad_tol)))
        hv_errors = []
        for direction, hv in zip(directions, direct[index], strict=True):
            hv_ref = fd_gradient(lambda z: model.oracle(z)[2], q, direction, 1e-4)
            hv_ref_half = fd_gradient(lambda z: model.oracle(z)[2], q, direction, 5e-5)
            ref_tol = 1e-5 + 1e-4*np.abs(hv_ref)
            hv_errors.append(float(np.max(np.abs((hv-hv_ref)/ref_tol))))
            ref_error = max(ref_error, np.max(np.abs((hv_ref_half-hv_ref)/ref_tol)))
        rows.append(dict(point=index, state=err_state, offset_density=err_density, gradient_budget=err_gradient,
                         hv_budget=max(hv_errors), reference_budget=float(ref_error)))
    equilibrium = np.r_[center[:4], np.log([30.,20.]), center[6:]]
    eq_states, eq_ok = trajectory(equilibrium)
    eq_error = float(np.max(np.abs(eq_states-equilibrium[4:6])))
    base = np.log(np.r_[RATES, [24,12,.2,.2]])
    fast_center = base.copy()
    fast_center[:4] += np.log(2)
    fast_states = ode_fixture(True)[0].trajectory(fast_center)[0]
    time_scaled = scipy_trajectory(base, times=np.arange(0,41,2))[0]
    scaling_error = float(np.max(np.abs(fast_states-time_scaled)))
    assert eq_ok and eq_error < 1e-6 and scaling_error < 1e-6
    values = np.asarray(model.functions(center))
    np.testing.assert_allclose(values, [np.exp(center[0]), np.exp(model.oracle(center)[0][-1,0])], rtol=1e-6)
    failed = replace(model, max_steps=1)
    assert not bool(failed.trajectory(center)[1]) and np.isnan(failed.log_density(center))
    passed = all(r["state"] <= 1e-6 and r["offset_density"] <= 1e-5 and r["gradient_budget"] <= 1
                 and r["hv_budget"] <= 1 and r["reference_budget"] <= .1 for r in rows)
    return {"n_points": len(points), "errors": rows, "equilibrium_error": eq_error,
            "time_scaling_error": scaling_error, "passed": passed,
            "hv_method": "Diffrax DirectAdjoint forward-over-reverse against five-point independent SciPy sensitivities"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    results = {"logistic": logistic(), "ode": {label: ode(fast)
               for label, fast in [("normal", False), ("fast", True)]}}
    with args.output.open("x") as file:
        json.dump(results, file, indent=2)
    if not all(report["passed"] for report in results["ode"].values()):
        raise SystemExit("ODE validation thresholds exceeded. See full pointwise receipt.")
