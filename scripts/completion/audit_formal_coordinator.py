"""Finite Mac coordinator companion over three existing scientific inputs.

Uses frozen runtime technical workers; does not open the formal inference gate.
Artificial process-loss tests are separate from these actual MCMC executions.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_coordinator import TaskCoordinator
from formal_runtime import atomic_json,file_hash,fingerprint
from selected_mh_readiness import compare


def audit(protocol,inputs,output,rscript,r_library,host_lock):
    p=json.loads(protocol.read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if fingerprint(unsigned)!=digest or p['identity']!='formal-runtime-technical-mac-v1':
        raise ValueError('Only the fixed technical dependency is accepted')
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Frozen dependency source changed: '+name)
    source_names=['scripts/completion/'+x for x in ('formal_coordinator.py','formal_recovery.py',
        'formal_outcomes.py','formal_runtime.py','audit_formal_coordinator.py')]
    sources={name:file_hash(ROOT/name) for name in source_names}
    import hashlib
    for name,h in sources.items():
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit source before running technical companion: '+name)
    tasks=[t for t in p['tasks'] if (t['model']=='G1' and t['kernel']=='rwm') or (t['model']=='L1' and t['kernel']=='nuts')]
    if len(tasks)!=3:raise ValueError('Expected G1 sequential/Picard and L1 spawn NUTS')
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    identity=dict(identity='formal-coordinator-companion-mac-v1',source_commit=subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_files=sources,
        dependency_protocol_sha256=digest,dependency_tasks=tasks,actual_inputs=p['inputs'],
        host_lock=str(host_lock.resolve()),required_platform='darwin',
        scope='Three technical executions of existing two-model four-chain inputs; zero new independent statistical repetitions',
        formal_inference_complete=False)
    identity['companion_sha256']=fingerprint(identity);atomic_json(output/'companion.json',identity)
    atomic_json(output/'environment.json',dict(python=sys.version,platform=platform.platform(),
        packages={n:importlib.metadata.version(n) for n in ['numpy','torch','pyro-ppl','scipy','psutil']}))
    c=TaskCoordinator(host_lock);results=[];jobs=[]
    for task in tasks:
        request=dict(protocol=str(protocol.resolve()),inputs=str(inputs.resolve()),task_id=task['id'],
                     rscript=str(rscript.resolve()),r_library=str(r_library.resolve()))
        location=output/('mh' if task['kernel']=='rwm' else 'nuts')/task['id']
        kwargs=dict(task=dict(task,protocol_sha256=identity['companion_sha256']),request=request,
                    worker=ROOT/'scripts/completion/formal_worker.py',output=location,
                    required_disk_bytes=p['required_disk_bytes_per_task'],max_tree_rss_bytes=p['process_tree_rss_limit_bytes'])
        result=c.run(**kwargs)
        results.append(result);jobs.append(kwargs)
        if result['status']!='completed':raise AssertionError('Technical task did not complete: '+task['id'])
    fits={};diagnostics=[];hashes={}
    for task,job in zip(tasks,jobs):
        directory=job['output'];attempt=directory/'attempt-0001'
        for f in directory.rglob('*'):
            if f.is_file():hashes[str(f)]=file_hash(f)
        worker_result=json.loads((attempt/'worker-result.json').read_text())
        if not worker_result['diagnostics_completed']:raise AssertionError('R diagnostics absent')
        if file_hash(attempt/'diagnostics/functions.bin')!=file_hash(attempt/'diagnostics/functions.bin.roundtrip'):
            raise AssertionError('R binary differs')
        diagnostics.extend(json.loads((attempt/'diagnostics/posterior.json').read_text())['results'][task['id']])
        if task['kernel']=='rwm':
            if not worker_result['full_MH_audit']['passed']:raise AssertionError('Independent MH audit failed')
            with np.load(attempt/'fit.npz',allow_pickle=False) as z:
                fits[task['executor']]=dict(status='completed',**{k:z[k].copy() for k in ('draws','unconstrained','accept')})
    paired=compare(fits['sequential'],fits['online_picard'],p)
    if not paired['passed']:raise AssertionError('Paired scientific trajectories differ')
    resumed=[c.run(**job,resume=True) for job in jobs]
    if any(r['newly_executed'] for r in resumed) or any(file_hash(Path(f))!=h for f,h in hashes.items()):
        raise AssertionError('Resume executed new work or changed terminal evidence')
    histories=[c.history(job['output']) for job in jobs]
    if any(h['summary']['attempt_count']!=1 or h['summary']['outcome']!='valid' for h in histories):
        raise AssertionError('Coordinator history does not represent actual tasks')
    receipt=dict(companion_sha256=identity['companion_sha256'],source_commit=identity['source_commit'],
        completed=3,paired_check=paired,independent_MH_audits=2,R_binary_roundtrips=3,
        finite_function_rhat_above_1_01=sum(r.get('rhat') is not None and r['rhat']>1.01 for r in diagnostics),
        undefined_function_rhat=sum(r.get('rhat') is None for r in diagnostics),
        terminal_files_unchanged=len(hashes),resume_new_tasks=0,histories=histories,
        registry=str(c.registry_path),actual_technical_MCMC_executions=3,
        new_independent_statistical_repetitions=0,native_Windows_validated=False,
        ordinary_workflow_measured_separately=False,formal_inference_complete=False,
        scope=identity['scope'])
    atomic_json(output/'receipt.json',receipt)
    atomic_json(output/'manifest.json',{f.relative_to(output).as_posix():file_hash(f) for f in sorted(output.rglob('*')) if f.is_file()})
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['protocol','inputs','output','rscript','r-library','host-lock']:
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    print(json.dumps(audit(a.protocol,a.inputs,a.output,a.rscript,a.r_library,a.host_lock),indent=2))
