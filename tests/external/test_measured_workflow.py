"""Separate ordinary-process timing from post-process trajectory eligibility."""
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python')]


def test_external_audit_preserves_candidate_and_quarantines_wrong_trajectory():
    from parallelbayes.torch_backend.models import make_model
    from parallelbayes.torch_backend.sampling import sample,settings,random_tape
    from measured_workflow import audit_candidate
    model=make_model(dict(kind='gaussian',dimension=2,mean=[0.,0.],covariance=[[1.,0.],[0.,1.]]),'cpu')
    config=settings(dict(kernel='rwm',executor='sequential',chains=2,draws=16,step_size=.3,audit=False))
    tape=random_tape(config,2);candidate=sample(model,config,tape)
    before=candidate['unconstrained'].copy()
    verified=audit_candidate(model,config,tape,candidate)
    assert verified['status']=='completed' and verified['samples_eligible']
    assert verified['audit']['passed'] and verified['audit']['acceptance_mismatches']==[0,0]
    assert candidate['audit'] is None and candidate['guarantee']=='executor_output_standard_only'
    np.testing.assert_array_equal(candidate['unconstrained'],before)
    wrong=dict(candidate,unconstrained=before+10.)
    rejected=audit_candidate(model,config,tape,wrong)
    assert rejected['status']=='failed' and not rejected['samples_eligible']
    assert rejected['failure_category']=='numerical_failure'
    assert rejected['candidate_arrays_retained']
    np.testing.assert_array_equal(wrong['unconstrained'],before+10.)
    with pytest.raises(ValueError,match='audit'):
        audit_candidate(model,dict(config,audit=True),tape,candidate)


def test_process_interval_includes_startup_until_exit_and_keeps_nonzero_exit(tmp_path):
    from measured_workflow import ordinary_process
    child="import sys,time; time.sleep(.02); print('ordinary-output',flush=True); sys.exit(7)"
    result=ordinary_process([sys.executable,'-c',child],tmp_path)
    assert result['return_code']==7
    assert result['ordinary_process_wall_seconds']>=.02
    assert (tmp_path/'ordinary-stdout.log').read_text().strip()=='ordinary-output'
    assert result['outer_audit_included'] is False
    assert result['nested_sampler_timings_additive'] is False
