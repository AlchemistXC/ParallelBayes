"""Owned audited task containing a separately measured ordinary subprocess."""
import json
from pathlib import Path
import sys
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from formal_runtime import atomic_json,file_hash,fingerprint,PhaseLedger


def main(request_path,output):
    output=Path(output);ledger=PhaseLedger(output/'phases.json')
    with ledger.phase('measurement_protocol_validation'):
        request=json.loads(Path(request_path).read_text());profile=json.loads(Path(request['measurement_protocol']).read_text())
        unsigned=dict(profile);digest=unsigned.pop('measurement_sha256')
        if fingerprint(unsigned)!=digest or profile['identity']!='measured-workflow-technical-mac-v1' or sys.platform!='darwin':
            raise ValueError('Only the frozen native Mac measurement profile is supported')
        for name,h in profile['source_files'].items():
            if file_hash(ROOT/name)!=h:raise ValueError('Measurement source changed: '+name)
        science=request['scientific_request'];p=json.loads(Path(science['protocol']).read_text())
        unsigned=dict(p);science_digest=unsigned.pop('protocol_sha256')
        if fingerprint(unsigned)!=science_digest or science_digest!=profile['dependency_protocol_sha256']:
            raise ValueError('Scientific dependency changed')
        task=next(t for t in p['tasks'] if t['id']==science['task_id'])
        if task not in profile['tasks']:raise ValueError('Task not in frozen measurement list')
        item=next(t for t in p['targets'] if t['name']==task['model'])
        atomic_json(output/'scientific-request.json',science)
    with ledger.phase('ordinary_process_startup_through_exit'):
        from measured_workflow import ordinary_process
        measured=ordinary_process([sys.executable,str(ROOT/'scripts/completion/measured_ordinary_worker.py'),
                                   str(output/'scientific-request.json'),str(output)],output)
    atomic_json(output/'ordinary-process.json',measured)
    if measured['return_code']==3 and (output/'ordinary-resource-failure.json').exists():
        atomic_json(output/'worker-result.json',dict(status='failed',samples_eligible=False,failure_category='resource_failure',
            task=task,protocol_sha256=science_digest,ordinary_process=measured,cached_execution_measured=False))
        return
    if measured['return_code']!=0:raise RuntimeError('Ordinary process failed with code '+str(measured['return_code']))
    with ledger.phase('independent_research_audit_after_ordinary_exit'):
        import numpy as np
        from inference_targets import build_target
        from formal_streaming import read_member
        from measured_workflow import audit_candidate
        from mechanism_runner import actual_hash
        ordinary=json.loads((output/'ordinary-output.json').read_text())
        metadata=json.loads((output/'candidate.json').read_text())
        if ordinary['samples_eligible'] is not False or ordinary['task']!=task or ordinary['protocol_sha256']!=science_digest:
            raise ValueError('Ordinary candidate contract differs')
        model=build_target(item,science.get('source_directory'),'cpu')
        if metadata['target_id']!=model.target_id or ordinary['target_id']!=model.target_id:
            raise ValueError('Candidate target identity differs')
        path=output/'fit.npz';raw_before=file_hash(path)
        input_file=Path(science['inputs'])/item['input'];expected=p['inputs'][item['input']]
        if file_hash(input_file)!=expected['sha256']:raise ValueError('Actual input file differs')
        payload={k:read_member(input_file,k) for k in ('initial','noise','log_uniform','directions','nuts_seeds')}
        if actual_hash(payload)!=expected['actual_sha256']:raise ValueError('Actual input arrays differ')
        if task['kernel']=='nuts':
            if metadata['status']=='completed':
                q=read_member(path,'unconstrained');theta=read_member(path,'draws')
                expected_shape=(p['chains'],p['draws'],model.dimension)
                passed=bool(q.shape==expected_shape and theta.shape==expected_shape and
                    np.isfinite(q).all() and np.isfinite(theta).all() and
                    np.allclose(theta,model.constrain(q),rtol=1e-10,atol=1e-12) and
                    np.array_equal(read_member(path,'initial'),payload['initial']) and
                    metadata['chain_seeds']==payload['nuts_seeds'].tolist())
                del q,theta
                audit=dict(kind='NUTS_shape_transform_and_actual_initial_seed_checks',passed=passed,
                           fixed_MH_path_equivalence=False,posterior_convergence_proven=False)
                decision=dict(status='completed' if passed else 'failed',samples_eligible=passed,
                    audit=audit,failure_category=None if passed else 'numerical_failure')
            else:decision=dict(status='failed',samples_eligible=False,audit=None,failure_category='output_failure_unclassified')
        else:
            total=p['mh_discard']+p['draws']
            expected_config=dict(kernel=task['kernel'],executor=task['executor'],device=task['device'],
                chains=p['chains'],draws=total,step_size=item['step_'+task['kernel']],window=p['window'],
                max_iter=total if task['executor']=='online_picard' else p['quasi_deer_max_iter'],
                atol=p['atol'],rtol=p['rtol'],memory_limit_mb=p['memory_limit_mb'],audit=False,on_failure='error',
                initial=payload['initial'].tolist())
            if any(metadata['config'].get(k)!=v for k,v in expected_config.items()):
                raise ValueError('Ordinary MH configuration differs from frozen scientific request')
            candidate=dict(metadata)
            if metadata['status']=='completed':
                candidate.update({k:read_member(path,k) for k in ('draws','unconstrained','accept')})
            tape={k:payload[k][:,:total] for k in ('noise','log_uniform','directions')}
            decision=audit_candidate(model,metadata['config'],tape,candidate)
            del candidate,tape
        if file_hash(path)!=raw_before:raise ValueError('Ordinary raw candidate changed during audit')
    with ledger.phase('research_evidence_finalization'):
        atomic_json(output/'external-audit.json',decision)
        final=dict(metadata,status=decision['status'],external_audit=decision,
                   ordinary_candidate_metadata_sha256=file_hash(output/'candidate.json'),
                   ordinary_candidate_arrays_sha256=raw_before,
                   ordinary_nested_timing_excludes_external_audit=True)
        if task['kernel']!='nuts':
            final.update(audit=decision['audit'],primary_audit=decision['audit'],
                guarantee='independently_audited_fixed_tape' if decision['samples_eligible'] else 'failed_output_quarantined')
        atomic_json(output/'fit.json',final)
    atomic_json(output/'worker-result.json',dict(status=decision['status'],samples_eligible=decision['samples_eligible'],
        failure_category=decision['failure_category'],target_id=model.target_id,task=task,protocol_sha256=science_digest,
        measurement_sha256=digest,ordinary_process=measured,diagnostics_completed=ordinary['diagnostics_completed'],
        full_MH_audit=None if task['kernel']=='nuts' else decision['audit'],
        ordinary_workflow_measured_separately=True,cached_execution_measured=False,
        ordinary_cost_scope='Declared standalone Python batch plus R diagnosis and full path output; not minimal R-front-end latency or cold OS file cache',
        scientific_scope='Technical cost-boundary validation on existing inputs; not performance comparison or new statistical repetition'))


if __name__=='__main__':
    try:main(sys.argv[1],sys.argv[2])
    except BaseException:
        traceback.print_exc();sys.exit(1)
