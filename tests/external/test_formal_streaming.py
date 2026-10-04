"""Raw-to-function extraction tested through its public research interface."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python')]


def test_original_parameter_functions_discard_prefix_and_preserve_chain_order(tmp_path):
    from formal_streaming import extract_functions
    from parallelbayes.reference import make_reference
    model=make_reference(dict(kind='gaussian',dimension=2,mean=[0.,0.],covariance=[[1.,0.],[0.,1.]]))
    draws=np.zeros((4,5,2));draws[:,0,0]=99.
    draws[:,1:,0]=[[0.,1.,2.,-1.],[-2.,-1.,0.,1.],[2.,3.,4.,1.],[0.,0.,0.,0.]]
    path=tmp_path/'raw.npz'
    np.savez_compressed(path,draws=draws,unconstrained=draws,accept=np.ones((4,5),bool))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    report=extract_functions(path,digest,model,(4,5,2),1,tmp_path/'functions',
                             maximum_member_bytes=4096,prefix_lengths=(3,5))
    assert report['names']==['standard_q1','standard_q1_squared','standard_q1_gt1']
    assert report['means']==[.625,2.625,.25]
    assert report['shape']==[4,4,3]
    transported=np.fromfile(tmp_path/'functions/functions.bin',dtype='<f8').reshape((4,4,3),order='F')
    np.testing.assert_array_equal(transported[:,0,0],[0.,1.,2.,-1.])
    np.testing.assert_array_equal(transported[:,1,0],[-2.,-1.,0.,1.])
    assert report['retained_acceptance_rate']==1.
    assert set(report['path_prefix_sha256'])=={'3','5'}
    with pytest.raises(ValueError,match='checksum'):
        extract_functions(path,'0'*64,model,(4,5,2),1,tmp_path/'bad')
    with pytest.raises(MemoryError,match='member'):
        extract_functions(path,digest,model,(4,5,2),1,tmp_path/'large',maximum_member_bytes=32)
    assert not (tmp_path/'bad').exists() and not (tmp_path/'large').exists()


def test_scalar_aggregation_retains_failed_repetitions_cost_and_unresolved_reference(tmp_path):
    from formal_streaming import aggregate_model
    records=[]
    for workflow in ('a','b'):
        for i in range(4):
            failed=workflow=='a' and i==2
            records.append(dict(workflow=workflow,replicate=str(i),budget=16,
                outcome='numerical_failure' if failed else 'valid',
                means=None if failed else [float(i) if workflow=='a' else 0.,0.],
                seconds=float(i+1),function_status='unavailable' if failed else 'completed'))
    references=dict(names=['mean','rare_event'],means=[0.,0.],kinds=['analytic','unresolved'],mcse=[0.,None])
    report=aggregate_model(records,model_name='fixture',replicate_ids=['0','1','2','3'],
        workflow_names=['a','b'],budgets=[16],reference=references,namespace='streaming-test',
        output=tmp_path/'summary',pairs=[('a','b')],cost_phase='fixture_seconds')
    mean=json.loads((tmp_path/'summary/function-0.json').read_text())
    event=json.loads((tmp_path/'summary/function-1.json').read_text())
    cost=json.loads((tmp_path/'summary/cost.json').read_text())
    assert mean['workflows']['a@16']['conditional_squared_discrepancy']==pytest.approx(10/3)
    assert mean['workflows']['a@16']['unconditional_squared_discrepancy'] is None
    assert mean['pairs'][0]['validity_table']==dict(n11=3,n10=0,n01=1,n00=0)
    assert event['workflows']['b@16']['conditional_squared_discrepancy'] is None
    assert event['workflows']['b@16']['observed_estimate_mean']==0
    assert cost['workflows']['a@16']['total_recorded_seconds']==10
    assert cost['workflows']['a@16']['unusable_output_cost_seconds']==3
    assert report['planned']==8 and report['available_bca_intervals']==0
    with pytest.raises(ValueError,match='planned'):
        aggregate_model(records[:-1],model_name='fixture',replicate_ids=['0','1','2','3'],
            workflow_names=['a','b'],budgets=[16],reference=references,namespace='streaming-test',
            output=tmp_path/'missing',pairs=[('a','b')],cost_phase='fixture_seconds')
