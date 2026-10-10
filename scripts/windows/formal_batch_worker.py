# Derived from scripts/windows/batch_worker.py; numerical/audit routines retained.
# Preserved template SHA256: 55110881cdb6cc5c95ce3ea0ed3c77f3d8296bb0ea0c92e2bbcca440eec7958c
"""Compact task -> ordinary process -> independent output eligibility.

Formal native Windows adapter; the original technical worker is preserved.
Scientific helpers/kernels are reused; ownership is supplied by Windows Jobs.
"""
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples'),str(ROOT/'scripts/windows')]
from formal_runtime import atomic_json,file_hash,PhaseLedger
from batch_contract import validate_capsule,mh_config


def request_data(path):
    from formal_execution import load_worker_request
    request,c=load_worker_request(path,ROOT)
    if request['phase']!='main':raise ValueError('Posterior worker cannot execute cache measurements')
    if c['source_files'].get('scripts/windows/formal_batch_worker.py')!=file_hash(__file__):
        raise ValueError('Formal posterior worker source must be bound')
    return request,c


def payload(request,c):
    from formal_streaming import read_member
    from mechanism_runner import actual_hash
    path=Path(request['inputs'])/c['task']['input']
    if file_hash(path)!=c['input']['sha256']:raise ValueError('Actual input file differs')
    values={k:read_member(path,k,c['controls']['maximum_member_bytes']) for k in ('initial','noise','log_uniform','directions','nuts_seeds')}
    if actual_hash(values)!=c['input']['actual_sha256']:raise ValueError('Actual input arrays differ')
    return values


