"""Run the small frozen-input R diagnostic fixture on native Windows or Mac."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(case, output, rscript):
    if output.exists():
        raise FileExistsError("Choose a new attempt output directory")
    if case == output or case in output.parents:
        raise ValueError("Do not write into the frozen fixture")
    meta = json.loads((case / "case.json").read_text())
    binary = case / meta["fixture_file"]
    if sha(binary) != meta["fixture_sha256"]:
        raise ValueError("Fixture checksum mismatch")
    script = Path(__file__).with_name("rhat_case.R")
    process = subprocess.run([rscript, "--vanilla", str(script), str(case), str(output)],
                             capture_output=True, text=True)
    output.mkdir(parents=True, exist_ok=True)
    (output / "R.log").write_text(process.stdout + process.stderr)
    receipt = dict(schema_version=1, script_sha256=sha(script), wrapper_sha256=sha(Path(__file__)),
                   fixture_sha256=sha(binary), R_exit_code=process.returncode)
    receipt["binary_roundtrip_identical"] = ((output / "roundtrip-f64le.bin").exists() and
        sha(output / "roundtrip-f64le.bin") == sha(binary))
    if (output / "result.json").exists():
        result = json.loads((output / "result.json").read_text())
        receipt["diagnostic_status"] = result["status"]
    receipt["passed"] = process.returncode == 0 and receipt["binary_roundtrip_identical"] and receipt.get("diagnostic_status") == "checks_passed"
    receipt["outputs"] = {p.name: sha(p) for p in output.iterdir() if p.is_file()}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rscript", default="Rscript")
    args = parser.parse_args()
    sys.exit(run(args.case.resolve(), args.output.resolve(), args.rscript))
