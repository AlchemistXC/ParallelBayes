"""Observe formal CLI costs/ownership outside the immutable execution tree.

No scientific lease, resource limit, time limit, RNG or sampler is introduced.
The accepted Job API is imported from the explicitly selected execution tree.
Outer CLI costs include nested task costs and must never be added to them.
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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('argv', nargs=argparse.REMAINDER)
    a = p.parse_args()
    root = a.root.resolve()
    argv = a.argv[1:] if a.argv[:1] == ['--'] else a.argv
    if sys.platform != 'win32' or not argv:
        raise ValueError('Native command required')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if commit != '0ba5643a6b580e79b8040f13a5e3165322db0e77':
        raise ValueError('Accepted execution commit required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip():
        raise ValueError('Execution tree must remain clean')
    sys.path[:0] = [str(root/'scripts/windows'), str(root/'scripts/completion')]
    from job_objects import Job
    from formal_runtime import atomic_json, file_hash
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    env.pop('PYTHONPATH', None)
    record = dict(command=argv, cwd=str(root), source_commit=commit,
        witness_sha256=file_hash(__file__), job_api_sha256=file_hash(root/'scripts/windows/job_objects.py'),
        started_utc=datetime.now(timezone.utc).isoformat(), started_ns=time.time_ns(),
        executable=sys.executable, environment_overrides={k: env[k] for k in
            ('PYTHONDONTWRITEBYTECODE', 'PYTHONUTF8', 'PYTHONIOENCODING')},
        removed_environment=['PYTHONPATH'], scientific_lease_owned_by_child=True,
        outer_job_has_no_additional_resource_or_time_limits=True,
        study_identity='windows-formal-inference-v1', planned_main_tasks=41472,
        planned_cache_probes=9216, planned_original_four_chain_repeats_per_target=128,
        observer_adds_statistical_repetitions=0,
        cost_scope='Whole CLI process and descendant lifetime; includes nested clocks, not additive. '
                   'Observer setup and final receipt writing excluded. Timestamps are not durations.')
    atomic_json(out/'started.json', record)
    begin = time.perf_counter()
    code = error = final = None
    try:
        with Job('Local\\ParallelBayes-formal-stage-'+uuid.uuid4().hex) as job:
            atomic_json(out/'job-intent.json', dict(name=job.name, kill_on_last_handle_close=True))
            with (out/'stdout.log').open('xb') as stdout, (out/'stderr.log').open('xb') as stderr, \
                    (out/'ownership.ndjson').open('x', encoding='utf-8') as observations:
                try:
                    atomic_json(out/'primary.json', job.launch_suspended(argv, root, stdout, stderr, env))
                    job.resume()
                    while True:
                        sample = job.observe()
                        observations.write(json.dumps(sample)+'\n')
                        observations.flush()
                        if job.poll() is not None and sample['active_processes'] == 0:
                            break
                        time.sleep(1)
                    code = job.poll()
                    final = job.observe()
                except BaseException:
                    job.terminate()
                    while job.observe()['active_processes']:
                        time.sleep(.1)
                    final = job.observe()
                    raise
    except BaseException as exc:
        error = type(exc).__name__+': '+str(exc)
        (out/'observer-error.log').write_text(traceback.format_exc(), encoding='utf-8')
        traceback.print_exc()
    result = dict(exit_code=code, error=error, job_final=final,
        invocation_seconds=time.perf_counter()-begin,
        finished_utc=datetime.now(timezone.utc).isoformat(), finished_ns=time.time_ns(),
        logs={f.name: file_hash(f) for f in (out/'stdout.log', out/'stderr.log') if f.exists()})
    atomic_json(out/'finished.json', result)
    print(json.dumps(result), flush=True)
    return code if code is not None and error is None else 1


if __name__ == '__main__':
    sys.exit(main())
