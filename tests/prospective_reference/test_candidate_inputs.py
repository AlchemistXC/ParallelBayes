"""Validate candidate identities, content, priors and preflight refusal."""
from pathlib import Path
import json
import sys
import tempfile

import numpy as np
from scipy.special import ndtr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_reference"))
from prepare_inputs import generate, digest
from formal_run import verify_freeze


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        generate(root / "one")
        generate(root / "two")
        first, second = root / "one", root / "two"
        manifest = json.loads((first / "manifest.json").read_text())
        assert digest(first/"data.npz") == manifest["data_sha256"]
        with np.load(first/"data.npz") as a, np.load(second/"data.npz") as b:
            assert all(np.array_equal(a[key], b[key]) for key in a.files)
            assert a["trials"].shape == (128,) and np.all(a["successes"] <= a["trials"])
            assert a["ode_log_observations"].shape == (21,2)
        with np.load(first/"initials.npz") as a, np.load(second/"initials.npz") as b:
            for name, center, scale in [
                ("logistic", np.r_[0, 0, np.zeros(128)], np.r_[2, 1, np.ones(128)]),
                ("ode", np.log([.55, .028, .80, .024, 30, 4, .25, .25]), np.full(8,.5))]:
                assert np.array_equal(a[name], b[name])
                assert np.array_equal(a[name+"_candidates"], b[name+"_candidates"])
                assert np.array_equal(a[name+"_candidates"][:,0,:], a[name])
                u = (ndtr((a[name]-center)/scale)-.1)/.8
                assert np.all((u > 0) & (u < 1))
                assert all(np.array_equal(np.sort(np.floor(u[:,i]*10)), np.arange(10))
                           for i in range(u.shape[1]))
                candidates = (ndtr((a[name+"_candidates"]-center)/scale)-.1)/.8
                assert np.all(np.floor(candidates*10) == np.floor(u[:,None,:]*10))
        bad = root/"seal.json"
        bad.write_text(json.dumps({"identity":"prospective-first-use-v1","status":"candidate"}))
        try:
            verify_freeze(bad, first, "logistic")
        except ValueError as exc:
            assert "frozen" in str(exc)
        else:
            raise AssertionError("unfrozen inputs must fail before sampling")
    print("candidate reproducibility, strata and freeze rejection passed")


if __name__ == "__main__":
    main()
