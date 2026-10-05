"""Measurement-only cache worker for an owned native process cohort.

The launch request contains a fixed MH capsule/probe, not a primary fit result.
Successful measurement never authorizes posterior samples or another retry.
"""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from cache_probe_execution import execute_cached_probe,read_cached_probe
from formal_runtime import atomic_json,file_hash


def run(request_path,output):
    request=json.loads(Path(request_path).read_text());output=Path(output)
    capsule=request['capsule']
    if capsule['source_files'].get('scripts/completion/owned_cache_worker.py')!=file_hash(__file__):
        raise ValueError('Owned cache worker is not in the frozen source inventory')
    report=execute_cached_probe(capsule,request['capsule_sha256'],request['probe'],
                                request['inputs'],output/'probe',request.get('source_directory'))
    verified=read_cached_probe(output/'probe')
    if verified!=report:raise ValueError('Saved cache result differs')
    category=None
    if report['status']=='failed':
        category='resource_failure' if 'resource_failure' in report['observation']['execution_outcomes'] else 'numerical_failure'
    atomic_json(output/'worker-result.json',dict(status=report['status'],artifact_kind='cache_measurement',
        samples_eligible=False,measurement_available=report['measurement_available'],failure_category=category,
        probe_id=request['probe']['id'],capsule_sha256=request['capsule_sha256'],
        cache_manifest_sha256=file_hash(output/'probe/MANIFEST.json'),
        known_executor_seconds=sum(r['executor_wall_seconds'] for r in report['observation']['records'] if r is not None),
        requires_successful_primary_fit=False,formal_independent_repetitions_added=0))


if __name__=='__main__':run(sys.argv[1],sys.argv[2])
