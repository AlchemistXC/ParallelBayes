"""Compare resumed synthetic ODE snapshots using explicitly mock study receipts."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from restart import blocks, same


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main(fixture, left_backup, right_backup, output):
    manifest = json.loads((fixture / "SYNTHETIC-inputs/manifest.json").read_text())
    prior = json.loads((fixture / "receipt.json").read_text())
    if manifest.get("scope") != "SYNTHETIC TEST ONLY" or not prior.get("field_bytes_identical"):
        raise ValueError("only the verified synthetic fixture may be used")
    for name in ("windows", "capacity", "restart"):
        if json.loads((fixture / f"MOCK-{name}.json").read_text()).get("scope") != "MOCK TEST ONLY":
            raise ValueError("mock qualification evidence required for this synthetic test")
    snapshots = []
    for backup in (left_backup, right_backup):
        receipt = json.loads((backup / "receipt.json").read_text())
        snapshot = backup / receipt["snapshot"]
        if (receipt.get("last_step") != 2000 or receipt.get("recovery_verified_without_wal") is not True
                or digest(snapshot) != receipt.get("sha256")):
            raise ValueError("snapshot receipt differs")
        snapshots.append(snapshot)
    output.mkdir()
    paths = [output / "restored-split.sqlite", output / "restored-continuous.sqlite"]
    for source, dest in zip(snapshots, paths, strict=True):
        shutil.copyfile(source, dest)
    same(blocks(paths[0]), blocks(paths[1]))
    runner = ROOT / "scripts/prospective_reference/formal_run.py"
    inputs, seal = fixture / "SYNTHETIC-inputs", fixture / "MOCK-seal/seal.json"
    results = []
    for index, path in enumerate(paths):
        command = [sys.executable, "-B", str(runner), "ode", str(inputs), str(seal), str(path),
                   "--chain", "1", "--steps", "4000"]
        start = time.monotonic()
        proc = subprocess.run(command, capture_output=True, text=True)
        record = {"command": command, "exit_code": proc.returncode, "stdout": proc.stdout,
                  "stderr": proc.stderr, "elapsed_seconds": time.monotonic() - start}
        (output / f"process-{index+1}.json").write_text(json.dumps(record, indent=2) + "\n")
        if proc.returncode:
            raise RuntimeError("synthetic restored-chain execution failed")
        result = json.loads(proc.stdout)
        if result["new_steps"] != 2000 or result["last_step"] != 4000:
            raise ValueError("unexpected number of resumed transitions")
        results.append(result)
    left, right = blocks(paths[0]), blocks(paths[1])
    same(left, right)
    if len(left) != 41 or left[-1][0] != 4000:
        raise ValueError("unexpected checkpoint length")
    receipt = {"scope": "synthetic ODE only; mock qualification and capacity", "from_steps": 2000,
               "to_steps": 4000, "blocks": len(left), "all_fields_byte_identical": True,
               "input_snapshot_sha256": [digest(path) for path in snapshots],
               "retained_divergences": sum(int(block["divergent"].sum()) for _, first, block in left if first),
               "retained_max_depth_hits": sum(int((block["expansions"] == 8).sum())
                                              for _, first, block in left if first)}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("left_backup", type=Path)
    parser.add_argument("right_backup", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(*(p.resolve() for p in (args.fixture, args.left_backup, args.right_backup, args.output)))
