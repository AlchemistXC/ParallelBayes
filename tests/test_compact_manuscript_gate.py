"""Final prose must be bound to the completed independent reader, not a preview."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts/analysis'))
from write_compact_manuscript import final_gate, file_hash, squared_error


def evidence(tmp_path):
    bundle = SimpleNamespace(frame={'identity':'synthetic'},summary={'analysis_identity_sha256':'independent'})
    value = dict(stage='complete_receiver_review',visited=4144,dispositions={'analyzed':4144},
        frame=bundle.frame,identity_sha256='independent',resume_proof_sha256='proof')
    path = tmp_path/'review.json'
    path.write_text(json.dumps(value))
    return bundle,value,path


def test_preview_or_partial_reader_cannot_feed_final_prose(tmp_path):
    bundle,value,path = evidence(tmp_path)
    value['stage'] = 'partial_snapshot'
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='complete Mac'):
        final_gate(bundle,path,file_hash(path))


def test_completed_reader_from_another_identity_is_rejected(tmp_path):
    bundle,value,path = evidence(tmp_path)
    value['identity_sha256'] = 'another-analysis'
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='complete Mac'):
        final_gate(bundle,path,file_hash(path))


def test_actual_resume_proof_is_required(tmp_path):
    bundle,value,path = evidence(tmp_path)
    value['resume_proof_sha256'] = None
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='complete Mac'):
        final_gate(bundle,path,file_hash(path))


def test_correct_binding_is_accepted_without_reanalysis(tmp_path):
    bundle,value,path = evidence(tmp_path)
    assert final_gate(bundle,path,file_hash(path)) == value


def test_missing_interval_stays_missing():
    assert squared_error(dict(point=2e-6,low=None,high=None)) == '2.00 [--]'
