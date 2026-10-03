"""Mature BlackJAX NUTS, with adaptation included and no same-path claim."""
import time
import numpy as np
import jax
import jax.numpy as jnp
import blackjax
from .output import constrain_checked


def sample_nuts(model, c):
    started = time.perf_counter()
    device = jax.devices(c["platform"])[0]
    q0 = np.zeros((c["chains"], model.dimension)) if c["initial"] is None else np.asarray(c["initial"], float)
    if q0.shape == (model.dimension,):
        q0 = np.broadcast_to(q0, (c["chains"], model.dimension))
    if c["chains"]*(c["draws"]+c["warmup"])*model.dimension*8*40 > c["memory_limit_mb"]*1024**2:
        raise MemoryError("NUTS workspace estimate exceeds limit")
    if q0.shape != (c["chains"], model.dimension) or not np.isfinite(q0).all():
        raise ValueError("invalid initial shape")
    with jax.default_device(device):
        adaptation = blackjax.window_adaptation(blackjax.nuts, model.log_density,
                                                progress_bar=False,
                                                max_num_doublings=c["max_tree_depth"])
        def adapt(key, q):
            (state, parameters), _ = adaptation.run(key, q, num_steps=c["warmup"])
            return state, {k: parameters[k] for k in ("step_size", "inverse_mass_matrix")}
        keys = jax.random.split(jax.random.PRNGKey(c["seed"]), 2*c["chains"])
        warm = jax.jit(jax.vmap(adapt))
        t = time.perf_counter()
        compiled_warm = warm.lower(keys[:c["chains"]], jnp.asarray(q0)).compile()
        compile_warm = time.perf_counter()-t
        t = time.perf_counter()
        state, parameters = compiled_warm(keys[:c["chains"]], jnp.asarray(q0))
        jax.block_until_ready((state, parameters))
        warm_seconds = time.perf_counter()-t
        def chain(key, state, parameters):
            algorithm = blackjax.nuts(model.log_density, **parameters,
                                      max_num_doublings=c["max_tree_depth"])
            def body(st, k):
                st, info = algorithm.step(k, st)
                return st, (st.position, info.acceptance_rate, info.is_divergent,
                            info.num_integration_steps)
            return jax.lax.scan(body, state, jax.random.split(key, c["draws"]))[1]
        run = jax.jit(jax.vmap(chain))
        t = time.perf_counter()
        compiled = run.lower(keys[c["chains"]:], state, parameters).compile()
        compile_sample = time.perf_counter()-t
        t = time.perf_counter()
        out = compiled(keys[c["chains"]:], state, parameters)
        jax.block_until_ready(out)
        execution = time.perf_counter()-t
        t = time.perf_counter()
        draws, accept, divergent, leapfrogs = map(np.asarray, out)
        transfer = time.perf_counter()-t
    valid = bool(np.isfinite(draws).all())
    t=time.perf_counter()
    constrained,transform_error=constrain_checked(model,draws) if valid else (None,None)
    transform_seconds=time.perf_counter()-t
    valid &= transform_error is None
    return dict(status="completed" if valid else "failed", draws=constrained if valid else None,
                unconstrained=draws if valid else None, names=model.names, config=c,
                failed_trajectory=draws if not valid else None, transform_error=transform_error,
                target_id=model.target_id, coordinate_id=model.spec["coordinate_id"],
                guarantee="adapt_then_fixed_nuts_kernel_not_equilibrium_certificate", fallback=False,
                diagnostics=dict(acceptance_rate=accept, divergent=divergent, leapfrogs=leapfrogs),
                adapted_parameters=jax.tree.map(np.asarray, parameters),
                timing=dict(compile=compile_warm+compile_sample, warmup=warm_seconds,
                            sample=execution, transfer=transfer,transform=transform_seconds,total=time.perf_counter()-started))
