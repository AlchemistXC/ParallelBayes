from pathlib import Path
import sys
import pytest
from flint import arb,ctx
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/analysis'))
from verified_cubature import rectangle_rule,integrate,integer_power


@pytest.fixture(autouse=True)
def precision():
    old=ctx.prec;ctx.prec=128
    yield
    ctx.prec=old


@pytest.mark.parametrize('method',['gauss2','simpson'])
def test_polynomial_remainder_contains_true_integral_and_omission_fails(method):
    value=lambda x,y:[integer_power(x,4)+integer_power(y,4)]
    fourth=lambda x,y,axis:[arb(24)]
    cell=rectangle_rule(value,fourth,(-1,1,-1,1),method)
    truth=arb(8)/5
    assert cell.enclosures()[0].contains(truth)
    assert not cell.value[0].contains(truth) # injected omission of required remainder


@pytest.mark.parametrize('method',['gauss2','simpson'])
def test_gaussian_finite_box_and_halfspace(method):
    def value(x,y):return [(-(x*x+y*y)/2).exp()]
    def fourth(x,y,axis):
        z=x if axis==0 else y
        return [value(x,y)[0]*(integer_power(z,4)-6*z*z+3)]
    for box,factor in [((-2,2,-2,2),arb(1)),((-2,2,0,2),arb(1)/2)]:
        r=integrate(value,fourth,box,['1e-4'],method=method,max_cells=4096,max_evaluations=100000)
        truth=2*arb.pi()*(arb(2).sqrt().erf())**2*factor
        assert r['enclosures'][0].contains(truth)
        assert r['status']=='interior_tolerance_met'
        assert not r['enclosures'][0].contains(2*arb.pi()*factor) # omitted tail would be a false total integral


def test_work_guard_returns_wide_valid_bound_not_false_precision():
    r=integrate(lambda x,y:[integer_power(x,4)+integer_power(y,4)],lambda x,y,axis:[arb(24)],(-1,1,-1,1),['1e-30'],max_cells=1)
    assert r['status']=='work_limit' and r['cells']==1 and r['enclosures'][0].contains(arb(8)/5)
    assert r['enclosures'][0].rad()>arb('1e-30')


def test_arbitrary_binary_input_and_signed_integrals_are_not_rounded_to_decimal():
    a=0.1;b=0.2
    r=rectangle_rule(lambda x,y:[x-3],lambda x,y,axis:[arb(0)],(a,b,0.,1.))
    aa,bb=arb(a),arb(b)
    truth=(bb*bb-aa*aa)/2-3*(bb-aa)
    assert r.enclosures()[0].contains(truth)
    assert arb(a)!=arb('0.1')


def test_inconsistent_or_nonfinite_bounds_are_rejected():
    with pytest.raises(ValueError):rectangle_rule(lambda x,y:[arb(1)],lambda x,y,axis:[arb('nan')],(0,1,0,1))
    with pytest.raises(ValueError):integrate(lambda x,y:[arb(1)],lambda x,y,axis:[arb(0)],(0,1,0,1),[0])


def test_cross_zero_integer_powers_and_adjacent_float_limit():
    x=arb(-2).union(arb(2))
    p=integer_power(x,4)
    assert p.is_finite() and p.contains(arb(0)) and p.contains(arb(16))
    import math
    a=1.;b=math.nextafter(a,2.)
    r=integrate(lambda x,y:[arb(1)],lambda x,y,axis:[arb(24)],(a,b,a,b),['1e-110'])
    assert r['status']=='coordinate_resolution' and r['cells']==1
    assert r['enclosures'][0].contains((arb(b)-arb(a))*(arb(b)-arb(a)))
