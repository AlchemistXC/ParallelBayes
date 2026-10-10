"""Reader-summary invariants; synthetic records are not scientific evidence."""
import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest

SPEC = importlib.util.spec_from_file_location('review_compact_reconstruction', Path(__file__).parents[1]/'scripts/analysis/review_compact_reconstruction.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def diagnostics():
    return [dict(variable='constant', mean=0., sd=0., rhat=None, ess_bulk=None, ess_tail=None, mcse_mean=None),
            dict(variable='q', mean=.2, sd=1., rhat=1.01, ess_bulk=120., ess_tail=95., mcse_mean=.08)]


def test_nulls_remain_undefined_and_a_threshold_crossing_is_exposed():
    old = diagnostics()
    new = diagnostics()
    new[1]['rhat'] = 1.010000000000001
    rows = m.diagnostic_pairs(old, new)
    assert sum(r['undefined'] for r in rows) == 4
    assert [r['variable'] for r in rows if r['rhat_classification_changed']] == ['q']
    assert all(r['absolute_difference'] is None for r in rows if r['undefined'])


def test_changed_missingness_is_rejected():
    new = diagnostics()
    new[0]['rhat'] = 1.
    with pytest.raises(ValueError, match='undefined'):
        m.diagnostic_pairs(diagnostics(), new)


def test_function_order_is_not_silently_repaired():
    with pytest.raises(ValueError, match='variable'):
        m.diagnostic_pairs(diagnostics(), list(reversed(diagnostics())))


@pytest.fixture
def receiver(tmp_path):
    root = tmp_path/'receiver'
    folder = root/'tasks'/'synthetic'
    folder.mkdir(parents=True)
    task = dict(id='synthetic')
    def write(path, obj):
        path.write_text(json.dumps(obj)+'\n')
    write(root/'identity.json', dict(frame=dict(protocol_sha256=m.PROTOCOL, identity='windows-compact-inference-v1',
        main_planned=3888, cache_planned=256), cross_platform=True, receiver_environment={'artificial':True}))
    write(folder/'FRAME.json', dict(task=task, phase='main', outcome='unavailable', error='synthetic retained reader failure'))
    receipt = dict(task=task, disposition='reader_error', row='FRAME.json', files={'FRAME.json':m.sha(folder/'FRAME.json')})
    write(folder/'RECEIPT.json', receipt)
    db = sqlite3.connect(root/'analysis.sqlite3')
    db.execute('CREATE TABLE results(id TEXT PRIMARY KEY, task TEXT, disposition TEXT, receipt TEXT, sha256 TEXT)')
    db.execute('INSERT INTO results VALUES(?,?,?,?,?)', ('synthetic', json.dumps(task), 'reader_error',
        'tasks/synthetic/RECEIPT.json', m.sha(folder/'RECEIPT.json')))
    db.commit()
    db.close()
    return root


def test_snapshot_retains_reader_error_without_claiming_completion(receiver, tmp_path):
    result = m.review(receiver, tmp_path/'summary', snapshot=True)
    assert result['stage'] == 'partial_snapshot'
    assert result['visited'] == 1
    assert result['dispositions'] == {'reader_error':1}
    assert result['new_sampler_calls'] == 0


def test_final_requires_actual_resume_proof(receiver, tmp_path):
    with pytest.raises(ValueError, match='resume proof'):
        m.review(receiver, tmp_path/'summary')
    assert not (tmp_path/'summary').exists()


def test_altered_projected_output_is_rejected(receiver, tmp_path):
    (receiver/'tasks/synthetic/FRAME.json').write_text('{}')
    with pytest.raises(ValueError, match='output changed'):
        m.review(receiver, tmp_path/'summary', snapshot=True)
    assert not (tmp_path/'summary').exists()


def test_unsafe_member_is_rejected(tmp_path):
    with pytest.raises(ValueError, match='Unsafe'):
        m.contained(tmp_path.resolve(), '../outside.json')
