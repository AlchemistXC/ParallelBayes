"""Relocatable owned-cache evidence, including unstarted and failed task slots.

This read-only interface consumes a checksum-pinned layout and registry snapshot.
Original absolute output names are identities; all reads use contained archive
locations. No process observation, recovery, sampling or path re-audit occurs.
"""
import json
import numpy as np
from pathlib import Path

from batch_contract import BatchPlan,mh_config
from batch_worker import payload
from cache_probe_execution import read_cached_probe
from formal_evidence import RuntimeEvidence,inside
from formal_measurement_plan import validate_measurement_plan,summarize_probe
from formal_outcomes import summarize_attempts
from formal_runtime import file_hash
from formal_streaming import read_member
from inference_targets import build_target
from measured_coordinator import read_calls,summarize_calls
from parallelbayes.torch_backend.sampling import settings,tape_hash


def _partial_calls(directory,capsule,digest,probe,binding):
    """Salvage immutable per-call receipts without certifying a complete task."""
    records=[None]*4;states=['not_run']*4
    if not directory.exists():return records,states,'absent'
    request=directory/'request.json';bound=directory/'binding.json'
    if request.exists() and json.loads(request.read_text())!=dict(capsule=capsule,capsule_sha256=digest,probe=probe):
        raise ValueError('Partial request differs from the planned capsule')
    if bound.exists() and json.loads(bound.read_text())!=binding:raise ValueError('Partial target/input binding differs')
    gap=False
    for i in range(4):
        marker=directory/f'execution-{i}.started.json'
        finished=directory/f'execution-{i}.json';candidate=directory/f'candidate-{i}.json'
        if not marker.exists():
            if finished.exists() or candidate.exists():raise ValueError('Call record lacks its start marker')
            gap=True;continue
        if gap or not request.exists() or not bound.exists():raise ValueError('Partial execution ordering or binding differs')
        started=json.loads(marker.read_text())
        if started['execution_index']!=i or started['probe_id']!=probe['id']:raise ValueError('Partial call marker identity differs')
        if not finished.exists() and not candidate.exists():
            states[i]='infrastructure_interruption';gap=True;continue
        r=json.loads((finished if finished.exists() else candidate).read_text())
        if r['actual_array_file'] is None:
            if r['technical_output_valid'] or r['actual_array_sha256'] is not None:raise ValueError('Missing raw array cannot be valid')
        else:
            if r['actual_array_file']!=f'execution-{i}.npz':raise ValueError('Partial array name differs')
            raw=directory/r['actual_array_file']
            if file_hash(raw)!=r['actual_array_sha256']:raise ValueError('Partial array checksum differs')
            q=read_member(raw,'unconstrained',capsule['controls']['maximum_member_bytes'])
            accept=read_member(raw,'accept',capsule['controls']['maximum_member_bytes'])
            shape=(binding['config']['chains'],binding['config']['draws'],capsule['target']['dimension'])
            if q.shape!=shape or accept.shape!=shape[:2] or accept.dtype!=np.bool_:raise ValueError('Partial array shape/type differs')
            if r['technical_output_valid'] and (not np.isfinite(q).all() or not r['audit']['passed'] or any(r['audit']['acceptance_mismatches'])):
                raise ValueError('Partial valid record conflicts with saved numerical audit')
        if r['technical_output_valid']:
            if not finished.exists():raise ValueError('Unaudited candidate cannot be valid')
            states[i]='valid'
        elif r.get('post_execution_error'):
            states[i]='resource_failure' if r['post_execution_error']['type']=='MemoryError' else 'infrastructure_interruption'
        elif r['status']=='failed' or r.get('audit') is not None:states[i]='numerical_failure'
        else:states[i]='infrastructure_interruption'
        records[i]=r
        if not finished.exists():gap=True
    return records,states,'partial'


