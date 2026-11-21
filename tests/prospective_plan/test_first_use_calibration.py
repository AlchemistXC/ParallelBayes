import math
from hashlib import sha256
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/prospective_plan'))
from first_use_calibration import bounds, calibrate
from first_use_policy import WINDOWS


def record(index, score):
    predictions={w:2. for w in WINDOWS}
    observed={w:2.*math.exp(-score) for w in WINDOWS}
    return {'input_sha256':sha256(f'input-{index}'.encode()).hexdigest(),'dimension':8,'rows':256,
            'predicted':predictions,'observed':observed}


def test_finite_sample_simultaneous_rank_over_all_heldout_positions():
    # Under exchangeability, each of ten distinct scores is equally likely to
    # occupy the future position. Nine calibration scores yield rank nine.
    data=[record(i,i/10) for i in range(10)]
    for i,row in enumerate(data):
        for w in WINDOWS:
            if w != WINDOWS[i % len(WINDOWS)]:
                row['observed'][w]=2.*math.exp(-i/30)
    covered=0
    for future in range(10):
        calibration=calibrate([x for i,x in enumerate(data) if i!=future],
                              fit_input_sha256s=['f'*64],model_sha256='a'*64)
        assert calibration['rank_1_based']==9
        lower=bounds(data[future]['predicted'],calibration,input_sha256=data[future]['input_sha256'])
        covered+=all(lower[w] <= data[future]['observed'][w]+1e-14 for w in WINDOWS)
    assert covered==9


def test_insufficient_inputs_or_failed_delivery_conservatively_zero_all_bounds():
    small=calibrate([record(i,i/10) for i in range(8)],fit_input_sha256s=['f'*64],model_sha256='b'*64)
    assert small['threshold_infinite'] and all(v==0 for v in bounds(record(10,0)['predicted'],small,input_sha256='e'*64).values())
    data=[record(i,i/10) for i in range(9)]
    data[3]['observed'][8]=None
    failed=calibrate(data,fit_input_sha256s=['f'*64],model_sha256='b'*64)
    assert failed['threshold_infinite'] and failed['failed_observations']==[{'input_sha256':data[3]['input_sha256'],'window':8}]
    assert all(v==0 for v in bounds(record(10,0)['predicted'],failed,input_sha256='e'*64).values())


def test_holdout_overlap_and_missing_windows_are_rejected():
    data=[record(i,i/10) for i in range(9)]
    valid=calibrate(data,fit_input_sha256s=['f'*64],model_sha256='c'*64)
    with pytest.raises(ValueError,match='overlaps'):
        bounds(data[0]['predicted'],valid,input_sha256=data[0]['input_sha256'])
    with pytest.raises(ValueError,match='disjoint'):
        calibrate(data,fit_input_sha256s=[data[0]['input_sha256']],model_sha256='c'*64)
    data[0]['dimension']=32
    with pytest.raises(ValueError,match='development dimensions'):
        calibrate(data,fit_input_sha256s=['f'*64],model_sha256='c'*64)
    data[0]['dimension']=8
    del data[0]['observed'][4]
    with pytest.raises(ValueError,match='all planned windows'):
        calibrate(data,fit_input_sha256s=['f'*64],model_sha256='c'*64)
