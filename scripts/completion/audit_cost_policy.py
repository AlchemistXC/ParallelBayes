"""Apply named task cost scopes to immutable batch and recovery archives.

This reads saved measurements, not clocks. The separate intentional recovery
fixture never becomes an independent inference repetition.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_evidence import RuntimeEvidence,inside
from formal_cost_policy import summarize_task_costs,POLICY,SCOPES
from measured_coordinator import read_calls
from batch_contract import BatchPlan
from audit_batch_archive import verify_binding


def manifest(root):
    m=json.loads((root/'MANIFEST.json').read_text())
    for name,h in m.items():
        if file_hash(inside(root,name))!=h:raise ValueError('Evidence asset differs: '+name)
    return m


def read_cost(evidence,locations,previous,ledger_root):
    expected=previous['history'];history=evidence.history(expected['task'],expected['original'])
    if history['summary']!=expected['summary'] or history['attempts']!=expected['attempts']:raise ValueError('Historical attempt costs differ')
    identity,calls=read_calls(ledger_root/fingerprint(expected['original']))
    if calls!=previous['calls']:raise ValueError('Historical invocation ledger differs')
    ordinary={};receipts=[]
    for attempt in history['attempts']:
        original=attempt['attempt_id'];f=inside(evidence.root,locations[original])/'attempt-0001/ordinary-process.json'
        if f.exists():
            r=json.loads(f.read_text())
            if (r['boundary']!='Before child process creation through wait for its exit; includes imports, model/input, sampling, transform, ordinary output and diagnostics'
                or r['outer_audit_included'] is not False or r['nested_sampler_timings_additive'] is not False):
                raise ValueError('Ordinary measurement scope differs')
            ordinary[original]=r['ordinary_process_wall_seconds']
            receipts.append(dict(attempt_id=original,relative_path=f.relative_to(evidence.root).as_posix(),sha256=file_hash(f),return_code=r['return_code']))
        else:ordinary[original]=None
    row=summarize_task_costs(history,identity,calls,ordinary)
    allcalls=row['phases']['all_invocations']
    if allcalls['complete_seconds']!=previous['complete_invocation_seconds'] or allcalls['known_seconds']!=previous['known_invocation_seconds']:
        raise ValueError('All-call consumption changed')
    row.update(ordinary_receipts=receipts,source_attempts=history['attempts'])
    return row


def audit(batch_bundle,recovery_bundle,output):
    batch_bundle,recovery_bundle,output=map(lambda p:p.resolve(),(batch_bundle,recovery_bundle,output))
    if output.exists() or any(output.is_relative_to(p) or p.is_relative_to(output) for p in (batch_bundle,recovery_bundle)):
        raise ValueError('New analysis directory separate from both evidence archives required')
    manifests={label:manifest(path) for label,path in [('batch',batch_bundle),('recovery',recovery_bundle)]}
    names=['formal_cost_policy.py','audit_cost_policy.py','formal_outcomes.py','formal_evidence.py','formal_runtime.py',
        'formal_uncertainty.py','formal_error_summary.py','measured_coordinator.py','audit_batch_archive.py','batch_contract.py']
    sources={'scripts/completion/'+n:file_hash(ROOT/'scripts/completion'/n) for n in names}
    for name,h in sources.items():
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:raise ValueError('Commit analysis source before running: '+name)
    identity=dict(policy=POLICY,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_files=sources,input_manifests={label:file_hash(path/'MANIFEST.json') for label,path in [('batch',batch_bundle),('recovery',recovery_bundle)]},
        scopes=SCOPES,scope='Read-only technical reconstruction; stored elapsed durations only; no statistical intervals, sampler calls or new timing',
        prospective_formal_protocol_frozen=False)
    identity['analysis_sha256']=fingerprint(identity);output.mkdir(parents=True);atomic_json(output/'analysis-identity.json',identity)
    p=json.loads((batch_bundle/'profile.json').read_text());plan=BatchPlan(p)
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Frozen numerical/scientific source differs')
    r=json.loads((batch_bundle/'receipt.json').read_text());binding=json.loads((batch_bundle/'run/binding.json').read_text());locations=r['locations']
    observed={json.loads(f.read_text())['task']['id']:json.loads(f.read_text()) for f in inside(batch_bundle,r['verification_invocation']).glob('task-*.json')}
    if set(observed)!={t['id'] for t in plan.tasks(r['batch'])}:raise ValueError('Planned frame differs')
    rows=[]
    with RuntimeEvidence(batch_bundle/'registry/registry.sqlite3',manifests['batch']['registry/registry.sqlite3'],batch_bundle,locations) as evidence:
        for task in plan.tasks(r['batch']):
            previous=observed[task['id']]['costs'];original=previous['history']['original']
            saved=json.loads((inside(batch_bundle,locations[original])/'binding.json').read_text())
            verify_binding(plan,task,saved,binding)
            row=read_cost(evidence,locations,previous,batch_bundle/'run/call-costs')
            row['evidence_role']='one_declared_technical_batch_task';rows.append(row)
    old=json.loads((recovery_bundle/'run/receipt.json').read_text());previous=old['recovery_cost_after_verification']
    original=previous['history']['original'];locations={original:'run/injected-recovery',original+'.retry':'run/injected-recovery.retry'}
    with RuntimeEvidence(recovery_bundle/'registry/registry.sqlite3',manifests['recovery']['registry/registry.sqlite3'],recovery_bundle,locations) as evidence:
        recovery=read_cost(evidence,locations,previous,recovery_bundle/'run/call-costs')
        if recovery['task']['role']!='intentional_recovery_fixture':raise ValueError('Recovery fixture identity differs')
        if recovery['phases']['research_execution']['complete_seconds']!=old['recovery_cost_before_verification']['complete_invocation_seconds']:
            raise ValueError('Recovery primary execution duration differs')
        recovery['evidence_role']='intentional_recovery_fixture_not_scientific_repetition'
    points=[]
    for model in ('G1','G2','L1'):
        for kernel,executor in [('rwm','online_picard'),('mala','quasi_deer')]:
            a=next(row for row in rows if row['task']['model']==model and row['task']['workflow']==f'cpu-{kernel}-sequential')
            b=next(row for row in rows if row['task']['model']==model and row['task']['workflow']==f'cpu-{kernel}-{executor}')
            ratios={}
            for phase in ('ordinary_workflow','research_execution'):
                x,y=a['phases'][phase]['complete_seconds'],b['phases'][phase]['complete_seconds']
                ratios[phase]=x/y if a['outcome']==b['outcome']=='valid' and x is not None and y is not None and x>0 and y>0 else None
            points.append(dict(model=model,kernel=kernel,budget=a['task']['budget'],ratio_sequence_over_time_executor=ratios,
                planned_independent_inputs=1,confidence_interval=None,interpretation='One technical paired timing observation; not a repeated performance inference'))
    allrows=rows+[recovery]
    summary=dict(policy=POLICY,analysis_sha256=identity['analysis_sha256'],source_commit=identity['source_commit'],
        batch_planned=len(rows),batch_valid=sum(x['outcome']=='valid' for x in rows),
        batch_interrupted=sum(x['outcome']=='infrastructure_interruption' for x in rows),
        recovery_fixture_tasks=1,actual_attempt_histories=sum(x['actual_attempts'] for x in allrows),
        ordinary_receipts_reconstructed=sum(len(x['ordinary_receipts']) for x in allrows),
        complete_primary_task_costs=sum(x['phases']['research_execution']['complete_seconds'] is not None for x in allrows),
        complete_ordinary_task_costs=sum(x['phases']['ordinary_workflow']['complete_seconds'] is not None for x in allrows),
        known_recovery_primary_seconds=recovery['phases']['research_execution']['complete_seconds'],
        known_recovery_ordinary_seconds=recovery['phases']['ordinary_workflow']['complete_seconds'],
        known_recovery_verification_seconds=recovery['phases']['additional_verification']['complete_seconds'],
        batch_missing_cost_is_not_zero=True,assets_checked={k:len(v) for k,v in manifests.items()},
        new_sampler_calls=0,new_R_calls=0,new_timing_experiments=0,new_independent_repetitions=0,
        statistical_intervals_generated=0,native_Windows_validated=False,formal_inference_complete=False)
    atomic_json(output/'batch-task-costs.json',rows);atomic_json(output/'intentional-recovery-costs.json',recovery)
    atomic_json(output/'technical-paired-costs.json',points);atomic_json(output/'summary.json',summary)
    for label,path in [('batch',batch_bundle),('recovery',recovery_bundle)]:
        if manifest(path)!=manifests[label]:raise ValueError('Source evidence changed')
    for name,h in sources.items():
        if file_hash(ROOT/name)!=h:raise ValueError('Source code changed')
    atomic_json(output/'manifest.json',{f.name:file_hash(f) for f in sorted(output.iterdir()) if f.is_file()})
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('batch-bundle','recovery-bundle','output'):p.add_argument('--'+name,type=Path,required=True)
    print(json.dumps(audit(**vars(p.parse_args())),indent=2))
