"""Persistent ordered compact phases; pause, command errors and resource waits stop dispatch.

This manager owns each actual child Job through compact_command. A manager
death closes its Job handle and ends descendants. Resume is explicit and
does not retry terminal sampling or cache tasks. No total-time cutoff.
"""
import argparse
import json
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/windows'),str(ROOT/'scripts/completion')]
from compact_command import run as command
from compact_freeze import verify
from compact_execution import CompactDispatch
from formal_runtime import atomic_json,host_lease
from formal_batch import verify_phase_closure


def run(bundle,output,native_acceptance,*,resume=False):
    bundle=Path(bundle).resolve();output=Path(output).resolve()
    marker,p,plan,_=verify(bundle);dispatch=CompactDispatch(p,plan,ROOT)
    if plan['technical']:raise ValueError('This sequence is only the three compact formal batches')
    if output.is_relative_to(bundle):raise ValueError('Outer cost directory must be separate from study evidence')
    output.mkdir(parents=True,exist_ok=True)
    with host_lease(output/'sequence.lock','single compact sequence manager'):
        invocation=output/'invocations'/uuid.uuid4().hex;invocation.mkdir(parents=True)
        from job_objects import identity
        import os
        atomic_json(invocation/'started.json',dict(protocol_sha256=p['protocol_sha256'],manager=identity(os.getpid()),
            source_commit=p['source_commit'],resume=resume,no_total_time_cutoff=True))
        for batch,phase in dispatch.phases:
            phase_root=bundle/'formal-runs'/f'batch-{batch:02d}'/phase
            if (phase_root/'latest-closed.json').exists():
                if not resume:raise ValueError('Already closed phase; explicit resume required')
                verify_phase_closure(phase_root,dispatch,batch,phase)
                atomic_json(invocation/f'batch-{batch}-{phase}-reused.json',dict(new_sampler_calls=0,closed=True))
                continue
            args=[sys.executable,str(ROOT/'scripts/windows/compact_batch.py'),'run','--bundle',str(bundle),
                '--batch',str(batch),'--phase',phase,'--native-acceptance',str(Path(native_acceptance).resolve())]
            if phase_root.exists():
                if not resume:raise ValueError('Previous open phase; explicit resume required')
                args.append('--resume')
            code=command(args,invocation/f'batch-{batch}-{phase}')
            if code!=0:
                result=dict(status='command_failed_dispatch_stopped',batch=batch,phase=phase,exit_code=code)
                atomic_json(invocation/'finished.json',result);return result
            if not (phase_root/'latest-closed.json').exists():
                result=dict(status='not_closed_dispatch_stopped',batch=batch,phase=phase,reason='Boundary pause or incomplete phase')
                atomic_json(invocation/'finished.json',result);return result
            verify_phase_closure(phase_root,dispatch,batch,phase)
        result=dict(status='all_prespecified_phases_closed',main=3888,cache=256,
            phase_closure_is_not_numerical_qualification=True)
        atomic_json(invocation/'finished.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bundle','output','native-acceptance'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume',action='store_true')
    result=run(**vars(p.parse_args()));print(json.dumps(result),flush=True)
    sys.exit(0 if result['status']=='all_prespecified_phases_closed' else 1)
