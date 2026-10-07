"""Sequential orchestration of the eight fixed, accepted formal CLI phases.

This lives outside the immutable sampling checkout. No retry, scientific lock,
input generation, sampler/config change, time limit or eligibility is added.
On any failed invocation/closure it stops and preserves the complete evidence.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid

ORDER = ((0,'main'), (0,'cache'), (1,'main'), (1,'cache'),
         (2,'main'), (2,'cache'), (3,'main'), (3,'cache'))
COMMIT = '0ba5643a6b580e79b8040f13a5e3165322db0e77'
DESIGN = '68a1cba1b9309216d237ac4613531216f167ff344dfdfcb72dc3aaca0ca0baa5'


def check_closed_summary(value, batch, phase):
    expected = 10368 if phase == 'main' else 2304
    if (value['batch'] != batch or value['phase'] != phase or
            value['planned'] != expected or value['visited'] != expected or value['closed'] is not True):
        raise ValueError('Incomplete or different fixed phase framework')


def directory_inventory(root):
    files=total=0
    for parent,dirs,names in os.walk(root):
        for name in names:
            path=Path(parent)/name
            if path.is_symlink():raise ValueError('Evidence symlink found')
            total+=path.stat().st_size;files+=1
    return dict(files=files,file_bytes=total,scope='File lengths, not allocated filesystem bytes')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--previous', type=Path)
    a = p.parse_args()
    config = json.loads(a.config.read_text(encoding='utf-8-sig'))
    root, bundle, costs = (Path(config[k]).resolve() for k in ('root', 'bundle', 'costs'))
    sys.path[:0] = [str(root/'scripts/windows'), str(root/'scripts/completion')]
    from formal_runtime import atomic_json, file_hash, host_lease
    from formal_freeze import verify_sealed_study
    from formal_execution import StudyDispatch
    from formal_batch import verify_phase_closure
    from formal_owned_runtime import Coordinator
    from job_objects import Job, observe_named_job, identity
    if a.resume != bool(a.previous):
        raise ValueError('Sequence resume requires the retained previous manager directory')
    if sys.platform != 'win32' or Path(sys.executable).resolve() != Path(config['python']).resolve():
        raise ValueError('Recorded native Python required')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()!=COMMIT:
        raise ValueError('Different execution commit')
    if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip():
        raise ValueError('Execution tree changed')
    if a.previous:
        previous = json.loads((a.previous/'started.json').read_text())
        import psutil
        try:
            psutil.Process(previous['manager_identity']['pid'])
            live_identity=identity(previous['manager_identity']['pid'])
        except psutil.NoSuchProcess:
            live_identity=None
        if live_identity and live_identity['creation_filetime']==previous['manager_identity']['creation_filetime']:
            raise ValueError('Original sequence manager still exists; do not launch another')
        for intent in a.previous.glob('*.job.json'):
            observed=observe_named_job(json.loads(intent.read_text())['name'])
            if observed['state']=='present' and observed['active_processes']:
                raise ValueError('Original sequence owned Job still active; resume refused')
    marker, protocol = verify_sealed_study(bundle)
    ready = json.loads((costs/'READY.json').read_text())
    if (marker['design_sha256'] != DESIGN or ready['freeze_sha256'] != file_hash(bundle/'FROZEN.json') or
            ready['protocol_sha256'] != protocol['protocol_sha256'] or ready['source_commit'] != COMMIT or
            ready['gate_exit_code'] != 0 or not ready['frozen_report_pushed']):
        raise ValueError('Explicit verified/pushed freeze receipt required')
    plan = json.loads((bundle/'study-plan.json').read_text())
    catalog = json.loads((bundle/'catalog.json').read_text())
    dispatch = StudyDispatch(protocol, plan['cache_allocation'], catalog)
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    env.pop('PYTHONPATH',None)
    atomic_json(out/'started.json', dict(config=config,config_sha256=file_hash(a.config),
        source_commit=COMMIT,coordinator_sha256=file_hash(__file__),manager_identity=identity(os.getpid()),
        started_utc=datetime.now(timezone.utc).isoformat(),explicit_resume=a.resume,
        order=ORDER,automatic_retry=False,total_time_cutoff=None,
        scope='Outer command sequence; nested CLI/task clocks are not additive'))
    begin=time.perf_counter()
    done=[]
    try:
        for position,(batch,phase) in enumerate(ORDER):
            if file_hash(Path(config['witness'])) != config['witness_sha256']:
                raise ValueError('Outer witness source changed')
            directory=bundle/'formal-runs'/f'batch-{batch:02d}'/phase
            pointer=directory/'latest-closed.json'
            if pointer.exists():
                if not a.resume:
                    raise ValueError('Prior phase exists; explicit sequence resume required')
                # Reuse only a complete verified frame, never merely a progress file.
                verify_phase_closure(directory,dispatch,batch,phase)
                with host_lease(Path(config['host_lock']), 'Read-only outer phase boundary check'):
                    coordinator=Coordinator(Path(config['host_lock']))
                    if coordinator._read()['tasks']:
                        raise ValueError('Active registry while reusing a phase; investigate native Jobs')
                done.append(dict(batch=batch,phase=phase,reused_closed_phase=True,new_cli_invocations=0))
                atomic_json(out/'progress.json',dict(completed_phases=done,next_position=position+1))
                continue
            if directory.exists() and not a.resume:
                raise ValueError('Partial phase exists; explicit resume and ended-process review required')
            name=f'{position:02d}-batch-{batch:02d}-{phase}'
            stage=out/name
            command=[config['python'],str(Path(config['witness'])), '--root',str(root),'--output',str(stage),'--',
                config['python'],'scripts/windows/formal_batch.py','--bundle',str(bundle),
                '--host-lock',config['host_lock'],'--rscript',config['rscript'],'--r-library',config['r_library'],
                '--native-acceptance',config['acceptance'],'--batch',str(batch),'--phase',phase]
            if directory.exists():command.append('--resume')
            intent=out/(name+'.intent.json')
            atomic_json(intent,dict(command=command,batch=batch,phase=phase,started_utc=datetime.now(timezone.utc).isoformat()))
            with Job('Local\\ParallelBayes-formal-sequence-'+uuid.uuid4().hex) as job:
                atomic_json(out/(name+'.job.json'),dict(name=job.name,kill_on_last_handle_close=True))
                with (out/(name+'.observer.stdout.log')).open('xb') as stdout, \
                        (out/(name+'.observer.stderr.log')).open('xb') as stderr:
                    primary=job.launch_suspended(command,root,stdout,stderr,env)
                    atomic_json(out/(name+'.primary.json'),primary)
                    job.resume()
                    while job.poll() is None or job.observe()['active_processes']:
                        atomic_json(out/'live.json',dict(batch=batch,phase=phase,primary=primary,
                            native_job=job.observe(),observed_utc=datetime.now(timezone.utc).isoformat(),
                            observations_are_not_closed_phase_proof=True))
                        time.sleep(5)
                    code=job.poll();final=job.observe()
            atomic_json(out/(name+'.exit.json'),dict(exit_code=code,native_job_final=final))
            if code!=0 or final['active_processes']!=0:
                raise RuntimeError('Phase CLI did not exit successfully with an ended owned process cohort')
            witness=json.loads((stage/'finished.json').read_text())
            if witness['exit_code']!=0 or witness['error'] is not None or witness['job_final']['active_processes']!=0:
                raise ValueError('Witness contradicts phase termination')
            boundary_start=time.perf_counter()
            proof=verify_phase_closure(directory,dispatch,batch,phase)
            report=json.loads((directory/proof['summary']).read_text())['summary']
            check_closed_summary(report,batch,phase)
            # Native parent Job membership provides actual descendant end proof;
            # the scientific journal additionally must have no active task rows.
            with host_lease(Path(config['host_lock']), 'Read-only outer phase boundary check'):
                coordinator=Coordinator(Path(config['host_lock']))
                if coordinator._read()['tasks']:raise ValueError('Active scientific journal after phase exit')
            import psutil, shutil
            resources=dict(observed_utc=datetime.now(timezone.utc).isoformat(),
                ram_available=psutil.virtual_memory().available,
                disks={v:shutil.disk_usage(v)._asdict() for v in ('C:/','D:/')},
                bundle_inventory=directory_inventory(bundle),
                scope='Phase boundary observations, not future capacity guarantees')
            atomic_json(out/(name+'.closed.json'),dict(summary=report,closure=proof,resources=resources,
                witnessed_job_end=True,active_scientific_entries=0,
                additional_boundary_verification_seconds=time.perf_counter()-boundary_start))
            done.append(dict(batch=batch,phase=phase,reused_closed_phase=False,summary=report))
            atomic_json(out/'progress.json',dict(completed_phases=done,next_position=position+1))
        atomic_json(out/'finished.json',dict(completed_phases=done,outer_sequence_seconds=time.perf_counter()-begin,
            finished_utc=datetime.now(timezone.utc).isoformat(),formal_study_execution_framework_closed=True,
            independent_reconstruction_complete=False,formal_research_complete=False))
        return 0
    except BaseException as exc:
        atomic_json(out/'failed.json',dict(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),
            completed_phases=done,known_sequence_seconds=time.perf_counter()-begin,
            automatic_retry=False,unvisited_tasks_are_not_failures=True))
        raise


if __name__=='__main__':
    sys.exit(main())
