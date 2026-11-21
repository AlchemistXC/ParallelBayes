"""Proposed test-only key vectors. Run from any directory in the candidate venv."""
import hashlib
import json
import os
from pathlib import Path

os.environ["JAX_PLATFORMS"] = "cpu"
os.environ["JAX_ENABLE_X64"] = "true"
import jax
from jax import random

jax.config.update("jax_threefry_partitionable", True)
here = Path(__file__).resolve().parent
seed = 20261121
phases = {"initialization": 1, "warmup": 2, "sampling": 3}
models = {"logistic": 1, "ode": 2}
mask = 0xffffffff


def threefry(key, counter):
    keys = (*key, 0x1BD11BDA ^ key[0] ^ key[1])
    a, b = (counter[0] + keys[0]) & mask, (counter[1] + keys[1]) & mask
    rotations = (13, 15, 26, 6, 17, 29, 16, 24)
    for r in range(20):
        a = (a + b) & mask
        n = rotations[r % len(rotations)]
        b = (((b << n) & mask) | (b >> (32 - n))) ^ a
        if (r + 1) % 4 == 0:
            s = (r + 1) // 4
            a = (a + keys[s % 3]) & mask
            b = (b + keys[(s + 1) % 3] + s) & mask
    return (a, b)


def verify(key, expected):
    words = tuple(map(int, random.key_data(key)))
    assert words == expected, (words, expected)
    return words


root = random.key(seed, impl="threefry2x32")
root_words = verify(root, (0, seed))
rows = []
for name, model in models.items():
    for chain in (1, 2):
        for phase, tag in phases.items():
            k, ref = root, root_words
            for ident in (model, chain, tag):
                k, ref = random.fold_in(k, ident), threefry(ref, (0, ident))
            row = dict(model=name, chain=chain, phase=phase, initial_key=verify(k, ref))
            if phase == "sampling":
                row["transitions"] = []
                for step in range(1, 1002):
                    consumed, following = random.split(k, 2)
                    used_ref, next_ref = threefry(ref, (0, 0)), threefry(ref, (0, 1))
                    u, v = verify(consumed, used_ref), verify(following, next_ref)
                    if step in (1, 100, 101, 1000, 1001):
                        row["transitions"].append(dict(step=step, consumed=u, next_carry=v))
                    k, ref = following, next_ref
            rows.append(row)
out = dict(status="proposed-test-only", seed=seed, root=root_words, models=models, phases=phases,
           fold_order=["model", "chain", "phase"], split_order=["consumed", "next_carry"],
           jax=jax.__version__, backend=jax.default_backend(), prng="threefry2x32",
           partitionable=True, lock_sha256=hashlib.sha256((here.parent/"requirements-arm64.lock").read_bytes()).hexdigest(),
           rows=rows)
payload = (json.dumps(out, indent=2)+"\n").encode()
path = here/"vectors.json"
if path.exists() and path.read_bytes() != payload:
    raise ValueError("Existing reference vector file differs")
if not path.exists():
    path.write_bytes(payload)
print(hashlib.sha256(payload).hexdigest())
print(next(r for r in rows if r["phase"]=="sampling"))
