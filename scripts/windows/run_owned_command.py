"""Native ancillary command receipt with owned descendants and a shared lease.

For installation/check/archive work, not a formal scientific task or retry
policy. Uses the tested Job API; never grants posterior/measurement eligibility.
Output is new, environment PYTHONPATH is removed, cwd is explicit.
"""
import argparse,json,os,shutil,subprocess,sys,time,traceback,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/windows'),str(ROOT/'scripts/completion')]
from job_objects import Job
from formal_runtime import atomic_json,file_hash,host_lease

def run(command,cwd,output,host_lock,env_json=None,rss_bytes=8*1024**3,commit_bytes=12*1024**3):
    if command[:1]==['--']:command=command[1:]
    if not command or sys.platform!='win32':raise ValueError('Native Windows command required')
    cwd=Path(cwd).resolve();out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    extra=json.loads(Path(env_json).read_text()) if env_json else {}
    if 'PYTHONPATH' in extra:raise ValueError('Installed import validation requires removed PYTHONPATH')
    env.update(extra)
    record=dict(command=command,cwd=str(cwd),started_ns=time.time_ns(),timestamp_is_not_duration=True,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256=file_hash(__file__),job_api_sha256=file_hash(ROOT/'scripts/windows/job_objects.py'),
        explicit_environment=extra,PYTHONPATH_removed=True,artifact_kind='ancillary_command',
        samples_eligible=False,measurement_available=False,stdout_stderr='Separate binary logs',
        cost_scope='Complete owned ancillary invocation, not added to nested scientific task clocks')
    atomic_json(out/'started.json',record);start=time.perf_counter();error=None;code=None;final=None
    try:
        with host_lease(host_lock,'ancillary '+out.name),Job('Local\\ParallelBayes-'+uuid.uuid4().hex,commit_limit_bytes=commit_bytes) as job:
            atomic_json(out/'job-intent.json',dict(name=job.name,kill_on_last_noninherited_handle_close=True))
            with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr,(out/'ownership.ndjson').open('x',encoding='utf-8') as observations:
                try:
                    primary=job.launch_suspended(command,cwd,stdout,stderr,env)
                    atomic_json(out/'primary.json',primary);job.resume()
                    while True:
                        sample=job.observe();sample['disk_free_bytes']=shutil.disk_usage(out).free
                        observations.write(json.dumps(sample)+'\n');observations.flush()
                        if sample['sampled_rss_bytes']>rss_bytes or sample['disk_free_bytes']<1024**3:
                            raise MemoryError('Ancillary owned RSS or disk guard triggered')
                        if job.poll() is not None and sample['active_processes']==0:break
                        time.sleep(.2)
                    code=job.poll();final=job.observe()
                except BaseException:
                    job.terminate()
                    while job.observe()['active_processes']:time.sleep(.2)
                    final=job.observe();raise
    except BaseException as exc:
        error=type(exc).__name__+': '+str(exc)
        traceback.print_exc()
    result=dict(exit_code=code,error=error,seconds=time.perf_counter()-start,job_final=final,
        samples_eligible=False,measurement_available=False,source_sha256=record['source_sha256'],
        logs={p.name:file_hash(p) for p in (out/'stdout.log',out/'stderr.log') if p.exists()},
        finished_ns=time.time_ns())
    atomic_json(out/'finished.json',result);print(json.dumps(result),flush=True)
    return code if code is not None and error is None else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cwd',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--host-lock',type=Path,required=True);p.add_argument('--env-json',type=Path);p.add_argument('--rss-bytes',type=int,default=8*1024**3);p.add_argument('--commit-bytes',type=int,default=12*1024**3);p.add_argument('command',nargs=argparse.REMAINDER)
    sys.exit(run(**vars(p.parse_args())))
