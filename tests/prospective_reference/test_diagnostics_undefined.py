"""A constant-chain diagnostic stays undefined and is never accepted as precise."""
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"scripts/prospective_reference"))
sys.path.insert(0, str(ROOT/"scripts/analysis"))
from checkpoint import Checkpoint
from prospective_reference_diagnostics import assess


def main(rscript):
    with tempfile.TemporaryDirectory(prefix="prospective-diagnostics-") as directory:
        root = Path(directory)
        paths = []
        rng = np.random.default_rng(5421)
        for chain in range(1, 11):
            path = root/f"chain-{chain}.sqlite"
            db = Checkpoint(path, {"scope":"synthetic test", "model":"logistic", "chain":chain})
            with db.transaction():
                db.append(0,0,{"initial":np.array([chain])})
                for start in range(1,1001,100):
                    # The probability function is constant in every chain.
                    block = {"draws":rng.normal(size=(100,2)),
                             "functions":np.column_stack((rng.normal(size=100), rng.normal(size=100),
                                                           np.full(100,.5))),
                             "energy":rng.normal(size=100), "divergent":np.zeros(100,dtype=bool),
                             "expansions":np.ones(100,dtype=int)}
                    db.append(start,start+99,block)
            db.db.close()
            paths.append(path)
        result = assess(paths, root/"report",1000,rscript)
        probability = result["quantities"]["probability"]
        assert probability["within_mcse"] is None
        assert probability["mcse"] is None and probability["relative_mcse"] is None
        assert not probability["precision_pass"] and not result["diagnostics_pass"]
        assert probability["mean"] == .5
        assert (root/"report/receipt.json").exists()
    print("undefined constant-function diagnostic preserved and not accepted")


if __name__ == "__main__":
    main(sys.argv[1])
