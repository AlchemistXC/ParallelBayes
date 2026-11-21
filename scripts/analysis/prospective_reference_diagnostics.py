"""Audit ten complete synthetic chains using posterior and chain-mean MCSE."""
import argparse
from contextlib import closing
import csv
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_reference"))
from checkpoint import unpack


def finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def read(path, steps):
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as db:
        identity = json.loads(db.execute("SELECT value FROM identity").fetchone()[0])
        chunks = db.execute("SELECT last_step, first_step, payload, checksum FROM blocks "
                            "WHERE last_step <= ? ORDER BY last_step", (steps,))
        expected = 0
        saved = []
        for end, first, blob, checksum in chunks:
            if first != expected or not (first <= end <= steps):
                raise ValueError(f"unexpected block boundaries in {path}")
            record = unpack(blob, checksum)
            if first:
                saved.append(record)
            else:
                if end != 0:
                    raise ValueError("missing warmup boundary")
            expected = end + 1
    if expected != steps+1:
        raise ValueError(f"{path} does not reach step {steps}")
    return identity, {name: np.concatenate([block[name] for block in saved])
                      for name in ("draws", "functions", "energy", "divergent", "expansions")}


def assess(paths, output, steps, rscript):
    chains = [read(path, steps) for path in paths]
    ids = [identity["chain"] for identity, _ in chains]
    if sorted(ids) != list(range(1, 11)):
        raise ValueError("expected each chain identity 1–10 once")
    identity, _ = chains[0]
    # Initial positions may vary by chain. All target and runtime identities must match.
    shared = {k: v for k, v in identity.items() if k not in {"chain", "initial_sha256"}}
    if any({k: v for k, v in ident.items() if k not in {"chain", "initial_sha256"}} != shared
           for ident, _ in chains):
        raise ValueError("chains differ in model or runtime identity")
    functions = ["mu", "tau", "probability"] if identity["model"] == "logistic" else ["alpha", "hare_20"]
    data = np.stack([np.column_stack((draw["draws"], draw["functions"])) for _, draw in chains], axis=1)
    names = [f"q{i}" for i in range(data.shape[-1]-len(functions))] + functions
    output.mkdir()
    (output/"draws.f64le").write_bytes(np.asarray(data, dtype="<f8").tobytes(order="F"))
    (output/"variables.txt").write_text("\n".join(names)+"\n")
    cmd = [rscript, "--vanilla", str(Path(__file__).with_suffix(".R")), str(output/"draws.f64le"),
           str(steps), str(output/"variables.txt"), str(output/"posterior.tsv")]
    runtime = subprocess.check_output(cmd, text=True)
    with (output/"posterior.tsv").open() as file:
        summary = {row["variable"]: row for row in csv.DictReader(file, delimiter="\t")}
    energy = []
    for chain_id, (_, draw) in zip(ids, chains, strict=True):
        variance = np.var(draw["energy"])
        bfmi = float(np.mean(np.diff(draw["energy"])**2)/variance) if variance > 0 else None
        energy.append(dict(chain=chain_id, bfmi=bfmi, divergent=int(draw["divergent"].sum()),
                           max_depth_hits=int(np.sum(draw["expansions"] == 8))))
    rhats = [finite_number(row["rhat"]) for row in summary.values()]
    diagnostics_pass = all(value is not None and value < 1.01 for value in rhats)
    diagnostics_pass &= all(row["divergent"] == 0 and row["bfmi"] is not None and row["bfmi"] >= .30
                            for row in energy)
    estimates = {}
    for f in functions:
        row = summary[f]
        chain_mean = data[:, :, names.index(f)].mean(axis=0)
        between = float(np.std(chain_mean, ddof=1)/np.sqrt(10))
        within = finite_number(row["mcse"])
        sd = finite_number(row["sd"])
        mean = finite_number(row["mean"])
        combined = None if within is None else max(within, between)
        ratio = combined/sd if combined is not None and sd is not None and sd > 0 else None
        precision_pass = ratio is not None and ratio <= .02 and (f != "probability" or combined <= .001)
        estimates[f] = dict(mean=mean, posterior_sd=sd, within_mcse=within, between_mcse=between,
                            mcse=combined, relative_mcse=ratio, precision_pass=precision_pass)
    result = dict(scope=identity["scope"], model=identity["model"], retained_per_chain=steps,
                  r=runtime.strip(), command=cmd, diagnostics_pass=diagnostics_pass,
                  chain_diagnostics=energy, quantities=estimates)
    (output/"receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("databases", type=Path, nargs=10)
    parser.add_argument("--steps", type=int, choices=[1000, 2000, 4000, 8000], required=True)
    parser.add_argument("--rscript", default="Rscript")
    args = parser.parse_args()
    print(json.dumps(assess(args.databases, args.output, args.steps, args.rscript)))
