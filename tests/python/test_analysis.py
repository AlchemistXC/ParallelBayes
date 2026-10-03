"""Scientific analysis checks using synthetic receipts, without rerunning kernels."""
import importlib.util
import json
from pathlib import Path
import numpy as np


def analysis():
    spec=importlib.util.spec_from_file_location('analysis',Path(__file__).parents[2]/'benchmark/analysis/analyze.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_funnel_functions_compare_same_constrained_estimands():
    a=analysis()
    v=np.array([-3.,0.,3.]);z=np.array([-.8,.2,.4])
    constrained=np.stack([v,z*np.exp(v/2)],axis=-1)[None]
    expected=np.stack([v/3,np.tanh(v/3),z>0,np.cos(z)],axis=-1)[None]
    for kind in ['funnel','funnel_noncentered']:
        np.testing.assert_allclose(a.functions({'kind':kind},constrained),expected)


def test_failures_remain_in_cost_and_precision_and_rebuild_is_stable(tmp_path,monkeypatch):
    a=analysis();rows=[]
    spec={'kind':'gaussian','dimension':1,'mean':[0.],'covariance':[[1.]]}
    for r in range(2):
        task={'model':'G','config':{'kernel':'rwm','executor':'sequential'},'retained_draws':4,'replicate':r,'discard':0}
        result={'status':'completed' if r==0 else 'failed','timing':{'total':9.,'sample':2.},'timing_replay_overhead':1.}
        state={'attempt':'attempt-001','elapsed_including_output':11.}
        folder=tmp_path/'runs'/'tasks'/a.fingerprint(task)[:20]/state['attempt'];folder.mkdir(parents=True)
        (folder/'result.json').write_text(json.dumps(result))
        raw={'draws':np.array([[[-1.],[0.],[1.],[0.]],[[1.],[0.],[-1.],[0.]]])}
        rows.append((task,result,raw,state))
    protocol=tmp_path/'p.json';p={'models':{'G':spec},'tasks':[x[0] for x in rows],'policy':{'replicates':2,'epsilon':[.1,.2]},'source_sha256':'source','platforms':['cpu']}
    p['protocol_sha256']=a.fingerprint(p);protocol.write_text(json.dumps(p))
    identity={'protocol_sha256':p['protocol_sha256'],'source_sha256':'source','platform':'cpu'}
    (tmp_path/'runs'/'manifest.json').write_text(json.dumps({'identity':identity}))
    for task,result,raw,state in rows:
        folder=tmp_path/'runs'/'tasks'/a.fingerprint(task)[:20]
        (folder/'state.json').write_text(json.dumps(dict(state,task=task,status=result['status'])))
    reference=tmp_path/'ref.json';reference.write_text('{}')
    reference.with_suffix('.provenance.json').write_text(json.dumps({'summary_sha256':a.file_hash(reference),'model_sha256':{}}))
    monkeypatch.setattr(a,'records',lambda root:iter(rows))
    out=tmp_path/'out'
    with np.errstate(invalid='ignore',divide='ignore'):
        result=a.formal_summary(protocol,tmp_path/'runs',reference,out)[0]
        rebuilt=a.formal_summary(protocol,tmp_path/'runs',reference,out)[0]
    assert result['attempted']==2 and result['failed']==1
    assert result['failed_attempt_cost_seconds']==10.
    assert result['all_attempt_cost_seconds']>20.
    assert all(x['status']=='not_assessable' for x in result['precision_assessment'])
    assert result['all_attempt_cost_seconds']==rebuilt['all_attempt_cost_seconds']
    assert result['max_mean_squared_error']==rebuilt['max_mean_squared_error']
    p['models']['G']['mean']=[2.];protocol.write_text(json.dumps(p))
    import pytest
    with pytest.raises(ValueError,match='freeze'):a.verify_inputs(protocol,tmp_path/'runs')


def test_constant_function_is_uninformative_not_perfect_convergence():
    a=analysis()
    assert np.isnan(a.split_rhat(np.zeros((4,20,1)))).all()
    assert np.isnan(a.split_rhat(np.ones((4,20,1)))).all()
    stuck=np.zeros((4,20,1));stuck[2:]=1
    assert np.isinf(a.split_rhat(stuck)).all()
