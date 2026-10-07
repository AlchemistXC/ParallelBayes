"""Complete v0.2 scientific frame, before platform freeze or actual inputs.

No sampling, input regeneration, environment substitution, or outcome-driven
selection. The native freezer must bind this plan to source, actual files,
devices, dependencies and resource checks before a worker may use it.
"""
import argparse
import copy
import json
from pathlib import Path
import re
from batch_contract import create_tasks,WORKFLOWS
from formal_measurement_plan import create_measurement_plan,validate_measurement_plan
from formal_runtime import fingerprint,atomic_json,file_hash

MODELS=('G1','G2','A1','L1','L2','H1','H2','M1','W1')
BUDGETS=(256,1024,4096,16384)
REPLICATES=128
BATCH_SIZE=32
DEVELOPMENT_PROTOCOL_SHA256='f8af8ab024baf0d0c97dc0e2cf52e61c112f57bfa647162204a74adc94ff298b'


def create_study_plan(identity,catalog):
    if not isinstance(identity,str) or not re.fullmatch(r'windows-formal-[a-z0-9-]+',identity):
        raise ValueError('An explicit new Windows formal experiment identity is required')
    unsigned=copy.deepcopy(catalog);digest=unsigned.pop('protocol_sha256')
    if (fingerprint(unsigned)!=digest or digest!=DEVELOPMENT_PROTOCOL_SHA256 or
            catalog['identity']!='inference-budget-pilot-mac-v1'):
        raise ValueError('Verified development catalog required; never tune from formal results')
    targets={t['name']:t for t in catalog['targets']}
    if set(targets)!=set(MODELS) or len(catalog['targets'])!=9:
        raise ValueError('All nine prespecified target families must remain present')
    groups=[dict(models=list(MODELS),replicates=list(range(REPLICATES)),budgets=list(BUDGETS),workflows=list(WORKFLOWS))]
    tasks=create_tasks(identity,groups,batch_size=BATCH_SIZE)
    allocation=create_measurement_plan(identity,tasks,batch_size=BATCH_SIZE,selected_per_batch=8,replays=3)
    plan=dict(schema='formal-study-plan-v1',identity=identity,design_basis='F3-FORMAL-DESIGN-DRAFT-v0.2',
        required_platform='win32',catalog_protocol_sha256=digest,
        targets=[copy.deepcopy(targets[n]) for n in MODELS],groups=groups,tasks=tasks,
        batches=[dict(batch=b,replicates=list(range(32*b,32*(b+1))),main_tasks=10368,cache_probes=2304) for b in range(4)],
        batch_size=BATCH_SIZE,independent_repeats_per_target=REPLICATES,
        independent_unit='One original four-chain repetition; paired budgets, workflows and replays are not new repetitions',
        input_requirements={f'{name}-rep{r:04d}.npz':dict(model=name,replicate=r,dimension=targets[name]['dimension'],
            chains=4,steps=16896,roles=['initial','noise','log_uniform','directions','nuts_seeds']) for name in MODELS for r in range(REPLICATES)},
        controls=dict(chains=4,mh_discard=512,nuts_warmup=1024,nuts_tree_depth=8,nuts_target_accept=.8,
            nuts_full_mass=False,nuts_workers=4,nuts_threads=1,torch_threads=4,window=32,quasi_deer_max_iter=2048,
            atol=1e-10,rtol=1e-10,memory_limit_mb=2048,maximum_member_bytes=128*1024**2,minimum_gpu_free_bytes=3*1024**3),
        initial_policy=dict(coordinates='frozen affine coordinates',distribution='N(0,4I)',
            M1_first_coordinate=[-5.,5.,-5.,5.],remaining_coordinates_unchanged=True),
        trajectory_policy=dict(Picard_max_iter='retained budget + 512',quasi_DEER_max_iter='2048 per window',
            MH_oracle='full independent NumPy path with actual frozen arrays',acceptance_mismatches_allowed=0,
            path_limit='100*(atol+rtol*max(1,maxabs(saved_chain)))',
            NUTS_same_path_claim=False,failed_trajectories_are_samples=False),
        analysis_policy=dict(functions='36 fixed original-output functions and fixed scales from development reference contract',
            analytical_models=['G1','G2','A1','H1','H2','M1'],finite_reference_models=['L1','L2'],
            uncertified_quadrature_models=['W1'],L2_unresolved_sign_error=None,
            reference_uncertainty='Keep finite MCSE and uncertified quadrature limits; no invented true MSE',
            resamples=9999,interval='pointwise two-sided 95% BCa',minimum_eligible_repetitions=20,
            resampling_unit='whole original four-chain repetitions, shared within each model',
            degenerate_intervals=None,reference_shift='shared +/-2 MCSE sensitivity, not a confidence interval',
            diagnostics=['rank-normalized/folded Rhat','bulk ESS','tail ESS','available NUTS divergences'],
            fixed_budget_only=True,adaptive_precision_stopping=False),
        cache_allocation=allocation,
        execution_policy=dict(primary_order='frozen independent schedule stream within repetition blocks',
            cache_after='Primary batch terminated or explicitly retained interrupted, with native Job end proof',
            later_batches='Only after the preceding main/cache phases have no unvisited or active tasks',
            numerical_retry=False,infrastructure_retry='at most one explicit same-identity posterior retry; none for cache',
            resource_wait='stop at task boundary without relabeling not-run tasks as numerical failures',
            host_lock='one shared absolute native Windows lease, with active legacy/new cohorts reconciled',
            total_experiment_time_cutoff=None),
        cost_policy=dict(ordinary='separate ordinary process wall',research='independent audit plus external invocation history',
            cached='separate prepared-execution measurement using selected original repetitions',
            batch_overhead='preparation, archive, transfer and verification ledger; no arbitrary per-fit allocation',
            unknown_cost=None,failures_retained=True,nested_phases_additive=False),
        formal_inputs_generated=False,native_environment_frozen=False,sampling_allowed=False,
        formal_inference_complete=False)
    plan['design_sha256']=fingerprint(plan)
    return plan


def validate_study_plan(plan,catalog):
    expected=create_study_plan(plan['identity'],catalog)
    if expected!=plan:raise ValueError('Complete scientific plan differs from the approved v0.2 frame')
    validate_measurement_plan(plan['cache_allocation'],plan['tasks'])
    return plan


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--identity',required=True)
    p.add_argument('--catalog',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError('No plan overwrite')
    plan=create_study_plan(a.identity,json.loads(a.catalog.read_text()))
    validate_study_plan(plan,json.loads(a.catalog.read_text()));atomic_json(a.output,plan)
    print(json.dumps(dict(design_sha256=plan['design_sha256'],catalog_file_sha256=file_hash(a.catalog),
        main_tasks=len(plan['tasks']),cache_probes=len(plan['cache_allocation']['probes']),inputs=len(plan['input_requirements']),
        sampling_allowed=False,formal_inference_complete=False),indent=2))
