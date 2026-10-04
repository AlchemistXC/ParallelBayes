"""Verified runtime history -> bounded raw extraction -> planned scalar frame.

No sampler is called. Scientific eligibility, function availability, reference
eligibility and cost completeness remain separate fields.
"""
import json
from pathlib import Path
import zipfile

import numpy as np

from formal_evidence import inside
from formal_runtime import atomic_json,file_hash
from formal_streaming import read_member,extract_functions,array_hash
from mechanism_runner import actual_hash
from formal_outcomes import summarize_attempts,analyze_attempt_costs
from formal_uncertainty import create_plan,save_plan,analyze_function


def extract_task(evidence,contract,model,output,maximum_member_bytes=128*1024**2):
    """Verify a declared runtime-v1 scientific layout, then extract one fit.

    The contract is pinned by the caller's analysis identity. Input and target
    identities are checked separately from registration/attempt eligibility.
    Failed attempts remain in history and never supply ordinary samples.
    """
    if model.target_id!=contract['target_id']:raise ValueError('Declared target identity differs')
    output=Path(output).resolve()
    if output.exists() or output.is_relative_to(evidence.root) or evidence.root.is_relative_to(output):
        raise ValueError('Fresh analysis output separate from evidence is required')
    history=evidence.history(contract['task'],contract['original'])
    row={k:contract[k] for k in ('model','workflow','budget','replicate')}
    row.update(id=contract['task']['id'],history=history,outcome=history['summary']['outcome'],
               means=None,names=None,function_status='unavailable',raw_sha256=None,divergences=None)
    if row['outcome']!='valid':return row
    root=Path(history['eligible_directory']);state=json.loads((root/'state.json').read_text())
    def asset(name):
        path=inside(root,name)
        if name not in state['assets'] or file_hash(path)!=state['assets'][name]:
            raise ValueError('Scientific asset is not sealed or checksum differs: '+name)
        return path
    directory=contract['science_directory']
    worker=json.loads(asset(directory+'/worker-result.json').read_text())
    if worker['status']!='completed' or worker['samples_eligible'] is not True or worker['target_id']!=model.target_id:
        raise ValueError('Worker output eligibility/target differs')
    if worker['task']!=contract['scientific_task'] or worker['protocol_sha256']!=contract['scientific_protocol_sha256']:
        raise ValueError('Scientific task/protocol differs')
    if state['worker_result']!=worker:raise ValueError('Supervisor and scientific worker result differ')
    raw=asset(directory+'/fit.npz');metadata=json.loads(asset(directory+'/fit.json').read_text())
    if metadata['status']!='completed' or metadata['target_id']!=model.target_id:raise ValueError('Raw target/output identity differs')
    row['raw_sha256']=file_hash(raw)
    inputs=inside(evidence.root,contract['input_relative'])
    if file_hash(inputs)!=contract['input_sha256']:raise ValueError('Actual input file checksum differs')
    with zipfile.ZipFile(inputs) as z:names=z.namelist()
    expected={k+'.npy' for k in ('initial','noise','log_uniform','directions','nuts_seeds')}
    if len(names)!=5 or set(names)!=expected:raise ValueError('Actual input roles differ')
    payload={name[:-4]:read_member(inputs,name[:-4],maximum_member_bytes) for name in names}
    if actual_hash(payload)!=contract['actual_input_sha256']:raise ValueError('Actual input arrays differ')
    chains=contract['chains'];budget=contract['budget'];discard=contract['discard'];total=budget+discard
    if any(type(x) is not int or x<1 for x in (chains,budget)) or type(discard) is not int or discard<0:
        raise ValueError('Invalid planned shape/discard')
    if payload['initial'].shape!=(chains,model.dimension):raise ValueError('Actual initial shape differs')
    task=contract['scientific_task']
    if task['kernel']=='nuts':
        if discard!=0:raise ValueError('NUTS archive contains retained states separately from warmup')
        initial=read_member(raw,'initial',maximum_member_bytes)
        if not np.array_equal(initial,payload['initial']) or metadata['chain_seeds']!=payload['nuts_seeds'].tolist():
            raise ValueError('NUTS initialization/actual seeds differ')
        warmup=read_member(raw,'warmup_states',maximum_member_bytes)
        if warmup.shape!=(chains,contract['nuts_warmup'],model.dimension):raise ValueError('NUTS warmup shape differs')
        del initial,warmup
        row['initial_rng_sha256']=array_hash(read_member(raw,'initial_torch_rng_states',maximum_member_bytes))
        children=metadata['worker_records']
        if len(children)!=chains or sorted(c['chain'] for c in children)!=list(range(chains)):
            raise ValueError('Missing or duplicate NUTS chains')
        row['divergences']=0
        for child in children:
            childmeta=json.loads(asset(directory+'/'+child['result_directory']+'/metadata.json').read_text())
            row['divergences']+=sum(len(v) for c in childmeta['chain_records'] for v in c['diagnostics']['divergences'].values())
    else:
        if task['kernel'] not in ('rwm','mala'):raise ValueError('Unsupported fixed-tape kernel')
        config=metadata['config']
        if any(config.get(k)!=v for k,v in contract['expected_config'].items()):raise ValueError('Kernel/executor configuration differs')
        if config['draws']!=total or config['chains']!=chains or not np.array_equal(config['initial'],payload['initial']):
            raise ValueError('MH planned length/chains/initial differs')
        tape={k:payload[k][:,:total] for k in ('noise','log_uniform','directions')}
        if any(x.shape[:2]!=(chains,total) for x in tape.values()) or actual_hash(tape)!=metadata['tape_sha256']:
            raise ValueError('Actual MH input prefix differs')
        audit=metadata['audit']
        if audit['passed'] is not True or len(audit['acceptance_mismatches'])!=chains or any(audit['acceptance_mismatches']):
            raise ValueError('Saved independent MH audit did not pass')
        if worker['full_MH_audit']!=audit:raise ValueError('Saved worker/fit audits differ')
        del tape
    del payload
    if file_hash(inputs)!=contract['input_sha256']:raise ValueError('Actual input changed during extraction')
    try:
        extracted=extract_functions(raw,row['raw_sha256'],model,(chains,total,model.dimension),discard,output,
            maximum_member_bytes=maximum_member_bytes,prefix_lengths=tuple(contract.get('prefix_lengths',[total])))
    except (FloatingPointError,OverflowError) as exc:
        output.mkdir(parents=True,exist_ok=True)
        row.update(function_status='failed',function_error=str(exc))
        atomic_json(output/'function-failure.json',row)
        return row
    row.update(names=extracted['names'],means=extracted['means'],function_status='completed',extraction=extracted)
    atomic_json(output/'task-summary.json',row)
    return row


