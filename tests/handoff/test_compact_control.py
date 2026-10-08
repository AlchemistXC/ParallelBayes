"""Administrative pause/resource interface, not a substitute for native Job tests."""
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/windows'),str(ROOT/'scripts/completion')]
from compact_control import request_pause,pause_pending,acknowledge_pause
from compact_batch import resource_guard
from formal_runtime import ResourceWait


def test_pause_request_preserved_and_wrong_identity_refused(tmp_path):
    h='1'*64;request=request_pause(tmp_path,h,'human resource amendment')
    original=(tmp_path/request['path']).read_bytes()
    assert pause_pending(tmp_path,h)['pointer']==request
    with pytest.raises(ValueError):pause_pending(tmp_path,'2'*64)
    acknowledge_pause(tmp_path,h,'new explicit continuation')
    assert pause_pending(tmp_path,h) is None
    assert (tmp_path/request['path']).read_bytes()==original


@pytest.mark.parametrize('ram,disk',[(1,100),(100,1)])
def test_low_resources_refused_before_dispatch(ram,disk):
    with pytest.raises(ResourceWait):resource_guard(ram,20,disk,20)
