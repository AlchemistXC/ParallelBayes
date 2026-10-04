"""Freeze/run a finite native Mac task-lifecycle validation, not formal inference."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_runtime import atomic_json,file_hash,fingerprint,execute_task


def freeze(protocol,inputs,rscript,r_library):
    import numpy as np
    from formal_inputs import build_payload,validate_addresses
    from inference_budget_pilot import source_files
    from mechanism_runner import actual_hash
    protocol=Path(protocol);inputs=Path(inputs)
    if protocol.exists() or inputs.exists():raise FileExistsError('New technical protocol and input directory required')
    if sys.platform!='darwin':raise ValueError('New native profile required for a different host')
    sources=source_files()
    for name in ['scripts/completion/formal_inputs.py','scripts/completion/formal_runtime.py',
        'scripts/completion/formal_worker.py','scripts/completion/formal_runtime_validation.py',
        'scripts/completion/inference_targets.py','scripts/completion/posterior_diagnostics.R',
        'benchmark/protocols/inference-budget-pilot-mac-v1.json']:
        sources[name]=file_hash(ROOT/name)
    for name,h in sources.items():
        import hashlib
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit all source before freezing: '+name)
    env=dict(os.environ)
    if r_library:env['R_LIBS_USER']=str(r_library)
    command='cat(jsonlite::toJSON(list(R=R.version.string,posterior=as.character(packageVersion("posterior"))),auto_unbox=TRUE))'
    r=json.loads(subprocess.check_output([str(rscript),'--vanilla','-e',command],env=env,text=True))
    old=json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    targets=[dict(x) for x in old['targets'] if x['name'] in ('G1','L1')]
    p=dict(identity='formal-runtime-technical-mac-v1',scope_kind='technical_runtime_validation',
        scope='Finite real-worker lifecycle validation, one actual four-chain input per target; not formal inference or timing comparison',
        required_platform='darwin',source_files=dict(sorted(sources.items())),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        required_versions={n:importlib.metadata.version(n) for n in ['numpy','torch','pyro-ppl','scipy','psutil']},
        required_R_version=r['R'],required_R_posterior=r['posterior'],
        targets=targets,chains=4,draws=64,mh_discard=16,nuts_warmup=32,torch_threads=4,
        window=32,quasi_deer_max_iter=2048,memory_limit_mb=2048,atol=1e-10,rtol=1e-10,
        process_tree_rss_limit_bytes=4*1024**3,required_disk_bytes_per_task=128*1024**2,
        inputs={},tasks=[],formal_inference_complete=False,
        geometry_step_source=old['protocol_sha256'],cached_execution_measured=False,
        no_total_time_cutoff=True,resource_guards_are_not_allocator_guarantees=True)
    p['address_check']=validate_addresses(p['identity'],[x['name'] for x in targets],[0],4)
    inputs.mkdir(parents=True)
    for item in targets:
        item['input']=item['name']+'.npz'
        tape=build_payload(p['identity'],item['name'],0,item['dimension'],p['draws']+p['mh_discard'],4)
        np.savez_compressed(inputs/item['input'],**tape)
        p['inputs'][item['input']]=dict(sha256=file_hash(inputs/item['input']),actual_sha256=actual_hash(tape))
        for kernel,executor in [('rwm','sequential'),('mala','sequential'),('rwm','online_picard'),('mala','quasi_deer'),('nuts','spawn_chains')]:
            task=dict(model=item['name'],kernel=kernel,executor=executor,device='cpu',replicate=0)
            task['id']=fingerprint(task)[:20];p['tasks'].append(task)
    p['protocol_sha256']=fingerprint(p);protocol.parent.mkdir(parents=True,exist_ok=True)
    atomic_json(protocol,p)
    return dict(source_commit=p['source_commit'],protocol_sha256=p['protocol_sha256'],tasks=len(p['tasks']))


def run(protocol,inputs,output,rscript,r_library,host_lock,resume=False):
    import numpy as np
    from selected_mh_readiness import compare
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if fingerprint(unsigned)!=digest:raise ValueError('Protocol hash differs')
    if p['scope_kind']!='technical_runtime_validation' or p['required_platform']!=sys.platform:
        raise ValueError('Only the declared native technical profile is supported')
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Frozen source changed: '+name)
    output=Path(output);output.mkdir(parents=True,exist_ok=resume)
    records=[];new=0
    for task in p['tasks']:
        request=dict(protocol=str(Path(protocol).resolve()),inputs=str(Path(inputs).resolve()),
            task_id=task['id'],rscript=str(Path(rscript).resolve()),r_library=str(Path(r_library).resolve()) if r_library else None)
        print(json.dumps(dict(starting=task)),flush=True)
        result=execute_task(dict(task,protocol_sha256=digest),request,ROOT/'scripts/completion/formal_worker.py',
            output/task['id'],host_lock,required_disk_bytes=p['required_disk_bytes_per_task'],
            max_tree_rss_bytes=p['process_tree_rss_limit_bytes'],resume=resume)
        new+=result['newly_executed'];records.append(result)
        print(json.dumps(dict(done=task['id'],status=result['status'],resumed=result['resumed'])),flush=True)
    pair_rows=[];diagnostics=[]
    for item in p['targets']:
        fits={}
        for state in records:
            task=state['task']
            if task['model']!=item['name']:continue
            folder=output/task['id']/state['attempt']
            if state['status']=='completed':
                post=json.loads((folder/'diagnostics/posterior.json').read_text())
                diagnostics.extend(post['results'][task['id']])
                if task['kernel']!='nuts':
                    with np.load(folder/'fit.npz',allow_pickle=False) as z:
                        fits[(task['kernel'],task['executor'])]=dict(status='completed',**{k:z[k] for k in ['draws','unconstrained','accept']})
        for kernel,executor in [('rwm','online_picard'),('mala','quasi_deer')]:
            pair=compare(fits.get((kernel,'sequential'),{}),fits.get((kernel,executor),{}),p)
            pair_rows.append(dict(model=item['name'],kernel=kernel,executor=executor,**pair))
    summary=dict(protocol_sha256=digest,source_commit=p['source_commit'],planned=len(p['tasks']),
        completed=sum(x['status']=='completed' for x in records),failed=sum(x['status']=='failed' for x in records),
        interrupted=sum(x['status']=='interrupted' for x in records),newly_executed_tasks=new,
        passed_pairs=sum(x['passed'] for x in pair_rows),pairs=pair_rows,
        R_diagnostic_workflows=sum(bool(x.get('worker_result') and x['worker_result']['diagnostics_completed']) for x in records),
        finite_function_rhat_above_1_01=sum(x.get('rhat') is not None and x['rhat']>1.01 for x in diagnostics),
        undefined_function_rhat=sum(x.get('rhat') is None for x in diagnostics),
        maximum_sampled_tree_rss_bytes=max(x['memory']['sampled_peak_tree_rss_bytes'] for x in records),
        formal_inference_complete=False,cached_execution_measured=False,
        scope=p['scope'],native_windows_validated=False)
    history=output/'invocations';history.mkdir(exist_ok=True)
    atomic_json(history/(str(time.time_ns())+'.json'),dict(summary,resume=resume))
    atomic_json(output/'summary.json',summary)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze')
    r=sub.add_parser('run')
    for child in [f,r]:
        for name in ['protocol','inputs','rscript','r-library']:child.add_argument('--'+name,type=Path,required=True)
    for name in ['output','host-lock']:r.add_argument('--'+name,type=Path,required=True)
    r.add_argument('--resume',action='store_true');a=parser.parse_args()
    result=freeze(a.protocol,a.inputs,a.rscript,a.r_library) if a.action=='freeze' else run(a.protocol,a.inputs,a.output,a.rscript,a.r_library,a.host_lock,a.resume)
    print(json.dumps(result,indent=2))
