"""A pooled exact mean must not conceal a path that never crosses the boundary."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts/analysis'))
from review_mixture_paths import path_metrics


def test_balanced_stuck_chains_have_zero_pooled_loss_and_zero_crossings():
    start = np.array([-6., -5., 5., 6.])
    states = np.repeat(start[:, None], 8, axis=1)
    r = path_metrics(start, states, 2, states[:, 2:] > 0)
    assert r['pooled_positive_fraction'] == .5 and r['pooled_squared_error'] == 0
    assert r['all_saved_sign_crossings'] == [0, 0, 0, 0]
    assert r['retained_positive_fraction'] == [0, 0, 1, 1]


def test_initial_and_warmup_crossings_separate_from_retained_crossings():
    start = np.array([-6., -5., 5., 6.])
    states = np.array([[1., -1., 1., 1.], [-1., -1., -1., -1.],
                       [1., 1., -1., 1.], [1., 1., 1., 1.]])
    r = path_metrics(start, states, 2, states[:, 2:] > 0)
    assert r['all_saved_sign_crossings'] == [3, 0, 2, 0]
    assert r['retained_sign_crossings'] == [0, 0, 1, 0]


def test_archived_event_mismatch_is_not_silently_recomputed():
    x = np.ones((4, 3)); event = x > 0; event[0, 0] = False
    with pytest.raises(ValueError, match='archived sign'):
        path_metrics(np.ones(4), x, 0, event)


def test_nonfinite_path_and_empty_retained_path_are_rejected():
    x = np.ones((4, 3)); x[0, 0] = np.nan
    with pytest.raises(ValueError, match='Invalid'):
        path_metrics(np.ones(4), x, 0, x > 0)
    with pytest.raises(ValueError, match='Invalid'):
        path_metrics(np.ones(4), np.ones((4, 3)), 3, np.ones((4, 0)))
