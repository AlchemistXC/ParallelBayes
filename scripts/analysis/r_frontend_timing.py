#!/usr/bin/env python3
"""Freeze and run a finite installed-R usage-cost companion; no formal samples.

No imports of samplers at planning time. Output folders are append-only attempts;
recovery reuses terminal records and refuses to rerun interrupted attempts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "r-frontend-timing-v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def read(path):
    return json.loads(Path(path).read_text())


def dependency_snapshot(python):
    """Read package metadata without requiring pip in a uv-created environment."""
    code = """import importlib.metadata as m,json,sys
rows=[dict(name=d.metadata['Name'],version=d.version,root=str(d.locate_file('')),
           direct_url=d.read_text('direct_url.json')) for d in m.distributions()]
print(json.dumps(dict(python=sys.version,prefix=sys.prefix,base_prefix=sys.base_prefix,
      packages=sorted(rows,key=lambda r:(r['name'].lower(),r['root']))),sort_keys=True))
"""
    return json.loads(subprocess.check_output([str(python), "-I", "-c", code], text=True))


def tasks():
    result = []
    for block in range(4):
        for offset in range(4):
            workflow = (block + offset) % 4
            for audit in ((False, True) if (block + workflow) % 2 == 0 else (True, False)):
                result.append(dict(id=f"block-{block}-workflow-{workflow}-audit-{int(audit)}",
                                   block=block, workflow=workflow, audit=audit))
    return result


def freeze(inputs, output, rscript, python, r_library):
    inputs, output = Path(inputs).resolve(), Path(output).resolve()
    r_library = Path(r_library).resolve()
    package = r_library / "parallelbayes"
    # Keep the venv's executable path: resolving its symlink would bypass it.
    python = Path(python).absolute()
    for required in (python, Path(rscript), package / "DESCRIPTION", inputs / "input-manifest.json"):
        if not required.is_file():
            raise ValueError("Missing required input: " + str(required))
    manifest = read(inputs / "input-manifest.json")
    if manifest.get("schema") != "installed-custom-target-input-v1":
        raise ValueError("Wrong input identity")
    if set(manifest["files"]) != {"model.json", "inputs.npz"}:
        raise ValueError("Unexpected input members")
    for name, digest in manifest["files"].items():
        if sha(inputs / name) != digest:
            raise ValueError("Corrupt actual input: " + name)
    source_names = ["scripts/analysis/r_frontend_timing.py", "scripts/analysis/r_frontend_timing.R",
                    "scripts/analysis/r_frontend_helper.py", "examples/installed_custom_target.py",
                    "scripts/analysis/r_frontend_verify.py",
                    "docs/R-FRONTEND-TIMING-PROTOCOL.md"]
    source = {name: sha(ROOT / name) for name in source_names}
    installed = {str(p.relative_to(package)): sha(p) for p in sorted(package.rglob("*"))
                 if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    numerical = {str(p.relative_to(package / "python")): sha(p)
                 for p in sorted((package / "python" / "parallelbayes").rglob("*.py"))}
    if not numerical:
        raise ValueError("No installed numerical modules")
    for name, digest in numerical.items():
        if sha(ROOT / "r-package" / "inst" / "python" / name) != digest:
            raise ValueError("Installed numerical source differs: " + name)
    dependencies = dependency_snapshot(python)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(inputs, output / "inputs", ignore=shutil.ignore_patterns("__pycache__"))
    write(output / "python-environment.json", dependencies)
    plan = dict(schema=SCHEMA, identity="mac-r-frontend-timing-v1", root=str(ROOT),
                source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                source_sha256=source, installed_package_sha256=installed,
                inputs_sha256={p.name: sha(p) for p in sorted((output / "inputs").iterdir()) if p.is_file()},
                rscript=str(Path(rscript).absolute()), python=str(python), r_library=str(r_library),
                package_path=str(package), python_environment_sha256=sha(output / "python-environment.json"),
                platform=platform.platform(), tasks=tasks(), planned_processes=32,
                maximum_sampler_calls=64, formal_repetitions_added=0,
                inference_claim="None: one reused four-chain input, technical cost repetitions only",
                failure_policy="Retain all; do not rerun failed/interrupted measurements")
    write(output / "protocol.json", plan)
    (output / "protocol.sha256").write_text(sha(output / "protocol.json") + "\n")
    return plan


def verify_plan(root):
    root = Path(root)
    if sha(root / "protocol.json") != (root / "protocol.sha256").read_text().strip():
        raise ValueError("Frozen protocol changed")
    plan = read(root / "protocol.json")
    if plan["schema"] != SCHEMA or plan["tasks"] != tasks():
        raise ValueError("Unknown task design")
    for base, members in ((ROOT, plan["source_sha256"]), (root / "inputs", plan["inputs_sha256"]),
                          (Path(plan["package_path"]), plan["installed_package_sha256"])):
        for name, expected in members.items():
            if sha(base / name) != expected:
                raise ValueError("Frozen source/input/installation changed: " + str(base / name))
    if sha(root / "python-environment.json") != plan["python_environment_sha256"]:
        raise ValueError("Dependency record changed")
    observed = dependency_snapshot(plan["python"])
    if observed != read(root / "python-environment.json"):
        raise ValueError("Python dependencies changed")
    return plan


def capture(command, output, env):
    """Measure launch-to-notification without mixing later raw archival into it."""
    started = time.perf_counter()
    markers = []
    marker_error = None
    with (output / "process.log").open("x") as log:
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, bufsize=1, env=env, cwd=output)
        for line in child.stdout:
            observed = time.perf_counter() - started
            log.write(line)
            log.flush()
            if line.startswith("PB_R_READY "):
                parts = line.strip().split()
                if len(parts) != 3 or parts[1] not in ("first", "subsequent"):
                    marker_error = "Malformed readiness marker"
                    continue
                if parts[1] in {m["call"] for m in markers}:
                    marker_error = "Repeated readiness marker"
                    continue
                markers.append(dict(call=parts[1], status=parts[2],
                                    seconds_from_process_launch=observed))
        code = child.wait()
    if marker_error is not None:
        raise ValueError(marker_error)
    return dict(returncode=code, process_wall_seconds=time.perf_counter() - started,
                markers=markers)


def run(root, quiet_record):
    root = Path(root).resolve()
    plan = verify_plan(root)
    quiet = read(quiet_record)
    if quiet.get("receiver_active") is not False or quiet.get("reconstruction_active") is not False:
        raise ValueError("Wait for intake/reconstruction to end before timing")
    if not quiet.get("actual_handle_observations"):
        raise ValueError("Quiescence requires actual process/handle observations")
    if not (root / "quiet-record.json").exists():
        shutil.copyfile(quiet_record, root / "quiet-record.json")
    elif sha(root / "quiet-record.json") != sha(quiet_record):
        raise ValueError("A recovery run must retain the original quiet record")
    env = dict(os.environ, R_LIBS_USER=plan["r_library"], RETICULATE_PYTHON=plan["python"],
               PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    summary = dict(schema=SCHEMA, new_processes=0, reused_processes=0, outcomes=[])
    for task in plan["tasks"]:
        output = root / "attempts" / task["id"]
        finished = output / "process.json"
        if finished.exists():
            existing = read(finished)
            for name, digest in existing["files_sha256"].items():
                if sha(output / name) != digest:
                    raise ValueError("Terminal evidence changed")
            summary["reused_processes"] += 1
            summary["outcomes"].append(existing)
            continue
        if output.exists():
            raise ValueError("Interrupted attempt preserved; do not retry: " + str(output))
        if shutil.disk_usage(root).free < 1024**3:
            raise OSError("Less than 1 GiB free; preserve remaining pending tasks")
        output.mkdir(parents=True)
        command = [plan["rscript"], "--vanilla", str(ROOT / "scripts/analysis/r_frontend_timing.R"),
                   str(root / "inputs"), str(ROOT / "examples/installed_custom_target.py"),
                   str(task["workflow"]), str(task["audit"]).lower(), str(output), plan["package_path"]]
        write(output / "started.json", dict(task=task, command=command, epoch=time.time()))
        result = dict(task=task, **capture(command, output, env))
        result["files_sha256"] = {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()}
        write(finished, result)
        summary["outcomes"].append(result)
        summary["new_processes"] += 1
        write(root / "RUN-SUMMARY.json", summary)
    write(root / "RUN-SUMMARY.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("freeze")
    for name in ("inputs", "output", "rscript", "python", "r-library"):
        p.add_argument("--" + name, required=True)
    p = sub.add_parser("run")
    p.add_argument("--root", required=True)
    p.add_argument("--quiet-record", required=True)
    args = vars(parser.parse_args())
    fn = freeze if args.pop("command") == "freeze" else run
    report = fn(**args)
    print(json.dumps({k: v for k, v in report.items() if k not in ("outcomes", "installed_package_sha256")}, indent=2))
