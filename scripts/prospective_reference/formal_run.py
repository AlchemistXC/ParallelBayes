"""Run a sealed formal reference chain after independently verified preflight."""
import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

os.environ["JAX_PLATFORMS"] = "cpu"
os.environ["JAX_ENABLE_X64"] = "true"

import blackjax
from blackjax.mcmc.hmc import HMCState
import diffrax
import jax
import jax.numpy as jnp
import numpy as np
import scipy

from checkpoint import Checkpoint
from models import Logistic, ODE
from run import phase_key, sampler, warmup

jax.config.update("jax_threefry_partitionable", True)
ROOT = Path(__file__).resolve().parents[2]
REAL_CANDIDATE_SCOPE = "candidate, not yet frozen or authorized for formal sampling"
SYNTHETIC_SCOPES = {"synthetic test fixture", "SYNTHETIC TEST ONLY", "SYNTHETIC TEST ONLY; no formal data"}


def reference_scope(manifest):
    scope = manifest.get("scope")
    if scope == REAL_CANDIDATE_SCOPE:
        return "formal"
    if scope in SYNTHETIC_SCOPES:
        return "synthetic_test"
    raise ValueError("unknown reference input scope")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def checked_json(path, expected):
    if digest(path) != expected:
        raise ValueError(f"hash mismatch: {path}")
    return json.loads(path.read_text())


def check_real_preflight(report, manifest_hash, manifest, model_name):
    if (report.get("scope") != "candidate-only preflight" or report.get("formal_sampling_started") is not False
            or report.get("inputs_manifest_sha256") != manifest_hash
            or report.get("data_sha256") != manifest["data_sha256"]
            or report.get("initials_sha256") != manifest["initials_sha256"]):
        raise ValueError("real candidate preflight identity differs")
    item = report.get("checks", {}).get(model_name, {})
    rows = item.get("rows", [])
    if (item.get("passed") is not True or not isinstance(rows,list) or len(rows) != 10
            or any(not isinstance(row,dict) or type(row.get("chain")) is not int for row in rows)
            or sorted(row.get("chain") for row in rows) != list(range(1,11))):
        raise ValueError("real candidate preflight chains incomplete")
    for row in rows:
        for key,limit in (("density_delta_error", 1e-8 if model_name == "logistic" else 1e-5),
                          ("gradient_max_ratio",1.)):
            value=row.get(key)
            if (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)
                    or value<0 or value>limit):
                raise ValueError("real candidate preflight numeric threshold failed")
        if row.get("finite") is not True:
            raise ValueError("real candidate preflight is nonfinite")


