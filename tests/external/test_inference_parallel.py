"""Actual spawn processes at the agreed whole-run baseline seam."""
from pathlib import Path
import sys
import os
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'r-package/inst/python'))
sys.path.insert(0,str(ROOT/'examples'))
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_spawned_cpu_chains_replay_serial_nuts_with_fixed_starts_and_rng_states():
    import torch
    from parallelbayes import make_model
    from affine_target import affine_model
    from inference_nuts import sample_nuts
    from inference_parallel_nuts import sample_parallel_nuts
    torch.set_num_threads(1)
    base=make_model(dict(kind='gaussian',dimension=2,mean=[1.,-2.],covariance=[[4.,2.],[2.,10.]]),backend='torch')
    model=affine_model(base,[1.,-2.],[[2.,0.],[1.,3.]])
    initial=[[-2.,1.],[2.,-1.]];seeds=[613001,613009]
    serial=sample_nuts(model,initial,seeds,draws=32,warmup=64,max_tree_depth=5)
    parallel=sample_parallel_nuts(model.spec,model.target_id,initial,seeds,workers=2,threads_per_worker=1,
        draws=32,warmup=64,max_tree_depth=5)
    assert serial['status']==parallel['status']=='completed'
    np.testing.assert_array_equal(parallel['draws'],serial['draws'])
    np.testing.assert_array_equal(parallel['unconstrained'],serial['unconstrained'])
    np.testing.assert_array_equal(parallel['initial_torch_rng_states'],serial['initial_torch_rng_states'])
    assert parallel['timing']['pool_wall']>0
    assert parallel['process_start_method']=='spawn'
    assert all(r['worker_pid']!=os.getpid() and r['threads']==1 for r in parallel['worker_records'])
    assert parallel['components_are_additive'] is False


def test_process_identity_failure_cannot_return_ordinary_samples():
    from parallelbayes.reference import make_reference
    from inference_parallel_nuts import sample_parallel_nuts
    model=make_reference(dict(kind='gaussian',dimension=1))
    result=sample_parallel_nuts(model.spec,'wrong-target-id',[[-1.],[1.]],[613021,613029],
        workers=2,draws=8,warmup=8,max_tree_depth=3)
    assert result['status']=='failed'
    assert result['draws'] is None and result['unconstrained'] is None
    assert len(result['worker_errors'])==2
    assert all('identity' in r['error'] for r in result['worker_errors'].values())
