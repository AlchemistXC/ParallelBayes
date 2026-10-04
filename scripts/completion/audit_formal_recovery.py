"""Recover one frozen real CPU workflow after an injected outer-worker exit.

This is a new technical companion, not a new statistical repetition or formal
inference protocol. The original ten-task evidence is only read.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_runtime import atomic_json,file_hash,fingerprint,execute_task
from formal_recovery import recover_task,retry_task
from formal_outcomes import read_attempt,summarize_attempts


WRAPPER='''import json,shutil,subprocess,sys
from pathlib import Path
out=Path(sys.argv[2]);request=json.loads(Path(sys.argv[1]).read_text())
science=out/'science';science.mkdir()
actual=out/'science-request.json'
actual.write_text(json.dumps(request['scientific_request'],sort_keys=True,indent=2)+'\\n')
completed=subprocess.run([sys.executable,request['real_worker'],str(actual),str(science)])
if completed.returncode:sys.exit(completed.returncode)
if str(out.parent)==request['inject_after_science_directory']:
    (out/'injected-exit.json').write_text(json.dumps({'scope':'artificial outer-worker exit after real audited output; never a numerical failure'}))
    sys.exit(7)
shutil.copy2(science/'worker-result.json',out/'worker-result.json')
'''


def audit(protocol,inputs,output,rscript,r_library,host_lock):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    p=json.loads(protocol.read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if fingerprint(unsigned)!=digest:raise ValueError('Scientific technical protocol differs')
    if p['identity']!='formal-runtime-technical-mac-v1':raise ValueError('Only the stated technical companion dependency is accepted')
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Frozen dependency source changed')
    task=next(t for t in p['tasks'] if t['model']=='G1' and t['kernel']=='mala' and t['executor']=='sequential')
    wrapper=output/'injection-wrapper.py';wrapper.write_text(WRAPPER,encoding='utf-8')
    scientific_request=dict(protocol=str(protocol.resolve()),inputs=str(inputs.resolve()),task_id=task['id'],
        rscript=str(rscript.resolve()),r_library=str(r_library.resolve()))
    initial=output/'initial'
    request=dict(scientific_request=scientific_request,real_worker=str(ROOT/'scripts/completion/formal_worker.py'),
                 inject_after_science_directory=str(initial))
    sources=[Path(__file__),ROOT/'scripts/completion/formal_recovery.py',ROOT/'scripts/completion/formal_outcomes.py',
             ROOT/'scripts/completion/formal_runtime.py',wrapper]
    identity=dict(identity='formal-recovery-companion-mac-v2',source_commit=subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sources={str(x):file_hash(x) for x in sources},
        dependency_protocol_sha256=digest,dependency_task=task,actual_input=p['inputs']['G1.npz'],
        injection='Exit outer worker after frozen scientific worker completes; same request in explicit retry',
        new_independent_statistical_repetitions=0,formal_inference_complete=False)
    identity['companion_sha256']=fingerprint(identity)
    atomic_json(output/'companion.json',identity)
    kwargs=dict(task=dict(id='G1-MALA-recovery',companion_sha256=identity['companion_sha256']),
        request=request,worker=wrapper,output=initial,host_lock=host_lock,
        required_disk_bytes=128*1024**2,max_tree_rss_bytes=4*1024**3)
    first=execute_task(**kwargs)
    if first['status']!='interrupted' or first['return_code']!=7:raise AssertionError('Expected injected interruption not observed')
    before={str(f.relative_to(initial)):file_hash(f) for f in initial.rglob('*') if f.is_file()}
    recovery=recover_task(initial,host_lock=host_lock,reason='Predeclared technical injection after completed scientific worker')
    retried=retry_task(initial,host_lock=host_lock)
    if retried['status']!='completed':raise AssertionError('Frozen technical workflow retry did not complete')
    retry=Path(recovery['retry_output'])
    a=initial/'attempt-0001';b=retry/'attempt-0001'
    if (a/'science-request.json').read_bytes()!=(b/'science-request.json').read_bytes():raise AssertionError('Scientific request bytes changed')
    with np.load(a/'science/fit.npz',allow_pickle=False) as x,np.load(b/'science/fit.npz',allow_pickle=False) as y:
        if set(x.files)!=set(y.files):raise AssertionError('Saved array names differ')
        arrays=[]
        for name in x.files:
            xx=x[name];yy=y[name]
            if xx.dtype!=yy.dtype or xx.shape!=yy.shape or xx.tobytes()!=yy.tobytes():raise AssertionError('Actual array bytes differ: '+name)
            arrays.append(name)
    for folder in [a,b]:
        worker_result=json.loads((folder/'science/worker-result.json').read_text())
        if not worker_result['full_MH_audit']['passed'] or not worker_result['diagnostics_completed']:
            raise AssertionError('Independent audit or diagnostics did not pass')
    old_post=json.loads((a/'science/diagnostics/posterior.json').read_text())['results']
    new_post=json.loads((b/'science/diagnostics/posterior.json').read_text())['results']
    if old_post!=new_post:raise AssertionError('Repeated technical diagnostics differ')
    if before!={str(f.relative_to(initial)):file_hash(f) for f in initial.rglob('*') if f.is_file()}:
        raise AssertionError('Original interrupted evidence changed')
    retry_before={str(f.relative_to(retry)):file_hash(f) for f in retry.rglob('*') if f.is_file()}
    resumed=retry_task(initial,host_lock=host_lock)
    if resumed['newly_executed'] or retry_before!={str(f.relative_to(retry)):file_hash(f) for f in retry.rglob('*') if f.is_file()}:
        raise AssertionError('Terminal retry was repeated or modified')
    attempts=[read_attempt(initial),read_attempt(retry)];cost=summarize_attempts(attempts)
    if cost['outcome']!='valid' or cost['prior_interruption_known_seconds']<=0 or cost['unknown_cost_attempts']:
        raise AssertionError('Measured interruption cost lost')
    receipt=dict(companion_sha256=identity['companion_sha256'],source_commit=identity['source_commit'],
        original_status=first['status'],retry_status=retried['status'],original_files_unchanged=len(before),
        retry_files_unchanged=len(retry_before),second_retry_new_tasks=0,saved_arrays_byte_identical=arrays,
        independent_MH_audits_passed=2,R_diagnostics_identical=True,attempts=attempts,cost=cost,
        actual_scientific_executions=2,new_independent_statistical_repetitions=0,
        native_windows_recovery_validated=False,formal_inference_complete=False,
        scope='Mac technical recovery/replay of one existing frozen four-chain G1 MALA input; not inference accuracy, speed or general crash recovery')
    atomic_json(output/'receipt.json',receipt)
    atomic_json(output/'manifest.json',{f.relative_to(output).as_posix():file_hash(f) for f in sorted(output.rglob('*')) if f.is_file()})
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['protocol','inputs','output','rscript','r-library','host-lock']:
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();print(json.dumps(audit(a.protocol,a.inputs,a.output,a.rscript,a.r_library,a.host_lock),indent=2))
