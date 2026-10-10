"""Versioned compact scientific frame; historical fixed-grid contracts stay intact.

New executable protocols use a distinct schema. Numerical capsules reuse the
unchanged scientific shape validator, with an explicit compact execution tag.
No input generation, process launch or outcome-driven selection occurs here.
"""
import copy
import json
from pathlib import Path
import sys

from batch_contract import BatchPlan, create_tasks, validate_capsule, WORKFLOWS
from formal_runtime import fingerprint, file_hash

IDENTITY='windows-compact-inference-v1'
TECHNICAL_ID='windows-compact-adapter-validation-v1'
PLAN_SCHEMA='compact-execution-plan-v1'
PROTOCOL_SCHEMA='compact-study-protocol-v1'
CONTRACT='windows-compact-contract-v1'


def create_plan(root, *, technical=False):
    root=Path(root).resolve()
    sys.path.insert(0,str(root/'scripts/analysis'))
    from plan_compact_study import build
    design,storage=build(root)
    saved=json.loads((root/'benchmark/designs/windows-compact-inference-v1/design.json').read_text())
    saved_storage=json.loads((root/'benchmark/designs/windows-compact-inference-v1/storage.json').read_text())
    if design!=saved or storage!=saved_storage:
        raise ValueError('Committed compact design/byte ledger differ from the metadata planner')
    identity=TECHNICAL_ID if technical else IDENTITY
    groups=([dict(models=['G2'],replicates=[0],budgets=[4096],workflows=list(WORKFLOWS)),
             dict(models=['W1'],replicates=[0],budgets=[1024],workflows=list(WORKFLOWS))]
             if technical else copy.deepcopy(design['groups']))
    tasks=create_tasks(identity,groups,batch_size=8)
    models={t['model'] for t in tasks}
    targets=[copy.deepcopy(t) for t in design['targets'] if t['name'] in models]
    requirements={}
    for t in tasks:
        name=t['input']; dimension=next(x['dimension'] for x in targets if x['name']==t['model'])
        count=512+t['budget'] if technical else 4608
        requirements[name]=dict(model=t['model'],replicate=t['replicate'],chains=4,dimension=dimension,
            steps=max(count,requirements.get(name,{}).get('steps',0)),
            roles=['initial','noise','log_uniform','directions','nuts_seeds'])
    probes=[]
    for t in tasks:
        if t['kernel']=='nuts':continue
        if not technical and (t['model'] not in design['cache_policy']['models'] or
                              t['replicate'] not in design['cache_policy']['original_replicates']):continue
        probe=dict(t,initial_calls=1,prepared_replays=3,primary_task_id=t['id'])
        probe['id']=fingerprint(dict(identity=identity,role='compact-cache-v1',primary=t['id']))[:24]
        probes.append(probe)
    if not technical:
        if fingerprint(tasks)!=design['primary_task_table_sha256'] or fingerprint(probes)!=design['cache_table_sha256']:
            raise ValueError('Compact prescribed order/task/cache IDs differ')
    alloc=dict(schema='compact-cache-allocation-v1',primary_identity=identity,probes=probes,
        primary_task_count=len(tasks),primary_grid_sha256=fingerprint(tasks),total_executor_calls=4*len(probes),
        prepared_replays=3,initial_calls=1,samples_eligible=False,statistical_repetitions_added=0,
        primary_outcome_is_selection_criterion=False,failed_selected_tasks_replaced=False,
        summary='All four calls valid and timed or median/ratio unavailable; per-input descriptive n4, no BCa')
    alloc['allocation_sha256']=fingerprint(alloc)
    p=dict(schema=PLAN_SCHEMA,identity=identity,technical=technical,
        scope_kind='technical_batch_validation' if technical else 'formal_inference',
        compact_design_sha256=design['design_sha256'],design_file_sha256=file_hash(root/'benchmark/designs/windows-compact-inference-v1/design.json'),
        required_platform='win32',groups=groups,tasks=tasks,targets=targets,input_requirements=requirements,
        batch_size=8,batches=[dict(batch=b,main_tasks=sum(t['batch']==b for t in tasks),
            cache_probes=sum(t['batch']==b for t in probes)) for b in range(1 if technical else 3)],
        independent_repeats_per_target=0 if technical else 24,formal_scientific_repetitions=0 if technical else 24,
        controls=copy.deepcopy(design['controls']),initial_policy=copy.deepcopy(design['initial_policy']),
        trajectory_policy=copy.deepcopy(design['trajectory_policy']),analysis_policy=copy.deepcopy(design['analysis_policy']),
        execution_policy=copy.deepcopy(design['execution_policy']),cost_policy=copy.deepcopy(design['cost_policy']),
        cache_allocation=alloc,old_results_used_as_repetitions=False,
        formal_sampling_allowed_by_plan=False,fully_prospective_preregistration=False)
    p['plan_sha256']=fingerprint(p)
    return p


def validate_plan(plan, root):
    if plan.get('schema')!=PLAN_SCHEMA or type(plan.get('technical')) is not bool:
        raise ValueError('Only the explicit compact execution plan is supported')
    if plan!=create_plan(root,technical=plan['technical']):
        raise ValueError('Compact scientific plan differs from the prescribed design')
    return plan


def allocation(plan):
    return copy.deepcopy(plan['cache_allocation'])


class CompactPlan(BatchPlan):
    def __init__(self, document):
        if document.get('schema')!=PROTOCOL_SCHEMA or document.get('compact_execution_contract')!=CONTRACT:
            raise ValueError('Compact protocol required; old protocols and design-only JSON refused')
        raw=copy.deepcopy(document);signature=raw.pop('protocol_sha256')
        if fingerprint(raw)!=signature:raise ValueError('Compact protocol checksum differs')
        if document['identity'] not in (IDENTITY,TECHNICAL_ID):raise ValueError('Unknown compact identity')
        expected='technical_batch_validation' if document['identity']==TECHNICAL_ID else 'formal_inference'
        if document['scope_kind']!=expected:raise ValueError('Technical/formal scope cannot be switched')
        # Internal reuse of the scientific capsule validator only. This object
        # never admits a schema-1 document as compact launch authority.
        numeric=copy.deepcopy(document);numeric['schema']=1
        numeric['protocol_sha256']=fingerprint({k:v for k,v in numeric.items() if k!='protocol_sha256'})
        self._compact_digest=signature
        super().__init__(numeric)
        self.protocol_sha256=signature
        self._p['protocol_sha256']=signature

    def capsule(self, task_id):
        c,_=super().capsule(task_id)
        c['protocol_sha256']=self._compact_digest
        c['compact_execution_contract']=CONTRACT
        return c,fingerprint(c)


def validate_probe(capsule,digest,probe):
    c=validate_capsule(capsule,digest)
    if c.get('compact_execution_contract')!=CONTRACT or c['identity'] not in (IDENTITY,TECHNICAL_ID):
        raise ValueError('Explicit compact capsule binding required')
    t=c['task'];expected=dict(t,initial_calls=1,prepared_replays=3,primary_task_id=t['id'])
    expected['id']=fingerprint(dict(identity=c['identity'],role='compact-cache-v1',primary=t['id']))[:24]
    if probe!=expected or t['kernel'] not in ('rwm','mala'):
        raise ValueError('Compact cache probe differs from frozen MH task')
    return c