def ordinary(request_path,output,*,request_loader=request_data):
    import numpy as np
    import torch
    from inference_targets import build_target
    from inference_readiness import save_result
    from inference_budget_pilot import save_parallel
    from inference_parallel_nuts import sample_parallel_nuts
    from inference_estimands import evaluate
    from parallelbayes.torch_backend.sampling import sample,sync
    output=Path(output);ledger=PhaseLedger(output/'ordinary-phases.json')
    with ledger.phase('source_environment_input_target'):
        request,c=request_loader(request_path);task=c['task'];ctrl=c['controls']
        torch.set_num_threads(ctrl['torch_threads']);torch.set_num_interop_threads(1)
        values=payload(request,c)
        from job_objects import Job,identity
        with Job(os.environ['PB_OWNED_JOB'],existing=True) as owned:
            membership=identity(os.getpid(),owned.handle)
            if not membership['member_of_owned_job']:raise RuntimeError('Ordinary worker is not owned')
        atomic_json(output/'ordinary-ownership.json',membership)
        if task['device']=='cuda':
            free,total=torch.cuda.mem_get_info()
            atomic_json(output/'cuda-before.json',dict(free_bytes=free,total_bytes=total,allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved(),scope='Device free snapshot includes other applications; allocator counters belong to ordinary process'))
            if free<request['required_gpu_free_bytes']:raise MemoryError('CUDA free budget refused without allocating it')
        model=build_target(c['target'],request.get('source_directory'),task['device'])
        ledger.synchronise=lambda:sync(model.device)
        atomic_json(output/'environment.json',dict(python=sys.version,platform=sys.platform,
            packages={n:importlib.metadata.version(n) for n in c['required_versions']},
            torch_threads=torch.get_num_threads(),interop_threads=torch.get_num_interop_threads(),
            thread_environment={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS')},
            device=str(model.device),dtype='float64',CPU_threads_are_not_exclusive_cores=True))
    with ledger.phase('ordinary_sampling_including_transfer_transform'):
        if task['kernel']=='nuts':
            result=sample_parallel_nuts(model.spec,model.target_id,values['initial'],values['nuts_seeds'].tolist(),
                workers=ctrl['nuts_workers'],threads_per_worker=ctrl['nuts_threads'],draws=task['budget'],
                warmup=ctrl['nuts_warmup'],max_tree_depth=ctrl['nuts_tree_depth'],target_accept_prob=ctrl['nuts_target_accept'],
                full_mass=ctrl['nuts_full_mass'],memory_limit_mb=ctrl['memory_limit_mb'])
        else:
            config=mh_config(c,values['initial'].tolist());n=config['draws']
            tape={k:values[k][:,:n] for k in ('noise','log_uniform','directions')}
            result=sample(model,config,tape)
    with ledger.phase('ordinary_full_array_output'):
        if task['kernel']=='nuts':save_parallel(output,result);(output/'fit.json').rename(output/'candidate.json')
        else:save_result(output,'candidate',result);(output/'candidate.npz').rename(output/'fit.npz')
    diagnostics='not_available';diagnostic_error=None
    if result['status']=='completed':
        with ledger.phase('ordinary_functions_and_R_diagnostics'):
            retained=result['draws'] if task['kernel']=='nuts' else result['draws'][:,ctrl['mh_discard']:]
            try:fn=evaluate(model.spec,retained)
            except (FloatingPointError,OverflowError) as exc:
                diagnostics='function_failure';diagnostic_error=str(exc)
                atomic_json(output/'function-failure.json',dict(error=diagnostic_error,samples_status='Numerical trajectory decision is separate'))
            else:
                folder=output/'diagnostics';folder.mkdir()
                array=fn['values'].transpose(1,0,2)
                if array.shape[:2]!=(task['budget'],ctrl['chains']):raise ValueError('Retained function shape differs')
                np.asarray(array,dtype='<f8').ravel(order='F').tofile(folder/'functions.bin')
                atomic_json(folder/'transport.json',dict(fits=[dict(id=task['id'],input='functions.bin',shape=list(array.shape),names=fn['names'])],
                    scope='Ordinary candidate; post-process numerical eligibility audit remains pending',independent_unit='One declared four-chain input; scope follows the bound protocol'))
                env=dict(os.environ)
                if request.get('r_library'):env['R_LIBS_USER']=request['r_library']
                run=subprocess.run([request['rscript'],'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(folder)],capture_output=True,text=True,env=env)
                (folder/'R.log').write_text(run.stdout+run.stderr)
                if run.returncode:raise RuntimeError('R diagnosis failed; candidate artifacts retained')
                if file_hash(folder/'functions.bin')!=file_hash(folder/'functions.bin.roundtrip'):raise ValueError('R transport changed bytes')
                post=json.loads((folder/'posterior.json').read_text())
                if post['R']!=c['required_R_version'] or post['posterior']!=c['required_R_posterior']:raise ValueError('R environment differs')
                atomic_json(folder/'estimates.json',dict(names=fn['names'],means=fn['values'].mean(axis=(0,1)).tolist()))
                diagnostics='completed'
    sync(model.device)
    if task['device']=='cuda':
        atomic_json(output/'cuda-after.json',dict(free_bytes=torch.cuda.mem_get_info()[0],allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved(),peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved(),synchronized=True,scope='Ordinary-process allocator peak, not whole-device or job RSS'))
    atomic_json(output/'ordinary-output.json',dict(candidate_status=result['status'],samples_eligible=False,
        task=task,protocol_sha256=c['protocol_sha256'],capsule_sha256=request['capsule_sha256'],target_id=model.target_id,
        diagnostics_status=diagnostics,diagnostic_error=diagnostic_error,nested_sampler_timing=result['timing'],
        output_policy='Full original/unconstrained paths and acceptance or NUTS adaptation, function transport and R diagnostics',
        timing_components_additive_to_process_wall=False))


def audited(request_path,output,*,request_loader=request_data,ordinary_worker=None):
    from measured_workflow import ordinary_process,audit_candidate
    output=Path(output);ledger=PhaseLedger(output/'phases.json')
    with ledger.phase('task_contract_validation'):
        request,c=request_loader(request_path);task=c['task'];ctrl=c['controls']
    with ledger.phase('ordinary_process_start_through_exit'):
        timing=ordinary_process([sys.executable,str(Path(ordinary_worker or __file__)),'ordinary',str(request_path),str(output)],output)
    atomic_json(output/'ordinary-process.json',timing)
    if timing['return_code']==3 and (output/'ordinary-resource-failure.json').exists():
        atomic_json(output/'worker-result.json',dict(status='failed',samples_eligible=False,failure_category='resource_failure',
            task=task,protocol_sha256=c['protocol_sha256'],ordinary_process=timing,capsule_sha256=request['capsule_sha256']))
        return
    if timing['return_code']!=0:raise RuntimeError('Ordinary child exited '+str(timing['return_code']))
    with ledger.phase('independent_research_audit'):
        import numpy as np
        from inference_targets import build_target
        from formal_streaming import read_member
        from mechanism_runner import plain
        from parallelbayes.torch_backend.sampling import settings
        values=payload(request,c);model=build_target(c['target'],request.get('source_directory'),'cpu')
        meta=json.loads((output/'candidate.json').read_text());candidate=json.loads((output/'ordinary-output.json').read_text())
        if candidate['samples_eligible'] is not False or candidate['task']!=task or candidate['capsule_sha256']!=request['capsule_sha256']:
            raise ValueError('Ordinary candidate contract differs')
        if meta['target_id']!=model.target_id or candidate['target_id']!=model.target_id:raise ValueError('Target identity differs')
        raw=output/'fit.npz';before=file_hash(raw)
        def read(name):return read_member(raw,name,ctrl['maximum_member_bytes'])
        if task['kernel']=='nuts':
            passed=False
            if meta['status']=='completed':
                q=read('unconstrained');theta=read('draws');warm=read('warmup_states')
                shape=(ctrl['chains'],task['budget'],model.dimension)
                passed=bool(meta['provider']=='pyro_cpu_spawn_chains' and len(meta['worker_records'])==ctrl['chains'] and
                    q.shape==theta.shape==shape and warm.shape==(ctrl['chains'],ctrl['nuts_warmup'],model.dimension) and
                    np.isfinite(q).all() and np.isfinite(theta).all() and np.isfinite(warm).all() and
                    np.allclose(theta,model.constrain(q),rtol=1e-10,atol=1e-12) and
                    np.array_equal(read('initial'),values['initial']) and meta['chain_seeds']==values['nuts_seeds'].tolist())
                del q,theta,warm
            audit=dict(kind='NUTS_full_shapes_finite_transform_actual_initial_and_seeds',passed=passed,
                       MH_path_equivalence=False,convergence_proven=False)
            decision=dict(status='completed' if passed else 'failed',samples_eligible=passed,audit=audit,
                          failure_category=None if passed else 'output_failure_unclassified')
        else:
            expected=settings(mh_config(c,values['initial'].tolist()))
            if meta['config']!=expected:raise ValueError('MH kernel configuration differs')
            fit=dict(meta)
            if meta['status']=='completed':fit.update({k:read(k) for k in ('draws','unconstrained','accept')})
            n=expected['draws'];tape={k:values[k][:,:n] for k in ('noise','log_uniform','directions')}
            decision=audit_candidate(model,expected,tape,fit)
            del fit,tape
        if file_hash(raw)!=before:raise ValueError('Candidate arrays changed during audit')
        decision=plain(decision)
    with ledger.phase('research_evidence_finalization'):
        atomic_json(output/'external-audit.json',decision)
        final=dict(meta,status=decision['status'],external_audit=decision,
            ordinary_candidate_metadata_sha256=file_hash(output/'candidate.json'),ordinary_candidate_arrays_sha256=before)
        if task['kernel']!='nuts':final.update(audit=decision['audit'],primary_audit=decision['audit'],
            guarantee='independently_audited_fixed_tape' if decision['samples_eligible'] else 'failed_output_quarantined')
        atomic_json(output/'fit.json',final)
    atomic_json(output/'worker-result.json',dict(status=decision['status'],samples_eligible=decision['samples_eligible'],
        failure_category=decision['failure_category'],task=task,target_id=model.target_id,protocol_sha256=c['protocol_sha256'],
        capsule_sha256=request['capsule_sha256'],ordinary_process=timing,diagnostics_status=candidate['diagnostics_status'],
        diagnostics_completed=candidate['diagnostics_status']=='completed',full_MH_audit=None if task['kernel']=='nuts' else decision['audit'],
        ordinary_workflow_measured_separately=True,cached_execution_measured=False,
        numerical_validity_is_not_statistical_exploration=True,formal_inference_complete=False))


if __name__=='__main__':
    # The supervisor supplies request/output; only this worker invokes its
    # internal ordinary mode explicitly.
    mode='ordinary' if sys.argv[1]=='ordinary' else 'audited'
    request_path,output=sys.argv[2:4] if mode=='ordinary' else sys.argv[1:3]
    try:(ordinary if mode=='ordinary' else audited)(request_path,output)
    except (MemoryError, __import__('torch').OutOfMemoryError) as exc:
        if mode=='ordinary':
            atomic_json(Path(output)/'ordinary-resource-failure.json',dict(error=str(exc),samples_eligible=False));sys.exit(3)
        atomic_json(Path(output)/'worker-result.json',dict(status='failed',samples_eligible=False,failure_category='resource_failure',error=str(exc)))
    except BaseException:
        traceback.print_exc();sys.exit(1)
