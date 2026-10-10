"""Cost-boundary/identity checks. These artificial processes never run MCMC."""
import importlib.util
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("timing", ROOT / "scripts/analysis/r_frontend_timing.py")
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)
verify_spec = importlib.util.spec_from_file_location("verify", ROOT / "scripts/analysis/r_frontend_verify.py")
verifier = importlib.util.module_from_spec(verify_spec)
verify_spec.loader.exec_module(verifier)


def test_plan_has_32_processes_and_one_each_condition_per_block():
    tasks = timing.tasks()
    assert len(tasks) == len({t["id"] for t in tasks}) == 32
    for block in range(4):
        assert {(t["workflow"], t["audit"]) for t in tasks if t["block"] == block} == {
            (workflow, audit) for workflow in range(4) for audit in (False, True)}


def test_mode_order_counterbalanced():
    tasks = timing.tasks()
    for workflow in range(4):
        first_modes = [next(t["audit"] for t in tasks if t["workflow"] == workflow and t["block"] == b)
                       for b in range(4)]
        assert first_modes.count(True) == 2


def test_ready_clock_excludes_subsequent_archive(tmp_path):
    code = "import time;print('PB_R_READY first completed',flush=True);time.sleep(.15)"
    result = timing.capture([sys.executable, "-u", "-c", code], tmp_path, os.environ.copy())
    assert result["returncode"] == 0
    assert result["process_wall_seconds"] - result["markers"][0]["seconds_from_process_launch"] > .1


def test_nonzero_exit_is_retained_not_promoted(tmp_path):
    code = "print('PB_R_READY first failed',flush=True);raise SystemExit(7)"
    result = timing.capture([sys.executable, "-u", "-c", code], tmp_path, os.environ.copy())
    assert result["returncode"] == 7
    assert result["markers"][0]["status"] == "failed"
    assert len(result["markers"]) == 1


@pytest.mark.parametrize("lines,match", [
    (["PB_R_READY first completed"] * 2, "Repeated"),
    (["PB_R_READY unrecognized completed"], "Malformed"),
])
def test_invalid_ready_markers_rejected_after_child_exit(tmp_path, lines, match):
    code = ";".join(f"print({line!r},flush=True)" for line in lines)
    with pytest.raises(ValueError, match=match):
        timing.capture([sys.executable, "-u", "-c", code], tmp_path, os.environ.copy())


def test_changed_protocol_fails_before_starting_any_process(tmp_path):
    protocol = tmp_path / "protocol.json"
    protocol.write_text('{"schema":"r-frontend-timing-v1"}')
    (tmp_path / "protocol.sha256").write_text(timing.sha(protocol) + "\n")
    protocol.write_text('{"schema":"changed"}')
    with pytest.raises(ValueError, match="protocol changed"):
        timing.verify_plan(tmp_path)
    assert not (tmp_path / "attempts").exists()


def test_path_or_event_corruption_is_not_accepted():
    import numpy as np
    ref = np.zeros((4, 128, 2))
    events = np.zeros((4, 128), dtype=bool)
    config = dict(atol=1e-10, rtol=1e-10)
    assert verifier.check_path(ref, events, ref, events, config)["passed"]
    changed = ref.copy()
    changed[2, 40, 1] = 1e-4
    assert not verifier.check_path(changed, events, ref, events, config)["passed"]
    wrong_events = events.copy()
    wrong_events[0, 0] = True
    checked = verifier.check_path(ref, wrong_events, ref, events, config)
    assert not checked["passed"] and checked["acceptance_mismatches"] == 1
