"""Actual outer command Job/cost evidence; optional lease only for ancillary tests.

Never lease-wrap the scientific driver: its children acquire that same host
lease themselves. No total duration limit or resource-limit override is added.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid
from contextlib import nullcontext

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/windows'),str(ROOT/'scripts/completion')]
from formal_runtime import atomic_json,file_hash,host_lease


def run(command,output,*,lease=None):
    if sys.platform!='win32':raise ValueError('Actual native Windows command observer required')
    from job_objects import Job,identity
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    env.pop('PYTHONPATH',None)
    metadata=dict(command=command,cwd=str(ROOT),started_utc=datetime.now(timezone.utc).isoformat(),
        manager_identity=identity(os.getpid()),source_sha256=file_hash(__file__),job_api_sha256=file_hash(ROOT/'scripts/windows/job_objects.py'),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        git_status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),
        lease=str(Path(lease).resolve()) if lease else None,
        cost_scope='Child process creation through actual owned cohort end; includes nested task costs, do not sum',
        total_time_cutoff=None)
    atomic_json(output/'started.json',metadata)
    seconds=time.perf_counter();code=None;error=None;final=None
    try:
        with (host_lease(Path(lease),'compact ancillary command') if lease else nullcontext()):
            with Job('Local\\ParallelBayes-compact-command-'+uuid.uuid4().hex) as job:
                atomic_json(output/'job-intent.json',dict(name=job.name,kill_on_last_handle_close=True))
                with (output/'stdout.log').open('xb') as stdout,(output/'stderr.log').open('xb') as stderr,(output/'ownership.ndjson').open('x') as observed:
                    try:
                        atomic_json(output/'primary.json',job.launch_suspended(command,ROOT,stdout,stderr,env));job.resume()
                        while True:
                            value=job.observe();observed.write(json.dumps(value)+'\n');observed.flush()
                            if job.poll() is not None and value['active_processes']==0:break
                            time.sleep(.2)
                        code=job.poll();final=job.observe()
                    except BaseException:
                        job.terminate()
                        while job.observe()['active_processes']:time.sleep(.1)
                        final=job.observe();raise
    except BaseException as exc:
        error=type(exc).__name__+': '+str(exc)
        (output/'error.log').write_text(traceback.format_exc(),encoding='utf-8')
    result=dict(exit_code=code,error=error,job_final=final,invocation_seconds=time.perf_counter()-seconds,
        finished_utc=datetime.now(timezone.utc).isoformat(),unknown_time_imputed=False,
        source_sha256=metadata['source_sha256'],logs={n:file_hash(output/n) for n in ('stdout.log','stderr.log') if (output/n).exists()})
    atomic_json(output/'finished.json',result);print(json.dumps(result),flush=True)
    return code if error is None and code is not None else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--lease',type=Path)
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command:raise ValueError('Command required')
    sys.exit(run(command,a.output,lease=a.lease))
