"""Declared grids and compact, individually bound scientific task contracts.

The driver validates the complete plan once. Workers receive only their own
target/input/configuration plus source/environment requirements, avoiding an
experiment-wide task table in every numerical process.
"""
import copy
import hashlib
from itertools import product
import numpy as np
from formal_runtime import fingerprint
from formal_inputs import MODEL_CODES

WORKFLOWS={device+'-'+kernel+'-'+executor:dict(device=device,kernel=kernel,executor=executor)
           for device in ('cpu','cuda') for kernel,executor in
           [('rwm','sequential'),('mala','sequential'),('rwm','online_picard'),('mala','quasi_deer')]}
WORKFLOWS['cpu-nuts-spawn_chains']=dict(device='cpu',kernel='nuts',executor='spawn_chains')


def create_tasks(identity,groups,batch_size=32):
    if not isinstance(identity,str) or not identity:raise ValueError('Explicit experiment identity required')
    if type(batch_size) is not int or batch_size<1:raise ValueError('Positive integer batch size required')
    tasks=[];seen=set()
    for group in groups:
        if set(group)!={'models','replicates','budgets','workflows'}:raise ValueError('Group fields differ')
        if any(not group[k] or len(set(group[k]))!=len(group[k]) for k in group):raise ValueError('Empty or duplicate group declaration')
        for name in group['models']:
            if name not in MODEL_CODES:raise ValueError('Unknown target')
        for rep in group['replicates']:
            if type(rep) is not int or not 0<=rep<2**32:raise ValueError('Invalid repeat address')
        for budget in group['budgets']:
            if type(budget) is not int or budget<4:raise ValueError('At least four retained steps required')
        for workflow in group['workflows']:
            if workflow not in WORKFLOWS:raise ValueError('Unsupported workflow: '+workflow)
        for model,rep,budget,workflow in product(group['models'],group['replicates'],group['budgets'],group['workflows']):
            key=(model,rep,budget,workflow)
            if key in seen:raise ValueError('Duplicate scientific task across groups')
            seen.add(key)
            row=dict(model=model,replicate=rep,budget=budget,workflow=workflow,**WORKFLOWS[workflow])
            row.update(id=fingerprint(dict(experiment=identity,**row))[:24],batch=rep//batch_size,input=f'{model}-rep{rep:04d}.npz')
            tasks.append(row)
    if not tasks:raise ValueError('Nonempty declared grid required')
    # A separate scheduling stream never consumes a sampling-input stream.
    words=np.frombuffer(hashlib.sha256((identity+'::schedule-v1').encode()).digest(),dtype='<u4')
    ordered=[]
    for batch in sorted({t['batch'] for t in tasks}):
        block=[t for t in tasks if t['batch']==batch]
        rng=np.random.Generator(np.random.Philox(np.random.SeedSequence([*map(int,words),batch])))
        ordered.extend(block[int(i)] for i in rng.permutation(len(block)))
    if len({t['id'] for t in ordered})!=len(ordered):raise ValueError('Task ID collision')
    return ordered


class BatchPlan:
    def __init__(self,document):
        p=copy.deepcopy(document);unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
        if fingerprint(unsigned)!=digest:raise ValueError('Plan checksum differs')
        if p['schema']!=1 or p['scope_kind'] not in ('technical_batch_validation','formal_inference'):
            raise ValueError('Unsupported plan schema/scope')
        if p['required_platform'] not in ('darwin','win32'):raise ValueError('Native platform required')
        if p['tasks']!=create_tasks(p['identity'],p['groups'],p['batch_size']):raise ValueError('Declared task table/order differs')
        target_map={t['name']:t for t in p['targets']}
        if len(target_map)!=len(p['targets']) or set(target_map)!={t['model'] for t in p['tasks']}:
            raise ValueError('Target catalog and task grid differ')
        if set(p['inputs'])!={t['input'] for t in p['tasks']}:raise ValueError('Actual input inventory differs')
        self._p=p;self._tasks={t['id']:t for t in p['tasks']};self._targets=target_map
        self.protocol_sha256=digest;self.identity=p['identity']
        for t in p['tasks']:
            capsule,h=self.capsule(t['id']);validate_capsule(capsule,h)

    def tasks(self,batch=None):
        for task in self._p['tasks']:
            if batch is None or task['batch']==batch:yield copy.deepcopy(task)

    def capsule(self,task_id):
        t=self._tasks[task_id]
        keep=('schema','identity','scope_kind','required_platform','source_commit','source_files',
              'required_versions','required_R_version','required_R_posterior','controls','cost_policy',
              'process_tree_rss_limit_bytes','required_disk_bytes_per_task','protocol_sha256')
        c={k:copy.deepcopy(self._p[k]) for k in keep}
        c.update(task=copy.deepcopy(t),target=copy.deepcopy(self._targets[t['model']]),
                 input=copy.deepcopy(self._p['inputs'][t['input']]))
        return c,fingerprint(c)


def validate_capsule(capsule,expected_sha256):
    if fingerprint(capsule)!=expected_sha256:raise ValueError('Task capsule checksum differs')
    c=capsule;task=c['task'];item=c['target'];data=c['input'];controls=c['controls']
    if c['schema']!=1 or c['scope_kind'] not in ('technical_batch_validation','formal_inference'):
        raise ValueError('Unsupported task capsule')
    if task['workflow'] not in WORKFLOWS or any(task[k]!=v for k,v in WORKFLOWS[task['workflow']].items()):
        raise ValueError('Task workflow/kernel/device conflict')
    if item['name']!=task['model'] or data['model']!=task['model'] or data['replicate']!=task['replicate']:
        raise ValueError('Target/repetition/input identity differs')
    if task['input']!=f"{task['model']}-rep{task['replicate']:04d}.npz":raise ValueError('Input path differs')
    integers=('chains','mh_discard','nuts_warmup','nuts_tree_depth','nuts_workers','nuts_threads','torch_threads',
              'window','quasi_deer_max_iter','memory_limit_mb','maximum_member_bytes')
    if any(type(controls[k]) is not int or controls[k]<1 for k in integers):raise ValueError('Invalid task controls')
    if controls['chains']!=4 or controls['nuts_workers']!=4 or controls['nuts_threads']!=1:
        raise ValueError('This schema declares a four-chain/four-worker CPU NUTS baseline')
    if type(task['budget']) is not int or task['budget']<4 or type(item['dimension']) is not int or item['dimension']<1:
        raise ValueError('Invalid task shape')
    if data['chains']!=controls['chains'] or data['dimension']!=item['dimension'] or data['steps']<controls['mh_discard']+task['budget']:
        raise ValueError('Actual master input does not cover the task prefix')
    for name in ('sha256','actual_sha256'):
        if len(data[name])!=64 or any(ch not in '0123456789abcdef' for ch in data[name]):raise ValueError('Invalid input hash')
    if any(not np.isfinite(controls[k]) or controls[k]<=0 for k in ('atol','rtol')) or not 0<controls['nuts_target_accept']<1:
        raise ValueError('Invalid numerical tolerances or adaptation target')
    if type(controls['nuts_full_mass']) is not bool:raise ValueError('Explicit NUTS geometry policy required')
    for name in ('process_tree_rss_limit_bytes','required_disk_bytes_per_task'):
        if type(c[name]) is not int or c[name]<1:raise ValueError('Positive resource guards required')
    if any(not np.isfinite(item['step_'+k]) or item['step_'+k]<=0 for k in ('rwm','mala')):
        raise ValueError('Fixed kernel step sizes required')
    return capsule


def mh_config(capsule,initial):
    c=capsule['controls'];t=capsule['task'];item=capsule['target']
    if t['kernel'] not in ('rwm','mala'):raise ValueError('MH configuration requested for another kernel')
    total=c['mh_discard']+t['budget']
    return dict(kernel=t['kernel'],executor=t['executor'],device=t['device'],chains=c['chains'],draws=total,
        initial=initial,step_size=item['step_'+t['kernel']],window=c['window'],
        max_iter=total if t['executor']=='online_picard' else c['quasi_deer_max_iter'],
        atol=c['atol'],rtol=c['rtol'],memory_limit_mb=c['memory_limit_mb'],audit=False,on_failure='error')
