"""Failures and missing inputs must remain visible in cross-kernel comparison."""
from pathlib import Path
from hashlib import sha256
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/analysis'))
from prospective_first_use_summary import align_reference_estimates, reference_sensitivity


def test_asymmetric_missing_inputs_keep_original_denominators():
    a=np.linspace(.01,.1,32);b=np.linspace(.1,.3,32)
    a[0]=np.nan;b[1]=np.nan
    report=reference_sensitivity(a,b,0.,.001,seed=2)
    assert (report['planned'],report['valid_a'],report['valid_b'],report['common'])==(32,31,31,30)
    assert report['direction']=='a'


def test_infinite_estimate_is_invalid_instead_of_missing():
    a=np.zeros(32);b=np.ones(32);a[3]=np.inf
    with pytest.raises(ValueError,match='infinite estimates'):
        reference_sensitivity(a,b,0.,.001,seed=1)
    with pytest.raises(ValueError,match='32 aligned'):
        reference_sensitivity(a[:31],b[:31],0.,.001,seed=1)


def test_empty_and_unidentifiable_comparisons_are_not_ranked():
    report=reference_sensitivity(np.full(32,np.nan),np.ones(32),0.,.01,seed=1)
    assert (report['valid_a'],report['valid_b'],report['common'])==(0,32,0)
    assert report['loss_difference'] is None and report['direction'] is None
    same=reference_sensitivity(np.ones(32),np.ones(32),0.,.01,seed=1)
    assert same['loss_difference']==[0.,0.] and same['direction'] is None


def test_nonfinite_reference_range_and_loss_overflow_are_rejected():
    with pytest.raises(ValueError,match='endpoints'):
        reference_sensitivity(np.zeros(32),np.ones(32),1e308,1e308,seed=1)
    with pytest.raises(FloatingPointError):
        reference_sensitivity(np.full(32,1e308),np.full(32,-1e308),0.,.01,seed=1)


def test_alignment_uses_input_hashes_not_mapping_order():
    ids=[sha256(str(i).encode()).hexdigest() for i in range(32)]
    a=[(ident,float(i)) for i,ident in enumerate(ids) if i!=0]
    b=[(ident,None if i==1 else float(i+100)) for i,ident in reversed(list(enumerate(ids)))]
    aligned=align_reference_estimates(ids,a,b)
    assert aligned['missing_a']==[ids[0]] and aligned['missing_b']==[ids[1]]
    assert np.isnan(aligned['a'][0]) and np.isnan(aligned['b'][1])
    assert aligned['a'][2]==2 and aligned['b'][2]==102
    report=reference_sensitivity(aligned['a'],aligned['b'],0.,.01,seed=1)
    assert (report['valid_a'],report['valid_b'],report['common'])==(31,31,30)


def test_alignment_rejects_duplicate_unknown_and_nonfinite_inputs():
    ids=[sha256(str(i).encode()).hexdigest() for i in range(32)]
    with pytest.raises(ValueError,match='unique'):
        align_reference_estimates(ids[:-1]+[ids[0]],[], [])
    with pytest.raises(ValueError,match='unknown'):
        align_reference_estimates(ids,[('f'*64,1.)], [])
    with pytest.raises(ValueError,match='finite'):
        align_reference_estimates(ids,[(ids[0],np.inf)], [])
    with pytest.raises(ValueError,match='duplicate'):
        align_reference_estimates(ids,[(ids[0],1.),(ids[0],2.)], [])
