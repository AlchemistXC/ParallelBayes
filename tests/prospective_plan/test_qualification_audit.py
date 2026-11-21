from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/prospective_plan"))
from audit_qualification import audit
from qualification_inventory import tasks


def write_ledger(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_attempt_accounting_and_evidence(tmp_path):
    artifact = tmp_path / "evidence.json"
    artifact.write_text('{"synthetic": true}')
    base = {"task_id": tasks()[0]["task_id"], "attempt": 1, "status": "failed",
            "reason": "synthetic failure", "elapsed_seconds": 1.0,
            "artifacts": [{"path": "evidence.json", "sha256": sha256(artifact.read_bytes()).hexdigest()}]}
    retry = {**base, "attempt": 2, "status": "completed", "reason": ""}
    ledger = tmp_path / "ledger.jsonl"
    write_ledger(ledger, [base, retry])
    result = audit(ledger, tmp_path)
    assert (result["planned"], result["attempted"], result["total_attempts"]) == (880, 1, 2)
    assert len(result["not_started_task_ids"]) == 879
    assert result["stages"]["gaussian_corners"]["first_failed"] == 1
    assert result["first_failures"][0]["reason"] == "synthetic failure"
    write_ledger(ledger, [base, base])
    with pytest.raises(ValueError, match="attempt sequence"):
        audit(ledger, tmp_path)
    changed = deepcopy(base)
    changed["artifacts"][0]["sha256"] = "0" * 64
    write_ledger(ledger, [changed])
    with pytest.raises(ValueError, match="checksum mismatch"):
        audit(ledger, tmp_path)
    changed["artifacts"][0]["path"] = "../escape"
    write_ledger(ledger, [changed])
    with pytest.raises(ValueError, match="unsafe artifact path"):
        audit(ledger, tmp_path)


def test_empty_ledger_is_not_a_pass(tmp_path):
    ledger = tmp_path / "empty.jsonl"
    ledger.write_text("")
    result = audit(ledger, tmp_path)
    assert result["attempted"] == result["total_attempts"] == 0
    assert len(result["not_started_task_ids"]) == 880
    assert "not a qualification pass" in result["scope"]


def test_complete_synthetic_plan_preserves_first_failure(tmp_path):
    artifact = tmp_path / "synthetic.txt"
    artifact.write_text("test only")
    digest = sha256(artifact.read_bytes()).hexdigest()
    rows = [{"task_id": task["task_id"], "attempt": 1, "status": "completed",
             "reason": "", "elapsed_seconds": 0.5,
             "artifacts": [{"path": artifact.name, "sha256": digest}]} for task in tasks()]
    rows[10]["status"], rows[10]["reason"] = "failed", "synthetic numerical failure"
    rows.append({**rows[10], "attempt": 2, "status": "completed", "reason": ""})
    ledger = tmp_path / "ledger.jsonl"
    write_ledger(ledger, rows)
    result = audit(ledger, tmp_path)
    assert (result["planned"], result["attempted"], result["total_attempts"]) == (880, 880, 881)
    assert not result["not_started_task_ids"]
    assert len(result["first_failures"]) == 1
    assert sum(stage["first_failed"] for stage in result["stages"].values()) == 1
