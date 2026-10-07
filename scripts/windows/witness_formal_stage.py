"""Observe one finite-validation CLI invocation without changing its policy.

The child owns the existing scientific host lease. This outer Job only binds
the command and descendants to the witness lifetime; it takes no competing
lease and imposes no extra resource or time limit. Receipts live outside the
immutable validation bundle. It never grants sample/measurement eligibility.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/windows'),str(ROOT/'scripts/completion')]
from job_objects import Job
from formal_runtime import atomic_json,file_hash


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('argv',nargs=argparse.REMAINDER)
    a=p.parse_args();argv=a.argv[1:] if a.argv[:1]==['--'] else a.argv
    if sys.platform!='win32' or not argv:raise ValueError('Native command required')
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1');env.pop('PYTHONPATH',None)
    record=dict(command=argv,cwd=str(ROOT),source_commit=subprocess.check_output(
        ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),witness_sha256=file_hash(__file__),
        job_api_sha256=file_hash(ROOT/'scripts/windows/job_objects.py'),started_ns=time.time_ns(),
        outer_job_has_no_additional_resource_or_time_limits=True,
        scientific_lease_owned_by_child=True,cost_scope='Whole CLI invocation; nested clocks not additive',
        formal_repetitions=0)
    atomic_json(out/'started.json',record)
    begin=time.perf_counter();code=None;error=None;final=None
    try:
        with Job('Local\\ParallelBayes-stage-'+uuid.uuid4().hex) as job:
            atomic_json(out/'job-intent.json',dict(name=job.name,kill_on_last_handle_close=True))
            with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr,\
                    (out/'ownership.ndjson').open('x',encoding='utf-8') as observations:
                try:
                    atomic_json(out/'primary.json',job.launch_suspended(argv,ROOT,stdout,stderr,env))
                    job.resume()
                    while True:
                        sample=job.observe();observations.write(json.dumps(sample)+'\n');observations.flush()
                        if job.poll() is not None and sample['active_processes']==0:break
                        time.sleep(1)
                    code=job.poll();final=job.observe()
                except BaseException:
                    job.terminate()
                    while job.observe()['active_processes']:time.sleep(.1)
                    final=job.observe();raise
    except BaseException as exc:
        error=type(exc).__name__+': '+str(exc);traceback.print_exc()
    result=dict(exit_code=code,error=error,job_final=final,invocation_seconds=time.perf_counter()-begin,
        finished_ns=time.time_ns(),logs={f.name:file_hash(f) for f in (out/'stdout.log',out/'stderr.log') if f.exists()})
    atomic_json(out/'finished.json',result);print(json.dumps(result),flush=True)
    return code if code is not None and error is None else 1


if __name__=='__main__':sys.exit(main())
