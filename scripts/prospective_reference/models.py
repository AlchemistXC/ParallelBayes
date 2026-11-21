"""Synthetic Mac qualification targets and independent CPU oracles."""
from dataclasses import dataclass

import diffrax
import jax
import jax.numpy as jnp
import numpy as np
from scipy.integrate import solve_ivp
from scipy.special import expit


@dataclass
class Logistic:
    trials: np.ndarray
    successes: np.ndarray

    def log_density(self, q):
        mu, log_scale = q[:2]
        local = q[2:]
        logits = mu + jnp.exp(log_scale) * local
        loglik = self.successes * -jax.nn.softplus(-logits)
        loglik -= (self.trials - self.successes) * jax.nn.softplus(logits)
        return jnp.sum(loglik) - (mu / 2)**2 / 2 - log_scale**2 / 2 - jnp.dot(local, local) / 2

    def functions(self, q):
        mu, log_scale = q[:2]
        scale = jnp.exp(log_scale)
        return jnp.stack((mu, scale, jnp.mean(jax.nn.sigmoid(mu + scale * q[2:]))))

    def oracle(self, q, direction):
        mu, log_scale = q[:2]
        scale = np.exp(log_scale)
        local = q[2:]
        logits = mu + scale * local
        p = expit(logits)
        residual = self.successes - self.trials * p
        loglik = np.dot(self.successes, logits) - np.dot(self.trials, np.logaddexp(0, logits))
        prior = -(mu**2 / 4 + log_scale**2 + local @ local) / 2
        grad = np.r_[residual.sum() - mu / 4, residual @ (scale * local) - log_scale,
                     scale * residual - local]
        dm, dl = direction[:2]
        dz = direction[2:]
        ds = scale * dl
        dr = -self.trials * p * (1-p) * (dm + ds * local + scale * dz)
        hv = np.r_[dr.sum() - dm / 4,
                   dr @ (scale * local) + residual @ (ds * local + scale * dz) - dl,
                   ds * residual + scale * dr - dz]
        return loglik + prior, grad, hv


def logistic_fixture():
    rng = np.random.default_rng(27101)
    trials = rng.integers(5, 25, size=128)
    successes = rng.binomial(trials, expit(-0.2 + 0.9 * rng.normal(size=128)))
    return Logistic(trials, successes), np.zeros(130)


TIMES = np.arange(21, dtype=float)
RATES = np.array([0.50, 0.025, 0.75, 0.025])


def scipy_trajectory(q, *, times=TIMES, rtol=2e-13, atol=2e-15):
    """Integrate log states and analytic forward sensitivities on an independent path."""
    alpha, beta, gamma, delta = np.exp(q[:4])
    initial = np.zeros((2, 8))
    initial[0, 4] = initial[1, 5] = 1

    def dynamics(_, combined):
        x, y = np.exp(combined[:2])
        derivative = np.array([alpha-beta*y, delta*x-gamma])
        state_jac = np.array([[0, -beta*y], [delta*x, 0]])
        parameter_jac = np.zeros((2, 8))
        parameter_jac[0, :2] = alpha, -beta*y
        parameter_jac[1, 2:4] = -gamma, delta*x
        sensitivity = combined[2:].reshape(2, 8)
        return np.r_[derivative, (state_jac @ sensitivity + parameter_jac).ravel()]

    result = solve_ivp(dynamics, (0., times[-1]), np.r_[q[4:6], initial.ravel()],
                       t_eval=times, method="DOP853", rtol=rtol, atol=atol)
    if not result.success or result.y.shape != (18, len(times)) or not np.isfinite(result.y).all():
        raise FloatingPointError(f"SciPy reference failed: {result.message}")
    return result.y[:2].T, result.y[2:].T.reshape(-1, 2, 8)


@dataclass
class ODE:
    observations: np.ndarray
    center: np.ndarray
    prior_scale: float = 0.30
    rtol: float = 2e-12
    atol: float = 2e-14
    max_steps: int = 2048

    def trajectory(self, q):
        def dynamics(_, log_population, params):
            alpha, beta, gamma, delta = params
            x, y = jnp.exp(log_population)
            return jnp.stack((alpha - beta*y, delta*x - gamma))

        solution = diffrax.diffeqsolve(
            diffrax.ODETerm(dynamics), diffrax.Dopri8(), t0=0., t1=20., dt0=0.02,
            y0=q[4:6], args=jnp.exp(q[:4]), saveat=diffrax.SaveAt(ts=TIMES),
            stepsize_controller=diffrax.PIDController(rtol=self.rtol, atol=self.atol),
            max_steps=self.max_steps, throw=False,
        )
        return solution.ys, solution.result == diffrax.RESULTS.successful

    def log_density(self, q):
        log_population, success = self.trajectory(q)
        def evaluate(states):
            standardized = (self.observations - states) * jnp.exp(-q[6:])
            prior = (q - self.center) / self.prior_scale
            return -jnp.sum(standardized**2) / 2 - len(TIMES) * jnp.sum(q[6:]) - jnp.dot(prior, prior) / 2

        # Numerical failure remains invalid, distinct from exact zero density.
        return jax.lax.cond(success, evaluate, lambda _: jnp.asarray(jnp.nan), log_population)

    def functions(self, q):
        states, success = self.trajectory(q)
        return jnp.stack((jnp.exp(q[0]), jnp.where(success, jnp.exp(states[-1, 0]), jnp.nan)))

    def oracle(self, q, **accuracy):
        states, sensitivity = scipy_trajectory(q, **accuracy)
        residual = self.observations - states
        scaled = residual**2 * np.exp(-2*q[6:])
        prior = (q-self.center)/self.prior_scale
        log_density = -scaled.sum()/2 - len(TIMES)*sum(q[6:]) - prior @ prior/2
        grad = np.einsum("ij,ijk->k", residual*np.exp(-2*q[6:]), sensitivity)
        grad[6:] += scaled.sum(axis=0) - len(TIMES)
        grad -= prior/self.prior_scale
        return states, log_density, grad


def ode_fixture(fast):
    center = np.log(np.r_[RATES*(2 if fast else 1), [24, 12, 0.2, 0.2]])
    states, _ = scipy_trajectory(center)
    noise = np.random.default_rng(27102).normal(scale=0.2, size=states.shape)
    return ODE(states + noise, center), center.copy()


def fixture(name):
    return logistic_fixture() if name == "logistic" else ode_fixture(name == "ode-fast")
