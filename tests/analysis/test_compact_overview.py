"""Artificial selector fixtures only; no research results are generated."""
import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/analysis'))
from plot_compact_overview import select_complete_contrasts,MODELS


def fixture():
    tables={m:{'ratios':[]} for m in MODELS}
    for m in MODELS:
        for device in ('cpu','cuda'):
            for kernel,executor in (('rwm','online_picard'),('mala','quasi_deer')):
                for budget in (1024,4096):
                    missing=m=='H1' and kernel=='mala'
                    tables[m]['ratios'].append(dict(phase='ordinary_workflow',kind='same_kernel_execution',
                        budget=budget,workflow_a=f'{device}-{kernel}-sequential',workflow_b=f'{device}-{kernel}-{executor}',
                        planned=24,paired=11 if missing else 24,point=.5,low=None if missing else .4,
                        high=None if missing else .6,interval_status='unavailable' if missing else 'available'))
    return tables


def test_complete_contrasts_preserve_missing_intervals():
    rows=select_complete_contrasts(fixture())
    assert len(rows)==72
    assert sum(r['low'] is None for r in rows)==4
    assert min(r['paired'] for r in rows)==11


def test_omission_and_duplicate_do_not_silently_change_frame():
    for duplicate in (False,True):
        tables=fixture()
        if duplicate:tables['G1']['ratios'].append(copy.deepcopy(tables['G1']['ratios'][0]))
        else:tables['G1']['ratios'].pop()
        with pytest.raises(ValueError,match='contrast'):select_complete_contrasts(tables)


def test_wrong_phase_and_zero_ratio_are_rejected():
    tables=fixture();tables['G1']['ratios'][0]['phase']='research_execution'
    with pytest.raises(ValueError,match='contrast'):select_complete_contrasts(tables)
    tables=fixture();tables['G1']['ratios'][0]['point']=0.
    with pytest.raises(ValueError,match='Positive'):select_complete_contrasts(tables)
