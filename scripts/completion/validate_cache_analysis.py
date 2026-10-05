"""Generate/rebuild an explicitly artificial cache-statistics audit fixture.

No sampler, clock benchmark, device operation or reference-posterior calculation
is performed. Fixture timing numbers are known literals, never research results.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import platform
import sys
import numpy as np
import scipy
from scipy.stats import bootstrap
from batch_contract import create_tasks,WORKFLOWS
from cache_probe_analysis import create_cache_plan,analyze_cache_probes
from formal_measurement_plan import create_measurement_plan
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_uncertainty import save_plan,load_plan

ROOT=Path(__file__).resolve().parents[2]


def split_report(report):
    result=dict(report);arrays=result.pop('bootstrap_statistics')
    return result,arrays


def generate(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    identity='artificial-cache-companion-validation-v1'
    tasks=create_tasks(identity,[dict(models=['G1'],replicates=list(range(128)),
        budgets=[8,16],workflows=list(WORKFLOWS))])
    allocation=create_measurement_plan(identity,tasks)
    plan=create_cache_plan(allocation,tasks,'G1')
    rank={int(r):i for i,r in enumerate(plan.replicate_ids)}
    bindings={};observations={}
    for p in allocation['probes']:
        i=rank[p['replicate']];c=dict(kernel=p['kernel'],executor=p['executor'],device=p['device'],chains=4,
            draws=p['budget']+4,step_size=.1,initial=[[float(p['replicate']),0.]]*4,
            atol=1e-10,rtol=1e-10,window=4,max_iter=100,audit=False,on_failure='error')
        binding=dict(input_file_sha256=fingerprint(['artificial-input',p['replicate']]),
            tape_sha256=fingerprint(['artificial-tape',p['replicate'],p['budget']]),target_id=fingerprint('artificial-target'),config=c)
        # Values are declared artificial seconds, not measured durations.
        midpoint=[2.,4.,8.,16.][i%4] if p['executor']=='sequential' else 1.
        records=[dict(execution_index=j,has_prior_execution=j>0,status='candidate',samples_eligible=False,
            technical_output_valid=True,executor_wall_seconds=s,tape_sha256=binding['tape_sha256'],
            target_id=binding['target_id'],config=copy.deepcopy(c)) for j,s in enumerate([10.,midpoint-.5,midpoint,midpoint+.5])]
        states=['valid']*4
        if i<4 and p['workflow']=='cpu-rwm-sequential' and p['budget']==8:
            records[0]['technical_output_valid']=False;states[0]='numerical_failure'
        bindings[p['id']]=binding;observations[p['id']]=dict(records=records,execution_outcomes=states)
    save_plan(plan,output/'cache-resampling')
    fixture=dict(primary_tasks=tasks,allocation=allocation,bindings=bindings,observations=observations,
        scope='Artificial statistical fixture only: every timing, hash, output flag and configuration below is constructed; no actual sampler evidence.')
    atomic_json(output/'fixture.json',fixture)
    report,arrays=split_report(analyze_cache_probes(allocation,tasks,plan,bindings,observations))
    atomic_json(output/'analysis.json',report);np.savez_compressed(output/'bootstrap-statistics.npz',**arrays)
    pair=next(p for p in report['pairs'] if p['workflow_a']=='cpu-rwm-sequential@8')
    logs=np.tile(np.log([2.,4.,8.,16.]),8);logs[:4]=np.nan
    oracle=bootstrap((logs,),np.nanmean,vectorized=True,method='BCa',batch=64,n_resamples=9999,rng=np.random.default_rng(plan.rng_seed))
    actual=pair['confidence_interval'];expected=[float(oracle.confidence_interval.low),float(oracle.confidence_interval.high)]
    errors=[abs(actual['low']-expected[0]),abs(actual['high']-expected[1])]
    if max(errors)>2e-12 or not math.isclose(pair['geometric_mean_ratio'],math.sqrt(32.),rel_tol=2e-14):
        raise AssertionError('Artificial paired statistic differs from independent oracle')
    sources=['scripts/completion/'+n+'.py' for n in ('cache_probe_analysis','formal_measurement_plan','formal_uncertainty','validate_cache_analysis')]
    summary=dict(scope=fixture['scope'],source_files={name:file_hash(ROOT/name) for name in sources},
        python=sys.version,platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,
        primary_frame_size=128,selected_original_inputs=len(plan.replicate_ids),
        selected_per_batch=[len(s['selected_replicates']) for s in allocation['strata']],
        planned_probes=len(allocation['probes']),artificial_execution_records=sum(len(v['records']) for v in observations.values()),
        same_model_shared_resampling_sha256=plan.sha256,n_resamples=len(plan.indices),
        comparison=pair,scipy_log_ratio_bounds=expected,absolute_endpoint_errors=errors,
        independent_hand_ratio=math.sqrt(32.),new_MCMC_fits=0,new_execution_timings=0,new_research_repetitions=0,
        limitations='Fixed artificial availability and durations; does not validate actual input provenance, sampler correctness, native runtime, or coverage under load drift.')
    atomic_json(output/'summary.json',summary)
    atomic_json(output/'MANIFEST.json',{p.relative_to(output).as_posix():file_hash(p) for p in sorted(output.rglob('*')) if p.is_file()})
    return summary


def audit(bundle):
    bundle=Path(bundle);manifest=json.loads((bundle/'MANIFEST.json').read_text())
    files={p.relative_to(bundle).as_posix() for p in bundle.rglob('*') if p.is_file()}
    if files!=set(manifest)|{'MANIFEST.json'}:raise ValueError('Fixture inventory differs')
    for name,digest in manifest.items():
        path=bundle/name
        if not path.resolve().is_relative_to(bundle.resolve()) or path.is_symlink() or file_hash(path)!=digest:
            raise ValueError('Fixture hash/path differs')
    f=json.loads((bundle/'fixture.json').read_text());plan=load_plan(bundle/'cache-resampling')
    report,arrays=split_report(analyze_cache_probes(f['allocation'],f['primary_tasks'],plan,f['bindings'],f['observations']))
    if report!=json.loads((bundle/'analysis.json').read_text()):raise ValueError('Relocated analysis differs')
    with np.load(bundle/'bootstrap-statistics.npz',allow_pickle=False) as z:
        if set(z.files)!=set(arrays) or any(not np.array_equal(z[k],arrays[k],equal_nan=True) for k in arrays):
            raise ValueError('Rebuilt bootstrap distributions differ')
    return dict(verified_files=len(manifest),planned_inputs=len(plan.replicate_ids),
        verified_probe_reductions=len(report['probes']),verified_distributions=len(arrays),
        resampling_sha256=plan.sha256,relocated_statistics_exact=True,new_MCMC_fits=0,new_execution_timings=0,
        scope='Read-only reconstruction of artificial statistics, not new experimental evidence')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output',type=Path);group.add_argument('--audit',type=Path)
    args=parser.parse_args();print(json.dumps(generate(args.output) if args.output else audit(args.audit),indent=2))
