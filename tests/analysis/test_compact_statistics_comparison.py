import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[2]/'scripts/analysis'))
from compare_compact_statistics import scalar_differences, decision_view


def test_missing_or_integer_denominator_changes_are_preserved():
    result=scalar_differences({'n':24,'error':None},{'n':23,'error':0.})
    assert {r['kind'] for r in result}=={'integer','state_or_label'}


def test_small_numeric_drift_is_not_hidden_by_a_tolerance():
    result=scalar_differences({'point':1.},{'point':1.+1e-14})
    assert len(result)==1 and result[0]['kind']=='numeric'
    assert result[0]['absolute_difference']>0


def test_threshold_changes_are_separate_from_numeric_drift():
    def table(value):
        return {'ratios':[dict(phase='ordinary',kind='same_kernel',workflow_a='a',workflow_b='b',budget=1024,
            point=value,low=None,high=None,interval_status='insufficient',paired=11)],'errors':[]}
    a,b=decision_view(table(1.)),decision_view(table(1.+1e-14))
    changes=scalar_differences(a,b)
    assert len(changes)==1 and changes[0]['kind']=='integer'
    assert a['ratios'][0]['low_vs_one'] is None


def test_undefined_resamples_are_compared_and_not_dropped():
    import numpy as np
    from compare_compact_statistics import bootstrap_difference
    a=np.array([np.nan,2.,np.nan])
    same=bootstrap_difference(a,a.copy())
    assert same['equal'] and same['left_nonfinite']==2
    changed=bootstrap_difference(a,np.array([np.nan,2.,0.]))
    assert changed['differing_elements']==1 and changed['nonfinite_pattern_changes']==1
    assert changed['maximum_absolute_difference']==0.
