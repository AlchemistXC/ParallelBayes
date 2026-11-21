"""Reconcile an append-only qualification attempt ledger with the 880-task plan.

This checks accounting and artifact integrity, not numerical or scientific
acceptance. Missing tasks and failed attempts remain visible in the report.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

from qualification_inventory import tasks


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(ledger, artifact_root):
    plan = tasks()
    by_id = {item["task_id"]: item for item in plan}
    attempts = defaultdict(list)
    artifact_root = artifact_root.resolve(strict=True)
    if not artifact_root.is_dir():
        raise ValueError("artifact root must be a directory")
    for line_number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank ledger line {line_number}")
        row = json.loads(line)
        if set(row) != {"task_id", "attempt", "status", "reason", "elapsed_seconds", "artifacts"}:
            raise ValueError(f"unexpected fields at line {line_number}")
        task_id = row["task_id"]
        if task_id not in by_id:
            raise ValueError(f"unknown task at line {line_number}")
        if type(row["attempt"]) is not int or row["attempt"] != len(attempts[task_id]) + 1:
            raise ValueError(f"attempt sequence differs at line {line_number}")
        if row["status"] not in {"completed", "failed"}:
            raise ValueError(f"nonterminal status at line {line_number}")
        if not isinstance(row["reason"], str) or (row["status"] == "failed" and not row["reason"].strip()):
            raise ValueError(f"missing failure reason at line {line_number}")
        seconds = row["elapsed_seconds"]
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError(f"invalid elapsed time at line {line_number}")
        artifacts = row["artifacts"]
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError(f"missing artifacts at line {line_number}")
        seen = set()
        for artifact in artifacts:
            if not isinstance(artifact, dict) or set(artifact) != {"path", "sha256"}:
                raise ValueError(f"invalid artifact entry at line {line_number}")
            relative = PurePosixPath(artifact["path"])
            if relative.is_absolute() or not relative.parts or ".." in relative.parts or "\\" in artifact["path"]:
                raise ValueError(f"unsafe artifact path at line {line_number}")
            path = (artifact_root / Path(*relative.parts)).resolve(strict=True)
            if not path.is_relative_to(artifact_root) or not path.is_file() or relative.as_posix() in seen:
                raise ValueError(f"invalid or duplicate artifact path at line {line_number}")
            seen.add(relative.as_posix())
            if file_hash(path) != artifact["sha256"]:
                raise ValueError(f"artifact checksum mismatch at line {line_number}")
        attempts[task_id].append(row)
    stages = {}
    for stage in dict.fromkeys(item["stage"] for item in plan):
        ids = [item["task_id"] for item in plan if item["stage"] == stage]
        first = Counter(attempts[task_id][0]["status"] for task_id in ids if attempts[task_id])
        stages[stage] = {"planned": len(ids), "attempted": sum(bool(attempts[x]) for x in ids),
                         "first_completed": first["completed"], "first_failed": first["failed"],
                         "not_started": sum(not attempts[x] for x in ids),
                         "total_attempts": sum(len(attempts[x]) for x in ids)}
    return {"identity": "prospective-first-use-v1", "scope": "accounting only; not a qualification pass",
            "planned": len(plan), "attempted": sum(bool(value) for value in attempts.values()),
            "not_started_task_ids": [x["task_id"] for x in plan if not attempts[x["task_id"]]],
            "total_attempts": sum(map(len, attempts.values())), "stages": stages,
            "ledger_sha256": file_hash(ledger),
            "plan_sha256": hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "first_failures": [{"task_id": x["task_id"], "reason": attempts[x["task_id"]][0]["reason"]}
                               for x in plan if attempts[x["task_id"]] and attempts[x["task_id"]][0]["status"] == "failed"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = audit(args.ledger, args.artifact_root)
    with args.output.open("x", encoding="utf-8") as target:
        json.dump(result, target, indent=2, allow_nan=False)
        target.write("\n")
