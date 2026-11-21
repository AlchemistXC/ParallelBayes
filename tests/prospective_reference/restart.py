"""Prove checkpoint continuity with independent OS processes and frozen PRNG keys."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/prospective_reference/run.py"
sys.path.insert(0, str(RUNNER.parent))
from checkpoint import unpack

KEYS = ROOT / "docs/prospective-first-use-v1/mac-environment/rng-fixture-draft/vectors.json"
KEYS_SHA256 = "df1b52b874963d173ff2a67836ea28cf8be500f555f7c0b5e47958bae0811edf"


def blocks(path):
    with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
        return [(n, first, unpack(blob, checksum)) for n, first, blob, checksum in connection.execute(
            "SELECT last_step, first_step, payload, checksum FROM blocks ORDER BY last_step")]


def same(left, right):
    assert len(left) == len(right)
    for (end, begin, a), (other_end, other_begin, b) in zip(left, right, strict=True):
        assert (end, begin, set(a)) == (other_end, other_begin, set(b))
        for name in a:
            assert a[name].shape == b[name].shape and a[name].dtype == b[name].dtype
            assert a[name].tobytes() == b[name].tobytes(), (begin, end, name)


def main(work, model):
    work.mkdir()
    baseline, split = work/"continuous.sqlite", work/"split.sqlite"
    log = work/"processes.jsonl"

    def run(path, steps, *extra, expected=0):
        command = [sys.executable, "-B", str(RUNNER), model, str(path), "--steps", str(steps), *extra]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        with log.open("a") as file:
            file.write(json.dumps(dict(code=process.returncode, pid=process.pid, command=command,
                                       stdout=stdout, stderr=stderr))+"\n")
        if process.returncode != expected:
            raise RuntimeError(f"unexpected exit {process.returncode}, see {log}: {stderr}")
        return json.loads(stdout) if expected == 0 else stderr

    first = run(split, 100)
    assert first["new_steps"] == 100 and first["warmup"]
    before = blocks(split)
    assert sha256(KEYS.read_bytes()).hexdigest() == KEYS_SHA256
    row = next(r for r in json.loads(KEYS.read_text())["rows"] if r["chain"] == 1
               and r["model"] == ("ode" if model == "ode-fast" else model) and r["phase"] == "sampling")
    np.testing.assert_array_equal(before[0][2]["next_key"], row["initial_key"])
    np.testing.assert_array_equal(before[-1][2]["next_key"], row["transitions"][1]["next_carry"])
    run(split, 300, "--interrupt-before-commit", "200", expected=75)
    same(before, blocks(split))
    assert "identity mismatch" in run(split, 300, "--chain", "2", expected=1)
    same(before, blocks(split))
    short = run(split, 300)
    assert short["new_steps"] == 200 and not short["warmup"]
    assert run(split, 300)["new_steps"] == 0
    checkpoint = run(split, 1000)
    assert checkpoint["new_steps"] == 700 and not checkpoint["warmup"]
    extended = run(split, 2000)
    assert extended["new_steps"] == 1000 and not extended["warmup"]
    continuous = run(baseline, 2000)
    assert continuous["new_steps"] == 2000 and continuous["warmup"]
    resumed, uninterrupted = blocks(split), blocks(baseline)
    same(resumed, uninterrupted)
    assert [(last, first) for last, first, _ in resumed] == [(0, 0)] + [
        (last, last-99) for last in range(100, 2001, 100)]
    consumed = np.concatenate([r["consumed"] for _, first, r in resumed if first > 0])
    for vector in row["transitions"]:
        np.testing.assert_array_equal(consumed[vector["step"]-1], vector["consumed"])
    diagnostic_counts = {
        "warmup_divergences": int(resumed[0][2]["warmup_divergent"].sum()),
        "retained_divergences": sum(int(r["divergent"].sum()) for _, first, r in resumed if first > 0),
        "retained_max_depth_hits": sum(int(np.sum(r["expansions"] == 8)) for _, first, r in resumed if first > 0),
    }
    (work/"receipt.json").write_text(json.dumps(dict(
        model=model, steps=2000, position_and_diagnostics_byte_identical=True,
        rollback_at_200=True, wrong_chain_rejected=True, idempotency=True,
        resume_warmup_steps=0, frozen_key_vectors_sha256=KEYS_SHA256,
        diagnostics=diagnostic_counts, executions=[first, short, checkpoint, extended, continuous],
        database_sha256={str(path.name): sha256(path.read_bytes()).hexdigest() for path in (baseline, split)},
    ), indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=["logistic", "ode-fast"])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.output.resolve(), args.model)
