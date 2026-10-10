from pathlib import Path
import sys
import pytest
from flint import arb,ctx
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/analysis'))
from run_w1_enclosure import posterior,nonnegative


def test_signed_numerator_ratio_and_distinct_moment_tails():
    ctx.prec=128
    regions=[[arb(2),arb(-4),arb(2),arb(10),arb(4),arb(1),arb(1)],
             [arb(1),arb(-1),arb(2),arb(3),arb(4),arb('.4'),arb('.5')]]
    tails=list(map(arb,['.1','.2','.3','.4','.5']))
    r=posterior(regions,tails);assert r['ratios'] is not None and not r['met']
    assert r['ratios'][0].contains(arb('-5.2')/arb('3.1'))
    assert r['ratios'][0].contains(arb('-4.8')/3)
    assert r['ratios'][2].contains(arb('13.4')/3)
    assert r['ratios'][-1].contains(1/arb('3.1')) and r['ratios'][-1].contains(arb('1.1')/3)


def test_no_division_with_unresolved_normalizer_or_negative_positive_quantity():
    a=[arb(0,2)]*7;r=posterior([a,a],[arb(0)]*5)
    assert r['ratios'] is None and r['status']=='normalizer_lower_unresolved'
    with pytest.raises(ArithmeticError):nonnegative(arb(-1))


def test_narrow_continuous_intervals_do_not_hide_bad_event_precision():
    regions=[[arb(1),arb(0),arb(0),arb(1),arb(1),arb('.5'),arb('.5')],
             [arb('1e-11', '2e-13'),arb(0),arb(0),arb(0),arb(0),arb(0),arb(0)]]
    r=posterior(regions,[arb(0)]*5)
    assert r['ratios'] is not None and not r['met']
