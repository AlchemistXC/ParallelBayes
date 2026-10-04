"""Reference audit guards, without sampling or treating saved draws as truth."""
import importlib.util
import json
from pathlib import Path
import subprocess
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location('wells_reference_audit', ROOT/'scripts/completion/audit_wells_reference.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_parameter_names_and_chain_order_control_mapping():
    # Reversed JSON key order cannot swap the two scientific parameters.
    raw = [{'beta[1]': [-1, 0, 1], 'alpha': [0, 1, 2]},
           {'alpha': [3, 4, 5], 'beta[1]': [2, 1, 0]}]
    spec = dict(parameter_names=['alpha', 'beta[1]'], chains=2, stored_draws_per_chain=3)
    draws, values = module().map_draws(raw, spec)
    np.testing.assert_array_equal(draws[:, 0, 0], [0, 1, 2])
    np.testing.assert_array_equal(draws[:, 1, 1], [2, 1, 0])
    np.testing.assert_array_equal(values[:, 0, -1], [0, 0, 1])
    assert values[0, 0, 4] == .5
    assert values[0, 0, 5] == pytest.approx(1/(1+np.exp(1)))
    with pytest.raises(ValueError, match='parameter names'):
        module().map_draws([{'alpha': [1, 2, 3], 'beta': [1, 2, 3]}]*2, spec)


def test_nonfinite_reference_is_not_summarized_as_valid():
    raw = [{'alpha': [0., np.nan], 'beta[1]': [0., 1.]}]
    spec = dict(parameter_names=['alpha', 'beta[1]'], chains=1, stored_draws_per_chain=2)
    with pytest.raises(ValueError, match='finite'):
        module().map_draws(raw, spec)


def test_R_preserves_last_bits_chain_units_and_undetermined_constant_event(tmp_path):
    values = np.empty((100, 4, 2))
    for j in range(4):
        values[:, j, 0] = np.arange(100)/100. + j
        values[:, j, 1] = 0.
    values[0, 0, 0] = np.nextafter(0., 1.)
    b = values.astype('<f8').ravel(order='F').tobytes()
    (tmp_path/'values-f64le.bin').write_bytes(b)
    (tmp_path/'array.json').write_text(json.dumps(dict(dimensions=list(values.shape),
        variables=['alpha', 'constant_event'], batch_length=50, posterior_version='1.7.0')))
    process = subprocess.run(['Rscript', '--vanilla', str(ROOT/'scripts/completion/wells_reference_audit.R'),
                              str(tmp_path)], capture_output=True, text=True)
    assert process.returncode == 0, process.stdout+process.stderr
    assert (tmp_path/'roundtrip-f64le.bin').read_bytes() == b
    result = json.loads((tmp_path/'diagnostics.json').read_text())
    row, constant = result['summary']
    assert row['mcse_between_chains'] == pytest.approx(np.std(np.arange(4), ddof=1)/2)
    assert result['batch_count'] == 8
    assert constant['mean'] == 0 and constant['global_constant'] is True
    assert constant['uncertainty_status'] == 'undetermined'
    assert constant['rhat'] is None and constant['mcse_max_available'] is None
    assert constant['mcse_posterior'] is None
