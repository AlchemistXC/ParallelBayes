"""Selected-kernel whole-batch validation, quarantine and immutable resume."""
from pathlib import Path
import copy
import json
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'r-package/inst/python'), str(ROOT/'scripts/completion')]


def test_actual_inputs_pair_time_executors_and_failed_target_stays_quarantined(tmp_path):
    import selected_mh_readiness as study
    from parallelbayes.reference import benchmark_model
    from parallelbayes.torch_backend.sampling import settings, random_tape
    from mechanism_runner import identity, sha, actual_hash
    item = dict(name='G1', dimension=8, base_target_id=benchmark_model('G1').target_id,
        geometry=dict(center=[0.]*8, factor=np.eye(8).tolist()), step_rwm=.1, step_mala=.1, input='G1.npz')
    broken = copy.deepcopy(item)
    broken.update(name='G2', base_target_id='wrong posterior identity', input='G2.npz')
    p = dict(identity='unit-selected-mh', required_platform=sys.platform, device='cpu',
        required_versions={}, torch_threads=1, source_files=study.source_files(),
        targets=[item, broken], chains=2, draws=16, windows=[4,8], max_iter=128,
        atol=1e-10, rtol=1e-10, memory_limit_mb=128, inputs={},
        scope='Interface test, not formal inference')
    inputs = tmp_path/'inputs'; inputs.mkdir()
    payload = random_tape(settings(dict(chains=2, draws=16, seed=7391011, solver_seed=7391013)), 8)
    payload['initial'] = np.array([[-.1]*8, [.1]*8])
    for name in ['G1.npz', 'G2.npz']:
        np.savez_compressed(inputs/name, **payload)
        p['inputs'][name] = dict(sha256=sha(inputs/name), actual_sha256=actual_hash(payload))
    p['protocol_sha256'] = identity(p)
    protocol = tmp_path/'plan.json'; protocol.write_text(json.dumps(p))
    out = tmp_path/'run'
    summary = study.run(protocol, inputs, tmp_path/'unused', out)
    assert summary['planned_workflows'] == 12 and summary['completed_workflows'] == 6
    assert summary['failed_workflows'] == 6 and summary['completed_targets'] == 1
    good = json.loads((out/'G1/state.json').read_text())
    assert len(good['pairs']) == 4 and all(v['passed'] for v in good['pairs'].values())
    assert all(v['acceptance_mismatches'] == [0,0] for v in good['pairs'].values())
    bad = json.loads((out/'G2/state.json').read_text())
    assert bad['status'] == 'failed' and not bad['samples_eligible_for_inference']
    assert 'target identity' in bad['setup_error']
    before = {f.relative_to(out).as_posix(): sha(f) for name in ['G1','G2'] for f in (out/name).rglob('*') if f.is_file()}
    resumed = study.run(protocol, inputs, tmp_path/'unused', out, resume=True)
    assert resumed['newly_executed_targets'] == 0
    after = {f.relative_to(out).as_posix(): sha(f) for name in ['G1','G2'] for f in (out/name).rglob('*') if f.is_file()}
    assert before == after
    from audit_selected_mh import audit
    receipt = audit(protocol, inputs, out, tmp_path/'unused', tmp_path/'audit')
    assert receipt['checked_completed_workflows'] == 6
    assert receipt['retained_failed_workflows'] == 6
    assert receipt['acceptance_mismatches'] == 0 and receipt['saved_array_replay_passed']
    raw = out/'G1'/good['attempt']/'rwm-sequential.npz'
    raw.write_bytes(raw.read_bytes()+b'corrupt')
    with pytest.raises(ValueError, match='checksum'):
        study.run(protocol, inputs, tmp_path/'unused', out, resume=True)
    with pytest.raises(ValueError, match='checksum'):
        audit(protocol, inputs, out, tmp_path/'unused', tmp_path/'bad-audit')
