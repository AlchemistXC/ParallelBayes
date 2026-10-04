"""Standalone ordinary Python batch plus R diagnostics; no MH path audit.

Writes candidate artifacts only. The outer audit worker decides research
eligibility after this process exits. The output policy includes full retained
paths and existing NUTS adaptation records; it is not a minimal R-user latency.
"""
import json
import os
from pathlib import Path
import sys
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]


def main(request_path,output):
    import importlib.metadata
    import platform
    import subprocess
    import numpy as np
    import torch
    from formal_runtime import PhaseLedger,atomic_json,file_hash,fingerprint
    from inference_targets import build_target
    from inference_readiness import save_result
    from inference_budget_pilot import save_parallel
    from inference_parallel_nuts import sample_parallel_nuts
    from inference_estimands import evaluate
    from mechanism_runner import actual_hash
    from parallelbayes.torch_backend.sampling import sample,sync
    output=Path(output);ledger=PhaseLedger(output/'ordinary-phases.json')
    with ledger.phase('protocol_input_and_target_setup'):
        request=json.loads(Path(request_path).read_text());p=json.loads(Path(request['protocol']).read_text())
        unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
        if fingerprint(unsigned)!=digest or p['scope_kind']!='technical_runtime_validation' or p['required_platform']!=sys.platform:
            raise ValueError('Only the declared native technical profile is supported')
        for name,h in p['source_files'].items():
            if file_hash(ROOT/name)!=h:raise ValueError('Frozen source differs: '+name)
        for name,version in p['required_versions'].items():
            if importlib.metadata.version(name)!=version:raise ValueError('Dependency differs: '+name)
        torch.set_num_threads(p['torch_threads']);torch.set_num_interop_threads(1)
        task=next(t for t in p['tasks'] if t['id']==request['task_id'])
        item=next(t for t in p['targets'] if t['name']==task['model'])
        model=build_target(item,request.get('source_directory'),task['device'])
        ledger.synchronise=lambda:sync(model.device)
        expected=p['inputs'][item['input']];input_file=Path(request['inputs'])/item['input']
        if file_hash(input_file)!=expected['sha256']:raise ValueError('Actual input file changed')
        with np.load(input_file,allow_pickle=False) as z:payload={k:z[k].copy() for k in z.files}
        if actual_hash(payload)!=expected['actual_sha256']:raise ValueError('Actual input arrays differ')
        initial=payload.pop('initial');seeds=payload.pop('nuts_seeds').tolist()
        atomic_json(output/'environment.json',dict(python=sys.version,platform=platform.platform(),
            packages={k:importlib.metadata.version(k) for k in p['required_versions']},
            device=task['device'],torch_threads=torch.get_num_threads(),torch_interop_threads=torch.get_num_interop_threads()))
    with ledger.phase('ordinary_sampler_including_transfer_and_transform'):
        if task['kernel']=='nuts':
            if task['device']!='cpu':raise ValueError('NUTS is native CPU only')
            result=sample_parallel_nuts(model.spec,model.target_id,initial,seeds,workers=4,threads_per_worker=1,
                draws=p['draws'],warmup=p['nuts_warmup'],max_tree_depth=8,target_accept_prob=.8,
                full_mass=False,memory_limit_mb=p['memory_limit_mb'])
        else:
            total=p['draws']+p['mh_discard'];tape={k:v[:,:total] for k,v in payload.items()}
            config=dict(kernel=task['kernel'],executor=task['executor'],device=task['device'],chains=p['chains'],draws=total,
                initial=initial.tolist(),step_size=item['step_'+task['kernel']],window=p['window'],
                max_iter=total if task['executor']=='online_picard' else p['quasi_deer_max_iter'],
                atol=p['atol'],rtol=p['rtol'],memory_limit_mb=p['memory_limit_mb'],audit=False,on_failure='error')
            result=sample(model,config,tape)
    with ledger.phase('declared_ordinary_array_output'):
        if task['kernel']=='nuts':
            save_parallel(output,result);(output/'fit.json').rename(output/'candidate.json')
        else:
            save_result(output,'candidate',result);(output/'candidate.npz').rename(output/'fit.npz')
    diagnostic=False
    if result['status']=='completed':
        with ledger.phase('ordinary_estimands_and_R_diagnostics'):
            values=evaluate(model.spec,result['draws'] if task['kernel']=='nuts' else result['draws'][:,p['mh_discard']:])
            folder=output/'diagnostics';folder.mkdir();array=values['values'].transpose(1,0,2)
            np.asarray(array,dtype='<f8').ravel(order='F').tofile(folder/'functions.bin')
            atomic_json(folder/'transport.json',dict(fits=[dict(id=task['id'],input='functions.bin',shape=list(array.shape),names=values['names'])],
                scope='Candidate ordinary Python batch, outer eligibility not yet decided',independent_unit='Existing technical four-chain input'))
            env=dict(os.environ)
            if request.get('r_library'):env['R_LIBS_USER']=request['r_library']
            call=subprocess.run([request['rscript'],'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(folder)],capture_output=True,text=True,env=env)
            (folder/'R.log').write_text(call.stdout+call.stderr)
            if call.returncode:raise RuntimeError('R diagnostics failed')
            if file_hash(folder/'functions.bin')!=file_hash(folder/'functions.bin.roundtrip'):raise ValueError('R transport differs')
            post=json.loads((folder/'posterior.json').read_text())
            if post['R']!=p['required_R_version'] or post['posterior']!=p['required_R_posterior']:raise ValueError('R environment differs')
            atomic_json(folder/'estimates.json',dict(names=values['names'],means=values['values'].mean(axis=(0,1)).tolist()))
            diagnostic=True
    sync(model.device)
    atomic_json(output/'ordinary-output.json',dict(candidate_status=result['status'],samples_eligible=False,
        eligibility='Outer research audit has not yet run',task=task,target_id=model.target_id,
        protocol_sha256=digest,diagnostics_completed=diagnostic,raw_file='fit.npz',metadata_file='candidate.json',
        nested_sampler_timing=result['timing'],nested_components_are_additive_to_ordinary_wall=False,
        output_policy='Full retained original/unconstrained paths, acceptance or NUTS warmup/adaptation records, R function transport and diagnostics; not a minimal R front-end output'))


if __name__=='__main__':
    try:main(sys.argv[1],sys.argv[2])
    except MemoryError as exc:
        from formal_runtime import atomic_json
        atomic_json(Path(sys.argv[2])/'ordinary-resource-failure.json',dict(error=str(exc),failure_category='resource_failure',samples_eligible=False))
        sys.exit(3)
    except BaseException:
        traceback.print_exc();sys.exit(1)
