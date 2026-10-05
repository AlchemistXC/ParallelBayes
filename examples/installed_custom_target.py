"""External Poisson model through installed ParallelBayes public interfaces.

prepare saves actual data/random arrays once. run and the R companion consume
those bytes; neither regenerates them from seeds. No repository core import.
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import sys
import numpy as np


SCOPE = "Small installation/extension check; not formal sampling, convergence, or speed evidence"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def prepare(output):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    rng = np.random.Generator(np.random.Philox(684321))
    x = np.column_stack([np.ones(32), rng.normal(size=32)])
    y = rng.poisson(np.exp(x @ np.array([.2, -.4])))
    spec = dict(kind="external_poisson_v1", dimension=2, coordinate_id="identity",
                X=x.tolist(), y=y.tolist(), prior_sd=2., parameter_order=["beta0", "beta1"],
                omitted_constant="sum log(y!)", jacobian_log_abs_det=0.)
    write_json(root / "model.json", spec)
    noise_rng = np.random.Generator(np.random.Philox(np.random.SeedSequence([9921, 101])))
    solver_rng = np.random.Generator(np.random.Philox(np.random.SeedSequence([9922, 102])))
    shape = (4, 128, 2)
    np.savez(root / "inputs.npz", noise=noise_rng.standard_normal(shape),
             log_uniform=np.log(np.maximum(noise_rng.random(shape[:2]), np.finfo(float).tiny)),
             directions=(2 * solver_rng.integers(0, 2, size=shape) - 1).astype(float),
             initial=np.zeros((4, 2)), points=np.array([[0., 0.], [.5, -.5], [-1., 1.], [1., -1.], [2., -2.]]))
    write_json(root / "input-manifest.json", dict(schema="installed-custom-target-input-v1",
        files={name: sha(root / name) for name in ("model.json", "inputs.npz")},
        config=dict(draws=128, chains=4, window=16, max_iter=1024, atol=1e-10,
                    rtol=1e-10, memory_limit_mb=512, audit=True, on_failure="error"),
        workflows=[dict(kernel="mala", executor="sequential", step_size=.01),
                   dict(kernel="mala", executor="quasi_deer", step_size=.01),
                   dict(kernel="rwm", executor="sequential", step_size=.08),
                   dict(kernel="rwm", executor="online_picard", step_size=.08)], scope=SCOPE))
    return str(root)


def make_target(spec, backend="torch", device="cpu"):
    """Provide density, independent reference/gradient and coordinate mapping.

    The two providers currently export distinct Model classes. Choose the one
    required by the selected sampler; do not import JAX in a torch-only process.
    """
    if backend not in ("torch", "jax") or device not in ("cpu", "cuda"):
        raise ValueError("Choose torch/cpu, torch/cuda, or jax/cpu")
    if backend == "jax" and device != "cpu":
        raise ValueError("This extension example only supports JAX CPU")
    if spec["kind"] != "external_poisson_v1" or spec["coordinate_id"] != "identity":
        raise ValueError("This model requires the declared Poisson identity coordinates")
    x, y = np.asarray(spec["X"], float), np.asarray(spec["y"], float)
    if x.ndim != 2 or x.shape[1] != 2 or y.shape != (len(x),) or not len(y):
        raise ValueError("Expected nonempty X with two columns and matching y")
    if not np.isfinite(x).all() or not np.isfinite(y).all() or (y < 0).any() or (y != np.floor(y)).any():
        raise ValueError("Finite predictors and nonnegative integer observations required")
    sd = float(spec["prior_sd"])
    if not np.isfinite(sd) or sd <= 0 or spec["dimension"] != 2 or spec["parameter_order"] != ["beta0", "beta1"]:
        raise ValueError("Invalid prior, dimension or parameter order")
    if spec["jacobian_log_abs_det"] != 0. or spec["omitted_constant"] != "sum log(y!)":
        raise ValueError("Coordinate and omitted-constant declarations differ")
    def reference(q):
        eta = np.einsum("ij,j->i", x, q)
        return float(np.sum(y * eta - np.exp(eta)) - .5 * np.sum(q * q) / sd**2)
    def gradient_reference(q):
        eta = np.einsum("ij,j->i", x, q)
        return np.einsum("ij,i->j", x, y - np.exp(eta)) - q / sd**2
    if backend == "torch":
        import torch
        from parallelbayes.reference import Model
        selected = torch.device(device)
        if selected.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable; no CPU substitution")
        xx, yy = (torch.tensor(a, dtype=torch.float64, device=selected) for a in (x, y))
        def log_density(q):
            eta = xx @ q
            return (yy * eta - torch.exp(eta)).sum() - .5 * q.square().sum() / sd**2
    else:
        from parallelbayes.models import Model
        import jax.numpy as jnp
        xx, yy = jnp.asarray(x, dtype=jnp.float64), jnp.asarray(y, dtype=jnp.float64)
        def log_density(q):
            eta = xx @ q
            return jnp.sum(yy * eta - jnp.exp(eta)) - .5 * jnp.sum(q * q) / sd**2
    model = Model(spec, 2, log_density, reference, gradient_reference,
                  lambda q: np.asarray(q), spec["parameter_order"], backend=backend)
    if backend == "torch":
        model.device = selected
        model.constrain_device = lambda q: q
    return model


def save_result(root, result):
    """Keep all raw arrays, including invalid paths, separate from JSON metadata."""
    arrays = {}
    def convert(value, key="result"):
        if isinstance(value, np.ndarray):
            arrays[key] = value
            return {"array": key, "shape": list(value.shape), "dtype": str(value.dtype)}
        if isinstance(value, np.generic):
            return convert(value.item(), key)
        if isinstance(value, dict):
            return {str(k): convert(v, key + "." + str(k)) for k, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [convert(v, key + "." + str(i)) for i, v in enumerate(value)]
        if isinstance(value, float) and not np.isfinite(value):
            return {"nonfinite": repr(value)}
        return value
    record = convert(result)
    np.savez(root.with_suffix(".npz"), **arrays)
    write_json(root.with_suffix(".json"), record)


def run_example(inputs, output, backend="torch", device="cpu"):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    inputs = Path(inputs)
    manifest = json.loads((inputs / "input-manifest.json").read_text(encoding="utf-8"))
    if manifest["schema"] != "installed-custom-target-input-v1" or set(manifest["files"]) != {"model.json", "inputs.npz"}:
        raise ValueError("Unsupported input manifest")
    for name, digest in manifest["files"].items():
        if sha(inputs / name) != digest:
            raise ValueError("Input checksum mismatch: " + name)
    spec = json.loads((inputs / "model.json").read_text(encoding="utf-8"))
    with np.load(inputs / "inputs.npz", allow_pickle=False) as z:
        tape = {k: z[k].copy() for k in ("noise", "log_uniform", "directions")}
        initial, points = z["initial"].copy(), z["points"].copy()
    import parallelbayes as pb
    model = make_target(spec, backend, device)
    validation = pb.validate_model(model, points, backend=backend)
    summary = dict(scope=SCOPE, backend=backend, device=device, target_id=model.target_id,
        inputs_manifest_sha256=sha(inputs / "input-manifest.json"), input_files=manifest["files"],
        package_version=pb.__version__, package_file=str(Path(pb.__file__).resolve()),
        python_executable=sys.executable, platform=platform.platform(),
        packages={p: metadata.version(p) for p in ("numpy", "scipy", backend)},
        validation=validation, workflows=[], comparisons=[], all_passed=False)
    write_json(root / "summary.json", summary)
    if not validation["passed"]:
        return dict(summary=summary, workflows=[])
    results, returned = [], []
    for index, workflow in enumerate(manifest["workflows"]):
        config = dict(manifest["config"], **workflow, initial=initial.tolist())
        config["device" if backend == "torch" else "platform"] = device
        try:
            result = pb.sample(model, config, tape=tape, backend=backend)
        except Exception as exc:
            # This example is batch-oriented: retain a failed entry and continue.
            result = dict(status="failed", draws=None, config=config,
                          error=f"{type(exc).__name__}: {exc}", stopping_reason="exception")
        save_result(root / f"workflow-{index}", result)
        results.append(result)
        summary["workflows"].append(dict(index=index, **workflow, status=result["status"],
            tape_sha256=result.get("tape_sha256"), audit=result.get("audit"),
            stopping_reason=result.get("stopping_reason"), error=result.get("error")))
        returned.append(dict(index=index, status=result["status"], names=model.names,
            draws=np.transpose(result["draws"], (1, 0, 2)) if result["status"] == "completed" else None))
    for i, j in ((0, 1), (2, 3)):
        a, b = results[i], results[j]
        pair = dict(sequential=i, parallel=j, passed=False)
        if a["status"] == b["status"] == "completed":
            accept_a = a["accept"] if backend == "torch" else a["diagnostics"]["accept"]
            accept_b = b["accept"] if backend == "torch" else b["diagnostics"]["accept"]
            error = float(np.max(np.abs(a["unconstrained"] - b["unconstrained"])))
            limit = 100 * (manifest["config"]["atol"] + manifest["config"]["rtol"] * max(1., float(np.max(np.abs(a["unconstrained"])))))
            pair.update(path_error=error, path_limit=limit,
                        acceptance_mismatches=int(np.sum(accept_a != accept_b)),
                        actual_tape_equal=a["tape_sha256"] == b["tape_sha256"])
            pair["passed"] = bool(error <= limit and pair["acceptance_mismatches"] == 0 and pair["actual_tape_equal"])
        summary["comparisons"].append(pair)
    summary["all_passed"] = all(p["passed"] for p in summary["comparisons"])
    summary["optional_provider_imported"] = {name: name in sys.modules for name in ("torch", "jax")}
    write_json(root / "summary.json", summary)
    return dict(summary=summary, workflows=returned)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--output", required=True)
    run = sub.add_parser("run")
    run.add_argument("--inputs", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--backend", choices=("torch", "jax"), required=True)
    run.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "prepare":
        print(prepare(**args))
    else:
        report = run_example(**args)["summary"]
        print(json.dumps(report, indent=2, allow_nan=False))
        sys.exit(0 if report["all_passed"] else 1)
