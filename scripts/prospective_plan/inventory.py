"""Enumerate planned comparisons without generating any formal random inputs."""
import argparse
from itertools import product
import json
from pathlib import Path

BUDGETS = (256, 1024, 4096, 16384)
REPLICATES = 32


def inventory():
    targets = [dict(dimension=d, rows=m) for d, m in product((8, 32, 128), (256, 2048, 16384, 65536))]
    targets += [{"model": "hierarchical_logistic"}, {"model": "lynx_hare"}]
    anchors = [{"dimension": 32, "rows": m} for m in (256, 65536)]
    longest = anchors + [{"model": "lynx_hare"}]
    arms = {256: ["sequential", "w32", "first_use"],
            1024: ["sequential", "w4", "w8", "w16", "w32", "w64", "first_use", "short_race"],
            4096: ["sequential", "w32", "first_use"], 16384: ["sequential", "first_use"]}
    cells = []
    for budget in BUDGETS:
        for target, device, kernel in product(longest if budget == 16384 else targets,
                                              ("cpu", "cuda"), ("rwm", "mala")):
            recommendation = (budget == 1024 and (target.get("dimension") == 32 or "model" in target)
                              or budget == 4096 and target in longest)
            joint = (budget == 1024 and device == "cuda" and kernel == "rwm"
                     and target in [anchors[-1], {"model": "lynx_hare"}])
            cells.append(dict(target=target, steps=budget, device=device, kernel=kernel,
                              arms=arms[budget], inputs=REPLICATES, recommendation=recommendation,
                              joint=joint))
    strata = {size: sum(row["inputs"] * len(row["arms"]) for row in cells if row["steps"] == size)
              for size in BUDGETS}
    bonus = [
        dict(work="nuts", executions=2*2*REPLICATES),
        dict(work="eager_compile", executions=2*2*2*2*REPLICATES),
        dict(work="warmup_probe", executions=2*REPLICATES),
        dict(work="technical", executions=24),
        dict(work="qualification", executions=sum([384, 144, 48, 160, 72, 72])),
        dict(work="nuts_preflight", executions=2*3),
        dict(work="profiler", executions=2*3*4),
    ]
    result = dict(scope="development inventory without formal inputs", cells=cells, strata=strata,
                  first_use=sum(row["inputs"] for row in cells),
                  core_executions=sum(strata.values()), additional=bonus,
                  fixed_executions=sum(strata.values())+sum(row["executions"] for row in bonus))
    assert len(cells) == 180
    assert sum(row["recommendation"] for row in cells) == 36
    assert sum(row["joint"] for row in cells) == 2
    assert result["first_use"] == 5760 and result["core_executions"] == 25856
    assert result["fixed_executions"] == 27494
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.output.open("x") as file:
        json.dump(inventory(), file, indent=2)
