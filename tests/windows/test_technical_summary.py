from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/windows'))
from technical_summary import cache_description

def report():
    return dict(samples_eligible=False,measurement_available=True,observation=dict(
        execution_outcomes=['valid']*4,records=[dict(technical_output_valid=True,executor_wall_seconds=t) for t in [8.,2.,4.,3.]]))

def test_one_input_is_descriptive_and_outer_interruption_is_not_available():
    original=report();success=cache_description(original,'measurement_available')
    assert success['cached_seconds']==3 and success['confidence_interval'] is None
    interrupted=cache_description(original,'infrastructure_interruption')
    assert interrupted['cached_seconds'] is None and interrupted['known_executor_seconds']==17
    assert not interrupted['measurement_available']

def test_failure_and_missing_slots_are_retained_without_replacement():
    original=report();original['measurement_available']=False
    original['observation']['execution_outcomes']=['valid','resource_failure','not_run','not_run']
    original['observation']['records'][1:]=[dict(technical_output_valid=False,executor_wall_seconds=None),None,None]
    value=cache_description(original,'resource_failure')
    assert value['executions_recorded']==2 and value['missing_clock_measurements']==1
    assert value['known_executor_seconds']==8 and value['cached_seconds'] is None
