"""Analytical targets test quadrature and tail control independently of wells."""
import importlib.util
from pathlib import Path
import math
import numpy as np
import pytest
from scipy.special import ndtr

ROOT = Path(__file__).resolve().parents[2]


def module():
    s = importlib.util.spec_from_file_location('wells_quadrature', ROOT/'scripts/completion/audit_wells_quadrature.py')
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def test_gaussian_moments_and_rotated_half_plane_probability():
    m = module()
    center = np.array([0., -2.])
    scale = np.array([[1., 0.], [.8, .6]])
    precision = np.linalg.inv(scale@scale.T)
    logp = lambda q: -.5*np.einsum('bi,ij,bj->b', q-center, precision, q-center)
    result = m.integrate_box(logp, center, scale, 10, 96)
    assert result['normalizer_z_scaled'] == pytest.approx(2*math.pi, rel=2e-13)
    np.testing.assert_allclose(result['means'][:4], [0., -2., 1., 5.], rtol=2e-13, atol=1e-13)
    assert result['means'][6] == pytest.approx(ndtr(-2.), rel=2e-12)


def test_supporting_plane_tail_bound_encloses_exact_gaussian_radial_tail():
    m = module()
    r = 6.
    bound = m.tail_bounds(lambda q: -.5*(q@q), lambda q: -q, np.zeros(2), np.eye(2), r, 256)
    exact_mass = 2*math.pi*math.exp(-r*r/2)
    assert exact_mass <= bound['mass_z_scaled'] <= 1.06*exact_mass
    exact_second_moment_per_coordinate = math.pi*(r*r+2)*math.exp(-r*r/2)
    assert all(x >= exact_second_moment_per_coordinate for x in bound['absolute_moment_z_scaled'][2:])


def test_absent_tail_decay_is_a_failure_not_a_zero_tail_claim():
    with pytest.raises(ValueError, match='No finite'):
        module().tail_bounds(lambda q: 0., lambda q: np.zeros(2), np.zeros(2), np.eye(2), 6, 32)
