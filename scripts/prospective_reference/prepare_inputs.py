"""Create independent candidate datasets and stratified initial values.

The artifact is a candidate until target validation and the study freeze.
"""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from scipy.special import expit, ndtri

SOURCE = Path(__file__).parent / "formal_source/hudson-bay-lynx-hare.csv"
SOURCE_COMMIT = "e5b7d9e2e9ecc375805c7e49e4a4d4c1882b5e3b"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def generate(output):
    output.mkdir()
    source = SOURCE.read_text()
    rows = list(csv.DictReader((line for line in source.splitlines() if not line.startswith("#")),
                               skipinitialspace=True))
    years = np.array([int(row["Year"]) for row in rows], dtype=np.int64)
    hare = np.array([float(row["Hare"]) for row in rows])
    lynx = np.array([float(row["Lynx"]) for row in rows])
    if not np.array_equal(years, np.arange(1900, 1921)) or np.any(hare <= 0) or np.any(lynx <= 0):
        raise ValueError("unexpected Hudson Bay data")
    rng = np.random.default_rng(20261122)
    trials = rng.integers(5, 25, size=128)
    latent = rng.normal(size=128)
    successes = rng.binomial(trials, expit(-0.2 + 0.9 * latent))
    np.savez(output / "data.npz", trials=trials, successes=successes, years=years,
             ode_log_observations=np.log(np.column_stack((hare, lynx))))

    # One randomized Latin hypercube per model, chain and parameter are indexed
    # independently. Draws are confined to the central 80% of each prior.
    rng = np.random.default_rng(20261123)
    centers = {
        "logistic": np.r_[0., 0., np.zeros(128)],
        "ode": np.log([.55, .028, .80, .024, 30., 4., .25, .25]),
    }
    scales = {
        "logistic": np.r_[2., 1., np.ones(128)],
        "ode": np.r_[[.5]*4, [.5]*2, [.5]*2],
    }
    initials = {}
    for model in ("logistic", "ode"):
        columns = []
        for center, scale in zip(centers[model], scales[model], strict=True):
            bins = rng.permutation(10)
            probabilities = .1 + .8 * (bins + rng.random(10)) / 10
            columns.append(center + scale * ndtri(probabilities))
        initials[model] = np.column_stack(columns)
    # Reserve three deterministic replacements inside each original stratum.
    # The first initial remains the selected point when it passes preflight.
    for model in ("logistic", "ode"):
        first = initials[model]
        from scipy.special import ndtr
        bins = np.floor((ndtr((first-centers[model])/scales[model])-.1)*12.5).astype(int)
        replacements = []
        for _ in range(3):
            probabilities = .1 + .8*(bins+rng.random(first.shape))/10
            replacements.append(centers[model] + scales[model]*ndtri(probabilities))
        initials[model + "_candidates"] = np.stack([first, *replacements], axis=1)
    np.savez(output / "initials.npz", **initials)
    meta = {
        "scope": "candidate, not yet frozen or authorized for formal sampling",
        "ode_source": "https://github.com/stan-dev/example-models/blob/" + SOURCE_COMMIT +
                      "/knitr/lotka-volterra/hudson-bay-lynx-hare.csv",
        "source_sha256": digest(SOURCE),
        "data_sha256": digest(output / "data.npz"),
        "initials_sha256": digest(output / "initials.npz"),
        "logistic": {"groups":128, "generation_seed":20261122, "mu":-.2, "scale":.9,
                     "prior": "mu ~ Normal(0,2); log(tau) ~ Normal(0,1); z_j ~ Normal(0,1)"},
        "ode": {"order":["alpha","beta","gamma","delta","hare0","lynx0","sigma_hare","sigma_lynx"],
                "times": "0..20 annual", "observations": "log(Hare),log(Lynx); units thousands",
                "prior": "independent Normal(log(center),0.5) in log coordinates",
                "center":np.exp(centers["ode"]).tolist()},
        "initials": {"seed":20261123, "rule":"Latin hypercube, central 80% of each independent prior",
                     "per_model":10, "candidates_per_chain":4, "space":"unconstrained",
                     "formal_random_stream_seed":20261124},
    }
    (output / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    generate(args.output)
