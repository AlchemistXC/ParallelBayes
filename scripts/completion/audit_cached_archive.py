"""Read-only reconstruction of cached execution and all-invocation costs."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python')]
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_evidence import RuntimeEvidence,inside
from measured_coordinator import read_calls,summarize_calls
from formal_streaming import read_member


def audit(bundle,output):
    import numpy as np
    bundle=bundle.resolve();output=output.resolve()
    if output.exists() or output.is_relative_to(bundle) or bundle.is_relative_to(output):raise ValueError('Separate new output required')
    manifest=json.loads((bundle/'MANIFEST.json').read_text())
    for name,h in manifest.items():
        if file_hash(inside(bundle,name))!=h:raise ValueError('Archive asset differs: '+name)
    old=json.loads((bundle/'run/receipt.json').read_text());profile=json.loads((bundle/'profile.json').read_text())
    unsigned=dict(profile);digest=unsigned.pop('protocol_sha256')
    if fingerprint(unsigned)!=digest or digest!=old['protocol_sha256']:raise ValueError('Technical identity differs')
    reports=old['cached_task_costs']+[old['recovery_cost_after_verification']];locations={}
    for report in reports:
        history=report['history'];original=history['original']
        rel='run/injected-recovery' if original.endswith('/injected-recovery') else 'run/cached/'+history['task']['id']
        locations[original]=rel
        for attempt in history['attempts']:
            if attempt['attempt_id']==original+'.retry':locations[original+'.retry']=rel+'.retry'
    rebuilt=[];snapshot=bundle/'registry/registry.sqlite3'
    with RuntimeEvidence(snapshot,manifest['registry/registry.sqlite3'],bundle,locations) as evidence:
        for expected in reports:
            history=expected['history'];actual=evidence.history(history['task'],history['original'])
            if actual['attempts']!=history['attempts'] or actual['summary']!=history['summary']:
                raise ValueError('Stored execution history changed')
            directory=bundle/'run/call-costs'/Path(expected['ledger_directory']).name
            identity,calls=read_calls(directory);report=summarize_calls(actual,identity,calls)
            for key in ('actual_attempts','recorded_invocations','verification_only_invocations','unfinished_invocations',
                        'attempts_missing_outer_measurement','known_invocation_seconds','complete_invocation_seconds','by_action','calls'):
                if report[key]!=expected[key]:raise ValueError('Cost reconstruction differs: '+key)
            rebuilt.append(dict(original=history['original'],complete_invocation_seconds=report['complete_invocation_seconds'],
                recorded_invocations=report['recorded_invocations'],actual_attempts=report['actual_attempts'],
                verification_only_invocations=report['verification_only_invocations'],outcome=report['outcome']))
    executions=0;warm=0;timings=[]
    for record in old['cached_records']:
        name=record['task']['id'];attempt=bundle/'run/cached'/name/'attempt-0001'
        reference=bundle/'reference'/name/'attempt-0001/fit.npz'
        for i,row in enumerate(record['records']):
            metadata=json.loads((attempt/f'execution-{i}.json').read_text());raw=attempt/f'execution-{i}.npz'
            if metadata!=row or row['samples_eligible'] is not False or not row['technical_output_valid'] or not row['audit']['passed']:
                raise ValueError('Prepared candidate and final technical audit differ')
            if file_hash(raw)!=row['actual_array_sha256']:raise ValueError('Cached raw array changed')
            for key in ('unconstrained','accept'):
                if not np.array_equal(read_member(raw,key),read_member(reference,key)):raise ValueError('Reference arrays differ')
            if any(row['audit']['acceptance_mismatches']):raise ValueError('Accepted branch mismatch')
            if row['has_prior_execution']!=(i>0) or row['executor_wall_seconds']<=0:
                raise ValueError('Initial/cached execution identity differs')
            executions+=1;warm+=i>0
        timings.append(dict(task=record['task'],initial_seconds=record['records'][0]['executor_wall_seconds'],
            warm_seconds=[row['executor_wall_seconds'] for row in record['records'][1:]]))
    original=bundle/'run/injected-recovery';retry=original.with_name(original.name+'.retry')
    if json.loads((original/'state.json').read_text())['samples_eligible'] is not False:
        raise ValueError('Interrupted original was promoted')
    for key in ('draws','unconstrained','accept'):
        if not np.array_equal(read_member(original/'attempt-0001/fit.npz',key),read_member(retry/'attempt-0001/fit.npz',key)):
            raise ValueError('Retry arrays differ')
    report=dict(protocol_sha256=digest,assets_checked=len(manifest),cached_arrays_exact=executions,warm_executions=warm,
        cost_histories_rebuilt=len(rebuilt),rows=rebuilt,timings=timings,original_retry_arrays_exact=3,
        new_MCMC_fits=0,new_R_invocations=0,new_independent_statistical_repetitions=0,
        native_Windows_validated=False,formal_inference_complete=False,
        scope='Moved read-only bundle; recorded executor durations and every call cost reconstructed. No new timing or inference experiment.')
    output.mkdir(parents=True);atomic_json(output/'receipt.json',report);return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(audit(**vars(parser.parse_args())),indent=2))
