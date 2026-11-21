"""Synthetic overflow must invalidate the run instead of becoming an MH rejection."""
from pathlib import Path
import json
import math
import os
import sys

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_torch"))
sys.path.insert(0, str(ROOT / "r-package/inst/python"))
from ode_candidate import OdeCandidate
from parallelbayes.reference import Model
from parallelbayes.torch_backend.sampling import sample


def clean(value):
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


@pytest.mark.parametrize("kernel,executor,policy", [
    ("rwm", "sequential", "error"), ("rwm", "online_picard", "error"),
    ("mala", "sequential", "error"), ("mala", "quasi_deer", "error"),
    ("rwm", "online_picard", "sequential"), ("mala", "quasi_deer", "sequential")])
def test_overflow_is_quarantined(kernel, executor, policy):
    center = np.log([.5,.025,.75,.025,24,12,.2,.2])
    # Coarse integration is deliberate: this is a failure-handling test only.
    target = OdeCandidate(np.zeros((21, 2)), center, substeps=4)
    def unused(*args):
        raise AssertionError("independent numerical reference must not be called in this failure test")
    spec = {"kind":"synthetic_ode_failure_fixture", "coordinate_id":"log-eight", "dimension":8}
    model = Model(spec, 8, target.log_density, unused, unused, lambda x:x,
                  [f"q{i}" for i in range(8)], backend="torch")
    model.device = torch.device("cpu")
    model.constrain_device = lambda x:x
    noise = np.zeros((1, 1, 8))
    noise[0, 0, 0] = 1_000_000
    tape = {"noise":noise, "log_uniform":np.array([[-.5]]), "directions":np.ones((1,1,8))}
    result = sample(model, {"kernel":kernel, "executor":executor, "device":"cpu", "draws":1,
                           "chains":1, "window":1, "max_iter":2, "initial":center,
                           "step_size":.01, "audit":False, "on_failure":policy}, tape=tape)
    assert result["status"] == "failed"
    assert result["diagnostics"]["status"] == 2
    assert result["draws"] is None and result["unconstrained"] is None
    assert result["failed_trajectory"] is not None
    assert result["fallback"] == (policy == "sequential")
    if result["fallback"]:
        assert result["primary_failed_trajectory"] is not None
        assert result["timing"]["fallback"] > 0
    evidence = os.environ.get("PARALLELBAYES_ODE_FAILURE_EVIDENCE")
    if evidence:
        directory = Path(evidence)
        stem = f"{kernel}-{executor}-{policy}"
        arrays = {**tape, "initial":center, "failed_trajectory":result["failed_trajectory"],
                  "accept":result["accept"]}
        if result["primary_failed_trajectory"] is not None:
            arrays["primary_failed_trajectory"] = result["primary_failed_trajectory"]
        with (directory / f"{stem}.npz").open("xb") as file:
            np.savez_compressed(file, **arrays)
        record = {key:result[key] for key in ("status","diagnostics","primary_diagnostics",
                  "fallback","timing","stopping_reason","tape_sha256")}
        record["scope"] = "synthetic nonfinite failure only; not numerical qualification"
        with (directory / f"{stem}.json").open("x") as file:
            json.dump(clean(record),file,indent=2,allow_nan=False)
            file.write("\n")
