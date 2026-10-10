from pathlib import Path
import sys
import math
import pytest
from flint import arb,arb_series,ctx
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/analysis'))
from wells_ball_target import WellsBallTarget


@pytest.fixture(autouse=True)
def precision():
    old=ctx.prec;cap=ctx.cap;ctx.prec=128;ctx.cap=5
    yield
    ctx.prec=old;ctx.cap=cap


def fixture():return WellsBallTarget([0.,0.,100.,100.],[0,1,0,1],[0.,0.],[[1.,.25],[0.,1.]])


@pytest.mark.parametrize('axis',[0,1])
def test_fourth_derivatives_enclose_independent_power_series(axis):
    model=fixture();x=arb('.2');y=arb('-.3')
    xs=arb_series([x,1 if axis==0 else 0],prec=5);ys=arb_series([y,1 if axis==1 else 0],prec=5)
    a=xs+ys/4;b=ys
    lp=-(1+a.exp()).log()-(1+(-a).exp()).log()-(1+(a+b).exp()).log()-(1+(-(a+b)).exp()).log()
    f=(lp+4*arb(2).log()).exp()
    formulas=[f,a*f,b*f,a*a*f,b*b*f,f/(1+(-a).exp()),f/(1+(-(a+b)).exp())]
    # A nonzero box must contain the derivative at its interior point.
    bounds=model.fourth(x+arb(0,'1e-6'),y+arb(0,'1e-6'),axis)
    for bound,series in zip(bounds,formulas):assert bound.contains(series[4]*24)


def test_value_uses_jacobian_and_binary_distance_contract():
    m=WellsBallTarget([.1,.1,100.,100.],[0,1,0,1],[0.,0.],[[2.,0.],[0.,3.]])
    values=m.value(arb(0),arb(0))
    assert values[0].contains(arb(6)) and values[5].contains(arb(3))
    assert m.groups[0][0]==arb(.1/100.)


def test_tail_sector_certification_and_invalid_geometry():
    m=fixture();result=m.tail(radius=12,sectors=256)
    assert result['minimum_decay']>0 and all(x>0 and x.is_finite() for x in result['bounds'])
    with pytest.raises(ValueError):WellsBallTarget([0,1],[0,1],[0,0],[[1,0],[0,0]])


def test_wide_box_has_finite_monotonic_logistic_enclosure():
    from wells_ball_target import sigmoid
    p=sigmoid(arb(-1000).union(arb(1000)))
    assert p.is_finite() and p.contains(sigmoid(arb(-1000))) and p.contains(sigmoid(arb(1000)))
    m=fixture();x=arb(-12).union(arb(12))
    assert all(v.is_finite() for v in m.fourth(x,x,0))
    with pytest.raises(ValueError,match='Binary'):WellsBallTarget([0,1],[.5,1],[0,0],[[1,0],[0,1]])
