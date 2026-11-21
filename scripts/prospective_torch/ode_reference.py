"""Independent SciPy trajectory and sensitivity oracle for ODE development."""
import numpy as np
from scipy.integrate import solve_ivp


def states_and_sensitivities(q):
    q = np.asarray(q, dtype=float)
    if q.shape != (8,) or not np.isfinite(q).all():
        raise ValueError("invalid ODE coordinates")
    with np.errstate(over="raise", invalid="raise"):
        alpha, beta, gamma, delta = np.exp(q[:4])
    initial = np.zeros((2, 8))
    initial[0,4] = initial[1,5] = 1

    def rhs(_, combined):
        with np.errstate(over="raise", invalid="raise"):
            x, y = np.exp(combined[:2])
            jac = np.array([[0, -beta*y], [delta*x, 0]])
            params = np.zeros((2, 8))
            params[0,:2] = alpha, -beta*y
            params[1,2:4] = -gamma, delta*x
            return np.r_[alpha-beta*y, delta*x-gamma,
                         (jac @ combined[2:].reshape(2,8) + params).ravel()]
    result = solve_ivp(rhs, (0.,20.), np.r_[q[4:6],initial.ravel()],
                       t_eval=np.arange(21), method="DOP853", rtol=2e-13, atol=2e-15)
    if not result.success or result.y.shape != (18,21) or not np.isfinite(result.y).all():
        raise FloatingPointError(f"independent ODE solve failed: {result.message}")
    return result.y[:2].T, result.y[2:].T.reshape(21,2,8)


def density_and_gradient(q, observations, center, prior_scale):
    states, sensitivities = states_and_sensitivities(q)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        residual = observations-states
        scaled = residual**2*np.exp(-2*q[6:])
        prior = (q-center)/prior_scale
        value = -scaled.sum()/2 - 21*sum(q[6:]) - prior @ prior/2
        grad = np.einsum("ij,ijk->k", residual*np.exp(-2*q[6:]), sensitivities)
        grad[6:] += scaled.sum(axis=0)-21
        grad -= prior/prior_scale
    if not np.isfinite(value) or not np.isfinite(grad).all():
        raise FloatingPointError("independent ODE density or gradient nonfinite")
    return value, grad
