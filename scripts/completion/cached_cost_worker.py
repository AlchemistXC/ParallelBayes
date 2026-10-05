"""Finite Mac cached-executor measurement using frozen existing MH inputs."""
import json
from pathlib import Path
import sys
import traceback
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from formal_runtime import atomic_json,file_hash,fingerprint,PhaseLedger


def main(request_path,output):
    import importlib.metadata
    import numpy as np
    import torch
    from inference_targets import build_target
    from formal_outcomes import read_attempt
    from formal_streaming import read_member
    from mechanism_runner import actual_hash,plain
    from parallelbayes.torch_backend.sampling import settings,audit_path
    from cached_execution import PreparedExecutor
    output=Path(output);ledger=PhaseLedger(output/'phases.json')
    with ledger.phase('protocol_input_and_prepared_executor'):
        req=json.loads(Path(request_path).read_text());profile=json.loads(Path(req['profile']).read_text())
        unsigned=dict(profile);digest=unsigned.pop('protocol_sha256')
        if fingerprint(unsigned)!=digest or profile['identity']!='cached-cost-technical-mac-v1' or sys.platform!='darwin':
            raise ValueError('Frozen native Mac technical profile required')
        p=json.loads(Path(req['scientific_protocol']).read_text());unsigned=dict(p);scientific=unsigned.pop('protocol_sha256')
        if fingerprint(unsigned)!=scientific or scientific!=profile['scientific_protocol_sha256']:raise ValueError('Scientific dependency differs')
        for source in (profile['source_files'],p['source_files']):
            for name,h in source.items():
                if file_hash(ROOT/name)!=h:raise ValueError('Frozen source changed: '+name)
        for name,version in p['required_versions'].items():
            if importlib.metadata.version(name)!=version:raise ValueError('Dependency differs: '+name)
        torch.set_num_threads(p['torch_threads']);torch.set_num_interop_threads(1)
        task=next(t for t in profile['cached_tasks'] if t['id']==req['task_id']);item=next(t for t in p['targets'] if t['name']==task['model'])
        model=build_target(item,None,'cpu');input_file=Path(req['inputs'])/item['input'];expected=p['inputs'][item['input']]
        if file_hash(input_file)!=expected['sha256']:raise ValueError('Actual input file differs')
        with np.load(input_file,allow_pickle=False) as z:payload={k:z[k].copy() for k in z.files}
        if actual_hash(payload)!=expected['actual_sha256']:raise ValueError('Actual arrays differ')
        total=p['draws']+p['mh_discard'];tape={k:payload[k][:,:total] for k in ('noise','log_uniform','directions')}
        c=settings(dict(kernel=task['kernel'],executor=task['executor'],device='cpu',chains=p['chains'],draws=total,
            step_size=item['step_'+task['kernel']],initial=payload['initial'].tolist(),window=p['window'],
            max_iter=total if task['executor']=='online_picard' else p['quasi_deer_max_iter'],
            memory_limit_mb=p['memory_limit_mb'],atol=p['atol'],rtol=p['rtol'],audit=False,on_failure='error'))
        reference=Path(req['reference'])/task['id'];old=read_attempt(reference)
        if old['outcome']!='valid' or old['fixed_task']!=dict(task,protocol_sha256=scientific):raise ValueError('Reference task differs')
        original_q=read_member(reference/'attempt-0001/fit.npz','unconstrained')
        original_a=read_member(reference/'attempt-0001/fit.npz','accept')
        prepared=PreparedExecutor(model,c,tape)
    records=[]
    for i in range(profile['warm_replays']+1):
        with ledger.phase('initial_execution' if i==0 else 'prepared_replay_'+str(i)):
            result=prepared.run()
        with ledger.phase('outside_timing_audit_and_archive_'+str(i)):
            raw=result.pop('unconstrained');accept=result.pop('accept')
            np.savez_compressed(output/f'execution-{i}.npz',unconstrained=raw,accept=accept)
            audit=audit_path(model,c,payload['initial'],tape,raw,accept) if result['status']=='candidate' else None
            match=bool(np.array_equal(raw,original_q) and np.array_equal(accept,original_a))
            valid=bool(audit and audit['passed'] and match)
            result.update(audit=audit,original_arrays_identical=match,technical_output_valid=valid,
                actual_array_file=f'execution-{i}.npz',actual_array_sha256=file_hash(output/f'execution-{i}.npz'))
            atomic_json(output/f'execution-{i}.json',plain(result));records.append(plain(result))
    valid=all(r['technical_output_valid'] for r in records)
    atomic_json(output/'worker-result.json',dict(status='completed' if valid else 'failed',samples_eligible=valid,
        failure_category=None if valid else 'numerical_failure',task=task,protocol_sha256=digest,
        scientific_protocol_sha256=scientific,target_id=model.target_id,records=records,
        actual_executions=len(records),cached_executions=profile['warm_replays'],
        cached_execution_measured=True,new_independent_statistical_repetitions=0,
        scope='Initial plus three prepared fixed-input eager executions; independent audits/output outside timed executor. All replays belong to one existing input, not additional inference replicates.',
        native_Windows_validated=False))


if __name__=='__main__':
    try:main(sys.argv[1],sys.argv[2])
    except MemoryError as exc:
        atomic_json(Path(sys.argv[2])/'worker-result.json',dict(status='failed',samples_eligible=False,failure_category='resource_failure',error=str(exc)))
    except BaseException:
        traceback.print_exc();sys.exit(1)
