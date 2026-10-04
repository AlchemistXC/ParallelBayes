"""Freeze and execute an existing-reference audit with lossless R transport."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile
import numpy as np
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'r-package/inst/python'))
sys.path.insert(0, str(ROOT / 'examples'))
from external_wells import load_wells, make_wells, propriety_certificate

SPEC = ROOT / 'benchmark/protocols/wells-reference-audit-v1.json'
DRAW_PATH = 'posterior_database/reference_posteriors/draws/draws/wells_data-wells_dist100_model.json.zip'
INFO_PATH = 'posterior_database/reference_posteriors/draws/info/wells_data-wells_dist100_model.info.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def map_draws(raw, spec):
    """Explicit names and preserved chain order; dictionary order is immaterial."""
    names = spec['parameter_names']
    if not isinstance(raw, list) or len(raw) != spec['chains']:
        raise ValueError('Unexpected chain count')
    if any(set(chain) != set(names) for chain in raw):
        raise ValueError('Reference parameter names differ')
    draws = np.asarray([[chain[name] for name in names] for chain in raw], dtype=np.float64)
    if draws.shape != (spec['chains'], 2, spec['stored_draws_per_chain']) or not np.isfinite(draws).all():
        raise ValueError('Reference dimensions or finite values differ')
    # Returned coordinates: iteration, chain, parameter; no chain flattening.
    draws = draws.transpose(2, 0, 1)
    a, b = draws[..., 0], draws[..., 1]
    values = np.stack([a, b, a*a, b*b, expit(a), expit(a+b), (b > 0).astype(float)], axis=-1)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite derived estimand')
    return draws, values


def freeze(output):
    if output.exists():
        raise FileExistsError('Preserve previous analysis lock')
    spec = json.loads(SPEC.read_text())
    # Analysis must be tied to committed bytes, without requiring unrelated
    # documentation to be clean. This does not call any sampling implementation.
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    sources = {}
    for name in spec['source_files']:
        committed = subprocess.check_output(['git', 'show', commit + ':' + name], cwd=ROOT)
        if (ROOT / name).read_bytes() != committed:
            raise ValueError('Commit analysis code before freezing: ' + name)
        sources[name] = sha(ROOT / name)
    output.parent.mkdir(parents=True, exist_ok=True)
    write(output, dict(identity=spec['identity'], source_commit=commit, sources=sources))
    print(json.dumps(dict(lock=str(output), sha256=sha(output), source_commit=commit)))


def run(source, lock, output, rscript):
    if output.exists():
        raise FileExistsError('Preserve prior analysis; select a fresh directory')
    if source == output or source in output.parents:
        raise ValueError('Do not write into the upstream source cache')
    frozen = json.loads(lock.read_text())
    spec = json.loads(SPEC.read_text())
    if frozen['identity'] != spec['identity'] or set(frozen['sources']) != set(spec['source_files']):
        raise ValueError('Unexpected lock identity/source list')
    for name, digest in frozen['sources'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Frozen analysis source changed: ' + name)
    data = load_wells(source)  # All eight pinned source hashes, not only draws.
    certificate = propriety_certificate(data)
    if not certificate['certified']:
        raise ValueError('Expected exact-target integrability certificate is absent')
    upstream = json.loads((source / INFO_PATH).read_text())
    with zipfile.ZipFile(source / DRAW_PATH) as archive:
        raw = json.loads(archive.read('wells_data-wells_dist100_model.json'))
    draws, values = map_draws(raw, spec)
    output.mkdir(parents=True)
    write(output / 'started.json', dict(identity=spec['identity'], lock_sha256=sha(lock),
          source_commit=frozen['source_commit'], python_version=platform.python_version(),
          numpy_version=np.__version__, target_id=make_wells(data).target_id))
    (output / 'analysis-lock.json').write_bytes(lock.read_bytes())
    write(output / 'array.json', dict(dimensions=list(values.shape), variables=spec['functions'],
          batch_length=spec['batch_length_stored_draws'], posterior_version=spec['posterior_version']))
    binary = output / 'values-f64le.bin'
    binary.write_bytes(values.astype('<f8').ravel(order='F').tobytes())
    receipt = dict(status='failed', scope=spec['scope'])
    try:
        process = subprocess.run([rscript, '--vanilla', str(ROOT / 'scripts/completion/wells_reference_audit.R'),
                                  str(output)], capture_output=True, text=True)
        (output / 'R.log').write_text(process.stdout + process.stderr)
        receipt['R_exit_code'] = process.returncode
        if process.returncode:
            raise RuntimeError('R reference audit failed; inspect R.log')
        if binary.read_bytes() != (output / 'roundtrip-f64le.bin').read_bytes():
            raise ValueError('R binary transport changed bytes')
        diagnostics = json.loads((output / 'diagnostics.json').read_text())
        if diagnostics['dimensions'] != list(values.shape) or [r['variable'] for r in diagnostics['summary']] != spec['functions']:
            raise ValueError('R dimensions or function order changed')
        upstream_diag = upstream['diagnostics']
        if upstream_diag['diagnostics_information']['names'] != spec['parameter_names']:
            raise ValueError('Upstream diagnostic parameter mapping differs')
        comparisons = []
        for k, row in enumerate(diagnostics['summary'][:2]):
            comparisons.append(dict(parameter=spec['parameter_names'][k],
                rhat_local=row['rhat'], rhat_upstream=upstream_diag['r_hat'][k],
                rhat_difference=row['rhat']-upstream_diag['r_hat'][k],
                ess_bulk_local=row['ess_bulk'], ess_bulk_upstream=upstream_diag['effective_sample_size_bulk'][k],
                ess_tail_local=row['ess_tail'], ess_tail_upstream=upstream_diag['effective_sample_size_tail'][k]))
        receipt.update(status='completed', source_commit=frozen['source_commit'],
            upstream_commit=spec['upstream_commit'], reference_zip_sha256=sha(source / DRAW_PATH),
            target_id=make_wells(data).target_id, raw_shape=list(draws.shape),
            functions=spec['functions'], additional_discard=0, binary_roundtrip_identical=True,
            binary_sha256=sha(binary), replication=spec['replication'],
            propriety_certificate=certificate, upstream_diagnostic_comparison=comparisons,
            upstream_generation=upstream['inference'], upstream_divergences_reported=upstream_diag['divergent_transitions'],
            upstream_divergences_independently_recomputed=False,
            reference_uncertainty=spec['reference_uncertainty'],
            all_functions_uncertainty_available=all(r['uncertainty_status'] != 'undetermined' for r in diagnostics['summary']),
            torch_imported='torch' in sys.modules, jax_imported='jax' in sys.modules)
    except Exception as error:
        receipt['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        write(output / 'receipt.json', receipt)
        write(output / 'checksums.json', {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != 'checksums.json'})
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    f = sub.add_parser('freeze'); f.add_argument('--output', type=Path, required=True)
    r = sub.add_parser('run')
    r.add_argument('--source', type=Path, required=True)
    r.add_argument('--lock', type=Path, required=True)
    r.add_argument('--output', type=Path, required=True)
    r.add_argument('--rscript', default='Rscript')
    a = p.parse_args()
    if a.action == 'freeze':
        freeze(a.output.resolve())
    else:
        run(a.source.resolve(), a.lock.resolve(), a.output.resolve(), a.rscript)
