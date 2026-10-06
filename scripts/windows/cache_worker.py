# Preserved template SHA256: 6f2418e6cb7aeff30b3cb77efb366c74fd0169e98f966583f0b0bae25389b8b5
"""Capsule-bound cache measurements, deliberately distinct from posterior fits.

Only small native-Mac technical use is launched here. Native Windows/process
supervision and formal launch remain separate gates. No successful primary fit
is read or required. An already-used output directory is never executed again.
"""
import importlib.metadata
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples'),str(ROOT/'scripts/windows')]
from batch_contract import validate_capsule,mh_config
from formal_measurement_plan import POLICY,summarize_probe
from formal_runtime import atomic_json,file_hash,fingerprint,PhaseLedger
from formal_streaming import read_member


def _probe(capsule,digest,probe):
    c=validate_capsule(capsule,digest);t=c['task']
    expected=dict(t);expected['primary_task_id']=expected.pop('id')
    expected.update(initial_calls=1,prepared_replays=3,samples_eligible=False,primary_outcome_is_selection_criterion=False)
    expected['id']=fingerprint(dict(policy=POLICY,identity=c['identity'],probe=expected))[:24]
    if probe!=expected or t['kernel'] not in ('rwm','mala'):raise ValueError('Cache probe and MH capsule differ')
    return c


def execute_cached_probe(capsule,capsule_sha256,probe,inputs,output,source_directory=None):
    """Run one initial plus three prepared replays, retaining every known cost.

    This numerical/artifact interface does not own an OS process cohort or grant
    a formal launch. Callers supply serialization and resource supervision. The
    independent Windows technical gate is enforced before target evaluation.
    """
    c=_probe(capsule,capsule_sha256,probe);output=Path(output)
    if (sys.platform!='win32' or c['required_platform']!='win32' or
        c['scope_kind']!='technical_batch_validation' or not c['identity'].startswith('windows-owned-cache-technical-')):
        raise ValueError('Only the independently frozen Windows technical cache identity is permitted')
    output.mkdir(parents=True,exist_ok=False)
    ledger=PhaseLedger(output/'phases.json')
    with ledger.phase('contract_source_environment_input_and_target'):
        import torch
        from windows_payload import payload
        from inference_targets import build_target
        from mechanism_runner import plain
        from parallelbayes.torch_backend.sampling import settings,tape_hash,sync,audit_path
        from cached_execution import PreparedExecutor
        required='scripts/windows/cache_worker.py'
        if c['source_files'].get(required)!=file_hash(__file__):raise ValueError('Cache execution source is not bound')
        for name,h in c['source_files'].items():
            if file_hash(ROOT/name)!=h:raise ValueError('Frozen source differs: '+name)
        for name,version in c['required_versions'].items():
            if importlib.metadata.version(name)!=version:raise ValueError('Dependency differs: '+name)
        torch.set_num_threads(c['controls']['torch_threads'])
        if torch.get_num_interop_threads()!=1:torch.set_num_interop_threads(1)
        values=payload(dict(inputs=str(inputs)),c)
        if c['task']['device']=='cuda':
            free,total=torch.cuda.mem_get_info()
            atomic_json(output/'cuda-before.json',dict(free_bytes=free,total_bytes=total,allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved()))
            if free<c['controls']['minimum_gpu_free_bytes']:raise MemoryError('CUDA free budget refused without allocating it')
        model=build_target(c['target'],source_directory,c['task']['device'])
        config=settings(mh_config(c,values['initial'].tolist()))
        tape={k:values[k][:,:config['draws']] for k in ('noise','log_uniform','directions')}
        binding=dict(input_file_sha256=c['input']['sha256'],tape_sha256=tape_hash(tape),target_id=model.target_id,config=config)
        request=dict(capsule=c,capsule_sha256=capsule_sha256,probe=probe)
        atomic_json(output/'request.json',request);atomic_json(output/'binding.json',binding)
        atomic_json(output/'environment.json',dict(python=sys.version,platform=sys.platform,
            packages={n:importlib.metadata.version(n) for n in c['required_versions']},
            device=str(model.device),dtype='float64',torch_threads=torch.get_num_threads(),interop_threads=torch.get_num_interop_threads()))
        ledger.synchronise=lambda:sync(model.device)
    records=[None]*4;states=['not_run']*4;error=None;interrupt=None;current=0;result=None
    try:
        with ledger.phase('prepared_target_and_tape'):
            prepared=PreparedExecutor(model,config,tape)
        for i in range(4):
            current=i;result=None
            atomic_json(output/f'execution-{i}.started.json',dict(execution_index=i,probe_id=probe['id'],started_ns=time.time_ns(),timestamp_is_not_elapsed_time=True))
            with ledger.phase('execute_and_transfer_'+str(i)):
                if model.device.type=='cuda':torch.cuda.reset_peak_memory_stats()
                result=prepared.run()
                if model.device.type=='cuda':
                    result['cuda_memory']=dict(free_bytes=torch.cuda.mem_get_info()[0],allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved(),peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved(),synchronized=True,scope='Current measurement-process allocator; not job RSS or a whole-device peak')
            with ledger.phase('candidate_archive_'+str(i)):
                raw=result.pop('unconstrained');accept=result.pop('accept')
                result.update(actual_array_file=None,actual_array_sha256=None,audit=None,technical_output_valid=False)
                np.savez_compressed(output/f'execution-{i}.npz',unconstrained=raw,accept=accept)
                result.update(actual_array_file=f'execution-{i}.npz',actual_array_sha256=file_hash(output/f'execution-{i}.npz'))
                atomic_json(output/f'candidate-{i}.json',plain(result))
            with ledger.phase('independent_numpy_audit_'+str(i)):
                audit=audit_path(model,config,values['initial'],tape,raw,accept) if result['status']=='candidate' else None
                valid=bool(audit and audit['passed'])
                result.update(audit=audit,technical_output_valid=valid)
                result=plain(result)
            # Durable per-call audit; later failures never erase preceding records.
            states[i]='valid' if valid else 'numerical_failure';records[i]=result
            atomic_json(output/f'execution-{i}.json',result)
    except (MemoryError, __import__('torch').OutOfMemoryError) as exc:
        states[current]='resource_failure';error=dict(type=type(exc).__name__,message=str(exc))
    except BaseException as exc:
        states[current]='infrastructure_interruption';error=dict(type=type(exc).__name__,message=str(exc));interrupt=exc
    if error is not None and result is not None:
        # A completed execute call has a measured cost even if subsequent storage
        # or audit failed. Preserve that receipt without inventing a valid path.
        result.pop('unconstrained',None);result.pop('accept',None)
        result.setdefault('actual_array_file',None);result.setdefault('actual_array_sha256',None)
        result.setdefault('audit',None);result['technical_output_valid']=False
        result['post_execution_error']=error
        records[current]=plain(result)
        atomic_json(output/f'execution-{current}.json',records[current])
    observation=dict(execution_outcomes=states,records=records)
    summary=summarize_probe(probe,records,expected_tape_sha256=binding['tape_sha256'],expected_target_id=binding['target_id'],expected_config=config)
    report=dict(artifact_kind='cache_measurement',probe=probe,binding=binding,observation=observation,summary=summary,
        measurement_available=summary['all_executions_valid'],samples_eligible=False,error=error,
        status='interrupted' if interrupt else 'completed' if summary['all_executions_valid'] else 'failed',
        new_independent_statistical_repetitions=0,requires_successful_primary_fit=False,
        process_supervision_provided=True,formal_inference_complete=False,native_Windows_validated=False,
        cost_scope='Executor wall and device transfer stored per call; outer worker phases include preparation, transfer, archive and independent audit. Nested times are not additive to those phases. Journal writes/gaps and caller startup remain outside worker phase sums.')
    atomic_json(output/'cache-result.json',report)
    atomic_json(output/'MANIFEST.json',{p.name:file_hash(p) for p in sorted(output.iterdir()) if p.is_file()})
    if interrupt:raise interrupt
    return report



