"""Continue independent tasks without silently retrying an interrupted one.

This operational adapter leaves the frozen coordinator, worker and protocol
unchanged. It never infers process death from file existence: report() obtains
and verifies the coordinator's actual lifecycle observation first.
"""
import json
from pathlib import Path
from formal_runtime import file_hash


def advance(measured,job):
    """Execute/verify a task, or retain a verified stopped interruption.

    Explicit retry remains a separate operation with the original one-retry
    policy. Source/request/resource changes, live groups and ambiguous process
    receipts raise; these are never converted into a convenient skipped cell.
    """
    output=Path(job['output']).resolve()
    if output.exists():
        costs=measured.report(output)
        binding=json.loads((output/'binding.json').read_text())
        requested=dict(task=job['task'],request=job['request'],worker_sha256=file_hash(job['worker']),
            required_disk_bytes=job['required_disk_bytes'],max_tree_rss_bytes=job['max_tree_rss_bytes'],
            host_lock=str(measured.coordinator.host_lock))
        if costs['history']['task']!=job['task'] or any(binding.get(k)!=v for k,v in requested.items()):
            raise ValueError('Requested job identity differs from retained history')
        process=json.loads((output/'attempt-0001/process.json').read_text())
        if process['worker']!=str(Path(job['worker']).resolve()):
            raise ValueError('Requested worker path identity differs')
        history=costs['history'];outcome=costs['outcome']
        if history['lifecycle']=='stopped_unsealed' or outcome=='infrastructure_interruption':
            return dict(task=job['task'],status='interrupted' if outcome=='infrastructure_interruption' else 'failed',
                outcome=outcome,samples_eligible=False,newly_executed=False,
                operation='retain_without_reexecution',costs=costs,
                sampled_peak_tree_rss_bytes=None,ordinary_process=None,diagnostics_status=None,
                retry_available=outcome=='infrastructure_interruption' and costs['actual_attempts']<2,
                retention_note='Stopped lifecycle verified; no task invocation or sampler retry. All attempts, failures and unknown durations retained.')
    result=measured.run(**job,resume=True)
    costs=measured.report(output)
    return dict(task=job['task'],status=result['status'],outcome=costs['outcome'],
        samples_eligible=result['samples_eligible'],newly_executed=result['newly_executed'],
        operation='execute' if result['newly_executed'] else 'verify_terminal',costs=costs,
        sampled_peak_tree_rss_bytes=result['memory']['sampled_peak_tree_rss_bytes'],
        ordinary_process=(result.get('worker_result') or {}).get('ordinary_process'),
        diagnostics_status=(result.get('worker_result') or {}).get('diagnostics_status'),
        retry_available=costs['outcome']=='infrastructure_interruption' and costs['actual_attempts']<2)
