"""Compare raw-streamed pilot analysis with archived independent companions."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_runtime import atomic_json,file_hash


def audit(run,output):
    if output.exists():raise FileExistsError('Fresh verification receipt required')
    original=ROOT/'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis'
    scalar=ROOT/'benchmark/analysis/outputs/formal-uncertainty-v1'
    old_manifest=json.loads((original/'manifest.json').read_text())
    for name in ['posterior.json','prefix-checks.json','function-estimates.json']:
        if file_hash(original/name)!=old_manifest[name]:raise ValueError('Original companion changed')
    new_manifest=json.loads((run/'manifest.json').read_text())
    for name,h in new_manifest.items():
        path=run/name
        if not path.resolve().is_relative_to(run.resolve()) or file_hash(path)!=h:
            raise ValueError('New companion changed: '+name)
    prior=json.loads((original/'posterior.json').read_text())['results']
    old_estimates=json.loads((original/'function-estimates.json').read_text())
    rows=[json.loads(line) for line in (run/'tasks.jsonl').read_text().splitlines()]
    receipt=dict(tasks=len(rows),failed_records=0,raw_rebuilt_means_exact=0,
        binary_transports_exact=0,R_function_rows_exact=0,R_function_rows_different=[],
        uncertainty_reports_exact=0,uncertainty_report_differences=[],prefix_rows_checked=0,
        prefix_differences=[],manifest_files_checked=len(new_manifest),new_MCMC_fits=0,
        source_analysis_commit=json.loads((run/'analysis-identity.json').read_text())['source_commit'],
        auditor_sha256=file_hash(Path(__file__)),formal_inference_complete=False,
        limitation='Same Mac and existing Python/R dependencies. Companion reconstruction only; '
                   'not a clean installation, Windows validation, formal-size memory proof or full paper reproduction.')
    for row in rows:
        if row['status']=='failed':
            receipt['failed_records']+=1
            if row['means'] is not None or row['outcome']!='numerical_failure':
                raise ValueError('Failed numerical output was promoted')
            receipt['failed_cost_seconds']=row['seconds']
            continue
        tid=row['id'];folder=run/'tasks'/tid
        if row['means']!=old_estimates[tid]:raise ValueError('Reconstructed means changed')
        receipt['raw_rebuilt_means_exact']+=1
        if file_hash(folder/'functions.bin')!=old_manifest[tid+'.bin']:
            raise ValueError('Function transport bytes changed')
        if file_hash(folder/'functions.bin.roundtrip')!=old_manifest[tid+'.bin.roundtrip']:
            raise ValueError('R roundtrip bytes changed')
        receipt['binary_transports_exact']+=1
        stats=json.loads((folder/'posterior.json').read_text())['results'][tid]
        if len(stats)!=len(prior[tid]):raise ValueError('Diagnostic function count differs')
        for old,new in zip(prior[tid],stats):
            if old==new:receipt['R_function_rows_exact']+=1
            else:receipt['R_function_rows_different'].append(dict(task=tid,previous=old,current=new))
    # Compare actual archived resampling/report identities, not just a count.
    scalar_manifest=json.loads((scalar/'manifest.json').read_text())
    for path in sorted((run/'models').glob('*/*.json')):
        if path.name=='summary.json':continue
        relative=path.relative_to(run/'models');old=scalar/relative
        if file_hash(old)!=scalar_manifest[relative.as_posix()]:raise ValueError('Scalar companion changed')
        if json.loads(path.read_text())==json.loads(old.read_text()):receipt['uncertainty_reports_exact']+=1
        else:receipt['uncertainty_report_differences'].append(relative.as_posix())
    identity=lambda r:tuple(r[k] for k in ['model','workflow','replicate','previous_budget','budget'])
    old_prefix={identity(r):r for r in json.loads((original/'prefix-checks.json').read_text())}
    new_prefix=[json.loads(line) for line in (run/'prefix-checks.jsonl').read_text().splitlines()]
    if set(old_prefix)!={identity(r) for r in new_prefix}:raise ValueError('Prefix comparison task frame changed')
    for row in new_prefix:
        old=old_prefix[identity(row)]
        equal=(row['bitwise_path_prefix_equal']==old['bitwise_path_prefix_equal'] and
            row['bitwise_acceptance_prefix_equal']==(None if old['acceptance_prefix_mismatches'] is None else old['acceptance_prefix_mismatches']==0) and
            row['initial_rng_equal']==old['rng_initial_equal'])
        receipt['prefix_rows_checked']+=1
        if not equal:receipt['prefix_differences'].append(dict(current=row,previous=old))
    receipt['passed']=not any(receipt[k] for k in ['R_function_rows_different','uncertainty_report_differences','prefix_differences'])
    atomic_json(output,receipt)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=audit(a.run,a.output)
    print(json.dumps(result,indent=2))
    if not result['passed']:sys.exit(1)
