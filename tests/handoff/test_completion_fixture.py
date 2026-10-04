"""Checks that the portable diagnostic cannot silently accept damaged evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
from fractions import Fraction

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "benchmark/fixtures/rhat-midpoint-v1"
spec = importlib.util.spec_from_file_location("rhat_receipt", ROOT / "scripts/completion/run_rhat_case.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_fixture_has_exact_archived_midpoint():
    meta = json.loads((FIXTURE / "case.json").read_text())
    raw = (FIXTURE / meta["fixture_file"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == meta["fixture_sha256"]
    values = sorted(struct.unpack("<1536d", raw))
    midpoint = (Fraction(values[767]) + Fraction(values[768])) / 2
    assert str(midpoint) == meta["exact_midpoint_fraction"]
    assert float(midpoint).hex() == meta["correctly_rounded_midpoint_hex"]
    assert meta["source_tasks"][0]["raw_sha256"] == meta["source_tasks"][1]["raw_sha256"]


def test_damaged_input_rejected_before_r(tmp_path):
    case = tmp_path / "case"
    shutil.copytree(FIXTURE, case)
    binary = case / "q2-f64le.bin"
    raw = bytearray(binary.read_bytes())
    raw[0] ^= 1
    binary.write_bytes(raw)
    output = tmp_path / "new"
    with pytest.raises(ValueError, match="checksum"):
        runner.run(case, output, "not-a-real-Rscript")
    assert not output.exists()


def test_prior_receipt_cannot_be_overwritten(tmp_path):
    output = tmp_path / "prior"
    output.mkdir()
    sentinel = output / "receipt.json"
    sentinel.write_text("keep prior failure")
    with pytest.raises(FileExistsError):
        runner.run(FIXTURE, output, "not-a-real-Rscript")
    assert sentinel.read_text() == "keep prior failure"


def test_output_inside_fixture_refused(tmp_path):
    case = tmp_path / "case"
    shutil.copytree(FIXTURE, case)
    with pytest.raises(ValueError, match="frozen fixture"):
        runner.run(case, case / "attempt", "not-a-real-Rscript")
    assert not (case / "attempt").exists()
