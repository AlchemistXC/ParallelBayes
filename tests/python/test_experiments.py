from pathlib import Path
import json
import numpy as np
import pytest
from parallelbayes import sample,validate_model
from parallelbayes.models import benchmark_model
from parallelbayes.experiment import freeze,run_protocol,load_protocol

@pytest.mark.parametrize('name',['H1','H2','A1','M1'])
def test_extended_target_independent_derivatives(name):
    assert validate_model(benchmark_model(name))['passed']


def test_frozen_protocol_resume_and_corruption_detection(tmp_path):
    root=tmp_path/'root';(root/'environment/locks').mkdir(parents=True)
    (root/'environment/locks/python-core.txt').write_text('')
    protocol=tmp_path/'protocol.json'
    freeze(protocol,dict(platforms=['cpu'],models={'g':dict(kind='gaussian',dimension=2)},
                         defaults=dict(draws=8,audit=True),tasks=[dict(model='g',config=dict(kernel='mala',executor='sequential'))]),root)
    output=tmp_path/'runs'
    first=run_protocol(protocol,output,root)
    assert first[0]['status']=='completed'
    statefile=next(output.glob('tasks/*/state.json'));before=statefile.read_bytes()
    run_protocol(protocol,output,root)
    assert statefile.read_bytes()==before
    raw=next(output.glob('tasks/*/attempt-*/raw.npz'))
    with np.load(raw) as arrays: assert 'tape__noise' in arrays
    raw.write_bytes(raw.read_bytes()+b'corrupted')
    with pytest.raises(ValueError,match='checksum'):run_protocol(protocol,output,root)
    (root/'environment/locks/python-core.txt').write_text('modified')
    with pytest.raises(ValueError,match='Runtime'):load_protocol(protocol,root)


def test_cached_timing_replays_are_separate_from_inference_cost():
    r=sample(dict(kind='gaussian',dimension=2),dict(draws=16,timing_repeats=3,audit=True))
    assert len(r['cached_execution_seconds'])==2
    assert r['timing_replay_overhead']>sum(r['cached_execution_seconds'])
    assert r['status']=='completed'
