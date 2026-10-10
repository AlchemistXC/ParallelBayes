"""Compact-only dispatch/worker contracts, reusing unchanged numerical semantics."""
import copy
import importlib.metadata
import json
from pathlib import Path
import sys

from batch_contract import validate_capsule
from compact_contract import CONTRACT, IDENTITY, TECHNICAL_ID, CompactPlan, validate_probe, validate_plan
from compact_freeze import MARKER_SCHEMA
from formal_execution import StudyDispatch
from formal_runtime import fingerprint,file_hash


def validate_worker_scope(c,request,marker,gate=None):
    if (c.get('compact_execution_contract')!=CONTRACT or request.get('compact_execution_contract')!=CONTRACT or
        c['required_platform']!='win32' or request.get('native_runtime_schema')!='windows-owned-runtime-v2' or
        request.get('phase') not in ('main','cache') or marker.get('schema')!=MARKER_SCHEMA or
        marker.get('source_files_sha256')!=fingerprint(c['source_files']) or
        marker.get('protocol_sha256')!=c['protocol_sha256'] or marker.get('identity')!=c['identity'] or
        marker.get('source_commit')!=c['source_commit'] or marker.get('sampling_authorized_by_this_document') is not False):
        raise ValueError('Explicit matching compact source/marker/phase contract required')
    technical=c['identity']==TECHNICAL_ID
    if technical:
        t=c['task']
        if (c['scope_kind']!='technical_batch_validation' or marker.get('inputs')!=2 or
            marker.get('main_tasks')!=18 or marker.get('cache_probes')!=16 or
            marker.get('formal_scientific_repetitions')!=0 or t['replicate']!=0 or t['batch']!=0 or
            (t['model'],t['budget']) not in (('G2',4096),('W1',1024))):
            raise ValueError('Only the distinct finite compact difference-validation grid is allowed')
    else:
        if (c['identity']!=IDENTITY or c['scope_kind']!='formal_inference' or marker.get('inputs')!=216 or
            marker.get('main_tasks')!=3888 or marker.get('cache_probes')!=256 or
            marker.get('formal_scientific_repetitions')!=24 or gate is None or
            gate.get('schema')!='compact-native-acceptance-v1' or gate.get('passed') is not True):
            raise ValueError('Complete compact freeze and new native acceptance required')
        unsigned=dict(gate);digest=unsigned.pop('gate_sha256')
        if fingerprint(unsigned)!=digest:raise ValueError('Compact native acceptance checksum differs')
        for name in ('source_files','required_versions','required_R_version','required_R_posterior'):
            if gate.get(name)!=c[name]:raise ValueError('Compact acceptance/source/environment differs: '+name)
    if request['phase']=='cache':
        validate_probe(c,request['capsule_sha256'],request['probe'])
    return c


def load_worker_request(path,source_root):
    if sys.platform!='win32':raise ValueError('Actual native Windows required')
    request=json.loads(Path(path).read_text())
    c=validate_capsule(request['capsule'],request['capsule_sha256'])
    marker_path=Path(request['sealed_marker'])
    if file_hash(marker_path)!=request['sealed_marker_sha256']:raise ValueError('Compact sealed marker changed')
    marker=json.loads(marker_path.read_text());gate=None
    if c['identity']==IDENTITY:
        path=Path(request['native_acceptance'])
        if file_hash(path)!=request['native_acceptance_sha256']:raise ValueError('Compact native acceptance changed')
        gate=json.loads(path.read_text())
    validate_worker_scope(c,request,marker,gate)
    for name,h in c['source_files'].items():
        if file_hash(Path(source_root)/name)!=h:raise ValueError('Frozen compact source changed: '+name)
    for name,version in c['required_versions'].items():
        if importlib.metadata.version(name)!=version:raise ValueError('Frozen dependency changed: '+name)
    if c['task']['model']=='W1' and not request.get('source_directory'):
        raise ValueError('Explicit archived W1 data required')
    return request,c


class CompactDispatch(StudyDispatch):
    def __init__(self,protocol,plan,root):
        validate_plan(plan,root)
        self.plan=CompactPlan(protocol)
        for name in ('identity','groups','tasks','targets','controls','analysis_policy','execution_policy','cost_policy'):
            if protocol[name]!=plan[name]:raise ValueError('Compact frozen scientific frame differs: '+name)
        if protocol['cache_allocation_sha256']!=plan['cache_allocation']['allocation_sha256']:
            raise ValueError('Compact frozen cache allocation differs')
        self.protocol=copy.deepcopy(protocol)
        self._primary={t['id']:t for t in protocol['tasks']}
        self._probes=copy.deepcopy(plan['cache_allocation']['probes'])
        self.phases=tuple((b,p) for b in range(1 if plan['technical'] else 3) for p in ('main','cache'))

    def _records(self,batch,phase):
        if type(batch) is not int or (batch,phase) not in self.phases:raise ValueError('Unknown compact batch/phase')
        return list(self.plan.tasks(batch)) if phase=='main' else [p for p in self._probes if p['batch']==batch]

    def predecessors(self,batch,phase):
        if type(batch) is not int or (batch,phase) not in self.phases:raise ValueError('Unknown compact batch/phase')
        return self.phases[:self.phases.index((batch,phase))]

    def request(self,slot,*,bundle,source_root,rscript,r_library,sealed_marker,native_acceptance=None):
        bundle=Path(bundle).resolve();source_root=Path(source_root).resolve();marker=Path(sealed_marker).resolve()
        c=slot['capsule'];task=slot['task'];phase='main' if task['artifact_kind']=='posterior' else 'cache'
        source_files={str(source_root/n):h for n,h in self.protocol['source_files'].items()}
        source_files.update({str(bundle/'external'/n):h for n,h in self.protocol['external_files'].items()})
        files={str(bundle/'inputs'/c['task']['input']):c['input']['sha256'],str(marker):file_hash(marker)}
        request=dict(capsule=c,capsule_sha256=slot['capsule_sha256'],phase=phase,
            compact_execution_contract=CONTRACT,native_runtime_schema='windows-owned-runtime-v2',
            inputs=str(bundle/'inputs'),source_directory=str(bundle/'external'),
            rscript=str(Path(rscript).resolve()),r_library=str(Path(r_library).resolve()),
            required_gpu_free_bytes=c['controls']['minimum_gpu_free_bytes'],sealed_marker=str(marker),
            sealed_marker_sha256=files[str(marker)],input_files=files,source_files=source_files)
        if c['identity']==IDENTITY:
            if native_acceptance is None:raise ValueError('New compact native acceptance path required')
            gate=Path(native_acceptance).resolve();files[str(gate)]=file_hash(gate)
            request.update(native_acceptance=str(gate),native_acceptance_sha256=files[str(gate)])
        if slot['probe'] is not None:request['probe']=slot['probe']
        return request
