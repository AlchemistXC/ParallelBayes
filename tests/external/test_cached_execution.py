"""Prepared fixed-input execution preserves numerical output and provenance."""
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python')]


@pytest.mark.parametrize('kernel,executor',[('rwm','sequential'),('rwm','online_picard'),('mala','sequential'),('mala','quasi_deer')])
def test_prepared_replay_keeps_original_inputs_and_independent_path(kernel,executor):
    from parallelbayes.torch_backend.models import make_model
    from parallelbayes.torch_backend.sampling import settings,random_tape,audit_path
    from cached_execution import PreparedExecutor
    model=make_model(dict(kind='gaussian',dimension=2,mean=[0.,0.],covariance=[[1.,.3],[.3,1.]]),'cpu')
    c=settings(dict(kernel=kernel,executor=executor,chains=2,draws=16,step_size=.1,window=4,audit=False))
    tape=random_tape(c,2);original={k:v.copy() for k,v in tape.items()}
    prepared=PreparedExecutor(model,c,tape)
    tape['noise'][:]=999.  # Provider owns a prepared copy; caller cannot change its path.
    first=prepared.run();second=prepared.run()
    assert first['status']==second['status']=='candidate'
    assert not first['has_prior_execution'] and second['has_prior_execution']
    assert first['samples_eligible'] is second['samples_eligible'] is False
    assert first['executor_wall_seconds']>0 and second['executor_wall_seconds']>0
    assert second['transfer_included_in_executor_wall'] is False
    assert second['audit_included_in_executor_wall'] is False
    assert first['tape_sha256']==second['tape_sha256']
    np.testing.assert_array_equal(first['unconstrained'],second['unconstrained'])
    np.testing.assert_array_equal(first['accept'],second['accept'])
    oracle=audit_path(model,c,np.zeros((2,2)),original,second['unconstrained'],second['accept'])
    assert oracle['passed'] and oracle['acceptance_mismatches']==[0,0]


def test_cached_solver_failure_remains_ineligible_and_keeps_candidate_path():
    from parallelbayes.torch_backend.models import make_model
    from parallelbayes.torch_backend.sampling import settings,random_tape
    from cached_execution import PreparedExecutor
    model=make_model(dict(kind='gaussian',dimension=2,mean=[0.,0.],covariance=[[1.,.6],[.6,1.]]),'cpu')
    c=settings(dict(kernel='mala',executor='quasi_deer',chains=1,draws=16,step_size=.4,window=16,max_iter=1,audit=False))
    tape=random_tape(c,2);tape['log_uniform'][:]=-1000
    replay=PreparedExecutor(model,c,tape)
    for result in (replay.run(),replay.run()):
        assert result['status']=='failed' and not result['samples_eligible']
        assert result['diagnostics']['status']==1 and result['unconstrained'].shape==(1,16,2)
        assert result['executor_wall_seconds']>0
