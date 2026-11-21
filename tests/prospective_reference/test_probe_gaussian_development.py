from pathlib import Path
import sys

import numpy as np

sys.path.insert(0,str(Path(__file__).parent))
from probe_gaussian_development import stream


def test_probe_and_dummy_streams_are_separate_and_reproducible():
    seeds=np.random.SeedSequence(810431).spawn(2)
    a,b=stream(seeds[0],64,8),stream(seeds[1],256,8)
    repeated=stream(np.random.SeedSequence(810431).spawn(2)[0],64,8)
    for key in ('noise','log_uniform','directions'):
        assert np.array_equal(a[key],repeated[key])
        assert not np.shares_memory(a[key],b[key])
        assert not np.array_equal(a[key],b[key][:,:64])
    assert a['noise'].shape==(4,64,8) and b['noise'].shape==(4,256,8)
