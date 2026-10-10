"""Finite R timing adapter; uses an installed provider and saved actual inputs.

This is analysis code, not another sampler or a replacement R model registry.
The R process imports the installed package before importing this module.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_context(inputs, example_path):
    inputs = Path(inputs)
    manifest = json.loads((inputs / "input-manifest.json").read_text())
    if manifest["schema"] != "installed-custom-target-input-v1":
        raise ValueError("Unsupported actual-input identity")
    if set(manifest["files"]) != {"model.json", "inputs.npz"}:
        raise ValueError("Unexpected actual-input members")
    for name, expected in manifest["files"].items():
        if digest(inputs / name) != expected:
            raise ValueError("Actual input changed: " + name)
    spec = importlib.util.spec_from_file_location("installed_custom_target", example_path)
    example = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)
    model_spec = json.loads((inputs / "model.json").read_text())
    with np.load(inputs / "inputs.npz", allow_pickle=False) as z:
        tape = {k: z[k].copy() for k in ("noise", "log_uniform", "directions")}
        initial = z["initial"].copy()
    return dict(model=example.make_target(model_spec, "torch", "cpu"),
                initial=initial, tape=tape, manifest=manifest, example=example)


def invoke(context, workflow, audit):
    import parallelbayes as pb
    config = dict(context["manifest"]["config"],
                  **context["manifest"]["workflows"][int(workflow)])
    config.update(audit=bool(audit), initial=context["initial"].tolist(), device="cpu")
    try:
        return pb.sample(context["model"], config, tape=context["tape"], backend="torch")
    except Exception as exc:
        # Preserve failed calls, including the configuration; do not retry them.
        return dict(status="failed", draws=None, config=config,
                    error=f"{type(exc).__name__}: {exc}", stopping_reason="exception")


def payload(result):
    return dict(status=result["status"], names=result.get("names"),
                draws=np.transpose(result["draws"], (1, 0, 2))
                if result["status"] == "completed" else None)


def persist(context, result, destination):
    context["example"].save_result(Path(destination), result)
