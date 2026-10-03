"""Fixed-noise kernels. MALA uses q'=q+h*grad(logp)+sqrt(2h)*z."""
import numpy as np
import jax
import jax.numpy as jnp


def transition(logp, kernel):
    value_grad = jax.value_and_grad(logp)

    def step(q, z, logu, scale, surrogate=False):
        if kernel == "mala":
            lp, g = value_grad(q)
            proposal = q+scale*g+jnp.sqrt(2*scale)*z
            lp2, g2 = value_grad(proposal)
            reverse = q-proposal-scale*g2
            forward = proposal-q-scale*g
            ratio = lp2-lp-(jnp.sum(reverse**2)-jnp.sum(forward**2))/(4*scale)
            finite = jnp.all(jnp.isfinite(g)) & jnp.all(jnp.isfinite(g2))
        else:
            proposal = q+scale*z
            lp, lp2 = logp(q), logp(proposal)
            ratio = lp2-lp
            finite = jnp.array(True)
        finite &= jnp.isfinite(lp) & jnp.isfinite(lp2) & jnp.all(jnp.isfinite(proposal))
        accept = (logu < ratio) & finite
        if surrogate:
            smooth = jax.nn.sigmoid(ratio-logu)
            gate = jax.lax.stop_gradient(accept.astype(q.dtype)) + smooth-jax.lax.stop_gradient(smooth)
            out = q+gate*(proposal-q)
        else:
            out = jnp.where(accept, proposal, q)
        return out, accept, finite
    return step


class ReferenceFailure(FloatingPointError):
    """Available prefix and stopping location from an independent serial kernel."""
    def __init__(self, message, draws, accepts, step, state):
        super().__init__(message)
        self.draws=np.asarray(draws).reshape(-1,len(state))
        self.accepts=np.asarray(accepts,dtype=bool)
        self.step=step
        self.state=np.asarray(state).copy()


def numpy_reference(model, kernel, q0, noise, logu, step_size, strict=True):
    q = np.array(q0, float, copy=True)
    draws, accepts = [], []
    for index,(z,u) in enumerate(zip(noise,logu)):
        try:
            lp = model.reference(q)
            if kernel == "mala":
                g = model.gradient_reference(q)
                proposed = q+step_size*g+np.sqrt(2*step_size)*z
                g2 = model.gradient_reference(proposed)
                rev, fwd = q-proposed-step_size*g2, proposed-q-step_size*g
                ratio = model.reference(proposed)-lp-(np.sum(rev**2)-np.sum(fwd**2))/(4*step_size)
            else:
                proposed = q+step_size*z
                ratio = model.reference(proposed)-lp
            if strict and (not np.isfinite(lp) or not np.isfinite(ratio) or not np.isfinite(proposed).all()):
                raise FloatingPointError("nonfinite target, proposal or acceptance ratio")
            accepted = bool(u < ratio)
            if accepted:
                q = proposed
            draws.append(q.copy())
            accepts.append(accepted)
        except (RuntimeError,ValueError,FloatingPointError,OverflowError) as exc:
            raise ReferenceFailure(str(exc),draws,accepts,index,q) from exc
    return np.asarray(draws), np.asarray(accepts)
