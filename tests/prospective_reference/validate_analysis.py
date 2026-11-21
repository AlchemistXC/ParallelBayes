"""Exercise recommendation and reference sensitivity on synthetic paired cells."""
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/analysis"))
from prospective_first_use_summary import first_use, reference_sensitivity


def verify():
    baseline = np.linspace(2, 3, 32)
    strategy = baseline / np.linspace(1.16, 1.24, 32)
    complete = np.ones(32, dtype=bool)
    valid = dict(validated=True, missing_explained=True, seed=1)
    good = first_use(baseline, strategy, complete, **valid)
    assert good["recommended"] and good["interval"][0] > 1.10
    assert abs(good["completeness_lower"] - .05**(1/32)) < 1e-14
    bad = first_use(baseline, np.r_[strategy[:30], np.nan, np.nan], complete, **valid)
    assert bad["pairs"] == 30 and not bad["recommended"] and "pair_coverage" in bad["reasons"]
    assert not first_use(baseline, strategy, complete, validated=True,
                         missing_explained=False, seed=1)["recommended"]
    a, b = np.linspace(.01, .1, 32), np.linspace(.1, .3, 32)
    robust = reference_sensitivity(a, b, 0., .001, seed=2)
    sensitive = reference_sensitivity(a, -b, -.1, .2, seed=2)
    assert robust["direction"] == "a"
    assert sensitive["direction"] is None and sensitive["loss_difference"][0]*sensitive["loss_difference"][1] < 0
    return dict(recommended=good, low_coverage=bad, robust=robust, reference_sensitive=sensitive)


if __name__ == "__main__":
    with Path(sys.argv[1]).open("x") as out:
        json.dump(verify(), out, indent=2)