def verify_freeze(seal_path, inputs, model_name):
    """Require explicit study approval and bind every dependency by hash."""
    seal = json.loads(seal_path.read_text())
    required = {"identity", "status", "study_protocol", "model_source", "runner_source",
                "checkpoint_source", "engine_source", "cohort_source", "extension_source", "diagnostics_source",
                "diagnostics_r_source", "environment_lock", "candidate_manifest",
                "preflight", "windows_qualification", "capacity"}
    optional = {"ode_points", "restart_logistic", "restart_ode", "candidate_audit", "fresh_preflight",
                "qualification_ledger", "qualification_accounting", "qualification_plan_source",
                "qualification_auditor_source"}
    model_fields = {"restart_logistic"} if model_name == "logistic" else {"ode_points", "restart_ode"}
    if (not required.issubset(seal) or not set(seal).issubset(required | optional)
            or not model_fields.issubset(seal)
            or seal["identity"] != "prospective-first-use-v1" or seal["status"] != "frozen"):
        raise ValueError("missing complete frozen study identity")
    for key, path in [
        ("study_protocol", ROOT / "docs/prospective-first-use-v1/DECISIONS.md"),
        ("model_source", ROOT / "scripts/prospective_reference/models.py"),
        ("runner_source", Path(__file__)),
        ("checkpoint_source", ROOT / "scripts/prospective_reference/checkpoint.py"),
        ("engine_source", ROOT / "scripts/prospective_reference/run.py"),
        ("cohort_source", ROOT / "scripts/prospective_reference/cohort.py"),
        ("extension_source", ROOT / "scripts/prospective_reference/extend_cohort.py"),
        ("diagnostics_source", ROOT / "scripts/analysis/prospective_reference_diagnostics.py"),
        ("diagnostics_r_source", ROOT / "scripts/analysis/prospective_reference_diagnostics.R"),
        ("environment_lock", ROOT / "docs/prospective-first-use-v1/mac-environment/requirements-arm64.lock"),
    ]:
        if digest(path) != seal[key]:
            raise ValueError(f"frozen {key} differs")
    manifest = checked_json(inputs / "manifest.json", seal["candidate_manifest"])
    scope = reference_scope(manifest)
    preflight = checked_json(inputs / "preflight.json", seal["preflight"])
    if (preflight["inputs_manifest_sha256"] != seal["candidate_manifest"]
            or preflight["checks"][model_name]["passed"] is not True):
        raise ValueError("model preflight differs or failed")
    if scope == "formal" and (preflight.get("scope") != "candidate-only preflight"
                              or preflight.get("formal_sampling_started") is not False):
        raise ValueError("real candidate requires actual candidate preflight")
    if scope == "formal":
        check_real_preflight(preflight,seal["candidate_manifest"],manifest,model_name)
    for key, filename in [("data_sha256", "data.npz"), ("initials_sha256", "initials.npz")]:
        if digest(inputs / filename) != manifest[key] or preflight[key] != manifest[key]:
            raise ValueError(f"input {key} differs")
    if model_name == "ode":
        points = checked_json(inputs / "ode-points.json", seal["ode_points"])
        if points.get("status") != "passed" or points.get("manifest_sha256") != seal["candidate_manifest"]:
            raise ValueError("candidate ODE fixed-point validation did not pass")
        if scope == "formal" and points.get("scope") != "candidate fixed-point validation, independent SciPy sensitivity oracle":
            raise ValueError("real candidate requires actual ODE fixed-point validation")
    for key in (("restart_logistic",) if model_name == "logistic" else ("restart_ode",)):
        entry = seal[key]
        receipt = checked_json(seal_path.parent / entry["file"], entry["sha256"])
        expected = "logistic" if key == "restart_logistic" else "ode-fast"
        if (receipt.get("model") != expected or receipt.get("steps") != 2000
                or not all(receipt.get(field) is True for field in
                           ("position_and_diagnostics_byte_identical", "rollback_at_200",
                            "wrong_chain_rejected", "idempotency"))):
            raise ValueError(f"{key} not passed")
        if scope == "formal" and any(word in str(receipt.get("scope", "")).lower()
                                     for word in ("mock", "synthetic", "test")):
            raise ValueError(f"{key} is marked as mock evidence")
    # The freeze references concrete external receipts. Their hashes, status and
    # study identity are checked on every invocation.
    for key in ("windows_qualification", "capacity"):
        entry = seal[key]
        receipt = checked_json(seal_path.parent / entry["file"], entry["sha256"])
        if receipt.get("status") != "passed" or receipt.get("identity") != seal["identity"]:
            raise ValueError(f"{key} not passed")
        expected_scope = {"windows_qualification":"prospective_windows_qualification",
                          "capacity":"prospective_capacity_budget"}[key]
        if scope == "formal" and (receipt.get("evidence_kind") != "actual"
                                  or receipt.get("scope") != expected_scope):
            raise ValueError(f"{key} must be explicitly identified as actual study evidence")
        if key == "windows_qualification" and (receipt.get("planned") != 880 or
                                                  receipt.get("accounted") != 880):
            raise ValueError("Windows qualification inventory incomplete")
        if key == "windows_qualification":
            qualification_receipt=receipt
        if key == "capacity":
            resources = receipt.get("resources", {})
            if set(resources) != {"windows_hours", "windows_disk", "mac_disk", "archive"}:
                raise ValueError("incomplete resource budget")
            if any(not (math.isfinite(item["available"]) and item["available"] > 0
                        and math.isfinite(item["conservative"])
                        and 0 <= item["conservative"] <= .8 * item["available"])
                   for item in resources.values()):
                raise ValueError("resource capacity exceeded")
    if scope == "formal":
        if not {"candidate_audit","fresh_preflight"}.issubset(seal):
            raise ValueError("real candidate audit and fresh preflight are required")
        entry=seal["candidate_audit"]
        candidate_audit=checked_json(seal_path.parent/entry["file"],entry["sha256"])
        fresh=seal["fresh_preflight"]
        fresh_report=checked_json(seal_path.parent/fresh["file"],fresh["sha256"])
        check_real_preflight(fresh_report,seal["candidate_manifest"],manifest,model_name)
        prior_reports=candidate_audit.get("preflights",[])
        model_strata=candidate_audit.get("strata",{}).get(model_name,{})
        audit_models=candidate_audit.get("models")
        archive_hash=candidate_audit.get("archive_sha256")
        if (candidate_audit.get("scope")!="candidate audit only; no freeze or posterior sampling"
                or candidate_audit.get("status")!="passed" or audit_models not in ([model_name],["logistic","ode"])
                or candidate_audit.get("audit_source_sha256")!=digest(ROOT/"scripts/prospective_reference/audit_candidate.py")
                or candidate_audit.get("manifest_sha256")!=seal["candidate_manifest"]
                or candidate_audit.get("data_sha256")!=manifest["data_sha256"]
                or candidate_audit.get("initials_sha256")!=manifest["initials_sha256"]
                or candidate_audit.get("prior_identity_verified") is not True
                or candidate_audit.get("actual_data_and_archive_bytes_match") is not True
                or candidate_audit.get("formal_sampling_started") is not False
                or not isinstance(archive_hash,str) or len(archive_hash)!=64
                or any(c not in "0123456789abcdef" for c in archive_hash)
                or model_strata!={"chains":10,"coordinates":130 if model_name=="logistic" else 8,
                                  "candidates_per_chain":4,"distinct_initials":True}
                or not isinstance(prior_reports,list) or len(prior_reports)!=2
                or any(not isinstance(row,dict) for row in prior_reports)
                or prior_reports[0].get("sha256")!=seal["preflight"]
                or prior_reports[1].get("sha256")!=fresh["sha256"]
                or prior_reports[0].get("path")==prior_reports[1].get("path")):
            raise ValueError("candidate audit identity or coverage differs")
        if model_name=="ode" and (candidate_audit.get("ode_fixed_points")!=21
                                  or candidate_audit.get("ode_fixed_points_sha256")!=seal["ode_points"]
                                  or candidate_audit.get("ode_source_sha256")!=manifest.get("source_sha256")):
            raise ValueError("candidate audit ODE fixed-point coverage differs")
        qualification_fields={"qualification_ledger","qualification_accounting",
                              "qualification_plan_source","qualification_auditor_source"}
        if not qualification_fields.issubset(seal):
            raise ValueError("qualification ledger and verified accounting are required")
        for key,path in (("qualification_plan_source",ROOT/"scripts/prospective_plan/qualification_inventory.py"),
                         ("qualification_auditor_source",ROOT/"scripts/prospective_plan/audit_qualification.py")):
            if digest(path)!=seal[key]:raise ValueError(f"frozen {key} differs")
        ledger=seal["qualification_ledger"]
        if digest(seal_path.parent/ledger["file"])!=ledger["sha256"]:
            raise ValueError("qualification ledger hash mismatch")
        account_entry=seal["qualification_accounting"]
        account=checked_json(seal_path.parent/account_entry["file"],account_entry["sha256"])
        sys.path.insert(0,str(ROOT/"scripts/prospective_plan"))
        from qualification_inventory import tasks
        plan_hash=sha256(json.dumps(tasks(),sort_keys=True,separators=(',',':')).encode()).hexdigest()
        expected_stages={"gaussian_corners":384,"gaussian_intermediate":144,"logistic_proxy":48,
                         "ode_1024":160,"ode_4096":72,"longest":72}
        stages=account.get("stages",{})
        if (account.get("identity")!=seal["identity"] or account.get("scope")!="accounting only; not a qualification pass"
                or account.get("planned")!=880 or account.get("attempted")!=880
                or account.get("not_started_task_ids")!=[] or account.get("ledger_sha256")!=ledger["sha256"]
                or qualification_receipt.get("ledger_sha256")!=ledger["sha256"] or account.get("plan_sha256")!=plan_hash
                or not isinstance(stages,dict) or set(stages)!=set(expected_stages)):
            raise ValueError("qualification accounting incomplete or identity differs")
        for stage,planned in expected_stages.items():
            row=stages[stage]
            if (not isinstance(row,dict) or row.get("planned")!=planned or row.get("attempted")!=planned
                    or type(row.get("not_started")) is not int or row["not_started"]!=0
                    or type(row.get("first_completed")) is not int
                    or type(row.get("first_failed")) is not int
                    or row["first_completed"]<0 or row["first_failed"]<0
                    or row["first_completed"]+row["first_failed"]!=planned
                    or type(row.get("total_attempts")) is not int or row["total_attempts"]<planned):
                raise ValueError(f"qualification stage accounting incomplete: {stage}")
        if (type(account.get("total_attempts")) is not int
                or account["total_attempts"]!=sum(row["total_attempts"] for row in stages.values())
                or not isinstance(account.get("first_failures"),list)
                or len(account["first_failures"])!=sum(row["first_failed"] for row in stages.values())):
            raise ValueError("qualification attempt or failure totals differ")
    return seal, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=("logistic", "ode"))
    parser.add_argument("inputs", type=Path)
    parser.add_argument("seal", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("--chain", type=int, required=True)
    parser.add_argument("--steps", type=int, required=True, choices=(1000, 2000, 4000, 8000))
    args = parser.parse_args()
    if args.chain not in range(1, 11):
        parser.error("chain must be 1–10")
    start = time.perf_counter()
    seal, manifest = verify_freeze(args.seal, args.inputs, args.model)
    with np.load(args.inputs / "data.npz", allow_pickle=False) as data:
        model = (Logistic(data["trials"].copy(), data["successes"].copy()) if args.model == "logistic"
                 else ODE(data["ode_log_observations"].copy(), np.log(manifest["ode"]["center"]), prior_scale=.5))
    with np.load(args.inputs / "initials.npz", allow_pickle=False) as initials:
        initial = initials[args.model][args.chain-1].copy()
    seed = manifest["initials"]["formal_random_stream_seed"]
    tag = {"logistic": 1, "ode": 2}[args.model]
    identity = {"scope": reference_scope(manifest), "model": args.model, "chain": args.chain, "seed": seed,
                "seal_sha256": digest(args.seal), "manifest_sha256": digest(args.inputs / "manifest.json"),
                "initial_sha256": sha256(initial.tobytes()).hexdigest(),
                "environment": [platform.platform(), sys.version, jax.__version__, jax.lib.__version__,
                                blackjax.__version__, diffrax.__version__, np.__version__, scipy.__version__,
                                jax.default_backend(), jax.config.x64_enabled, jax.config.jax_threefry_partitionable]}
    if jax.default_backend() != "cpu" or not jax.config.x64_enabled:
        raise ValueError("CPU/x64 runtime required")
    if (jax.__version__, jax.lib.__version__, blackjax.__version__, diffrax.__version__,
        np.__version__, scipy.__version__) != ("0.6.2", "0.6.2", "1.2.5", "0.7.0", "2.2.6", "1.15.3"):
        raise ValueError("reference dependency versions differ from approved environment")
    db = Checkpoint(args.database, identity)
    with db.transaction():
        saved = list(db.blocks())
        if not saved:
            state, params, divergences = warmup(model, initial, phase_key(seed, tag, args.chain, 2))
            record = {**state._asdict(), "step_size": params["step_size"],
                      "inverse_mass_matrix": params["inverse_mass_matrix"],
                      "next_key": jax.random.key_data(phase_key(seed, tag, args.chain, 3)),
                      "warmup_divergent": divergences}
            if not all(np.isfinite(value).all() for value in record.values()):
                raise FloatingPointError("invalid warmup state")
            db.append(0, 0, record)
    advance = sampler(model)
    advanced = 0
    while True:
        with db.transaction():
            n, record = list(db.blocks())[-1]
            if n >= args.steps:
                break
            state = HMCState(*(jnp.asarray(record[k]) for k in HMCState._fields))
            key = jax.random.wrap_key_data(jnp.asarray(record["next_key"]), impl="threefry2x32")
            (state, next_key), outputs = advance(state, key, record["step_size"], record["inverse_mass_matrix"])
            block = jax.tree.map(np.asarray, {**outputs, **state._asdict(),
                "step_size": record["step_size"], "inverse_mass_matrix": record["inverse_mass_matrix"],
                "next_key": jax.random.key_data(next_key)})
            if not all(np.isfinite(value).all() for value in block.values()):
                failure = args.database.with_suffix(f".failed-{n+100}-{os.getpid()}.npz")
                np.savez(failure, **block)
                raise FloatingPointError(f"nonfinite output preserved in {failure}")
            db.append(n+1, n+100, block)
            advanced += 100
    print(json.dumps({"model": args.model, "chain": args.chain, "last_step": n,
                      "new_steps": advanced, "elapsed_seconds": time.perf_counter()-start,
                      "seal_sha256": identity["seal_sha256"]}))


if __name__ == "__main__":
    main()
