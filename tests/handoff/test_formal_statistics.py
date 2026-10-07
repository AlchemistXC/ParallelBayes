"""Artificial scalar frames: no native execution or new scientific repetitions."""
import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'scripts/completion')]
from batch_contract import create_tasks
from formal_measurement_plan import create_measurement_plan
from formal_runtime import fingerprint,file_hash
from formal_cost_policy import summarize_task_costs
from formal_outcomes import summarize_attempts
from formal_statistics import summarize_model
from formal_uncertainty import load_plan


def artificial_frame(n=32):
    identity='artificial-receiver-statistics-no-sampling'
    tasks=create_tasks(identity,[dict(models=['G1'],replicates=list(range(n)),budgets=[8,16],
        workflows=['cpu-rwm-sequential','cpu-rwm-online_picard','cpu-nuts-spawn_chains'])])
    protocol=dict(identity=identity,scope_kind='formal_inference',tasks=tasks,protocol_sha256=fingerprint(identity))
    allocation=create_measurement_plan(identity,tasks,selected_per_batch=32)
    ref=dict(names=['varying','constant','unresolved','finite_reference','quadrature'],
        means=[0.,0.,0.,0.,0.],kinds=['analytic','analytic','unresolved','finite_mcmc','numerical_uncertified'],
        mcse=[0.,0.,None,.05,None])
    rows=[];primary={t['id']:t for t in tasks}
    for t in tasks:
        task=dict(t,protocol_sha256=protocol['protocol_sha256'],artifact_kind='posterior')
        rep=t['replicate'];seq=t['executor']=='sequential';nuts=t['kernel']=='nuts'
        outcome='numerical_failure' if t['executor']=='online_picard' and rep==0 else 'valid'
        aid=task['id']+'-attempt0';seconds=float(rep+2)
        attempt=dict(attempt_id=aid,binding_sha256=fingerprint(task),outcome=outcome,seconds=seconds)
        h=dict(task=task,original=aid,attempts=[attempt],summary=summarize_attempts([attempt]))
        call=dict(index=0,action='run',finished=True,seconds=seconds+1,error=None,
                  result=dict(task=task,attempt_id=aid,newly_executed=True))
        cost=summarize_task_costs(h,dict(task=task,original=aid),[call],{aid:seconds})
        # Lost ordinary return is explicit, never an imputed zero.
        if seq and rep==3:
            phase=cost['phases']['ordinary_workflow']
            phase.update(complete_seconds=None,known_seconds=0.,recorded_measurements=0,unknown_measurements=1)
        eligible=outcome=='valid' and not(seq and rep==1)
        value=(rep+1)/32*(.8 if nuts else 1.)
        rows.append(dict(task=task,phase='main',disposition='analyzed',outcome=outcome,
            means=[value,0.,0.,value,value] if eligible else None,names=ref['names'] if eligible else None,
            function_status='completed' if eligible else 'failed' if outcome=='valid' else 'unavailable',
            diagnostics=None,costs=cost,cache=None))
    for p in allocation['probes']:
        task=dict(primary[p['primary_task_id']],id=p['id'],protocol_sha256=protocol['protocol_sha256'],artifact_kind='cache_measurement')
        rep=p['replicate'];seq=p['executor']=='sequential'
        config=dict(kernel=p['kernel'],executor=p['executor'],device=p['device'],chains=4,draws=p['budget']+4,
            step_size=.1,initial=[[float(rep),0.]]*4,atol=1e-10,rtol=1e-10,window=4,max_iter=100,audit=False,on_failure='error')
        binding=dict(input_file_sha256=fingerprint(['input',rep]),tape_sha256=fingerprint(['tape',rep,p['budget']]),
            target_id=fingerprint('artificial-G1'),config=config)
        median=2.+rep/32 if seq else 1.
        records=[dict(execution_index=j,has_prior_execution=j>0,status='candidate',samples_eligible=False,
            technical_output_valid=True,executor_wall_seconds=s,tape_sha256=binding['tape_sha256'],
            target_id=binding['target_id'],config=copy.deepcopy(config)) for j,s in enumerate([10.,median-.25,median,median+.25])]
        states=['valid']*4;outcome='measurement_available'
        if seq and rep==0:
            records[0]['technical_output_valid']=False;states[0]='numerical_failure';outcome='numerical_failure'
        rows.append(dict(task=task,phase='cache',disposition='analyzed',outcome=outcome,means=None,names=None,
            function_status='unavailable',diagnostics=None,costs=None,
            cache=dict(binding=binding,observation=dict(records=records,execution_outcomes=states))))
    return rows,ref,protocol,allocation


def read(path):return json.loads(Path(path).read_text())


@pytest.fixture(scope='module')
def complete(tmp_path_factory):
    rows,ref,protocol,allocation=artificial_frame();root=tmp_path_factory.mktemp('scalar-statistics')/'model'
    result=summarize_model(rows,ref,name='G1',protocol=protocol,allocation=allocation,output=root)
    return root,result,rows


