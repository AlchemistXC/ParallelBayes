"""Formal actual-input contract: no target/repetition alias, stable prefixes."""
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_formal_inputs_separate_target_repetition_and_keep_each_chain_prefix():
    from formal_inputs import build_payload, stream_address, validate_addresses
    # These two addresses collide in the historical offset=100*target+rep
    # formula (L1 index3, L2 index4), despite being different experiments.
    a=build_payload('formal-unit','L1',100,8,7,chains=4)
    b=build_payload('formal-unit','L2',0,8,7,chains=4)
    assert not np.array_equal(a['noise'],b['noise'])
    assert not np.array_equal(a['initial'],b['initial'])
    longer=build_payload('formal-unit','L1',100,8,19,chains=4)
    for name in ['noise','directions','log_uniform']:
        np.testing.assert_array_equal(a[name],longer[name][:,:7])
    for name in ['initial','nuts_seeds']:
        np.testing.assert_array_equal(a[name],longer[name])
    replay=build_payload('formal-unit','L1',100,8,7,chains=4)
    assert all(a[k].tobytes()==replay[k].tobytes() for k in a)
    models=['G1','G2','A1','L1','L2','H1','H2','M1','W1']
    receipt=validate_addresses('formal-unit',models,range(256),chains=4)
    assert receipt['distinct_stream_addresses']==9*256*4*5
    assert receipt['distinct_nuts_seeds']==9*256*4
    assert stream_address('formal-unit','L1',100,'noise',0)!=stream_address('formal-unit','L2',0,'noise',0)
    mixture=build_payload('formal-unit','M1',0,8,3,chains=4)
    np.testing.assert_array_equal(mixture['initial'][:,0],[-5,5,-5,5])


def test_formal_nuts_seeds_respect_frozen_uint32_provider_contract():
    from formal_inputs import build_payload
    payload=build_payload('formal-seed-contract','G1',0,8,4,chains=4)
    # inference_nuts.sample_nuts and Pyro/NumPy accept uint32 seeds.
    assert all(0 <= int(seed) < 2**32 for seed in payload['nuts_seeds'])
    assert len(set(payload['nuts_seeds'].tolist())) == 4
