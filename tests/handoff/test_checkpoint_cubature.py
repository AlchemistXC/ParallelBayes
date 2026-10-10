from pathlib import Path
import sys
import pytest
from flint import arb,ctx
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/analysis'))
from checkpoint_cubature import Engine,pack,unpack
from verified_cubature import integer_power


def value(x,y):return [integer_power(x,4)+integer_power(y,4)]
def fourth(x,y,axis):return [arb(24)]


def engine(p,identity='test',value_fn=value,maxwork=10000):
    return Engine(p,identity,value_fn,fourth,[(-1,1,-1,0),(-1,1,0,1)],[['1e-5'],['1e-5']],
                  method='gauss2',maximum_cells=1000,maximum_charged_evaluations=maxwork)


def test_ball_restore_can_only_widen_not_narrow():
    ctx.prec=128
    for x in [arb(1)/3,arb(-1).union(arb(2)),arb('1e-40')]:assert unpack(pack(x)).contains(x)


def test_persisted_partition_resumes_and_contains_integral(tmp_path):
    ctx.prec=128;e=engine(tmp_path/'state.sqlite');e.advance(32);before=e.counters();e.close()
    e=engine(tmp_path/'state.sqlite');assert e.counters()==before
    e.advance(32);v=sum((row[0] for row in e.enclosures()),arb(0));assert v.contains(arb(8)/5)
    assert e.counters()['committed_splits']==64;e.close()


def test_interrupted_evaluation_remains_charged_with_old_partition(tmp_path):
    ctx.prec=128;p=tmp_path/'state.sqlite';e=engine(p);old=e.counters()
    e.value=lambda x,y:(_ for _ in ()).throw(RuntimeError('injected evaluation failure'))
    with pytest.raises(RuntimeError,match='injected'):e.advance(4)
    e.close();e=engine(p)
    assert e.counters()['active_cells']==old['active_cells']
    assert e.counters()['charged_evaluations_upper_bound']==old['charged_evaluations_upper_bound']+48
    e.advance(1);assert sum((x[0] for x in e.enclosures()),arb(0)).contains(arb(8)/5);e.close()


def test_identity_and_budget_are_enforced(tmp_path):
    ctx.prec=128;p=tmp_path/'state.sqlite';e=engine(p,maxwork=24);e.advance(5)
    assert e.counters()['charged_evaluations_upper_bound']==24 and e.advance(1)=='work_limit';e.close()
    with pytest.raises(ValueError,match='identity'):engine(p,identity='changed',maxwork=24)


def test_uncertain_event_cut_is_propagated_through_region_widths(tmp_path):
    ctx.prec=128;cut=arb(1)/3
    e=Engine(tmp_path/'event.sqlite','uncertain-boundary',lambda x,y:[arb(1)],lambda x,y,axis:[arb(0)],
        [(-1,1,-1,cut),(-1,1,cut,1)],[['1e-10'],['1e-10']],method='gauss2',maximum_cells=8,maximum_charged_evaluations=100)
    a,b=e.enclosures();assert a[0].contains(arb(8)/3) and b[0].contains(arb(4)/3)
    assert (a[0]+b[0]).contains(arb(4));e.close()
