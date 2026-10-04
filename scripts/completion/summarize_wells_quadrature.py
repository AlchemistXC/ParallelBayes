"""Rebuild the finite-reference/quadrature comparison from checked result files."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def checked(folder, name):
    checks = json.loads((folder/'checksums.json').read_text())
    data = (folder/name).read_bytes()
    if hashlib.sha256(data).hexdigest() != checks[name]:
        raise ValueError('Result checksum mismatch: '+name)
    return json.loads(data)


def summarize(quadrature, reference, output):
    if output.exists():
        raise FileExistsError('Preserve previous comparisons')
    if any(output == p or p in output.parents for p in [quadrature, reference]):
        raise ValueError('Do not write into source evidence directories')
    q = checked(quadrature, 'result.json')
    ref = checked(reference, 'receipt.json')
    diagnostic = checked(reference, 'diagnostics.json')
    if q['status'] != 'completed' or ref['status'] != 'completed' or q['target_id'] != ref['target_id']:
        raise ValueError('Different targets or incomplete results')
    if q['functions'] != [r['variable'] for r in diagnostic['summary']]:
        raise ValueError('Different function definitions/order')
    rows = {(r['radius'], r['order']): r for r in q['rows']}
    if len(q['rows']) != 12 or set(rows) != {(r,n) for r in [6,8,10,12] for n in [32,64,96]}:
        raise ValueError('Missing, duplicated or unexpected quadrature rules')
    selected = rows[12,96]
    changes = []
    for radius in [6,8,10,12]:
        means = np.array(rows[radius,96]['means'])
        changes.append(dict(radius=radius,
            max_continuous_change_64_to_96=float(np.max(np.abs(means[:6]-np.array(rows[radius,64]['means'])[:6]))),
            event_change_64_to_96=float(abs(means[6]-rows[radius,64]['means'][6])),
            event_probability=float(means[6]),
            tail_mass_over_computed_normalizer=rows[radius,96]['tail_mass_over_computed_normalizer']))
    comparisons = []
    for mean, r in zip(selected['means'], diagnostic['summary']):
        se = r['mcse_max_available']
        comparisons.append(dict(function=r['variable'], quadrature_mean=mean,
            MCMC_mean=r['mean'], MCMC_MCSE=se, difference_MCMC_minus_quadrature=r['mean']-mean,
            difference_in_reported_MCSE=(r['mean']-mean)/se if se else None,
            reference_uncertainty_status=r['uncertainty_status']))
    report = dict(status='completed', target_id=q['target_id'],
        input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                      [quadrature/'result.json', reference/'receipt.json', reference/'diagnostics.json']},
        source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        selected_radius=12, selected_order=96, comparisons=comparisons, convergence_changes=changes,
        all_finite_MCMC_functions_determined=ref['all_functions_uncertainty_available'],
        error_interpretation=q['error_interpretation'],
        limits=['Differences divided by estimated MCSE are descriptive, not z tests or coverage proofs.',
                'MCMC constant-event uncertainty and diagnostics remain undetermined.',
                'Tail control does not certify the interior quadrature or floating-point roundoff.',
                'No inference-precision gate or speed conclusion is supplied by this companion analysis.'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--quadrature', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a=p.parse_args(); summarize(a.quadrature.resolve(), a.reference.resolve(), a.output.resolve())
