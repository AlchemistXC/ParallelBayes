"""Extract the two already reported Rhat discrepancies into a small fixture.

Reads archived arrays and their saved checksums; does not run a sampler.
The binary is chain-major little-endian float64, read by R as iterations x chains.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import numpy as np

TASKS = [
    "a31fe6e8c9f4cc42ae23650e204a784de458ea2651c3bbd5646a9bfda0389f91",
    "e134691aa461969b1fda891a8279f2cfd5a09a7bea354fb796c7b64e050d48e8",
]
PROTOCOL = "1d233dd09956c4575fc5775082310e5edca65407db5fcef40bc2ce329e6f5898"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(evidence, output):
    if output.exists():
        raise FileExistsError("Choose a new fixture output directory")
    if evidence == output or evidence in output.parents:
        raise ValueError("Do not write inside the evidence directory")
    root = evidence / "execution/windows-native/windows-native-v1"
    protocol = json.loads((root / "protocol.json").read_text())
    unsigned = dict(protocol)
    recorded = unsigned.pop("protocol_sha256")
    digest = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    if recorded != PROTOCOL or digest != PROTOCOL:
        raise ValueError("Unexpected or altered protocol")
    original = json.loads((root / "modern-diagnostics.json").read_text())
    provenance = []
    arrays = []
    for task_id in TASKS:
        task_dir = root / "tasks" / task_id[:20]
        state = json.loads((task_dir / "state.json").read_text())
        task = state["task"]
        actual_id = hashlib.sha256(json.dumps(task, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if actual_id != task_id or state["protocol_sha256"] != PROTOCOL:
            raise ValueError("Task identity mismatch")
        raw_path = task_dir / state["attempt"] / "raw.npz"
        if sha(raw_path) != state["checksums"]["raw.npz"]:
            raise ValueError("Raw array checksum mismatch")
        with np.load(raw_path, allow_pickle=False) as raw:
            draws = raw["draws"][:, task["discard"]:, 1].copy()
        if draws.shape != (4, 384) or not np.isfinite(draws).all():
            raise ValueError("Unexpected q2 fixture shape or nonfinite values")
        record = next(v for k, v in original.items() if k.endswith("/" + task_id))
        q2 = next(v for v in record["summary"] if v["variable"] == "q2")
        arrays.append(draws)
        provenance.append(dict(task_id=task_id, model=task["model"], config=task["config"],
                               discard=task["discard"], raw_sha256=sha(raw_path),
                               original_windows_diagnostic=q2))
    np.testing.assert_array_equal(arrays[0], arrays[1])
    values = np.sort(arrays[0].ravel())
    middle = values[len(values)//2 - 1:len(values)//2 + 1]
    exact = (Fraction(float(middle[0])) + Fraction(float(middle[1]))) / 2
    rounded = float(exact)
    lower = float(np.nextafter(rounded, -np.inf))
    output.mkdir(parents=True)
    binary = output / "q2-f64le.bin"
    arrays[0].astype("<f8").tofile(binary)
    result = dict(schema_version=1, purpose="post hoc diagnostic sensitivity fixture; not new MCMC data",
        protocol_sha256=PROTOCOL, fixture_file=binary.name, fixture_sha256=sha(binary),
        chains=4, iterations=384, dtype="little-endian float64", order="chain-major",
        cpu_cuda_values_identical=True, source_tasks=provenance,
        middle_values_hex=[float(x).hex() for x in middle],
        exact_midpoint_fraction=str(exact), correctly_rounded_midpoint_hex=rounded.hex(),
        one_ulp_lower_hex=lower.hex(), midpoint_ulp=rounded-lower,
        midpoint_rounding_error_fraction=str(exact-Fraction(rounded)),
        lower_rounding_error_fraction=str(exact-Fraction(lower)),
        observed_mac_rhat=1.4085688369053788, archived_windows_rhat=provenance[0]["original_windows_diagnostic"]["rhat"],
        expected_bulk_rhat=1.1777201953723706, comparison_atol=1e-11, comparison_rtol=1e-11,
        software_scope="posterior 1.7.0; Mac R 4.6.0 observed; Windows runtime confirmation pending")
    (output / "case.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.evidence.resolve(), args.output.resolve())
