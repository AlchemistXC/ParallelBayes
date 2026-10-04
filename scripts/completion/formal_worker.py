"""One native worker: frozen target/input -> audited fit -> bounded R diagnostics.

This is an execution component, not permission to run an unfrozen experiment.
Only technical protocols are accepted until the full formal gates are closed.
"""
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from formal_runtime import PhaseLedger,atomic_json,file_hash,fingerprint


def main(request_path,output):
    output=Path(output);ledger=PhaseLedger(output/'phases.json')
    with ledger.phase('request_protocol_source_validation'):
        request=json.loads(Path(request_path).read_text())
        p=json.loads(Path(request['protocol']).read_text());unsigned=dict(p)
        digest=unsigned.pop('protocol_sha256')
        if fingerprint(unsigned)!=digest:raise ValueError('Protocol checksum differs')
        if p['scope_kind']!='technical_runtime_validation':raise ValueError('Formal launch gates are not implemented/closed')
        if sys.platform!=p['required_platform']:raise ValueError('Native platform mismatch')
        for name,h in p['source_files'].items():
            if file_hash(ROOT/name)!=h:raise ValueError('Frozen source changed: '+name)
        task=next(t for t in p['tasks'] if t['id']==request['task_id'])
        item=next(t for t in p['targets'] if t['name']==task['model'])
        for name,version in p['required_versions'].items():
            if importlib.metadata.version(name)!=version:raise ValueError('Dependency mismatch: '+name)
    with ledger.phase('backend_import_and_initialization'):
        import numpy as np
        import torch
        from inference_targets import build_target
        from inference_readiness import save_result
        from inference_budget_pilot import save_parallel
        from inference_parallel_nuts import sample_parallel_nuts
        from inference_estimands import evaluate
        from parallelbayes.torch_backend.sampling import sample,sync
        from mechanism_runner import actual_hash
        torch.set_num_threads(p['torch_threads']);torch.set_num_interop_threads(1)
        device=task['device']
        if device.startswith('cuda') and not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; no substitution')
        ledger.synchronise=lambda:sync(torch.device(device))
        atomic_json(output/'environment.json',dict(python=platform.python_version(),platform=platform.platform(),
            packages={k:importlib.metadata.version(k) for k in p['required_versions']},
            device=device,torch_threads=torch.get_num_threads(),torch_interop_threads=torch.get_num_interop_threads(),
            thread_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS']},
            cuda_build=torch.version.cuda,cpu_allocation='Requested thread counts, not exclusive physical cores'))
    with ledger.phase('input_read_and_actual_array_validation'):
        input_file=Path(request['inputs'])/item['input'];expected=p['inputs'][item['input']]
        if file_hash(input_file)!=expected['sha256']:raise ValueError('Input file changed')
        with np.load(input_file,allow_pickle=False) as z:payload={k:z[k].copy() for k in z.files}
        if actual_hash(payload)!=expected['actual_sha256']:raise ValueError('Actual input arrays differ')
        initial=payload.pop('initial');seeds=payload.pop('nuts_seeds').tolist()
    with ledger.phase('target_reconstruction'):
        model=build_target(item,request.get('source_directory'),device)
    with ledger.phase('sampler_including_internal_transfer_audit_transform'):
        if task['kernel']=='nuts':
            if device!='cpu':raise ValueError('This NUTS workflow is native CPU only')
            result=sample_parallel_nuts(model.spec,model.target_id,initial,seeds,workers=4,threads_per_worker=1,
                draws=p['draws'],warmup=p['nuts_warmup'],max_tree_depth=8,target_accept_prob=.8,
                full_mass=False,memory_limit_mb=p['memory_limit_mb'])
        else:
            total=p['mh_discard']+p['draws'];tape={k:v[:,:total] for k,v in payload.items()}
            config=dict(kernel=task['kernel'],executor=task['executor'],device=device,chains=p['chains'],draws=total,
                initial=initial.tolist(),step_size=item['step_'+task['kernel']],window=p['window'],
                max_iter=total if task['executor']=='online_picard' else p['quasi_deer_max_iter'],
                atol=p['atol'],rtol=p['rtol'],memory_limit_mb=p['memory_limit_mb'],audit=True,on_failure='error')
            result=sample(model,config,tape)
    with ledger.phase('raw_result_archive'):
        if task['kernel']=='nuts':save_parallel(output,result)
        else:save_result(output,'fit',result)
    diagnostic=False
    if result['status']=='completed':
        with ledger.phase('estimands_and_R_diagnostics_including_transport'):
            draws=result['draws'] if task['kernel']=='nuts' else result['draws'][:,p['mh_discard']:]
            values=evaluate(model.spec,draws)
            if values['values'].shape[:2]!=(p['chains'],p['draws']):raise ValueError('Retained function shape differs')
            folder=output/'diagnostics';folder.mkdir()
            array=values['values'].transpose(1,0,2);binary=folder/'functions.bin'
            np.asarray(array,dtype='<f8').ravel(order='F').tofile(binary)
            atomic_json(folder/'transport.json',dict(fits=[dict(id=task['id'],input=binary.name,
                shape=list(array.shape),names=values['names'])],scope=p['scope'],
                independent_unit='One technical four-chain input per model; executions are not independent repetitions'))
            env=dict(os.environ)
            if request.get('r_library'):env['R_LIBS_USER']=request['r_library']
            r=subprocess.run([request['rscript'],'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(folder)],
                capture_output=True,text=True,env=env)
            (folder/'R.log').write_text(r.stdout+r.stderr,encoding='utf-8')
            if r.returncode:raise RuntimeError('R diagnostics failed; sampler arrays remain saved')
            if file_hash(binary)!=file_hash(folder/'functions.bin.roundtrip'):raise ValueError('R binary roundtrip differs')
            posterior=json.loads((folder/'posterior.json').read_text())
            if posterior['posterior']!=p['required_R_posterior'] or posterior['R']!=p['required_R_version']:
                raise ValueError('R diagnostic environment differs')
            atomic_json(folder/'estimates.json',dict(names=values['names'],means=values['values'].mean(axis=(0,1)).tolist()))
            diagnostic=True
    atomic_json(output/'worker-result.json',dict(status=result['status'],samples_eligible=result['status']=='completed',
        target_id=model.target_id,task=task,protocol_sha256=digest,diagnostics_completed=diagnostic,
        scientific_scope='Technical numerical/workflow validation, not inference accuracy or performance evidence',
        nested_sampler_timing=result['timing'],nested_sampler_timing_is_additive_to_worker_phases=False,
        cached_execution_measured=False,ordinary_workflow_measured_separately=False,
        full_MH_audit=None if task['kernel']=='nuts' else result['audit']))


if __name__=='__main__':
    try:main(sys.argv[1],sys.argv[2])
    except BaseException:
        traceback.print_exc();sys.exit(1)