if __name__=='__main__':
    request=json.loads(Path(sys.argv[1]).read_text());attempt=Path(sys.argv[2])
    if request.get('native_runtime_schema')!='windows-owned-runtime-v1':raise ValueError('Owned Windows adapter required')
    from job_objects import Job,identity
    import os
    with Job(os.environ['PB_OWNED_JOB'],existing=True) as job:
        member=identity(os.getpid(),job.handle)
        if not member['member_of_owned_job']:raise RuntimeError('Cache worker is not owned')
    atomic_json(attempt/'cache-ownership.json',member)
    try:
        report=execute_cached_probe(request['capsule'],request['capsule_sha256'],request['probe'],request['inputs'],attempt/'cache')
        result=dict(status='completed' if report['measurement_available'] else 'failed',artifact_kind='cache_measurement',
            samples_eligible=False,measurement_available=report['measurement_available'],
            failure_category=None if report['measurement_available'] else 'resource_failure' if 'resource_failure' in report['observation']['execution_outcomes'] else 'numerical_failure')
        atomic_json(attempt/'worker-result.json',result)
    except (MemoryError,__import__('torch').OutOfMemoryError) as exc:
        atomic_json(attempt/'worker-result.json',dict(status='failed',artifact_kind='cache_measurement',samples_eligible=False,measurement_available=False,failure_category='resource_failure',error=str(exc)))
        sys.exit(3)
