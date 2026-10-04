"""Runtime raw-to-summary adapter uses full planned units and actual arrays."""
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python')]


@pytest.mark.skipif(sys.platform!='darwin',reason='Artificial evidence producer uses native Mac runtime')
def test_only_eligible_registered_raw_output_enters_function_analysis(tmp_path):
    from formal_coordinator import TaskCoordinator
    from formal_evidence import RuntimeEvidence
    from formal_runtime import file_hash
    from mechanism_runner import actual_hash
    from parallelbayes.reference import make_reference
    from formal_runtime_analysis import extract_task
    evidence_root=tmp_path/'evidence';evidence_root.mkdir()
    model=make_reference(dict(kind='gaussian',dimension=2,mean=[0.,0.],covariance=[[1.,0.],[0.,1.]]))
    tape=dict(noise=np.zeros((4,5,2)),log_uniform=np.zeros((4,5)),directions=np.ones((4,5,2)))
    payload=dict(tape,initial=np.zeros((4,2)),nuts_seeds=np.arange(4,dtype=np.uint32))
    inputs=evidence_root/'inputs.npz';np.savez_compressed(inputs,**payload)
    draws=np.zeros((4,5,2));draws[:,0,0]=99.
    draws[:,1:,0]=[[0.,1.,2.,-1.],[-2.,-1.,0.,1.],[2.,3.,4.,1.],[0.,0.,0.,0.]]
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys,numpy as np
from pathlib import Path
out=Path(sys.argv[2]);r=json.loads(Path(sys.argv[1]).read_text());x=np.array(r['artificial_draws'],dtype=float)
np.savez_compressed(out/'fit.npz',draws=x,unconstrained=x,accept=np.ones(x.shape[:2],bool))
audit=dict(passed=True,acceptance_mismatches=[0,0,0,0],oracle='artificial_fixture_not_sampler_evidence')
(out/'fit.json').write_text(json.dumps(dict(status=r['status'],target_id=r['target_id'],config=r['config'],audit=audit,tape_sha256=r['tape_sha256'])))
(out/'worker-result.json').write_text(json.dumps(dict(status=r['status'],samples_eligible=r['status']=='completed',target_id=r['target_id'],task=r['science_task'],protocol_sha256='science-fixture',full_MH_audit=audit)))
''')
    c=TaskCoordinator(tmp_path/'host.lock');locations={};contracts=[]
    for status in ('completed','failed','contradictory'):
        science=dict(id=status,model='G',kernel='mala' if status=='contradictory' else 'rwm',executor='sequential',device='cpu',replicate=0)
        task=dict(science,protocol_sha256='registry-fixture')
        config=dict(kernel='rwm',executor='sequential',device='cpu',chains=4,draws=5,initial=payload['initial'].tolist(),step_size=.1)
        request=dict(task_id=status,status='completed' if status=='contradictory' else status,science_task=science,target_id=model.target_id,
                     artificial_draws=draws.tolist(),config=config,tape_sha256=actual_hash(tape))
        out=evidence_root/status;c.run(task,request,worker,out,0,2**30);locations[str(out)]=status
        contracts.append(dict(task=task,original=str(out),model='G',workflow=status,budget=4,replicate='0',
            scientific_task=science,scientific_protocol_sha256='science-fixture',science_directory='attempt-0001',
            target_id=model.target_id,chains=4,discard=1,expected_config=config,
            input_relative='inputs.npz',input_sha256=file_hash(inputs),actual_input_sha256=actual_hash(payload)))
    snapshot=evidence_root/'snapshot.sqlite3'
    with sqlite3.connect(c.registry_path/'registry.sqlite3') as src:
        with sqlite3.connect(snapshot) as dst:src.backup(dst)
    with RuntimeEvidence(snapshot,file_hash(snapshot),evidence_root,locations) as evidence:
        good=extract_task(evidence,contracts[0],model,tmp_path/'analysis-good')
        assert good['means']==[.625,2.625,.25] and good['function_status']=='completed'
        assert good['history']['summary']['attempt_count']==1
        bad=extract_task(evidence,contracts[1],model,tmp_path/'analysis-failed')
        assert bad['means'] is None and bad['outcome']=='output_failure_unclassified'
        assert bad['function_status']=='unavailable'
        assert not (tmp_path/'analysis-failed/functions.bin').exists()
        wrong=dict(contracts[0],target_id='different-model')
        with pytest.raises(ValueError,match='target'):
            extract_task(evidence,wrong,model,tmp_path/'wrong-model')
        with pytest.raises(ValueError,match='Kernel/executor'):
            extract_task(evidence,contracts[2],model,tmp_path/'contradictory-kernel')


def test_planned_aggregation_keeps_resource_failure_unknown_retry_cost_and_not_run(tmp_path):
    from formal_runtime_analysis import aggregate_records
    from formal_outcomes import summarize_attempts
    def attempt(name,outcome,seconds,binding):
        return dict(attempt_id=name,binding_sha256=binding,outcome=outcome,seconds=seconds,
                    cost_scope='runtime_v1_preflight_through_terminal')
    records=[]
    for workflow in ('a','b'):
        for i in range(4):
            binding=workflow+str(i)
            if workflow=='b':history=[attempt(binding,'valid',6.+i,binding)];means=[float(i),0.]
            elif i==0:
                history=[attempt('a0-old','infrastructure_interruption',2.,binding),attempt('a0-retry','valid',10.,binding)];means=[1.,0.]
            elif i==1:history=[attempt('a1','resource_failure',5.,binding)];means=None
            elif i==2:
                history=[attempt('a2-old','infrastructure_interruption',None,binding),attempt('a2-retry','valid',4.,binding)];means=[3.,0.]
            else:history=[];means=None
            summary=summarize_attempts(history)
            records.append(dict(id=binding,model='G',workflow=workflow,budget=16,replicate=str(i),
                history=dict(attempts=history,summary=summary),outcome=summary['outcome'],means=means,
                names=['mean','event'] if means is not None else None,
                function_status='completed' if means is not None else 'unavailable'))
    reference=dict(names=['mean','event'],means=[0.,0.],kinds=['analytic','unresolved'],mcse=[0.,None])
    report=aggregate_records(records,model_name='G',replicate_ids=['0','1','2','3'],workflow_names=['a','b'],
        budgets=[16],reference=reference,namespace='runtime-fixture',output=tmp_path/'summary',pairs=[('a','b')])
    mean=json.loads((tmp_path/'summary/function-0.json').read_text())
    event=json.loads((tmp_path/'summary/function-1.json').read_text())
    cost=json.loads((tmp_path/'summary/cost.json').read_text())
    assert report['planned']==8 and report['available_bca_intervals']==0
    assert mean['workflows']['a@16']['conditional_squared_discrepancy']==5.
    assert mean['workflows']['a@16']['unconditional_squared_discrepancy'] is None
    assert mean['pairs'][0]['validity_table']==dict(n11=2,n10=0,n01=2,n00=0)
    assert event['workflows']['b@16']['conditional_squared_discrepancy'] is None
    assert cost['workflows']['a@16']['total_recorded_seconds']==21.
    assert cost['workflows']['a@16']['known_partial_task_seconds']==4.
    assert cost['workflows']['a@16']['unusable_output_cost_seconds']==5.
    assert cost['workflows']['a@16']['outcome_counts']['resource_failure']==1
    assert cost['workflows']['a@16']['outcome_counts']['not_run']==1
    assert cost['workflows']['a@16']['failure_rate_interval'] is None
    assert cost['pairs'][0]['geometric_mean_ratio'] is None
    with pytest.raises(ValueError,match='planned'):
        aggregate_records(records[:-1],model_name='G',replicate_ids=['0','1','2','3'],workflow_names=['a','b'],
            budgets=[16],reference=reference,namespace='runtime-fixture',output=tmp_path/'missing',pairs=[('a','b')])