def aggregate_records(records,*,model_name,replicate_ids,workflow_names,budgets,reference,namespace,output,pairs=()):
    """Aggregate one model's verified scalars using every planned repetition.

    Attempts are nested execution history, never bootstrap units. Missing
    function estimates and incomplete total costs have separate masks.
    """
    ids=tuple(str(x) for x in replicate_ids)
    if len(ids)!=len(set(ids)) or len(workflow_names)!=len(set(workflow_names)) or len(budgets)!=len(set(budgets)):
        raise ValueError('Duplicate planned identities')
    expected={(w,b,r) for w in workflow_names for b in budgets for r in ids}
    rows={(r['workflow'],r['budget'],str(r['replicate'])):r for r in records}
    if len(rows)!=len(records) or set(rows)!=expected or len({r['id'] for r in records})!=len(records):
        raise ValueError('Every planned task must appear once, including explicit unavailable rows')
    count=len(reference['names'])
    if len(set(reference['names']))!=count or any(len(reference[k])!=count for k in ('means','kinds','mcse')):
        raise ValueError('Reference function contract differs')
    for r in records:
        if r['model']!=model_name:raise ValueError('Model group identity differs')
        reduced=summarize_attempts(r['history']['attempts'])
        if reduced!=r['history']['summary'] or r['outcome']!=reduced['outcome']:
            raise ValueError('Task history and scalar outcome differ')
        if r['means'] is not None:
            if r['outcome']!='valid' or r['function_status']!='completed' or r['names']!=reference['names'] or len(r['means'])!=count:
                raise ValueError('Ineligible or mismatched function estimates')
        elif r['function_status']=='completed':raise ValueError('Completed function estimates are missing')
    plan=create_plan(namespace,model_name,ids)
    output=Path(output);output.mkdir(parents=True,exist_ok=False);save_plan(plan,output/'resampling-plan')
    comparisons=[(f'{a}@{b}',f'{c}@{b}') for b in budgets for a,c in pairs]
    summary=dict(model=model_name,planned=len(records),planned_repetitions=len(ids),
        function_workflow_rows=0,paired_function_rows=0,available_bca_intervals=0,
        function_failed_tasks=sum(r['function_status']=='failed' for r in records),
        attempts_are_statistical_replicates=False,reference_uncertainty_propagated=False)
    def save(name,report):
        arrays=report.pop('bootstrap_statistics')
        if arrays:
            np.savez_compressed(output/(name+'.bootstrap.npz'),**arrays)
            report['bootstrap_statistics_sha256']=file_hash(output/(name+'.bootstrap.npz'))
        report['bootstrap_statistics_saved']=bool(arrays);atomic_json(output/(name+'.json'),report)
    for j,fn in enumerate(reference['names']):
        estimates={f'{w}@{b}':{r:None if rows[w,b,r]['means'] is None else rows[w,b,r]['means'][j] for r in ids}
                   for w in workflow_names for b in budgets}
        ref=dict(kind=reference['kinds'][j],value=reference['means'][j],mcse=reference['mcse'][j])
        report=analyze_function(plan,estimates,ref,comparisons);report.update(model=model_name,function=fn)
        summary['function_workflow_rows']+=len(report['workflows']);summary['paired_function_rows']+=len(report['pairs'])
        summary['available_bca_intervals']+=sum(x['confidence_interval'] is not None for x in [*report['workflows'].values(),*report['pairs']])
        save('function-'+str(j),report)
    executions={f'{w}@{b}':{r:rows[w,b,r]['history']['attempts'] for r in ids} for w in workflow_names for b in budgets}
    report=analyze_attempt_costs(plan,executions,comparisons,phase='runtime_v1_preflight_through_terminal_all_attempts')
    summary['cost_workflow_rows']=len(report['workflows']);summary['cost_pair_rows']=len(report['pairs'])
    summary['available_bca_intervals']+=sum(x['confidence_interval'] is not None for x in report['workflows'].values())
    summary['available_bca_intervals']+=sum(x['ratio_confidence_interval'] is not None for x in report['pairs'])
    save('cost',report);atomic_json(output/'summary.json',summary)
    return summary
