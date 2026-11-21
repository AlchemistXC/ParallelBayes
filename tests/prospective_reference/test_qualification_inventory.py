"""Audit qualification allocation and paired arms without executing a sampler."""
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"scripts/prospective_plan"))
from qualification_inventory import tasks, COMBINATIONS, EIGHT, THREE, FOUR


def main():
    entries = tasks()
    assert len(entries) == len({x["task_id"] for x in entries}) == 880
    expected = {"gaussian_corners":384, "gaussian_intermediate":144, "logistic_proxy":48,
                "ode_1024":160, "ode_4096":72, "longest":72}
    assert Counter(x["stage"] for x in entries) == expected
    grouped = defaultdict(list)
    for item in entries:
        key = (item["stage"], item["model"], item["steps"], item["replicate"])
        grouped[key].append(item)
        assert item["input_set"] == "qualification" and item["chains"] == 4
    assert len(grouped) == (4+4+1)*3 + 2*5 + 2*3 + 3*3
    arm_by_stage = {"gaussian_corners":EIGHT, "gaussian_intermediate":THREE, "logistic_proxy":FOUR,
                    "ode_1024":FOUR, "ode_4096":THREE,
                    "longest":("sequential","first_use")}
    for (stage, _, _, _), group in grouped.items():
        expected_pairs = {(device,kernel,arm) for device,kernel in COMBINATIONS
                          for arm in arm_by_stage[stage]}
        assert {(x["device"],x["kernel"],x["arm"]) for x in group} == expected_pairs
        assert len(group) == len(expected_pairs)
    assert tasks() == entries
    print("880 unique planned calls and all matched arm combinations verified")


if __name__ == "__main__":
    main()
