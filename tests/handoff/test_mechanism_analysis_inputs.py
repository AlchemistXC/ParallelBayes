"""The analysis interface must consume the original frozen random arrays."""
import json
from pathlib import Path
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/completion'))


def test_analysis_uses_frozen_files_and_rejects_changed_files(tmp_path):
    from mechanism_runner import design, run_group, source_files, sha, actual_hash, identity
    from analyze_mechanism_pilot import analyze
    plan = design('smoke')
    spec = dict(kind='gaussian', dimension=1, mean=[0.], covariance=[[1.]])
    group = dict(id='literal-normal', model='G1', kernel='rwm', replicate=0,
                 chains=1, draws=4, windows=[2], step_size=.5, role='input_contract_test')
    # Deliberately literal data, not reconstructed from the plan's RNG seed.
    tape = dict(noise=np.array([[[.25],[-.5],[1.],[.1]]]),
                log_uniform=np.full((1,4), -1.), directions=np.ones((1,4,1)))
    inputs = tmp_path/'inputs'; inputs.mkdir()
    np.savez_compressed(inputs/'G1-r0.npz', **tape)
    plan.update(models={'G1':spec}, groups=[group], technical_replays=1,
                source_commit='test-fixture', source_files=source_files(),
                inputs={'G1-r0':dict(file_sha256=sha(inputs/'G1-r0.npz'), actual_sha256=actual_hash(tape))})
    plan['protocol_sha256'] = identity(plan)
    protocol = tmp_path/'plan.json'; protocol.write_text(json.dumps(plan))
    run = tmp_path/'run'; run.mkdir()
    (run/'run.json').write_text(json.dumps(dict(protocol_sha256=plan['protocol_sha256'], device='cpu')))
    run_group(spec, group, tape, run/'groups'/group['id'], 'cpu', technical_replays=1)
    out = tmp_path/'analysis'
    analyze(protocol, run, out, inputs=inputs)
    receipt = json.loads((out/'summary.json').read_text())
    assert receipt['workflows_completed'] == 2
    assert receipt['input_verification']['mode'] == 'frozen_files'
    assert receipt['input_verification']['files'] == 1
    before = (out/'workflows.csv').read_bytes()
    # A Windows-origin state must resolve the same files on a receiving Mac.
    state_path = run/'groups'/group['id']/'state.json'
    state = json.loads(state_path.read_text())
    state['assets'] = {name.replace('/', '\\'): value for name, value in state['assets'].items()}
    state_path.write_text(json.dumps(state))
    analyze(protocol, run, tmp_path/'windows-path-analysis', inputs=inputs)
    assert (tmp_path/'windows-path-analysis/workflows.csv').read_bytes() == before
    with pytest.raises(ValueError, match='frozen input'):
        analyze(protocol, run, tmp_path/'no-inputs')
    assert not (tmp_path/'no-inputs').exists()
    (inputs/'G1-r0.npz').write_bytes((inputs/'G1-r0.npz').read_bytes()+b'corruption')
    with pytest.raises(ValueError, match='checksum'):
        analyze(protocol, run, tmp_path/'corrupt', inputs=inputs)
    assert not (tmp_path/'corrupt').exists()
    assert (out/'workflows.csv').read_bytes() == before


@pytest.mark.parametrize('name', ['../outside', '..\\outside', 'C:\\outside', '/outside'])
def test_archived_path_cannot_escape_group(tmp_path, name):
    from analyze_mechanism_pilot import evidence_path
    with pytest.raises(ValueError, match='evidence path'):
        evidence_path(tmp_path, name)
