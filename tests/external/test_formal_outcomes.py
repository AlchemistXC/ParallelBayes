"""Outcome and cost accounting does not erase interrupted or failed attempts."""
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_resource_failure_and_partial_interruption_cost_are_preserved():
    from formal_uncertainty import create_plan
    from formal_outcomes import analyze_attempt_costs
    plan=create_plan('attempt-cost-fixture','G1',['0','1','2','3'])
    def attempt(identity,outcome,seconds,binding='same-request'):
        return dict(attempt_id=identity,binding_sha256=binding,outcome=outcome,seconds=seconds)
    a={'0':[attempt('a0-old','infrastructure_interruption',2.),attempt('a0-new','valid',3.)],
       '1':[attempt('a1','resource_failure',7.)],
       '2':[attempt('a2','numerical_failure',11.)],
       '3':[attempt('a3-old','infrastructure_interruption',None),attempt('a3-new','valid',13.)]}
    b={str(i):[attempt('b'+str(i),'valid',2.)] for i in range(4)}
    report=analyze_attempt_costs(plan,{'a':a,'b':b},pairs=[('a','b')],phase='fixture_wall')
    row=report['workflows']['a']
    assert row['total_recorded_seconds']==36.
    assert row['known_partial_task_seconds']==13.
    assert row['unusable_output_cost_seconds']==18.
    assert row['prior_interruption_known_seconds']==2.
    assert row['mean_all_planned_seconds'] is None
    assert row['failure_rate']==.5
    assert row['outcome_counts']['resource_failure']==1 and row['outcome_counts']['numerical_failure']==1
    assert row['attempts_with_unknown_cost']==1
    assert report['pairs'][0]['validity_table']==dict(n11=2,n10=0,n01=2,n00=0)
    assert report['pairs'][0]['geometric_mean_ratio'] is None
    assert report['pairs'][0]['jointly_valid_pairs_missing_cost']==1
    a['1'].append(attempt('forbidden','valid',1.))
    with pytest.raises(ValueError,match='Only infrastructure'):
        analyze_attempt_costs(plan,{'a':a,'b':b},phase='fixture_wall')


def test_record_reader_separates_resource_from_unspecified_output_failure(tmp_path):
    import json
    from formal_runtime import execute_task
    from formal_outcomes import read_attempt
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys,time
from pathlib import Path
time.sleep(.1)
(Path(sys.argv[2])/'worker-result.json').write_text(json.dumps(dict(status='failed',samples_eligible=False)))
''')
    for name,limit,expected in [('resource',1,'resource_failure'),('output',2**30,'output_failure_unclassified')]:
        execute_task({'id':name},{},worker,tmp_path/name,tmp_path/'host.lock',1024,limit)
        record=read_attempt(tmp_path/name)
        assert record['outcome']==expected and record['seconds']>0
    state=tmp_path/'output/state.json'
    content=json.loads(state.read_text());content['status']='completed';state.write_text(json.dumps(content))
    with pytest.raises(ValueError,match='checksum'):read_attempt(tmp_path/'output')
