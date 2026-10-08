"""Explicit compact contract adapter around the preserved numerical workers."""
import json
import os
from pathlib import Path
import sys
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'scripts/windows'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from compact_execution import load_worker_request
from compact_contract import validate_probe
from formal_runtime import atomic_json,file_hash


def request_data(path):
    request,c=load_worker_request(path,ROOT)
    if c['source_files'].get('scripts/windows/compact_worker.py')!=file_hash(__file__):
        raise ValueError('Compact worker must be explicitly source-bound')
    return request,c


def main():
    from job_objects import Job,identity
    mode='ordinary' if sys.argv[1]=='ordinary' else 'audited'
    request_path,folder=sys.argv[2:4] if mode=='ordinary' else sys.argv[1:3]
    folder=Path(folder)
    with Job(os.environ['PB_OWNED_JOB'],existing=True) as owned:
        member=identity(os.getpid(),owned.handle)
        if not member['member_of_owned_job']:raise RuntimeError('Compact worker is not owned')
    request,c=request_data(request_path)
    phase=request['phase']
    try:
        if phase=='main':
            import formal_batch_worker
            if mode=='ordinary':formal_batch_worker.ordinary(request_path,folder,request_loader=request_data)
            else:formal_batch_worker.audited(request_path,folder,request_loader=request_data,ordinary_worker=__file__)
        else:
            if mode!='audited':raise ValueError('Cache cannot enter ordinary posterior mode')
            from formal_cache_worker import execute_cached_probe
            from compact_cache_summary import summarize_probe
            atomic_json(folder/'cache-ownership.json',member)
            report=execute_cached_probe(request_path,folder/'cache',request_loader=request_data,
                probe_validator=validate_probe,worker_source='scripts/windows/compact_worker.py',summary_reducer=summarize_probe)
            atomic_json(folder/'worker-result.json',dict(status='completed' if report['measurement_available'] else 'failed',
                artifact_kind='cache_measurement',samples_eligible=False,measurement_available=report['measurement_available'],
                failure_category=None if report['measurement_available'] else
                    'resource_failure' if 'resource_failure' in report['observation']['execution_outcomes'] else 'numerical_failure'))
    except (MemoryError,__import__('torch').OutOfMemoryError) as exc:
        if mode=='ordinary':
            atomic_json(folder/'ordinary-resource-failure.json',dict(error=str(exc),samples_eligible=False));return 3
        atomic_json(folder/'worker-result.json',dict(status='failed',samples_eligible=False,
            measurement_available=False,failure_category='resource_failure',error=str(exc)))
    except BaseException:
        traceback.print_exc();return 1
    return 0


if __name__=='__main__':sys.exit(main())
