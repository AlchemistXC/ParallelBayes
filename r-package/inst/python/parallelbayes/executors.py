"""JAX time executors; all outputs have explicit status and finite-work limits.

Diagonal affine scans follow quasi-DEER (Zoltowski et al., 2025).
Our windows are non-overlapping blocks, not the upstream sliding-window policy.
Online Picard uses accepted RWM increments (Grazzi and Zanella, Algorithm 2).
"""
import jax
import jax.numpy as jnp
from .kernels import transition


def sequential(step, q0, noise, logu, scale):
    def body(q, xs):
        out, accept, finite = step(q, xs[0], xs[1], scale)
        return out, (out, accept, finite)
    _, (draws, accept, finite) = jax.lax.scan(body, q0, (noise, logu))
    return draws, dict(accept=accept, status=jnp.where(jnp.all(finite), 0, 2),
                      iterations=jnp.asarray(noise.shape[0]), residual=jnp.array(0.),
                      clips=jnp.array(0), confirmed=jnp.asarray(noise.shape[0]),
                      forward_evals=jnp.asarray(noise.shape[0]), jvp_evals=jnp.array(0))


def affine_scan(a, b, q0):
    def compose(left, right):
        ai, bi = left
        aj, bj = right
        return aj*ai, aj*bi+bj
    aa, bb = jax.lax.associative_scan(compose, (a, b))
    return aa*q0+bb


def quasi_deer(step, q0, noise, logu, directions, scale, window, max_iter,
               atol, rtol, jacobian_clip):
    n, d = noise.shape
    padded = ((n+window-1)//window)*window
    zz = jnp.pad(noise, ((0, padded-n), (0, 0))).reshape(-1, window, d)
    uu = jnp.pad(logu, ((0, padded-n),), constant_values=-1.).reshape(-1, window)
    vv = jnp.pad(directions, ((0, padded-n), (0, 0)), constant_values=1.).reshape(-1, window, d)
    real=(jnp.arange(padded)<n).reshape(-1,window)

    def solve_block(base, xs):
        z, u, v, mask = xs
        f = lambda q, zi, ui: step(q, zi, ui, scale, surrogate=True)[0]
        batch = jax.vmap(lambda q, zi, ui: step(q, zi, ui, scale))
        def residual(path):
            prev = jnp.concatenate((base[None], path[:-1]))
            out, acc, finite = batch(prev, z, u)
            normalized = jnp.max(jnp.where(mask[:,None],jnp.abs(path-out)/(atol+rtol*jnp.abs(out)),0.))
            return normalized, acc, jnp.all(finite | ~mask) & jnp.all(jnp.isfinite(path) | ~mask[:,None])
        def body(carry):
            path, it, _, _, clips = carry
            prev = jnp.concatenate((base[None], path[:-1]))
            values, jv = jax.vmap(lambda qi, zi, ui, vi: jax.jvp(
                lambda qi: f(qi, zi, ui), (qi,), (vi,)))(prev, z, u, v)
            diag = v*jv
            clipped = jnp.clip(diag, -jacobian_clip, jacobian_clip)
            updated = affine_scan(clipped, values-clipped*prev, base)
            err, _, finite = residual(updated)
            return updated, it+1, err, finite, clips+jnp.sum(jnp.abs(diag)>jacobian_clip)
        initial = (jnp.broadcast_to(base, z.shape), jnp.array(0), jnp.array(jnp.inf),
                   jnp.array(True), jnp.array(0))
        out, it, err, finite, clips = jax.lax.while_loop(
            lambda s: (s[1]<max_iter) & (s[2]>1.) & s[3], body, initial)
        _, acc, _ = residual(out)
        status = jnp.where(~finite, 2, jnp.where(err<=1., 0, 1))
        return out[jnp.sum(mask)-1], (out, acc, status, it, err, clips)
    _, (paths, accepts, statuses, iters, errors, clips) = jax.lax.scan(solve_block, q0, (zz, uu, vv, real))
    return paths.reshape(-1, d)[:n], dict(
        accept=accepts.reshape(-1)[:n], status=jnp.max(statuses),
        iterations=jnp.sum(iters), residual=jnp.max(errors), clips=jnp.sum(clips),
        confirmed=jnp.array(0), forward_evals=window*(2*jnp.sum(iters)+len(zz)),
        jvp_evals=window*jnp.sum(iters))


def online_picard(step, q0, noise, logu, scale, window, max_iter):
    n, d = noise.shape
    zz = jnp.pad(noise, ((0, window), (0, 0)))
    uu = jnp.pad(logu, ((0, window),), constant_values=-1.)
    batch = jax.vmap(lambda q, z, u: step(q, z, u, scale))
    output = jnp.zeros((n+window, d), dtype=q0.dtype)
    all_accept = jnp.zeros(n+window, dtype=bool)
    initial = (jnp.array(0), jnp.broadcast_to(q0, (window, d)), output,
               all_accept, jnp.array(0), jnp.array(True))
    def body(carry):
        offset, guess, out, acc_out, it, finite_so_far = carry
        z = jax.lax.dynamic_slice(zz, (offset, 0), (window, d))
        u = jax.lax.dynamic_slice(uu, (offset,), (window,))
        _, old_acc, finite1 = batch(guess, z, u)
        increments = jnp.where(old_acc[:, None], scale*z, 0.)
        new_path = guess[0]+jnp.cumsum(increments, axis=0)
        new_prev = jnp.concatenate((guess[:1], new_path[:-1]))
        _, new_acc, finite2 = batch(new_prev, z, u)
        valid = jnp.arange(window)+offset < n
        same = old_acc == new_acc
        prefix = jnp.minimum(jnp.sum(jnp.cumprod(same.astype(jnp.int32))), n-offset)
        finite = jnp.all((finite1 & finite2) | ~valid) & (prefix>0)
        out = jax.lax.dynamic_update_slice(out, new_path, (offset, 0))
        acc_out = jax.lax.dynamic_update_slice(acc_out, old_acc, (offset,))
        indices = jnp.arange(window)+prefix
        shifted = new_prev[jnp.minimum(indices, window-1)]
        shifted = jnp.where((indices>=window)[:, None], new_path[-1], shifted)
        return offset+prefix, shifted, out, acc_out, it+1, finite_so_far & finite
    offset, _, out, acc, it, finite = jax.lax.while_loop(
        lambda s: (s[0]<n) & (s[4]<max_iter) & s[5], body, initial)
    return out[:n], dict(accept=acc[:n], status=jnp.where(~finite, 2, jnp.where(offset==n, 0, 1)),
                        iterations=it, residual=jnp.array(0.), clips=jnp.array(0),
                        confirmed=offset, forward_evals=2*window*it, jvp_evals=jnp.array(0))


def program(model, kernel, executor, window, max_iter, atol, rtol, jacobian_clip):
    step = transition(model.log_density, kernel)
    def one(q0, noise, logu, directions, scale):
        if executor == "sequential":
            return sequential(step, q0, noise, logu, scale)
        if executor == "online_picard":
            return online_picard(step, q0, noise, logu, scale, window, max_iter)
        return quasi_deer(step, q0, noise, logu, directions, scale, window, max_iter,
                          atol, rtol, jacobian_clip)
    return jax.jit(jax.vmap(one, in_axes=(0, 0, 0, 0, None)))
