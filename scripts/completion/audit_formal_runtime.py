"""Audit a finite native runtime run and exercise an owned memory-guard fixture.

No new MCMC fits are requested. The fixture's ten-second sleep bounds only
this technical test; scientific execution has no total-time cutoff.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/completion'))
from formal_runtime import atomic_json, execute_task, file_hash
from formal_runtime_validation import run


def hashes(directory):
    return {p.relative_to(directory).as_posix(): file_hash(p)
            for p in sorted(directory.rglob('*')) if p.is_file()}


def audit(protocol, inputs, evidence, output, rscript, r_library, host_lock):
    import psutil
    output.mkdir(parents=True, exist_ok=False)
    p = json.loads(protocol.read_text())
    before_summary = json.loads((evidence / 'summary.json').read_text())
    before = {t['id']: hashes(evidence / t['id']) for t in p['tasks']}
    atomic_json(output / 'terminal-before.json', before)
    resumed = run(protocol, inputs, evidence, rscript, r_library, host_lock, resume=True)
    after = {t['id']: hashes(evidence / t['id']) for t in p['tasks']}
    if before != after or resumed['newly_executed_tasks'] != 0:
        raise AssertionError('Resume modified terminal evidence or repeated a fit')

    phase_rows = []
    for task in p['tasks']:
        directory = evidence / task['id']
        state = json.loads((directory / 'state.json').read_text())
        completion = json.loads((directory / 'completion.json').read_text())
        if completion['state_sha256'] != file_hash(directory / 'state.json'):
            raise AssertionError('Completion state hash differs')
        for name, digest in state['assets'].items():
            if file_hash(directory / name) != digest:
                raise AssertionError('Asset hash differs: ' + name)
        phases = json.loads((directory / state['attempt'] / 'phases.json').read_text())['phases']
        if any(a['end_offset_seconds'] > b['start_offset_seconds']
               for a, b in zip(phases, phases[1:])):
            raise AssertionError('Worker phases overlap')
        if any(row['status'] != 'completed' for row in phases):
            raise AssertionError('Unexpected failed phase in this finite validation')
        phase_rows.append(dict(task=task, phases=phases, completion=completion,
                               memory=state['memory']))
    atomic_json(output / 'phase-accounting.json', phase_rows)

    # Independent artificial child uses bounded allocation and writes an
    # observable marker before allocating. Never target unrelated processes.
    child = output / 'guard-child.py'
    child.write_text(
        'import json, os, pathlib, sys, time\n'
        'p = pathlib.Path(sys.argv[1])\n'
        'p.write_text(json.dumps({"pid": os.getpid()}))\n'
        'buffer = bytearray(128 * 1024**2)\n'
        'time.sleep(10)\n', encoding='utf-8')
    worker = output / 'guard-worker.py'
    worker.write_text(
        'import json, pathlib, subprocess, sys\n'
        'request = json.loads(pathlib.Path(sys.argv[1]).read_text())\n'
        'output = pathlib.Path(sys.argv[2])\n'
        '(output / "preserved-marker.bin").write_bytes(b"keep failure evidence")\n'
        'child = subprocess.Popen([sys.executable, request["child"], '
        'str(output / "child.json")])\n'
        'child.wait()\n'
        '(output / "worker-result.json").write_text(json.dumps('
        '{"status": "completed", "samples_eligible": True}))\n', encoding='utf-8')
    task = dict(identity='formal-runtime-memory-guard-fixture-v1', statistical_fits=0)
    request = dict(child=str(child.resolve()), child_sha256=file_hash(child))
    guarded = execute_task(task, request, worker, output / 'guarded-task', host_lock,
                           required_disk_bytes=1024**2, max_tree_rss_bytes=64 * 1024**2)
    if guarded['status'] != 'failed' or guarded['failure_kind'] != 'process_tree_memory_guard':
        raise AssertionError('Memory guard did not classify the artificial allocation')
    if guarded['samples_eligible']:
        raise AssertionError('Memory-guard output was exposed as normal samples')
    attempt = output / 'guarded-task' / guarded['attempt']
    if (attempt / 'preserved-marker.bin').read_bytes() != b'keep failure evidence':
        raise AssertionError('Failure evidence lost')
    identities = {key: json.loads((attempt / name).read_text())['pid']
                  for key, name in [('worker', 'process.json'), ('child', 'child.json')]}
    alive = {}
    for role, pid in identities.items():
        try:
            process = psutil.Process(pid)
            alive[role] = process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            alive[role] = False
    if any(alive.values()):
        raise AssertionError('Owned fixture process remains live')
    guard_before = hashes(output / 'guarded-task')
    guard_resume = execute_task(task, request, worker, output / 'guarded-task', host_lock,
        required_disk_bytes=1024**2, max_tree_rss_bytes=64 * 1024**2, resume=True)
    if guard_resume['newly_executed'] or guard_before != hashes(output / 'guarded-task'):
        raise AssertionError('Failed resource task was recomputed or altered')
    receipt = dict(protocol_sha256=p['protocol_sha256'], sampler_source_commit=p['source_commit'],
        auditor_sha256=file_hash(Path(__file__)), original_summary=before_summary,
        terminal_files_unchanged=sum(map(len, before.values())), newly_executed_MCMC_fits=0,
        resumed_tasks=len(p['tasks']), nonoverlapping_phase_workflows=len(phase_rows),
        guard=dict(status=guarded['status'], failure_kind=guarded['failure_kind'],
                   samples_eligible=guarded['samples_eligible'], memory=guarded['memory'],
                   observed_pids=identities, still_running=alive,
                   terminal_files_unchanged=len(guard_before), failed_resume_new_tasks=0),
        formal_inference_complete=False, windows_validation=False,
        ordinary_workflow_measured_separately=False,
        limitation='One Mac technical profile and one owned bounded allocation fixture. '
                   'No interrupted-attempt recovery, allocator guarantee, CUDA/Windows guard, '
                   'formal inference or end-to-end manuscript reproduction claim.')
    atomic_json(output / 'receipt.json', receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['protocol', 'inputs', 'evidence', 'output', 'rscript', 'r-library', 'host-lock']:
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    result = audit(a.protocol, a.inputs, a.evidence, a.output, a.rscript, a.r_library, a.host_lock)
    print(json.dumps(result, indent=2))
