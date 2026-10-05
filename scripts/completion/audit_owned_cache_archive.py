"""Read-only owned-cache archive audit, including actual inputs and target binding.

No sampler, independent path oracle, process observation or old absolute data
path is used. This validates saved numerical-audit evidence, not a new audit.
"""
import argparse,copy,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from batch_contract import BatchPlan,mh_config
from batch_worker import payload
from cache_probe_execution import read_cached_probe
from inference_targets import build_target
from parallelbayes.torch_backend.sampling import settings,tape_hash
from formal_runtime import file_hash
from formal_outcomes import read_attempt
from formal_measurement_plan import validate_measurement_plan
from measured_coordinator import read_calls,summarize_calls
from validate_cache_execution import stats


def single_input_summary(bundle):
    """Technical point measurements only; a single input has no repeat interval."""
    bundle=Path(bundle);p=json.loads((bundle/'protocol.json').read_text());BatchPlan(p)
    allocation=json.loads((bundle/'allocation.json').read_text());validate_measurement_plan(allocation,p['tasks'])
    if len({(t['model'],t['replicate']) for t in p['tasks']})!=1:
        raise ValueError('This companion is for exactly one original technical input')
    workflows={}
    for probe in allocation['probes']:
        report=read_cached_probe(bundle/'tasks'/probe['id']/'attempt-0001/probe')
        workflows[probe['workflow']]=dict(probe_id=probe['id'],measurement_available=report['measurement_available'],
            cached_seconds=report['summary']['cached_seconds'],known_executor_seconds=report['summary']['known_executor_seconds'])
    pairs=[]
    for kernel,executor in [('rwm','online_picard'),('mala','quasi_deer')]:
        first=workflows['cpu-'+kernel+'-sequential'];second=workflows['cpu-'+kernel+'-'+executor]
        ratio=first['cached_seconds']/second['cached_seconds'] if first['measurement_available'] and second['measurement_available'] else None
        pairs.append(dict(kernel=kernel,sequential_over_parallel=ratio,confidence_interval=None))
    return dict(protocol_sha256=p['protocol_sha256'],original_inputs=1,workflows=workflows,pairs=pairs,
        resampling_plan_created=False,confidence_intervals_created=0,independent_repetitions_added=0,
        scope='Single reused technical input; prepared-call medians and descriptive ratios, not repeat-level inference or a general speed result')


def audit(bundle):
    bundle=Path(bundle)
    manifest=json.loads((bundle/'MANIFEST.json').read_text())
    if {str(p.relative_to(bundle)) for p in bundle.rglob('*') if p.is_file()}!=set(manifest)|{'MANIFEST.json'}:
        raise ValueError('Bundle inventory differs')
    for name,h in manifest.items():
        path=bundle/name
        if path.is_symlink() or not path.resolve().is_relative_to(bundle.resolve()) or file_hash(path)!=h:raise ValueError('Archive asset differs')
    p=json.loads((bundle/'protocol.json').read_text());plan=BatchPlan(p)
    allocation=json.loads((bundle/'allocation.json').read_text());audits=events=records=0;max_error=0.
    validate_measurement_plan(allocation,p['tasks'])
    if allocation['allocation_sha256']!=p['cache_allocation_sha256']:raise ValueError('Allocation differs')
    latest=json.loads(sorted((bundle/'invocations').glob('*.json'))[-1].read_text())
    saved_rows={row['probe_id']:row for row in latest['rows']};reports={};outer_calls=0;runtime_seconds=0.
    if set(saved_rows)!={probe['id'] for probe in allocation['probes']}:raise ValueError('Planned outcome frame differs')
    for probe in allocation['probes']:
        c,digest=plan.capsule(probe['primary_task_id'])
        saved=saved_rows[probe['id']];directory=bundle/'tasks'/probe['id']
        row=read_attempt(directory);history=copy.deepcopy(saved['costs']['history']);expected=history['attempts'][0]
        row['attempt_id']=expected['attempt_id']
        if row!=expected or row['artifact_kind']!='cache_measurement':raise ValueError('Rebuilt attempt differs')
        if row['fixed_task']!=dict(id=probe['id'],protocol_sha256=plan.protocol_sha256,artifact_kind='cache_measurement'):
            raise ValueError('Runtime task is not the planned measurement')
        identity,calls=read_calls(bundle/saved['relative_calls']);reduced=summarize_calls(history,identity,calls)
        if any(saved['costs'][key]!=value for key,value in reduced.items()):raise ValueError('Outer costs differ')
        outer_calls+=len(calls);runtime_seconds+=row['seconds'] or 0.
        report=read_cached_probe(directory/'attempt-0001/probe')
        request=json.loads((directory/'attempt-0001/probe/request.json').read_text())
        if request!=dict(capsule=c,capsule_sha256=digest,probe=probe):raise ValueError('Saved capsule differs')
        if report['samples_eligible'] or (row['outcome']=='measurement_available')!=report['measurement_available']:
            raise ValueError('Measurement eligibility differs')
        values=payload(dict(inputs=str(bundle/'inputs')),c)
        config=settings(mh_config(c,values['initial'].tolist()))
        tape={k:values[k][:,:config['draws']] for k in ('noise','log_uniform','directions')}
        model=build_target(c['target'],None,'cpu')
        binding=dict(input_file_sha256=c['input']['sha256'],tape_sha256=tape_hash(tape),target_id=model.target_id,config=config)
        if binding!=report['binding']:raise ValueError('Saved measurement input/target/config binding differs')
        reports[probe['id']]=report
        for record in report['observation']['records']:
            if record is None:continue
            records+=1;path_audit=record.get('audit')
            if path_audit is not None:
                audits+=bool(path_audit['passed'])
                events+=sum(path_audit.get('acceptance_mismatches',[]))
                max_error=max(max_error,max(path_audit.get('max_abs_path_error',[0.])))
    singleton=len({(t['model'],t['replicate']) for t in p['tasks']})==1
    if singleton:
        if single_input_summary(bundle)!=json.loads((bundle/'single-input-summary.json').read_text()):raise ValueError('Singleton companion differs')
    else:
        for model in p['groups'][0]['models']:stats(allocation,p['tasks'],model,reports,stored=bundle/'analysis'/model)
    return dict(verified_manifest_assets=len(manifest),probe_artifacts=len(reports),outer_calls_verified=outer_calls,
                runtime_seconds_rebuilt=runtime_seconds,actual_input_bindings_verified=len(allocation['probes']),saved_numerical_records=records,
                saved_audits_passed=audits,saved_acceptance_mismatches=events,saved_max_abs_path_error=max_error,
                singleton_companion_rebuilt=singleton,new_executor_calls=0,new_independent_audits=0,samples_eligible=0,
                formal_inference_complete=False,native_Windows_validated=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(audit(args.bundle),indent=2))
