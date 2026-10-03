"""Recovery must reject changed science, environment, random inputs and outputs."""
import copy
import importlib.util
import json
import sys
from pathlib import Path
import numpy as np
import pytest

SCRIPTS=Path(__file__).resolve().parents[2]/'scripts/windows'
sys.path.insert(0,str(SCRIPTS))
import evidence
import run_study


def test_output_checksum_and_negative_array_preservation(tmp_path):
    result=dict(status='failed',draws=None,failed_trajectory=np.array([[[1.],[np.nan]]]))
    checks,_=evidence.save_result(tmp_path,result,{'noise':np.ones((1,2,1))})
    evidence.verify_checksums(tmp_path,checks)
    with np.load(tmp_path/'raw.npz') as arrays:
        assert 'failed_trajectory' in arrays and 'tape__noise' in arrays
        assert np.isnan(arrays['failed_trajectory'][0,1,0])
    with (tmp_path/'raw.npz').open('ab') as f:f.write(b'corrupted')
    with pytest.raises(ValueError,match='checksum'):evidence.verify_checksums(tmp_path,checks)


def test_protocol_environment_and_source_gates(tmp_path,monkeypatch):
    monkeypatch.setattr(run_study,'ROOT',tmp_path)
    monkeypatch.setattr(run_study,'source_files',lambda:{'source':'v1'})
    monkeypatch.setattr(run_study,'runtime',lambda:{'torch':'test'})
    monkeypatch.setattr(sys,'prefix',str(tmp_path/'venv'))
    lock=tmp_path/'lock.txt';lock.write_text('locked')
    payload=dict(source_files={'source':'v1'},runtime={'torch':'test'},dependency_lock='lock.txt',dependency_lock_sha256=evidence.sha(lock))
    payload['protocol_sha256']=evidence.fingerprint(payload)
    evidence.write_json(tmp_path/'venv/PARALLELBAYES-FROZEN.json',dict(protocol_sha256=payload['protocol_sha256']))
    run_study.verify_protocol(payload)
    bad=copy.deepcopy(payload);bad['runtime']={'torch':'altered'}
    with pytest.raises(ValueError,match='protocol'):run_study.verify_protocol(bad)
    monkeypatch.setattr(run_study,'runtime',lambda:{'torch':'altered'})
    with pytest.raises(ValueError,match='runtime'):run_study.verify_protocol(payload)
    monkeypatch.setattr(run_study,'runtime',lambda:{'torch':'test'})
    monkeypatch.setattr(run_study,'source_files',lambda:{'source':'v2'})
    with pytest.raises(ValueError,match='source'):run_study.verify_protocol(payload)
    monkeypatch.setattr(run_study,'source_files',lambda:{'source':'v1'})
    lock.write_text('changed')
    with pytest.raises(ValueError,match='lock'):run_study.verify_protocol(payload)
