"""Formal report seam: unresolved truth and failures must not become zero loss."""
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_unresolved_reference_preserves_observation_but_never_reports_zero_error():
    from formal_error_summary import summarize
    row=summarize([0.,0.,0.,0.],dict(kind='unresolved',value=0.,mcse=None))
    assert row['planned']==row['valid']==4 and row['observed_estimate_mean']==0
    assert not row['reference_eligible'] and row['supplied_reference_value']==0
    for key in ['conditional_squared_discrepancy','unconditional_squared_discrepancy',
                'squared_discrepancy_standard_error','reference_shift_min','reference_shift_max']:
        assert row[key] is None
    assert row['interval_status']=='unresolved_reference'


def test_missing_runs_and_common_success_comparison_have_different_denominators():
    from formal_error_summary import summarize,paired_difference
    ref=dict(kind='analytic',value=1.,mcse=0.)
    row=summarize([0.,None,2.,3.],ref)
    assert row['planned']==4 and row['valid']==3 and row['failed_or_unavailable']==1
    assert row['conditional_squared_discrepancy']==pytest.approx(2.)
    assert row['unconditional_squared_discrepancy'] is None
    pair=paired_difference([0.,None,2.,3.],[2.,1.,None,0.],ref)
    assert pair['validity_table']==dict(n11=2,n10=1,n01=1,n00=0)
    # Common-success rows have losses (1,1) and (4,1); A minus B = (0,3).
    assert pair['conditional_mean_loss_difference']==pytest.approx(1.5)
    assert pair['conditioning']=='both_workflows_have_valid_estimates'
    assert pair['unconditional_mean_loss_difference'] is None
    constant=summarize([0.,0.,0.,0.],ref)
    assert constant['conditional_squared_discrepancy']==1
    assert constant['interval_status']=='degenerate_empirical_loss'


def test_finite_reference_sensitivity_is_not_a_confidence_interval():
    from formal_error_summary import summarize
    row=summarize([1.,3.],dict(kind='finite_mcmc',value=0.,mcse=.1))
    assert row['conditional_squared_discrepancy']==5
    assert row['reference_shift_min']==pytest.approx(4.24)
    assert row['reference_shift_max']==pytest.approx(5.84)
    assert row['claim_type']=='finite_reference_discrepancy'
    assert row['reference_shift_is_confidence_interval'] is False
