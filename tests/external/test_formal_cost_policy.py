"""Worked ledgers at the cost/statistics interface; no sampler or clock mocks."""
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def history(name,attempts):
    from formal_outcomes import summarize_attempts
    task=dict(id=name,protocol_sha256='artificial-cost-fixture')
    rows=[dict(attempt_id=name+str(i),binding_sha256=name,outcome=o,seconds=s) for i,(o,s) in enumerate(attempts)]
    return dict(task=task,original=name,attempts=rows,summary=summarize_attempts(rows))


def call(h,index,seconds,attempt=None,verification=False,error=None):
    result=None if attempt is None else dict(task=h['task'],attempt_id=h['attempts'][attempt]['attempt_id'],newly_executed=not verification)
    return dict(index=index,action='retry' if attempt==1 and not verification else 'run',seconds=seconds,result=result,
        finished=seconds is not None,error=error)


def test_complete_recovery_and_extra_verification_have_distinct_costs():
    from formal_cost_policy import summarize_task_costs
    h=history('a',[('infrastructure_interruption',5.),('valid',9.)])
    calls=[call(h,0,7.,0),call(h,1,11.,1),call(h,2,2.,1,True)]
    identity=dict(task=h['task'],original='a')
    report=summarize_task_costs(h,identity,calls,{'a0':3.,'a1':5.})
    assert report['outcome']=='valid' and report['actual_attempts']==2
    assert report['phases']['ordinary_workflow']['complete_seconds']==8.
    assert report['phases']['research_execution']['complete_seconds']==18.
    assert report['phases']['additional_verification']['complete_seconds']==2.
    assert report['phases']['all_invocations']['complete_seconds']==20.
    assert report['phases']['research_execution']['prior_interruption_known_seconds']==7.
    assert report['attempts_are_statistical_repetitions'] is False
    calls.append(call(h,3,100.,1,True))
    again=summarize_task_costs(h,identity,calls,{'a0':3.,'a1':5.})
    assert again['phases']['research_execution']==report['phases']['research_execution']
    assert again['phases']['ordinary_workflow']==report['phases']['ordinary_workflow']
    assert again['phases']['all_invocations']['complete_seconds']==120.
    with pytest.raises(ValueError,match='ordinary'):
        summarize_task_costs(h,identity,calls,{'a1':5.})


def test_planned_cost_analysis_keeps_failures_unknown_costs_and_joint_valid_pairs():
    from formal_cost_policy import summarize_task_costs,analyze_task_costs
    from formal_uncertainty import create_plan
    plan=create_plan('artificial-policy-costs','G1',['0','1','2','3'])
    def record(name,rep,attempts,seconds,ordinary,checks=()):
        h=history(name,attempts);h['task'].update(model='G1',replicate=rep)
        calls=[call(h,i,s,i) if s is not None else call(h,i,None) for i,s in enumerate(seconds)]
        calls += [call(h,len(calls)+i,t,len(attempts)-1,True) for i,t in enumerate(checks)]
        return summarize_task_costs(h,dict(task=h['task'],original=name),calls,
            {name+str(i):value for i,value in enumerate(ordinary)})
    a={'0':record('a0',0,[('infrastructure_interruption',5.),('valid',9.)],[7.,11.],[3.,5.],checks=[2.]),
       '1':record('a1',1,[('resource_failure',6.)],[8.],[4.]),
       '2':record('a2',2,[('infrastructure_interruption',None),('valid',12.)],[None,13.],[None,6.],checks=[1.])}
    h=history('a3',[]);h['task'].update(model='G1',replicate=3)
    a['3']=summarize_task_costs(h,dict(task=h['task'],original='a3'),[call(h,0,2.,error=dict(type='ResourceWait'))],{})
    b={str(i):record('b'+str(i),i,[('valid',9.)],[10.],[5.]) for i in range(4)}
    report=analyze_task_costs(plan,{'a':a,'b':b},pairs=[('a','b')])
    ordinary=report['phases']['ordinary_workflow']['workflows']['a']
    audit=report['phases']['research_execution']['workflows']['a']
    pair=report['phases']['research_execution']['pairs'][0]
    assert ordinary['total_recorded_seconds']==18. and ordinary['known_partial_task_seconds']==6.
    assert audit['total_recorded_seconds']==41. and audit['known_partial_task_seconds']==13.
    assert audit['unusable_output_cost_seconds']==10. and audit['prior_interruption_known_seconds']==7.
    assert audit['mean_all_planned_seconds'] is None and audit['mean_successful_seconds']==18.
    assert audit['outcome_counts']['resource_failure']==1 and audit['outcome_counts']['not_run']==1
    assert audit['failure_rate_interval'] is None
    assert pair['validity_table']==dict(n11=2,n10=0,n01=2,n00=0)
    assert pair['jointly_valid_pairs_missing_cost']==1 and pair['geometric_mean_ratio'] is None
    assert report['operational_consumption']['a']['additional_verification_known_seconds']==3.
    assert report['operational_consumption']['a']['all_invocations_known_seconds']==44.
    assert report['new_independent_repetitions']==0
    assert report['phases']['ordinary_workflow']['resampling']['sha256']==report['phases']['research_execution']['resampling']['sha256']==plan.sha256
    incomplete=dict(a);incomplete.pop('3')
    with pytest.raises(ValueError,match='planned'):
        analyze_task_costs(plan,{'a':incomplete,'b':b},pairs=[('a','b')])
