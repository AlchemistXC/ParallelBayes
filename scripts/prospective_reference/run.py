"""Mac synthetic reference runner. No formal data entry point in this build."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import resource
import sys
from time import perf_counter

os.environ["JAX_PLATFORMS"] = "cpu"
os.environ["JAX_ENABLE_X64"] = "true"

import blackjax
from blackjax.mcmc.hmc import HMCState
import diffrax
import jax
import jax.numpy as jnp
import numpy as np
import scipy

from checkpoint import Checkpoint
from models import fixture

jax.config.update("jax_threefry_partitionable", True)
BLOCK_SIZE = 100
PRNG = "threefry2x32"
MAX_DEPTH = 8


def phase_key(seed, tag, chain, phase):
    key = jax.random.key(seed, impl=PRNG)
    for value in (tag, chain, phase):
        key = jax.random.fold_in(key, value)
    return key


def warmup(model, q, key):
    adaptation = blackjax.window_adaptation(
        blackjax.nuts, model.log_density, initial_step_size=0.01,
        target_acceptance_rate=0.9, max_num_doublings=MAX_DEPTH,
        adaptation_info_fn=lambda _, info, __: info.is_divergent,
    )
    (state, parameters), divergences = jax.jit(
        lambda: adaptation.run(key, jnp.asarray(q), num_steps=1024)
    )()
    return state, parameters, np.asarray(divergences)


def sampler(model):
    def block(state, key, step_size, inverse_mass):
        nuts = blackjax.nuts(model.log_density, step_size, inverse_mass, max_num_doublings=MAX_DEPTH)

        def step(carry, _):
            state, key = carry
            consumed, following = jax.random.split(key, 2)
            state, info = nuts.step(consumed, state)
            return (state, following), {
                "draws": state.position, "log_density": state.logdensity,
                "gradients": state.logdensity_grad, "acceptance": info.acceptance_rate,
                "divergent": info.is_divergent, "integration_steps": info.num_integration_steps,
                "expansions": info.num_trajectory_expansions, "energy": info.energy,
                "functions": model.functions(state.position), "consumed": jax.random.key_data(consumed),
            }

        return jax.lax.scan(step, (state, key), None, length=BLOCK_SIZE)

    return jax.jit(block)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=["logistic", "ode", "ode-fast"])
    parser.add_argument("database", type=Path)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--chain", type=int, default=1)
    parser.add_argument("--interrupt-before-commit", type=int, help="synthetic recovery fixture")
    args = parser.parse_args()
    if args.steps not in range(0, 8001, BLOCK_SIZE) or args.chain not in range(1, 11):
        parser.error("steps must be a multiple of 100 through 8000, chain must be 1–10")
    start = perf_counter()
    model, initial = fixture(args.model)
    tag = {"logistic": 1, "ode-fast": 2, "ode": 3}[args.model]
    seed = 20261121
    files = {f.name: sha256(f.read_bytes()).hexdigest() for f in Path(__file__).parent.glob("*.py")}
    data = {k: sha256(v.tobytes()).hexdigest() if isinstance(v, np.ndarray) else v
            for k, v in vars(model).items()}
    identity = {"scope": "synthetic", "model": args.model, "chain": args.chain,
                "seed": seed, "files": files, "data": data,
                "initial_sha256": sha256(initial.tobytes()).hexdigest(),
                "environment": [platform.platform(), sys.version, jax.__version__, jax.lib.__version__,
                                blackjax.__version__, diffrax.__version__, np.__version__, scipy.__version__,
                                jax.default_backend(), jax.config.x64_enabled, jax.config.jax_threefry_partitionable]}
    checkpoint = Checkpoint(args.database, identity)
    block = sampler(model)
    advanced = 0
    warmed = False
    with checkpoint.transaction():
        saved = list(checkpoint.blocks())
        if not saved:
            state, params, warm_divergences = warmup(model, initial, phase_key(seed, tag, args.chain, 2))
            initial_record = {**state._asdict(), "step_size": params["step_size"],
                              "inverse_mass_matrix": params["inverse_mass_matrix"],
                              "next_key": jax.random.key_data(phase_key(seed, tag, args.chain, 3)),
                              "warmup_divergent": warm_divergences}
            if not all(np.isfinite(v).all() for v in initial_record.values()):
                raise FloatingPointError("nonfinite warmup output")
            checkpoint.append(0, 0, initial_record)
            warmed = True

    while True:
        with checkpoint.transaction():
            n, record = list(checkpoint.blocks())[-1]
            if n >= args.steps:
                break
            state = HMCState(*(jnp.asarray(record[field]) for field in HMCState._fields))
            key = jax.random.wrap_key_data(jnp.asarray(record["next_key"]), impl=PRNG)
            (state, following), samples = block(
                state, key, jnp.asarray(record["step_size"]), jnp.asarray(record["inverse_mass_matrix"]))
            result = {**samples, **state._asdict(),
                      "step_size": record["step_size"], "inverse_mass_matrix": record["inverse_mass_matrix"],
                      "next_key": jax.random.key_data(following)}
            result = jax.tree.map(np.asarray, result)
            if not all(np.isfinite(v).all() for v in result.values()):
                bad = [name for name, array in result.items() if not np.isfinite(array).all()]
                failure = args.database.with_suffix(f".failed-{n+100}-{os.getpid()}.npz")
                np.savez(failure, **result)
                raise FloatingPointError(f"nonfinite block {n+1}: {bad}; preserved in {failure}")
            checkpoint.append(n+1, n+100, result)
            if args.interrupt_before_commit == n+100:
                print(json.dumps({"intentional_interrupt": n+100}), flush=True)
                os._exit(75)
            advanced += 100
    print(json.dumps({"model": args.model, "chain": args.chain, "last_step": n, "new_steps": advanced,
                      "warmup": warmed, "seconds": perf_counter() - start,
                      "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))


if __name__ == "__main__":
    main()
