"""Independent repetition and finite-reference reporting contract."""
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_failed_repetition_stays_in_denominator_and_reference_shift_is_not_truth():
    from inference_error_summary import summarize_function
    s=summarize_function([0.,2.,None],reference=1.,reference_kind='finite_mcmc',reference_mcse=.25)
    assert s['planned']==3 and s['valid']==2 and s['failed_or_unavailable']==1
    assert s['conditional_squared_discrepancy']==1.
    assert s['unconditional_squared_discrepancy'] is None
    assert s['reference_shift_min']==1.
    assert s['reference_shift_max']==1.25
    assert s['reference_shift_is_confidence_interval'] is False
    assert s['planning_repetitions_relative_25pct'] is None


def test_unresolved_zero_event_never_becomes_zero_uncertainty_or_complete_error():
    from inference_error_summary import summarize_function
    s=summarize_function([0.,0.,0.,0.],reference=0.,reference_kind='unresolved',reference_mcse=None)
    assert s['conditional_squared_discrepancy']==0.
    assert s['reference_adequacy']=='unresolved'
    assert s['reference_shift_min'] is None and s['reference_shift_max'] is None
    assert s['planning_repetitions_relative_25pct'] is None