class OwnedCacheEvidence:
    def __init__(self,root,descriptor,descriptor_sha256):
        self.root=Path(root).resolve();path=inside(self.root,descriptor)
        if file_hash(path)!=descriptor_sha256:raise ValueError('Owned cache descriptor checksum differs')
        self.layout=json.loads(path.read_text());d=self.layout
        if d['schema']!='owned-cache-evidence-v1':raise ValueError('Unknown owned cache evidence schema')
        self.protocol=json.loads(inside(self.root,d['protocol']).read_text());self.plan=BatchPlan(self.protocol)
        self.allocation=json.loads(inside(self.root,d['allocation']).read_text())
        validate_measurement_plan(self.allocation,self.protocol['tasks'])
        if self.allocation['allocation_sha256']!=self.protocol['cache_allocation_sha256']:raise ValueError('Cache allocation binding differs')
        self.probes={p['id']:p for p in self.allocation['probes']};self.probe_ids=tuple(self.probes)
        if set(d['probes'])!=set(self.probes):raise ValueError('Every planned probe needs an archived location')
        originals=[p['original'] for p in d['probes'].values()]
        calls=[p['calls'] for p in d['probes'].values() if p['calls'] is not None]
        if len(set(originals))!=len(originals) or set(d['locations'])!=set(originals) or len(set(calls))!=len(calls):
            raise ValueError('Owned task or call locations are aliased')
        for name in calls:inside(self.root,name)
        self.inputs=inside(self.root,d['inputs'])
        self.runtime=RuntimeEvidence(inside(self.root,d['snapshot']),d['snapshot_sha256'],self.root,d['locations'])

    def __enter__(self):return self

    def __exit__(self,*args):return self.runtime.__exit__(*args)

    def read_probe(self,probe_id):
        probe=self.probes[probe_id];location=self.layout['probes'][probe_id]
        capsule,digest=self.plan.capsule(probe['primary_task_id'])
        task=dict(id=probe_id,protocol_sha256=self.plan.protocol_sha256,artifact_kind='cache_measurement')
        history=self.runtime.history(task,location['original'])
        if len(history['attempts'])>1 or history['lifecycle']=='recovered':raise ValueError('Cache measurement retries are forbidden')
        # The older generic reader predates cache roles on stopped/unsealed rows.
        # The snapshot has already verified the complete fixed measurement task.
        for row in history['attempts']:
            if row.get('artifact_kind','cache_measurement')!='cache_measurement':raise ValueError('Posterior history in cache evidence')
            row['artifact_kind']='cache_measurement'
        history['summary']=summarize_attempts(history['attempts'])
        outcome=history['summary']['outcome']
        values=payload(dict(inputs=str(self.inputs)),capsule)
        config=settings(mh_config(capsule,values['initial'].tolist()))
        tape={k:values[k][:,:config['draws']] for k in ('noise','log_uniform','directions')}
        model=build_target(capsule['target'],None,'cpu')
        binding=dict(input_file_sha256=capsule['input']['sha256'],tape_sha256=tape_hash(tape),target_id=model.target_id,config=config)
        records=[None]*4;states=['not_run']*4;kind='absent'
        if history['attempts']:
            directory=inside(self.root,self.layout['locations'][location['original']])
            request=json.loads((directory/'binding.json').read_text())['request']
            if any(request.get(k)!=v for k,v in dict(capsule=capsule,capsule_sha256=digest,probe=probe).items()):
                raise ValueError('Runtime request differs from the planned measurement capsule')
            artifact=directory/'attempt-0001/probe'
            if (artifact/'MANIFEST.json').is_file():
                report=read_cached_probe(artifact)
                saved=json.loads((artifact/'request.json').read_text())
                if saved!=dict(capsule=capsule,capsule_sha256=digest,probe=probe) or report['binding']!=binding:
                    raise ValueError('Cache artifact differs from actual planned inputs/target/config')
                records=report['observation']['records'];states=report['observation']['execution_outcomes'];kind='sealed'
                worker=directory/'attempt-0001/worker-result.json'
                if worker.is_file():
                    result=json.loads(worker.read_text())
                    if result.get('probe_id')!=probe_id or result.get('capsule_sha256')!=digest or result.get('cache_manifest_sha256')!=file_hash(artifact/'MANIFEST.json'):
                        raise ValueError('Worker receipt does not bind the sealed cache artifact')
                if outcome=='measurement_available' and report['status']!='completed':
                    raise ValueError('Completed task conflicts with failed numerical artifact')
            else:
                records,states,kind=_partial_calls(artifact,capsule,digest,probe,binding)
        observation=dict(execution_outcomes=states,records=records,task_outcome=outcome)
        summary=summarize_probe(probe,records,expected_tape_sha256=binding['tape_sha256'],expected_target_id=binding['target_id'],expected_config=config)
        if outcome=='measurement_available' and not summary['all_executions_valid']:
            raise ValueError('Completed task lacks complete valid cache evidence')
        available=outcome=='measurement_available' and summary['all_executions_valid']
        costs=None
        if location['calls'] is not None:
            identity,calls=read_calls(inside(self.root,location['calls']));costs=summarize_calls(history,identity,calls)
        return dict(probe=probe,binding=binding,task_outcome=outcome,history=history,observation=observation,
            numerical_summary=summary,numerical_evidence_kind=kind,measurement_available=available,
            cached_seconds=summary['cached_seconds'] if available else None,
            outer_costs=costs,outer_measurement_missing=costs is None,samples_eligible=False,
            new_executor_calls=0,new_independent_audits=0,new_independent_repetitions=0)
