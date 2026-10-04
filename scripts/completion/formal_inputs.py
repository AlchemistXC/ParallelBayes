"""Domain-separated actual inputs for a new formal experiment identity.

Addresses explicitly encode target, repetition, role and chain. No historical
offset arithmetic or frozen inputs are changed. Save payloads and their hashes
before sampling; unique addresses alone are not a proof of RNG independence.
"""
import hashlib
import numpy as np

MODEL_CODES={name:i+1 for i,name in enumerate(['G1','G2','A1','L1','L2','H1','H2','M1','W1'])}
ROLE_CODES={name:i+1 for i,name in enumerate(['initial','noise','uniform','direction','nuts'])}


def stream_address(experiment,model,replicate,role,chain):
    if not isinstance(experiment,str) or not experiment:
        raise ValueError('Explicit nonempty experiment identity required')
    if model not in MODEL_CODES or role not in ROLE_CODES:
        raise ValueError('Unknown target or random-input role')
    for value in [replicate,chain]:
        if isinstance(value,bool) or not isinstance(value,(int,np.integer)) or not 0<=value<2**32:
            raise ValueError('Nonnegative uint32 replicate/chain required')
    words=np.frombuffer(hashlib.sha256(experiment.encode('utf-8')).digest(),dtype='<u4')
    return (20261005,1,*map(int,words),MODEL_CODES[model],int(replicate),ROLE_CODES[role],int(chain))


def nuts_seed(experiment,model,replicate,chain):
    seq=np.random.SeedSequence(stream_address(experiment,model,replicate,'nuts',chain))
    return int(seq.generate_state(1,dtype=np.uint64)[0]) & ((1<<63)-1)


def build_payload(experiment,model,replicate,dimension,draws,chains=4):
    for value in [dimension,draws,chains]:
        if isinstance(value,bool) or not isinstance(value,(int,np.integer)) or value<1:
            raise ValueError('Positive dimensions/draws/chains required')
    # Guard construction itself; the formal runner must separately guard target
    # workspaces, process memory and disk. No full experiment is held in RAM.
    if chains*draws*(2*dimension+1)*8 > 2048*1024**2:
        raise MemoryError('Single actual-input payload exceeds 2048 MiB')
    def rng(role,ch):
        return np.random.Generator(np.random.Philox(np.random.SeedSequence(
            stream_address(experiment,model,replicate,role,ch))))
    initial=[];noise=[];uniform=[];directions=[];seeds=[]
    for ch in range(chains):
        q=2*rng('initial',ch).standard_normal(dimension)
        if model=='M1':q[0]=-5. if ch%2==0 else 5.
        initial.append(q)
        noise.append(rng('noise',ch).standard_normal((draws,dimension)))
        uniform.append(np.log(np.maximum(rng('uniform',ch).random(draws),np.finfo(float).tiny)))
        directions.append((2*rng('direction',ch).integers(0,2,size=(draws,dimension))-1).astype(float))
        seeds.append(nuts_seed(experiment,model,replicate,ch))
    return dict(initial=np.asarray(initial),noise=np.asarray(noise),log_uniform=np.asarray(uniform),
                directions=np.asarray(directions),nuts_seeds=np.asarray(seeds,dtype=np.int64))


def validate_addresses(experiment,models,replicates,chains=4):
    models=list(models);replicates=list(replicates)
    if len(set(models))!=len(models) or len(set(replicates))!=len(replicates):
        raise ValueError('Repeated target/replicate declaration')
    addresses=set();keys=set();seeds=set()
    for model in models:
        for rep in replicates:
            for ch in range(chains):
                for role in ROLE_CODES:
                    a=stream_address(experiment,model,rep,role,ch)
                    key=np.random.SeedSequence(a).generate_state(4,dtype=np.uint32).tobytes()
                    if a in addresses or key in keys:
                        raise ValueError('Declared random stream collision; use a new explicit protocol identity')
                    addresses.add(a);keys.add(key)
                s=nuts_seed(experiment,model,rep,ch)
                if s in seeds:
                    raise ValueError('NUTS seed collision; do not silently redraw')
                seeds.add(s)
    return dict(distinct_stream_addresses=len(addresses),distinct_seedsequence_keys=len(keys),
                distinct_nuts_seeds=len(seeds),
                scope='Finite address/key audit, not mathematical independence or a substitute for archived actual arrays')
