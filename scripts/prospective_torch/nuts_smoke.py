"""Four spawned Pyro NUTS chains on synthetic logistic data.

This small qualification checks process/diagnostics integration only.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
import json
import multiprocessing
from pathlib import Path
import random
import sys
import time
import traceback

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"scripts/prospective_torch"))
from logistic import HierarchicalLogistic


def chain_worker(chain, trials, successes, initial, output):
    import pyro
    import torch
    from pyro.infer.mcmc import MCMC, NUTS

    def reject_legacy_diagnostics(*args, **kwargs):
        raise RuntimeError("legacy MCMC.diagnostics must not run in this smoke")

    MCMC.diagnostics = reject_legacy_diagnostics

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    pyro.set_rng_seed(105010+chain)
    output.mkdir()
    q0 = torch.as_tensor(initial, dtype=torch.float64)
    np_state = np.random.get_state()
    with (output/"rng.npz").open("xb") as file:
        np.savez(file, torch=torch.get_rng_state().numpy(), numpy_keys=np_state[1],
                 numpy_position=np.array(np_state[2]), numpy_has_gauss=np.array(np_state[3]),
                 numpy_cached=np.array(np_state[4]))
    rng_description = {"numpy_generator":np_state[0], "python_state":random.getstate()}
    (output/"rng.json").write_text(json.dumps(rng_description)+"\n")
    counter = 0
    target = HierarchicalLogistic(trials,successes,"cpu")

    def potential(params):
        nonlocal counter
        counter += 1
        return -target.log_density(params["q"])

    started = time.perf_counter()
    try:
        kernel = NUTS(potential_fn=potential, target_accept_prob=.8, max_tree_depth=8)
        mcmc = MCMC(kernel, num_samples=24, warmup_steps=32, num_chains=1,
                    initial_params={"q":q0}, disable_progbar=True)
        mcmc.run()
        draws = mcmc.get_samples(group_by_chain=True)["q"].detach().cpu().numpy()
        if draws.shape != (1,24,130) or not np.isfinite(draws).all():
            raise ValueError("invalid chain output")
        # MCMC.diagnostics() is intentionally bypassed. Kernel diagnostics are
        # already captured by Pyro's run and do not invoke posterior ESS.
        # Pyro cleans up the kernel after collecting its diagnostics. Access the
        # captured per-chain record; calling kernel.diagnostics() again after
        # cleanup is invalid. This private attribute is version-sensitive.
        captured = getattr(mcmc, "_diagnostics", None)
        if not isinstance(captured, list) or len(captured) != 1 or not isinstance(captured[0], dict):
            raise RuntimeError("Pyro did not expose the expected per-chain diagnostics")
        kernel_diagnostics = captured[0]
        with (output/"draws.npy").open("xb") as file:
            np.save(file, draws, allow_pickle=False)
        status = {"status":"completed", "chain":chain, "pid":__import__("os").getpid(),
                  "seed":105010+chain, "samples":list(draws.shape),
                  "draws_sha256":sha256((output/"draws.npy").read_bytes()).hexdigest(),
                  "initial_rng_sha256":sha256((output/"rng.npz").read_bytes()).hexdigest(),
                  "potential_calls":counter, "kernel_diagnostics":kernel_diagnostics,
                  "torch":torch.__version__, "pyro":pyro.__version__, "seconds":time.perf_counter()-started,
                  "legacy_mcmc_diagnostics_called":False}
    except BaseException as error:
        status = {"status":"failed", "chain":chain, "error":repr(error),
                  "traceback":traceback.format_exc(), "potential_calls":counter,
                  "seconds":time.perf_counter()-started}
    (output/"result.json").write_text(json.dumps(status,indent=2)+"\n")
    return status


def main(output):
    output.mkdir()
    rng = np.random.default_rng(30115)
    trials = rng.integers(5,25,size=128)
    successes = rng.binomial(trials, .45)
    initials = rng.normal(scale=.02,size=(4,130))
    with (output/"inputs.npz").open("xb") as file:
        np.savez(file,trials=trials,successes=successes,initials=initials)
    results=[]
    with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context("spawn")) as pool:
        pending={pool.submit(chain_worker,i,trials,successes,initials[i],output/f"chain-{i}"):i for i in range(4)}
        for future in as_completed(pending):
            i=pending[future]
            try:
                results.append(future.result())
            except BaseException as error:
                results.append({"status":"worker_exception","chain":i,"error":repr(error)})
    results.sort(key=lambda row:row["chain"])
    summary={"scope":"synthetic smoke; no formal posterior samples",
             "inputs_sha256":sha256((output/"inputs.npz").read_bytes()).hexdigest(),
             "results":results,"status":"completed" if len(results)==4 and all(
                 row["status"]=="completed" for row in results) else "failed"}
    (output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    if summary["status"] != "completed":
        raise SystemExit("four-chain smoke did not complete")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    main(args.output)
