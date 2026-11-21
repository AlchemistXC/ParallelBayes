"""Assemble and verify a reference seal from existing, independently produced receipts."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

from formal_run import ROOT, verify_freeze
sys.path.insert(0,str(ROOT/'scripts/prospective_plan'))
from audit_qualification import audit as audit_qualification


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def create(output, inputs, model, windows_qualification, capacity, restart, candidate_audit=None, fresh_preflight=None,
           qualification_ledger=None, qualification_artifact_root=None):
    sources = {
        "study_protocol":ROOT/"docs/prospective-first-use-v1/DECISIONS.md",
        "model_source":ROOT/"scripts/prospective_reference/models.py",
        "runner_source":ROOT/"scripts/prospective_reference/formal_run.py",
        "checkpoint_source":ROOT/"scripts/prospective_reference/checkpoint.py",
        "engine_source":ROOT/"scripts/prospective_reference/run.py",
        "cohort_source":ROOT/"scripts/prospective_reference/cohort.py",
        "extension_source":ROOT/"scripts/prospective_reference/extend_cohort.py",
        "diagnostics_source":ROOT/"scripts/analysis/prospective_reference_diagnostics.py",
        "diagnostics_r_source":ROOT/"scripts/analysis/prospective_reference_diagnostics.R",
        "environment_lock":ROOT/"docs/prospective-first-use-v1/mac-environment/requirements-arm64.lock",
        "candidate_manifest":inputs/"manifest.json",
        "preflight":inputs/"preflight.json",
    }
    if model == "ode":
        sources["ode_points"] = inputs/"ode-points.json"
    receipts = {"windows_qualification":windows_qualification, "capacity":capacity,
                "restart_"+model:restart}
    if (candidate_audit is None)!=(fresh_preflight is None):
        raise ValueError("candidate audit and fresh preflight must be provided together")
    if candidate_audit is not None:
        receipts.update(candidate_audit=candidate_audit, fresh_preflight=fresh_preflight)
    if (qualification_ledger is None)!=(qualification_artifact_root is None):
        raise ValueError("qualification ledger and artifact root must be provided together")
    accounting = None
    if qualification_ledger is not None:
        before = digest(qualification_ledger)
        accounting = audit_qualification(qualification_ledger,qualification_artifact_root)
        if digest(qualification_ledger)!=before or accounting['ledger_sha256']!=before:
            raise ValueError("qualification ledger changed during audit")
        sources['qualification_plan_source']=ROOT/'scripts/prospective_plan/qualification_inventory.py'
        sources['qualification_auditor_source']=ROOT/'scripts/prospective_plan/audit_qualification.py'
    # Read all dependencies before creating an output directory.
    hashes = {key:digest(path) for key,path in sources.items()}
    for path in receipts.values():
        if not path.is_file():
            raise ValueError(f"missing receipt: {path}")
    output.mkdir()
    seal = {"identity":"prospective-first-use-v1", "status":"frozen", **hashes}
    for key, path in receipts.items():
        destination = output/(key+".json")
        with destination.open("xb") as target, path.open("rb") as source:
            shutil.copyfileobj(source,target)
        seal[key] = {"file":destination.name,"sha256":digest(destination)}
    if accounting is not None:
        ledger_copy=output/'qualification_ledger.jsonl'
        with ledger_copy.open('xb') as target,qualification_ledger.open('rb') as source:
            shutil.copyfileobj(source,target)
        if digest(ledger_copy)!=accounting['ledger_sha256']:
            raise ValueError('qualification ledger changed before copy')
        accounting_path=output/'qualification_accounting.json'
        with accounting_path.open('x',encoding='utf-8') as target:
            json.dump(accounting,target,indent=2,allow_nan=False);target.write('\n')
        seal['qualification_ledger']={'file':ledger_copy.name,'sha256':digest(ledger_copy)}
        seal['qualification_accounting']={'file':accounting_path.name,'sha256':digest(accounting_path)}
    temporary = output/"candidate-seal.json"
    with temporary.open("x", encoding="utf-8") as file:
        json.dump(seal,file,indent=2)
        file.write("\n")
    # The reference runner is the single source of truth for receipt binding.
    verify_freeze(temporary, inputs, model)
    final = output/"seal.json"
    with final.open("xb") as target, temporary.open("rb") as source:
        shutil.copyfileobj(source,target)
    print(json.dumps({"seal":str(final),"sha256":digest(final)}))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs",type=Path,required=True)
    parser.add_argument("--windows-qualification",type=Path,required=True)
    parser.add_argument("--capacity",type=Path,required=True)
    parser.add_argument("--model",choices=("logistic","ode"),required=True)
    parser.add_argument("--restart",type=Path,required=True)
    parser.add_argument("--candidate-audit",type=Path)
    parser.add_argument("--fresh-preflight",type=Path)
    parser.add_argument("--qualification-ledger",type=Path)
    parser.add_argument("--qualification-artifact-root",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    create(args.output,args.inputs,args.model,args.windows_qualification,args.capacity,args.restart,
           args.candidate_audit,args.fresh_preflight,args.qualification_ledger,args.qualification_artifact_root)
