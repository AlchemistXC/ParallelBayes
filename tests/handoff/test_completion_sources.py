"""Integrity gates for reference reuse and the selected external case."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[2]


def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts/completion"/(name+".py"))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def test_changed_prior_cannot_reuse_reference_identity(tmp_path):
    runner=module("audit_reference_reuse")
    original=json.loads((ROOT/"benchmark/protocols/reference-v1.json").read_text())
    expected=original["protocol_sha256"]
    original["models"]["L1"]["prior_scale"] *= 2
    tampered=tmp_path/"protocol.json";tampered.write_text(json.dumps(original))
    with pytest.raises(ValueError,match="Protocol identity"):
        runner.checked_protocol(tampered,expected)


def test_changed_cached_source_is_not_overwritten(tmp_path):
    runner=module("fetch_wells")
    manifest=json.loads((ROOT/"models/external/wells/source-manifest.json").read_text())
    first=manifest["files"][0]
    destination=tmp_path/"data"/first["path"]
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"wrong source content")
    with pytest.raises(ValueError,match="checksum"):
        runner.fetch(ROOT/"models/external/wells/source-manifest.json",tmp_path/"data")
    assert destination.read_bytes()==b"wrong source content"


def test_source_manifest_cannot_escape_destination(tmp_path):
    runner=module("fetch_wells")
    manifest=json.loads((ROOT/"models/external/wells/source-manifest.json").read_text())
    manifest["files"][0]["path"]="../outside.txt"
    path=tmp_path/"manifest.json";path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match="Unsafe source path"):
        runner.fetch(path,tmp_path/"data")
    assert not (tmp_path/"outside.txt").exists()