def test_full_frames_share_indices_keep_failure_and_unknown_costs(complete):
    root,result,rows=complete
    assert result['main_planned']==192 and result['cache_planned']==128
    assert result['main_outcomes']=={'valid':190,'numerical_failure':2}
    assert result['main_statistics']==result['cache_statistics']=='completed'
    assert result['formal_inference_complete'] is False
    assert read(root/'task-frame.json')==rows
    error=read(root/'function-0.json');costs=read(root/'costs.json')
    plan=load_plan(root/'main-resampling')
    assert error['error']['resampling']['sha256']==plan.sha256==costs['phases']['ordinary_workflow']['resampling']['sha256']
    assert plan.indices.shape==(9999,32)
    pair=error['error']['pairs'][0]
    assert pair['validity_table']==dict(n11=30,n10=1,n01=1,n00=0)
    assert pair['conditional_mean_loss_difference']==0. and pair['confidence_interval'] is None
    axis=error['costs']['ordinary_workflow']['workflows']['cpu-rwm-sequential@8']
    assert axis['available_functions_missing_cost']==1 and axis['mean_seconds'] is None
    assert axis['plot_error_cost_point'] is False
    assert costs['phases']['research_execution']['workflows']['cpu-rwm-online_picard@8']['unusable_output_cost_seconds']==3.
    assert file_hash(root/error['bootstrap_file'])==error['bootstrap_file_sha256']
    with np.load(root/error['bootstrap_file'],allow_pickle=False) as arrays:
        assert all(arrays[k].shape==(9999,) for k in arrays.files)


def test_reference_classes_and_constant_diagnostics_are_not_promoted(complete):
    root,_,_=complete
    constant=read(root/'function-1.json')['error']['workflows']['cpu-rwm-sequential@8']
    assert constant['conditional_squared_discrepancy']==0. and constant['confidence_interval'] is None
    unresolved=read(root/'function-2.json')
    assert unresolved['error']['workflows']['cpu-rwm-sequential@8']['conditional_squared_discrepancy'] is None
    assert unresolved['costs']['research_execution']['workflows']['cpu-rwm-sequential@8']['plot_error_cost_point'] is False
    finite=read(root/'function-3.json')['error']['workflows']['cpu-nuts-spawn_chains@8']
    assert finite['reference_mcse']==.05 and finite['reference_shift_min']<finite['reference_shift_max']
    assert finite['reference_shift_is_confidence_interval'] is False
    quad=read(root/'function-4.json')['error']['workflows']['cpu-nuts-spawn_chains@8']
    assert quad['claim_type']=='uncertified_numerical_discrepancy'


def test_cached_calls_remain_selected_inputs_and_all_failed_costs_stay(complete):
    root,_,_=complete;cache=read(root/'cache-costs.json');plan=load_plan(root/'cache-resampling')
    assert cache['resampling']['sha256']==plan.sha256 and len(plan.replicate_ids)==32
    assert cache['samples_eligible'] is False and cache['new_independent_repetitions']==0
    a=cache['workflows']['cpu-rwm-sequential@8']
    assert a['planned_executions']==128 and a['available_cache_points']==31 and a['availability_counts']['failed']==1
    assert a['unavailable_probe_known_seconds']==16.
    pair=next(p for p in cache['pairs'] if p['workflow_a']=='cpu-rwm-sequential@8')
    assert pair['validity_table']==dict(n11=31,n10=0,n01=1,n00=0)
    assert pair['geometric_mean_ratio']==pytest.approx(float(np.exp(np.log(2.+np.arange(1,32)/32).mean())))
    assert pair['confidence_interval'] is not None


def test_evidence_gaps_block_affected_phase_without_dropping_rows(tmp_path):
    rows,ref,protocol,allocation=artificial_frame(4)
    rows[0].update(disposition='evidence_gap',outcome=None,means=None,costs=None)
    cache=next(r for r in rows if r['phase']=='cache');cache.update(disposition='reader_error',outcome=None,cache=None)
    report=summarize_model(rows,ref,name='G1',protocol=protocol,allocation=allocation,output=tmp_path/'partial')
    assert report['main_statistics']==report['cache_statistics']=='unavailable_evidence'
    assert report['main_outcomes']['unknown_evidence']==1
    assert len(read(tmp_path/'partial/task-frame.json'))==len(rows)
    assert not (tmp_path/'partial/main-resampling').exists()
    with pytest.raises(ValueError,match='exactly once'):
        summarize_model(rows[:-1],ref,name='G1',protocol=protocol,allocation=allocation,output=tmp_path/'omitted')
    cache['task']['replicate']=999
    with pytest.raises(ValueError,match='Cache scalar task'):
        summarize_model(rows,ref,name='G1',protocol=protocol,allocation=allocation,output=tmp_path/'changed')


def test_technical_gate_never_produces_formal_intervals(tmp_path):
    rows,ref,protocol,allocation=artificial_frame(1);protocol['scope_kind']='technical_batch_validation'
    report=summarize_model(rows,ref,name='G1',protocol=protocol,allocation=allocation,output=tmp_path/'technical')
    assert report['main_statistics']==report['cache_statistics']=='technical_descriptive_only'
    assert not (tmp_path/'technical/main-resampling').exists()
    assert not list((tmp_path/'technical').glob('*.bootstrap.npz'))
