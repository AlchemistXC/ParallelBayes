"""Outer sequencing checks only; no native acceptance or statistical repeats."""
import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).resolve().parents[2]/'scripts/windows/sequence_formal_study.py'
spec = importlib.util.spec_from_file_location('formal_outer_sequence', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_prespecified_order():
    assert module.ORDER == ((0,'main'),(0,'cache'),(1,'main'),(1,'cache'),
                            (2,'main'),(2,'cache'),(3,'main'),(3,'cache'))


@pytest.mark.parametrize('phase,n', [('main',10368),('cache',2304)])
def test_closed_frame_can_retain_failures(phase,n):
    module.check_closed_summary(dict(batch=1,phase=phase,planned=n,visited=n,
        closed=True,counts={'numerical_failure':n}),1,phase)


@pytest.mark.parametrize('change', [dict(visited=10367),dict(closed=False),
                                   dict(batch=2),dict(phase='cache'),dict(planned=27)])
def test_incomplete_or_foreign_frame_cannot_advance(change):
    value=dict(batch=1,phase='main',planned=10368,visited=10368,closed=True)
    value.update(change)
    with pytest.raises(ValueError):module.check_closed_summary(value,1,'main')
