#!/usr/bin/env python3
"""Replay saved v5 R paths against NumPy using hash-matched restored inputs.

The tape is restored independently from the recorded generator specification,
then accepted only if its actual-array digest equals the saved digest. This is
not seed-only comparison or a new independent random input. No JAX/torch import.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def audit(source, exported, evidence, output):
    source, exported, evidence, output = map(Path,(source,exported,evidence,output))
    if output.exists():
        raise FileExistsError('Use a new audit directory')
    output.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('v5_independent_reference',source/'r-package/inst/python/parallelbayes/reference.py')
    ref=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ref;spec.loader.exec_module(ref)
    raw=json.loads((exported/'EXPORT.json').read_text(encoding='utf-8'))
    if raw['posterior']!='1.7.0':
        raise ValueError('Use the recorded posterior version')
    checks=[]
    for row in raw['records']:
        if row['status']!='completed':
            if row['ordinary_samples'] is not False or row['confirmed']!=3848 or row['iterations']!=256:
                raise ValueError('Historical failed example qualification changed')
            checks.append(dict(id=row['id'],status='retained_failure',ordinary_samples=False))
            continue
        c=row['config'];shape=tuple(row['shape']);d=shape[2]
        rng=np.random.Generator(np.random.Philox(np.random.SeedSequence([c['seed'],101])))
        solver=np.random.Generator(np.random.Philox(np.random.SeedSequence([c['solver_seed'],102])))
        tape=dict(noise=rng.standard_normal(shape),
                  log_uniform=np.log(np.maximum(rng.random(shape[:2]),np.finfo(float).tiny)),
                  directions=(2*solver.integers(0,2,size=shape)-1).astype(float))
        h=hashlib.sha256()
        for key in sorted(tape):
            array=np.ascontiguousarray(tape[key],dtype='<f8')
            h.update(key.encode());h.update(str(array.shape).encode());h.update(array.tobytes())
        if h.hexdigest()!=row['tape_sha256']:
            raise ValueError('Restored actual random arrays differ from saved digest')
        np.savez_compressed(output/(row['id']+'-restored-inputs.npz'),**tape)
        model=ref.make_reference(row['spec'])
        if model.target_id!=row['target_id']:
            raise ValueError('Target identity differs')
        q=np.fromfile(exported/(row['id']+'.f64'),dtype='<f8').reshape(shape,order='F')
        events=np.fromfile(exported/(row['id']+'.u8'),dtype=np.uint8).reshape(shape[:2],order='F').astype(bool)
        errors=[];branches=[]
        for chain in range(shape[0]):
            initial=np.zeros(d) if c['initial'] is None else np.asarray(c['initial'])[chain]
            expected,accepted=ref.numpy_reference(model,c['kernel'],initial,
                tape['noise'][chain],tape['log_uniform'][chain],c['step_size'])
            errors.append(float(np.max(np.abs(q[chain]-expected))))
            branches.append(int(np.sum(events[chain]!=accepted)))
        limits=[100*(c['atol']+c['rtol']*max(1.,float(np.max(np.abs(p))))) for p in q]
        if any(branches) or any(e>t for e,t in zip(errors,limits)):
            raise ValueError('Saved completed trajectory fails independent check')
        checks.append(dict(id=row['id'],status='completed_verified',ordinary_samples=True,
            restored_tape_sha256=h.hexdigest(),max_abs_error=max(errors),
            acceptance_mismatches=sum(branches),limits=limits))
    final=json.loads((evidence/'r-example-v5-final/summary.json').read_text(encoding='utf-8'))
    observed=[r['diagnostics'] for r in raw['records'] if r['id'].startswith('r-example-v5-final')]
    comparisons=0
    for left,right in zip(observed,final['diagnostics']):
        if len(left)!=len(right):
            raise ValueError('Diagnostic variables changed')
        for a,b in zip(left,right):
            if a['variable']!=b['variable']:
                raise ValueError('Diagnostic variable order differs')
            for key in ('mean','sd','rhat','ess_bulk','ess_tail'):
                if not np.isclose(a[key],b[key],rtol=1e-12,atol=1e-12):
                    raise ValueError('Original final diagnostic differs: '+key)
                comparisons+=1
    forbidden=[name for name in ('jax','torch','blackjax','parallelbayes') if name in sys.modules]
    if forbidden:
        raise ValueError('Scientific implementation imported during independent replay')
    result=dict(passed=True,records=checks,final_diagnostic_values_matched=comparisons,
        reference_source_sha256=digest(source/'r-package/inst/python/parallelbayes/reference.py'),
        R_export_sha256=digest(exported/'EXPORT.json'),new_sampler_calls=0,
        new_independent_random_inputs=0,forbidden_backend_imports=forbidden,
        scope='Three previously saved completed technical paths replayed; one failure kept excluded. No new posterior fits or speed measurement.')
    (output/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','exported','evidence','output'):
        p.add_argument('--'+name,type=Path,required=True)
    audit(**vars(p.parse_args()))
