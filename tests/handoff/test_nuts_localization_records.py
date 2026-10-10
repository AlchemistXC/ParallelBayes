from pathlib import Path
import json
import random
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/followups'))
from nuts_events import ChainRecorder,sha
from nuts_instrumented_worker import require_windows,rng_snapshot,restore_rng


def test_chunks_survive_partial_chain_and_do_not_consume_rng(tmp_path):
    np.random.seed(42);random.seed(43);before_numpy=np.random.get_state();before_py=random.getstate()
    r=ChainRecorder(tmp_path,0,3,8,block=2)
    for i in range(3):r.hook('Warmup',i,np.array([i,i+1.]),.1)
    for i in range(3):r.hook('Sample',i,np.array([i,-i]),.1)
    r.partial();events=[json.loads(x) for x in (tmp_path/'events.ndjson').read_text().splitlines()]
    assert any(x['event']=='warmup_completed' for x in events)
    assert not any(x['event']=='sample_completed' for x in events)
    assert np.array_equal(np.load(tmp_path/'sample-000002-000003.npy'),[[2,-2]])
    for p in tmp_path.glob('*.npy'):assert sha(p)==json.loads(p.with_suffix('.json').read_text())['sha256']
    assert random.getstate()==before_py
    now=np.random.get_state();assert now[0]==before_numpy[0] and np.array_equal(now[1],before_numpy[1]) and now[2:]==before_numpy[2:]


def test_original_attempt_and_invalid_state_are_not_overwritten(tmp_path):
    r=ChainRecorder(tmp_path,0,2,2)
    with pytest.raises(FileExistsError):ChainRecorder(tmp_path,0,2,2)
    with pytest.raises(ValueError):r.hook('Warmup',1,[0.],.1)
    with pytest.raises(ValueError):r.hook('Warmup',0,[np.nan],.1)


class FakeTensor:
    def __init__(self,x):self.x=list(x)
    def tolist(self):return list(self.x)
class FakeTorch:
    uint8='uint8'
    def __init__(self):self.x=[1,2,3]
    def get_rng_state(self):return FakeTensor(self.x)
    def set_rng_state(self,x):self.x=x.tolist()
    def tensor(self,x,**kwargs):return FakeTensor(x)


def test_actual_three_rng_states_are_restored_not_only_seeds():
    torch=FakeTorch();before=rng_snapshot(torch)
    np.random.normal(size=8);random.random();torch.x=[9,8,7]
    restore_rng(torch,before)
    assert rng_snapshot(torch)==before


def test_mac_cannot_claim_native_execution():
    if sys.platform=='win32':return
    with pytest.raises(RuntimeError,match='Native Windows'):require_windows()
