"""Launch the first ten sealed reference chains with bounded Mac concurrency."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

from formal_run import verify_freeze
from checkpoint import unpack

ROOT = Path(__file__).resolve().parents[2]
RUNNER = Path(__file__).with_name("formal_run.py")
DIAGNOSTICS = ROOT/"scripts/analysis/prospective_reference_diagnostics.py"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def run(model, inputs, seal, output, rscript, resume=False):
    # Validate the frozen study before creating any output directory.
    verify_freeze(seal, inputs, model)
    paths = [output/f"chain-{chain:02d}.sqlite" for chain in range(1, 11)]
    metadata = {"model":model, "retained_per_chain":1000, "chains":10,
                "seal_sha256":digest(seal), "input_manifest_sha256":digest(inputs/"manifest.json"),
                "runner_sha256":digest(RUNNER), "concurrency":2 if model == "logistic" else 1,
                "rscript":str(rscript.resolve())}
    if resume:
        recorded = json.loads((output/"cohort.json").read_text())
        if recorded != metadata:
            raise ValueError("cohort identity differs")
        if (output/"cohort-failed.json").exists() or any(output.glob("cohort-failed-*.json")):
            raise ValueError("cohort has failed calls requiring classification")
        for index, path in enumerate(paths, start=1):
            log = output/f"chain-{index:02d}.json"
            if not path.is_file() or not log.is_file():
                raise ValueError(f"chain {index} has unknown terminal state")
            record = json.loads(log.read_text())
            if record.get("exit_code") != 0:
                raise ValueError(f"chain {index} failed; classify before recovery")
            # Prove the committed prefix is complete before invoking the
            # idempotent runner. A missing block must never trigger new draws.
            with sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True) as database:
                blocks = database.execute(
                    "SELECT last_step, first_step, payload, checksum FROM blocks "
                    "WHERE last_step <= 1000 ORDER BY last_step").fetchall()
            expected = [(0,0)] + [(end,end-99) for end in range(100,1001,100)]
            if [(end,first) for end,first,_,_ in blocks] != expected:
                raise ValueError(f"chain {index} committed prefix is incomplete")
            for _,_,payload,checksum in blocks:
                unpack(payload,checksum)
        previous = output/"first-checkpoint.json"
        if previous.exists():
            checkpoint = json.loads(previous.read_text())
            if digest(output/"diagnostics/receipt.json") != checkpoint["diagnostics_sha256"]:
                raise ValueError("prior diagnostic receipt mismatch")
    else:
        output.mkdir()
        (output/"cohort.json").write_text(json.dumps(metadata,indent=2)+"\n")

    def chain_call(index):
        command = [sys.executable, "-B", str(RUNNER), model, str(inputs), str(seal),
                   str(paths[index-1]), "--chain", str(index), "--steps", "1000"]
        log = (output/f"chain-{index:02d}.resume-{uuid.uuid4().hex}.json" if resume
               else output/f"chain-{index:02d}.json")
        completed = subprocess.run(command,text=True,capture_output=True)
        with log.open("x") as file:
            json.dump({"command":command,"exit_code":completed.returncode,
                       "stdout":completed.stdout,"stderr":completed.stderr},file,indent=2)
        if resume and completed.returncode == 0:
            try:
                result = json.loads(completed.stdout)
                if result.get("new_steps") != 0 or result.get("last_step", 0) < 1000:
                    return index, -1
            except (ValueError, AttributeError, TypeError):
                return index, -1
        return index, completed.returncode

    completed = []
    # Wait for every launched process. Failed chain records remain in place;
    # diagnostic analysis occurs only when all ten complete.
    with ThreadPoolExecutor(max_workers=metadata["concurrency"]) as pool:
        pending = {pool.submit(chain_call,i) for i in (1,2) if i <= metadata["concurrency"]}
        next_chain = metadata["concurrency"]+1
        failure = False
        while pending:
            current = next(as_completed(pending))
            pending.remove(current)
            chain, code = current.result()
            completed.append({"chain":chain,"exit_code":code})
            failure |= code != 0
            if not failure and next_chain <= 10:
                pending.add(pool.submit(chain_call,next_chain))
                next_chain += 1
    if any(item["exit_code"] != 0 for item in completed) or len(completed) != 10:
        failure_path = output/("cohort-failed-"+uuid.uuid4().hex+".json" if resume else "cohort-failed.json")
        failure_path.write_text(json.dumps({"completed":completed},indent=2)+"\n")
        raise RuntimeError("reference cohort incomplete; inspect recorded chains before recovery")
    if resume and (output/"first-checkpoint.json").exists():
        print(json.dumps({"scope":"reference first checkpoint read-only recovery",
                          "model":model,"all_chains_complete":True,"new_sampling_steps":0,
                          "diagnostics_sha256":digest(output/"diagnostics/receipt.json")}))
        return
    if resume and (output/"diagnostics").exists():
        raise ValueError("diagnostics directory is incomplete; preserve and classify before recovery")
    command = [sys.executable,"-B",str(DIAGNOSTICS),str(output/"diagnostics"),
               *map(str,paths),"--steps","1000","--rscript",str(rscript)]
    result = subprocess.run(command,text=True,capture_output=True)
    (output/"diagnostic-process.json").write_text(json.dumps(
        {"command":command,"exit_code":result.returncode,"stdout":result.stdout,"stderr":result.stderr},
        indent=2)+"\n")
    if result.returncode:
        raise RuntimeError("reference diagnostics failed")
    receipt = json.loads((output/"diagnostics/receipt.json").read_text())
    result = {"scope":"reference first checkpoint", "model":model, "seal_sha256":digest(seal),
              "all_chains_complete":True, "diagnostics_pass":receipt["diagnostics_pass"],
              "quantities":receipt["quantities"],"diagnostics_sha256":digest(output/"diagnostics/receipt.json")}
    (output/"first-checkpoint.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=("logistic","ode"))
    parser.add_argument("inputs", type=Path)
    parser.add_argument("seal", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rscript", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args=parser.parse_args()
    run(args.model,args.inputs,args.seal,args.output,args.rscript,args.resume)
