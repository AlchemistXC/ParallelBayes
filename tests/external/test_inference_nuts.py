"""Public whole-run baseline: custom Model, dispersed starts and replay."""
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'r-package/inst/python'))
sys.path.insert(0,str(ROOT/'examples'))
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_custom_target_nuts_preserves_explicit_starts_rng_and_replay():
    import torch
    import random
    from parallelbayes import make_model
    from affine_target import affine_model
    from inference_nuts import sample_nuts
    base=make_model(dict(kind='gaussian',dimension=1,mean=[100.],covariance=[[4.]]),backend='torch')
    model=affine_model(base,[100.],[[2.]])
    before=torch.get_rng_state().clone();py_before=random.getstate();np_before=np.random.get_state()
    result=sample_nuts(model,initial=[[-2.],[2.]],chain_seeds=[561021,561029],draws=64,warmup=96,max_tree_depth=6)
    assert result['status']=='completed'
    assert result['draws'].shape==(2,64,1)
    np.testing.assert_array_equal(result['initial'],[[-2.],[2.]])
    np.testing.assert_allclose(result['draws'],100+2*result['unconstrained'],atol=1e-12)
    # Loose sanity only; this is not the formal accuracy gate.
    assert abs(result['draws'].mean()-100)<1.5
    assert np.all(np.isfinite(result['unconstrained']))
    assert result['warmup_states'].shape==(2,96,1)
    assert result['timing']['warmup']>0 and result['timing']['sample']>0
    assert torch.equal(torch.get_rng_state(),before) and random.getstate()==py_before
    np.testing.assert_array_equal(np.random.get_state()[1],np_before[1])
    replay=sample_nuts(model,initial=[[-2.],[2.]],chain_seeds=[561021,561029],draws=64,warmup=96,max_tree_depth=6)
    np.testing.assert_array_equal(result['unconstrained'],replay['unconstrained'])
    assert result['fixed_mh_tape_comparison'] is False
    assert result['mass_matrix_adaptation'] is True
    assert len(result['chain_records'])==2


def test_nuts_unrepresentable_original_output_is_quarantined_with_partial_states():
    from parallelbayes import make_model
    from inference_nuts import sample_nuts
    model=make_model(dict(kind='lognormal',mu=1000.,sigma=1.),backend='torch')
    result=sample_nuts(model,initial=[[1000.]],chain_seeds=[561031],draws=8,warmup=16,max_tree_depth=3)
    assert result['status']=='failed'
    assert result['draws'] is None and result['unconstrained'] is None
    assert len(result['partial_chains'][0]['sample'])==8
    assert 'transform' in result['error']
