"""Owned Mac cache measurement, explicit output roles, resume and relocation.

Reuses archived technical inputs; does not generate a primary fit, new research
repeat or formal performance conclusion. short and maximum are distinct freezes.
"""
import argparse,copy,hashlib,importlib.metadata,json,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from batch_contract import BatchPlan,create_tasks
from cache_probe_execution import read_cached_probe
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_outcomes import read_attempt
from formal_measurement_plan import create_measurement_plan,validate_measurement_plan
from measured_coordinator import MeasuredCoordinator,read_calls,summarize_calls
from validate_cache_execution import stats


def freeze(baseline,output,profile):
    if sys.platform!='darwin':raise ValueError('Native Mac technical gate only')
    baseline=Path(baseline);output=Path(output)
    p=json.loads((baseline/'protocol.json').read_text());BatchPlan(p)
    expected='cache-probe-capsule-mac-v2' if profile=='short' else 'batch-schema-maximum-mac-v1'
    if p['identity']!=expected:raise ValueError('Wrong original technical input identity')
    original_sha=file_hash(baseline/'protocol.json')
    p.pop('protocol_sha256');p['identity']='owned-cache-runtime-mac-'+profile+'-v1'
    p['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    workflows=['cpu-rwm-sequential','cpu-rwm-online_picard','cpu-mala-sequential','cpu-mala-quasi_deer']
    p['groups']=[dict(models=['G1','L1'] if profile=='short' else ['G2'],replicates=[0,1] if profile=='short' else [0],budgets=[8] if profile=='short' else [16384],workflows=workflows)]
    p['tasks']=create_tasks(p['identity'],p['groups']);models=p['groups'][0]['models']
    p['targets']=[t for t in p['targets'] if t['name'] in models]
    names={t['input'] for t in p['tasks']};p['inputs']={n:v for n,v in p['inputs'].items() if n in names}
    for name,row in p['inputs'].items():
        if file_hash(baseline/'inputs'/name)!=row['sha256']:raise ValueError('Original input file differs')
    modified=['formal_runtime','formal_coordinator','formal_outcomes','formal_recovery']
    added=['cached_execution','cache_probe_execution','cache_probe_analysis','formal_measurement_plan',
           'validate_cache_execution','owned_cache_worker','validate_owned_cache']
    for module in modified+added:
        path='scripts/completion/'+module+'.py';p['source_files'][path]=file_hash(ROOT/path)
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h or hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Committed source differs: '+name)
    p['required_versions']={n:importlib.metadata.version(n) for n in p['required_versions']}
    for key in ('addresses','measurement_design_sha256','cache_allocation_sha256'):p.pop(key,None)
    p.update(source_input_identity=expected,source_input_protocol_file_sha256=original_sha,
        input_reuse_is_not_new_independent_repetition=True,
        scientific_scope='Owned cache-only technical measurements; no posterior fits and no formal inference repetitions',
        resource_policy='Four-thread CPU, declared sampler workspace estimate and sampled 6GiB process-tree RSS guard; native Mac fresh process group; no total-time cutoff',
        recovery_policy='Completed/failed cache terminals resume with no execution; interrupted cache probes cannot be retried',
        cost_policy=dict(primary='No primary fits in this technical validation',cached='One initial plus three prepared calls, all independently audited',outer='All coordinator invocations including later verification retained separately; nested times are not additive'),
        process_tree_rss_limit_bytes=6*1024**3,required_disk_bytes_per_task=2*1024**3)
    allocation=create_measurement_plan(p['identity'],p['tasks']);p['cache_allocation_sha256']=allocation['allocation_sha256']
    p['protocol_sha256']=fingerprint(p);BatchPlan(p)
    output.mkdir(parents=True,exist_ok=False);(output/'inputs').mkdir()
    for name in names:shutil.copy2(baseline/'inputs'/name,output/'inputs'/name)
    atomic_json(output/'protocol.json',p);atomic_json(output/'allocation.json',allocation)
    return dict(identity=p['identity'],protocol_sha256=p['protocol_sha256'],probes=len(allocation['probes']),source_commit=p['source_commit'],new_independent_inputs=0)


def run(bundle,host_lock,resume=False):
    bundle=Path(bundle).resolve();p=json.loads((bundle/'protocol.json').read_text());plan=BatchPlan(p)
    allocation=json.loads((bundle/'allocation.json').read_text());validate_measurement_plan(allocation,p['tasks'])
    if allocation['allocation_sha256']!=p['cache_allocation_sha256']:raise ValueError('Allocation differs')
    if sys.platform!='darwin' or not p['identity'].startswith('owned-cache-runtime-mac-'):raise ValueError('Technical launch only')
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Frozen source changed: '+name)
    for name,version in p['required_versions'].items():
        if importlib.metadata.version(name)!=version:raise ValueError('Dependency differs: '+name)
    c=MeasuredCoordinator(host_lock,bundle/'call-costs');new=0;reports={};rows=[];started=time.perf_counter()
    for i,probe in enumerate(allocation['probes']):
        capsule,digest=plan.capsule(probe['primary_task_id']);directory=bundle/'tasks'/probe['id']
        task=dict(id=probe['id'],protocol_sha256=plan.protocol_sha256,artifact_kind='cache_measurement')
        print(json.dumps(dict(starting=i+1,total=len(allocation['probes']),model=probe['model'],workflow=probe['workflow'])),flush=True)
        if directory.exists() and resume and c.coordinator.history(directory)['summary']['outcome']=='infrastructure_interruption':
            result=None  # no implicit retry, even if the cache output happens to exist
        else:
            result=c.run(task,dict(capsule=capsule,capsule_sha256=digest,probe=probe,inputs=str(bundle/'inputs')),
                         ROOT/'scripts/completion/owned_cache_worker.py',directory,
                         p['required_disk_bytes_per_task'],p['process_tree_rss_limit_bytes'],resume=resume)
            new+=result['newly_executed']
        costs=c.report(directory);history=costs['history'];row=history['attempts'][0]
        if len(history['attempts'])!=1:raise ValueError('Cache probe has unexpected retry history')
        available=history['summary']['outcome']=='measurement_available'
        if available or history['summary']['outcome']=='numerical_failure':
            report=read_cached_probe(directory/'attempt-0001/probe')
            if available!=report['measurement_available'] or report['samples_eligible']:raise ValueError('Lifecycle and cache eligibility differ')
            reports[probe['id']]=report
        rows.append(dict(probe_id=probe['id'],relative_task='tasks/'+probe['id'],relative_calls=str(Path(costs['ledger_directory']).relative_to(bundle)),
            costs=costs,outcome=row['outcome'],samples_eligible=False,
            sampled_peak_tree_rss_bytes=result['memory']['sampled_peak_tree_rss_bytes'] if result else None))
    index=bundle/'invocations';index.mkdir(exist_ok=True)
    report=dict(identity=p['identity'],protocol_sha256=plan.protocol_sha256,source_commit=p['source_commit'],
        newly_executed=new,probes=len(rows),available=sum(r['outcome']=='measurement_available' for r in rows),
        samples_eligible=0,independent_statistical_repetitions_added=0,driver_loop_wall_seconds=time.perf_counter()-started,
        nested_costs_not_additive=True,rows=rows,formal_inference_complete=False,native_Windows_validated=False)
    atomic_json(index/(str(time.time_ns())+'.json'),report)
    if not resume and len(reports)==len(rows):
        analysis=bundle/'analysis';analysis.mkdir()
        for model in p['groups'][0]['models']:stats(allocation,p['tasks'],model,reports,output=analysis/model)
    return {k:v for k,v in report.items() if k!='rows'}


def audit(bundle):
    bundle=Path(bundle);manifest=json.loads((bundle/'MANIFEST.json').read_text())
    actual={str(p.relative_to(bundle)) for p in bundle.rglob('*') if p.is_file()}
    if actual!=set(manifest)|{'MANIFEST.json'}:raise ValueError('Bundle inventory differs')
    for name,h in manifest.items():
        path=bundle/name
        if path.is_symlink() or not path.resolve().is_relative_to(bundle.resolve()) or file_hash(path)!=h:raise ValueError('Archive asset differs')
    p=json.loads((bundle/'protocol.json').read_text());plan=BatchPlan(p)
    allocation=json.loads((bundle/'allocation.json').read_text());validate_measurement_plan(allocation,p['tasks'])
    if allocation['allocation_sha256']!=p['cache_allocation_sha256']:raise ValueError('Allocation binding differs')
    for name,row in p['inputs'].items():
        if file_hash(bundle/'inputs'/name)!=row['sha256']:raise ValueError('Saved actual input differs')
    invocations=[json.loads(path.read_text()) for path in sorted((bundle/'invocations').glob('*.json'))]
    latest=invocations[-1];reports={};calls_verified=0;runtime_costs=0.
    for saved in latest['rows']:
        directory=bundle/saved['relative_task'];row=read_attempt(directory)
        history=copy.deepcopy(saved['costs']['history']);expected=history['attempts'][0]
        row['attempt_id']=expected['attempt_id']  # original absolute name is an identity, never a read location
        if row!=expected:raise ValueError('Rebuilt attempt history differs')
        identity,calls=read_calls(bundle/saved['relative_calls']);reduced=summarize_calls(history,identity,calls)
        if any(saved['costs'][key]!=value for key,value in reduced.items()):raise ValueError('Outer call costs differ')
        calls_verified+=len(calls);runtime_costs+=row['seconds'] or 0.
        report=read_cached_probe(directory/'attempt-0001/probe');probe=report['probe']
        capsule,digest=plan.capsule(probe['primary_task_id'])
        request=json.loads((directory/'attempt-0001/probe/request.json').read_text())
        if request!=dict(capsule=capsule,capsule_sha256=digest,probe=probe):raise ValueError('Saved capsule differs')
        if probe not in allocation['probes'] or row['artifact_kind']!='cache_measurement' or report['samples_eligible']:
            raise ValueError('Measurement frame or eligibility differs')
        reports[probe['id']]=report
    for model in p['groups'][0]['models']:stats(allocation,p['tasks'],model,reports,stored=bundle/'analysis'/model)
    return dict(verified_manifest_assets=len(manifest),probe_artifacts=len(reports),
        saved_executor_calls=sum(r['summary']['observed_executions'] for r in reports.values()),
        outer_calls_verified=calls_verified,runtime_seconds_rebuilt=runtime_costs,
        new_executor_calls=0,new_independent_audits=0,samples_eligible=0,
        formal_inference_complete=False,native_Windows_validated=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');f.add_argument('--baseline',type=Path,required=True);f.add_argument('--output',type=Path,required=True);f.add_argument('--profile',choices=['short','maximum'],required=True)
    r=sub.add_parser('run');r.add_argument('--bundle',type=Path,required=True);r.add_argument('--host-lock',type=Path,required=True);r.add_argument('--resume',action='store_true')
    a=sub.add_parser('audit');a.add_argument('--bundle',type=Path,required=True)
    args=vars(parser.parse_args());action=args.pop('action');print(json.dumps(globals()[action](**args),indent=2),flush=True)
