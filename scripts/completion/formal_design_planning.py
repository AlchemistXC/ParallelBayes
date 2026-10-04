"""Saved-pilot planning companion; no sampler calls or executable protocol.

Rebuilds finite-grid resource arithmetic and reference-eligibility corrections
without changing historical CSVs. Output must be a new directory.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess

from scipy.stats import binomtest

from formal_error_summary import summarize
from formal_inputs import validate_addresses

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / 'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis'
PROTOCOL = ROOT / 'benchmark/protocols/inference-budget-pilot-mac-v1.json'
BUDGETS = [256, 1024, 4096, 16384]
CANDIDATES = [32, 64, 96, 128, 192, 256]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def resources(n, dimensions, functions):
    """All-success logical array bytes under the draft storage contract."""
    c = 4
    m = len(dimensions)
    d = sum(dimensions)
    f = sum(functions)
    mh_steps = sum(b + 512 for b in BUDGETS)
    nuts_steps = sum(b + 1024 for b in BUDGETS)
    longest = max(BUDGETS) + 512
    parts = {
        'master_noise_uniform_directions': n*c*longest*(2*d+m)*8,
        'master_initial_and_nuts_seeds': n*c*(d+m)*8,
        'mh_two_coordinate_paths': n*c*d*mh_steps*8*8*2,
        'mh_accept_and_primary_accept': n*c*m*mh_steps*8*2,
        'nuts_two_retained_paths_and_one_warmup_path': n*c*d*(2*sum(BUDGETS)+1024*len(BUDGETS))*8,
        'nuts_warmup_and_sample_step_sizes': n*c*m*nuts_steps*8,
        'R_function_binary_and_roundtrip': n*c*f*sum(BUDGETS)*9*8*2,
    }
    return dict(repetitions=n, planned_fits=m*len(BUDGETS)*9*n,
        planned_mh_fits=m*len(BUDGETS)*8*n, planned_nuts_fits=m*len(BUDGETS)*n,
        bytes_by_component=parts, logical_bytes=sum(parts.values()),
        logical_gib=sum(parts.values())/2**30,
        master_input_gib=(parts['master_noise_uniform_directions']+parts['master_initial_and_nuts_seeds'])/2**30,
        legacy_last_prefix_path_cache_gib=n*c*d*(8*longest+max(BUDGETS))*8/2**30,
        mh_chain_transitions=n*c*m*mh_steps*8,
        nuts_chain_updates=n*c*m*nuts_steps,
        retained_draws=n*c*m*sum(BUDGETS)*9,
        scope='Logical uncompressed array payload, all tasks successful. Not compressed disk use, RSS, or runtime. Excludes JSON/logs, independent audit workspaces, metadata, failed partial output, archive/extraction copies and filesystem overhead.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Use a new companion directory; never overwrite previous evidence')
    inputs = [ANALYSIS/name for name in ['function-errors.csv', 'function-estimates.json', 'reference-contract.json', 'tasks.csv']]
    manifest = json.loads((ANALYSIS/'manifest.json').read_text())
    before = {str(p.relative_to(ROOT)): sha(p) for p in inputs+[PROTOCOL]}
    for path in inputs:
        if manifest.get(path.name) != sha(path):
            raise ValueError(f'Frozen analysis hash mismatch: {path.name}')
    p = json.loads(PROTOCOL.read_text())
    rows = read_csv(ANALYSIS/'function-errors.csv')
    tasks = read_csv(ANALYSIS/'tasks.csv')
    estimates = json.loads((ANALYSIS/'function-estimates.json').read_text())
    references = json.loads((ANALYSIS/'reference-contract.json').read_text())
    assert len(rows) == 324 and len(tasks) == 324
    assert len({x['id'] for x in tasks}) == 324
    projected = [int(x['planning_repetitions_relative_25pct']) for x in rows if x['planning_repetitions_relative_25pct']]
    missing = {'uncertified_reference': 0, 'unresolved_reference': 0, 'failed_repetition': 0, 'constant_or_zero_loss': 0}
    for row in rows:
        if row['planning_repetitions_relative_25pct']:
            continue
        if row['reference_adequacy'] == 'numerical_uncertified': key = 'uncertified_reference'
        elif row['reference_adequacy'] == 'unresolved': key = 'unresolved_reference'
        elif int(row['failed_or_unavailable']): key = 'failed_repetition'
        else: key = 'constant_or_zero_loss'
        missing[key] += 1
    # For m nonnegative observations, sample_sd/mean <= sqrt(m). At
    # m=4 the plug-in normal-approximation formula cannot exceed 246.
    structural_limit = math.ceil((1.96*math.sqrt(4)/.25)**2)
    assert structural_limit == 246 and max(projected) <= structural_limit
    candidate_rows = []
    dims = [x['dimension'] for x in p['targets']]
    funcs = [len(references[x['name']]['names']) for x in p['targets']]
    for n in CANDIDATES:
        zero = binomtest(0, n).proportion_ci(confidence_level=.95, method='exact')
        half = binomtest(n//2, n).proportion_ci(confidence_level=.95, method='exact')
        r = resources(n, dims, funcs)
        r.update(pilot_projected_cells_at_or_below_n=sum(x <= n for x in projected),
                 legacy_target_rep_entries=len(dims)*n,
                 legacy_unique_offsets=len({100*i+j for i in range(len(dims)) for j in range(n)}),
                 zero_failures_two_sided_95pct_cp_upper=float(zero.high),
                 half_failures_two_sided_95pct_cp_width=float(half.high-half.low))
        candidate_rows.append(r)
    corrections = []
    for old in rows:
        if old['reference_adequacy'] != 'unresolved':
            continue
        name = old['model']; ref = references[name]; index = ref['names'].index(old['function'])
        matching = sorted([x for x in tasks if x['model'] == name and x['workflow'] == old['workflow'] and x['budget'] == old['budget']], key=lambda x: int(x['replicate']))
        assert [int(x['replicate']) for x in matching] == list(range(4))
        xs = [estimates[x['id']][index] if x['function_status'] == 'completed' else None for x in matching]
        new = summarize(xs, dict(kind=ref['kinds'][index], value=ref['means'][index], mcse=ref['mcse'][index]))
        corrections.append(dict(model=name, workflow=old['workflow'], budget=int(old['budget']), function=old['function'],
            task_ids=[x['id'] for x in matching], observed_estimates=xs,
            historical_conditional_squared_discrepancy=float(old['conditional_squared_discrepancy']),
            historical_standard_error=float(old['squared_discrepancy_standard_error']), corrected_companion=new))
    assert len(corrections) == 9
    assert all(x['corrected_companion']['conditional_squared_discrepancy'] is None for x in corrections)
    models = [x['name'] for x in p['targets']]
    address_check = validate_addresses('formal-design-planning-v0.1-not-sampling', models, range(256), chains=4)
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--', 'scripts/completion/formal_design_planning.py', 'scripts/completion/formal_inputs.py', 'scripts/completion/formal_error_summary.py'], cwd=ROOT, text=True)
    if dirty:
        raise ValueError('Commit the three analysis/input helpers before durable analysis')
    assert before == {str(path.relative_to(ROOT)): sha(path) for path in inputs+[PROTOCOL]}
    output.mkdir(parents=True)
    dump(output/'planning.json', dict(identity='formal-design-planning-v0.1', source_commit=source,
        new_mcmc_fits=0, executable_protocol=False, formal_launch_authorized_by_this_file=False,
        inputs_sha256=before, input_manifest_sha256=sha(ANALYSIS/'manifest.json'),
        old_protocol_identity=p['identity'], old_protocol_sha256=p['protocol_sha256'],
        draft_budgets=BUDGETS, target_count=len(dims), dimension_sum=sum(dims), function_sum=sum(funcs),
        pilot_function_groups=len(rows), pilot_defined_projections=len(projected), pilot_unprojectable=missing,
        pilot_projection_structural_upper=structural_limit,
        projection_warning='246 is forced by four nonnegative losses, not evidence that n=256 achieves desired precision. Counts are dependent pilot cells, not probabilities.',
        selected_draft_repetitions=128, candidates=candidate_rows, new_address_check=address_check,
        uncertainty_scope='Clopper-Pearson intervals are per-cell iid Bernoulli failure summaries, not simultaneous study coverage, sampler correctness, or a guarantee of MSE precision.'))
    dump(output/'unresolved-reference-companion.json', dict(source_commit=source,
        historical_files_unchanged=True, new_mcmc_fits=0, corrections=corrections,
        rule='Observed zero events retained; unresolved references never yield numerical loss, error standard error, or all-functions accuracy. This accompanies, never replaces, frozen pilot reports.'))
    dump(output/'manifest.json', {x.name:sha(x) for x in sorted(output.iterdir()) if x.is_file()})
    print(json.dumps(dict(source_commit=source, candidate_designs=len(candidate_rows), corrected_unresolved_rows=len(corrections), new_mcmc_fits=0, selected_draft_fits=resources(128,dims,funcs)['planned_fits'])))


if __name__ == '__main__':
    main()
