#!/usr/bin/env python3
"""Hash-bound NUTS failure description; no root-cause or reclassification rule.

Read the original bounded-transfer manifest and task table. A partial report
must explicitly state its missing tasks; the full report refuses missing files.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def review(delivery, manifest, manifest_sha256, tasks, output, partial=False):
    delivery, output = Path(delivery), Path(output)
    if output.exists():
        raise FileExistsError(output)
    manifest_data = Path(manifest).read_bytes()
    if digest(manifest_data) != manifest_sha256:
        raise ValueError("Transfer manifest checksum differs")
    members = json.loads(manifest_data)["files"]
    task_bytes = Path(tasks).read_bytes()
    planned = [r for r in csv.DictReader(task_bytes.decode().splitlines())
               if r["phase"] == "main" and r["workflow"] == "cpu-nuts-spawn_chains"]
    if len(planned) != 432 or len({r["id"] for r in planned}) != 432:
        raise ValueError("Expected all 432 frozen NUTS tasks")
    rows, pending, provenance = [], [], {}
    required = ("state.json", "completion.json", "job.json", "candidate.json", "ordinary-process.json")
    logs = ("ordinary-stderr.log", "stderr.log", "ordinary-stdout.log", "stdout.log")
    for task in planned:
        prefix = f"formal-runs/batch-{int(task['batch']):02d}/main/tasks/{task['id']}/attempt-0001/"
        names = required + logs
        available = all((delivery / (prefix + n)).is_file() or
                        (partial and n in logs and members[prefix+n]["bytes"] == 0) for n in names)
        if not available:
            pending.append(task["id"])
            continue
        record = {}
        for name in names:
            path = delivery / (prefix + name)
            expected = members[prefix + name]
            if not path.is_file():
                # Empty logs are not materialized until final component verify.
                # Their size below is explicitly a manifest declaration only.
                continue
            data = path.read_bytes()
            if len(data) != expected["bytes"] or digest(data) != expected["sha256"]:
                raise ValueError("Original task asset differs: " + prefix + name)
            provenance[prefix + name] = expected["sha256"]
            if name.endswith(".json"):
                record[name] = json.loads(data)
        state, job, candidate, process = (record[n] for n in
                                          ("state.json", "job.json", "candidate.json", "ordinary-process.json"))
        if record["completion.json"]["state_sha256"] != members[prefix+"state.json"]["sha256"]:
            raise ValueError("Terminal completion does not bind the original state")
        for key in ("id", "model", "workflow"):
            if state["task"][key] != task[key]:
                raise ValueError("Task identity differs")
        if state["outcome"] != task["outcome"] or state["task"]["budget"] != int(task["budget"]):
            raise ValueError("Task classification differs")
        limit = job["limits"]["job_commit_bytes"]
        final = state["job_final"]
        if final["active_processes"] != 0 or final["hard_job_commit_limit_bytes"] != limit:
            raise ValueError("Missing matching final owned-Job state")
        raw_peak = final.get("kernel_peak_job_commit_bytes")
        errors = candidate.get("worker_errors", {})
        error_types = sorted({e["error"].split(":", 1)[0] for e in errors.values()})
        rows.append(dict(id=task["id"], batch=int(task["batch"]), model=task["model"],
            replicate=int(task["replicate"]), budget=int(task["budget"]), outcome=state["outcome"],
            candidate_status=candidate["status"], ordinary_exit_code=process["return_code"],
            worker_results_returned=len(candidate.get("worker_records", [])),
            unresolved_futures=len(errors), error_types=";".join(error_types),
            job_limit_bytes=limit, raw_peak_job_counter_bytes=raw_peak,
            raw_counter_over_limit=None if raw_peak is None else raw_peak > limit,
            raw_counter_limit_ratio=None if raw_peak is None else raw_peak/limit,
            sampled_rss_peak_bytes=state.get("observed_rss_peak_bytes"),
            final_active_processes=final["active_processes"],
            ordinary_seconds=process["ordinary_process_wall_seconds"],
            stderr_declared_bytes=sum(members[prefix+n]["bytes"] for n in logs if "stderr" in n),
            all_log_files_materialized=all((delivery/(prefix+n)).is_file() for n in logs)))
    if pending and not partial:
        raise ValueError(f"Full failure review requires {len(pending)} further original tasks")
    groups = []
    for model, budget, outcome in sorted({(r["model"],r["budget"],r["outcome"]) for r in rows}):
        chosen = [r for r in rows if (r["model"],r["budget"],r["outcome"]) == (model,budget,outcome)]
        ratios = [r["raw_counter_limit_ratio"] for r in chosen if r["raw_counter_limit_ratio"] is not None]
        groups.append(dict(model=model,budget=budget,outcome=outcome,observed=len(chosen),
            raw_counter_ratio_range=[min(ratios),max(ratios)] if ratios else None,
            raw_counter_above_limit=sum(r["raw_counter_over_limit"] is True for r in chosen),
            worker_results_returned_counts=dict(Counter(r["worker_results_returned"] for r in chosen)),
            stderr_nonempty=sum(r["stderr_declared_bytes"] > 0 for r in chosen)))
    report = dict(schema="compact-nuts-failure-review-v1", complete=not pending, partial_mode=partial,
        manifest_sha256=manifest_sha256, task_display_table_sha256=digest(task_bytes),
        planned_nuts_tasks=432, inspected=len(rows), pending_task_ids=pending,
        outcome_counts=dict(Counter(r["outcome"] for r in rows)),groups=groups,
        valid_outputs_with_raw_counter_above_limit=sum(r["outcome"]=="valid" and r["raw_counter_over_limit"] is True for r in rows),
        root_cause="Not established by these records",
        interpretation=["BrokenProcessPool identifies failed futures, not the number or cause of worker crashes",
            "An ordinary parent exit code of zero is compatible with a recorded failed sampler result",
            "The raw kernel peak counter is not a certified maximum of successful memory commitments",
            "Counter/limit association does not prove OOM or justify changing frozen outcome categories",
            "Successful subsets are conditional results; missing chains are not pooled as complete fits"],
        source_assets_sha256=provenance,new_sampler_calls=0)
    output.mkdir(parents=True)
    with (output/"tasks.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ["id"],lineterminator="\n")
        writer.writeheader();writer.writerows(rows)
    (output/"SUMMARY.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("delivery","manifest","manifest-sha256","tasks","output"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--partial",action="store_true")
    result=review(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in result.items() if k not in
        ("source_assets_sha256","pending_task_ids","groups")},indent=2))
