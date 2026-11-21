from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/prospective_plan'))
from first_use_policy import baseline, decide


def inputs():
    return {'retained':256,'shared_seconds':1.,'sequential_setup_seconds':2.,
            'sequential_step_seconds':.01,'delivery_fixed_seconds':1.,
            'delivery_per_step_seconds':.001,'probe_seconds':.5}


def candidate(lower):
    return {'setup_seconds':1.,'progress_per_round':4.,'round_seconds':.02,
            'simultaneous_lower':lower}


def test_first_use_costs_include_discard_delivery_and_probe():
    result=decide(**inputs(),candidates={8:candidate(1.2)})
    assert result['baseline_seconds']==pytest.approx(11.936)
    assert result['predicted_strategy_seconds']==pytest.approx(7.596)
    assert result['choice']==8 and result['probe_performed']


def test_threshold_and_invalid_bounds_force_sequential_with_probe_cost():
    result=decide(**inputs(),candidates={8:candidate(1.10),32:candidate(float('nan'))})
    assert result['choice']=='sequential' and result['probe_performed']
    assert result['predicted_strategy_seconds']==pytest.approx(result['baseline_seconds']+.5)
    assert all(not row['eligible'] for row in result['windows'])


def test_optimistic_screen_avoids_probe_and_ties_are_deterministic():
    skipped=decide(**inputs(),candidates={},optimistic_upper=1.10)
    assert not skipped['probe_performed'] and skipped['choice']=='sequential'
    assert skipped['predicted_strategy_seconds']==skipped['baseline_seconds']
    selected=decide(**inputs(),candidates={32:candidate(1.2),8:candidate(1.2)})
    assert selected['choice']==8


def test_invalid_budget_and_excess_progress_are_not_accepted():
    with pytest.raises(ValueError):baseline(1000,1,1,.1,1,0)
    bad=candidate(2.);bad['progress_per_round']=9
    result=decide(**inputs(),candidates={8:bad})
    assert result['choice']=='sequential' and not result['windows'][0]['eligible']
