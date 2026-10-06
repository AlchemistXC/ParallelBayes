"""Independent, read-only NumPy replay of the October Windows return.

Run after archive/manifests and identities have passed their dedicated readers.
No random tape generation, sampler imports, device calls or performance reruns.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import sys
import time
import numpy as np


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def arrays(p):
    with np.load(p, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def relative(root, name):
    w = PureWindowsPath(name)
    parts = PurePosixPath(name.replace('\\', '/')).parts
    if w.drive or w.root or not parts or '..' in parts:
        raise ValueError('Invalid relative evidence name')
    result = root.joinpath(*parts).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError('Evidence path escapes root')
    return result


def tape_hash(tape):
    h = hashlib.sha256()
    for k in sorted(tape):
        a = np.ascontiguousarray(tape[k], dtype='<f8')
        h.update(k.encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def run(evidence, source, output):
    if output.exists():
        raise FileExistsError('Preserve prior reconstruction')
    if output.is_relative_to(evidence) or output.is_relative_to(source):
        raise ValueError('Do not write into evidence or source')
    sys.path.insert(0, str(source/'r-package/inst/python'))
    sys.path.insert(0, str(source/'examples'))
    from parallelbayes.reference import make_reference, numpy_reference
    from affine_target import affine_model
    assert 'torch' not in sys.modules and 'jax' not in sys.modules
    output.mkdir(parents=True)
    (output/'references').mkdir()
    reference_cache, records = {}, []

    def check(model, config, tape, metadata, raw, label):
        assert metadata['target_id'] == model.target_id
        assert metadata['tape_sha256'] == tape_hash(tape)
        initial = np.asarray(config['initial'], dtype=float)
        scientific = dict(target=model.target_id, initial=config['initial'], kernel=config['kernel'],
                          step_size=config['step_size'], tape=tape_hash(tape))
        key = hashlib.sha256(json.dumps(scientific, sort_keys=True).encode()).hexdigest()
        if key not in reference_cache:
            start = time.perf_counter()
            refs = [numpy_reference(model, config['kernel'], initial[i], tape['noise'][i],
                                    tape['log_uniform'][i], config['step_size'])
                    for i in range(config['chains'])]
            q, a = np.stack([r[0] for r in refs]), np.stack([r[1] for r in refs])
            path = output/'references'/(key+'.npz')
            np.savez_compressed(path, unconstrained=q, accept=a)
            reference_cache[key] = dict(q=q, a=a, seconds=time.perf_counter()-start,
                                        sha256=sha(path), specification=scientific)
        ref = reference_cache[key]
        path, accept = raw['unconstrained'], raw['accept']
        assert path.shape == ref['q'].shape and accept.shape == ref['a'].shape
        assert np.isfinite(path).all() and accept.dtype == np.dtype(bool)
        errors = np.max(np.abs(path-ref['q']), axis=(1, 2))
        limits = 100*(config['atol'] + config['rtol']*np.maximum(1, np.max(np.abs(path), axis=(1, 2))))
        mismatches = np.count_nonzero(accept != ref['a'])
        transformed = np.asarray(model.constrain(path))
        constrained_error = float(np.max(np.abs(model.constrain(ref['q'])-transformed)))
        output_difference = None if 'draws' not in raw else float(np.max(np.abs(raw['draws']-transformed)))
        passed = bool(np.all(errors <= limits) and mismatches == 0)
        row = dict(label=label, reference_key=key, passed=passed, path_bitwise=bool(np.array_equal(path,ref['q'])),
            maximum_path_error=float(errors.max()), maximum_error_over_frozen_limit=float(np.max(errors/limits)),
            acceptance_mismatches=int(mismatches), maximum_constrained_reference_error=constrained_error,
            saved_output_transform_maximum_difference=output_difference,
            saved_output_transform_bitwise=None if output_difference is None else output_difference == 0,
            acceptance_fraction=float(accept.mean()), transitions=int(accept.size))
        records.append(row)
        if not passed:
            raise ValueError('Independent path/event verification failed: '+label)

    mechanism=evidence/'mechanism/output/completion/windows-mechanism-original-attempt01'
    plan=read(source/'benchmark/protocols/mechanism-windows-pilot-v1.json')
    for device in ('cpu','cuda'):
        runroot=mechanism/('mechanism-'+device)
        for group in plan['groups']:
            folder=runroot/'groups'/group['id'];state=read(folder/'state.json')
            assert state['status']=='completed'
            attempt=relative(folder,state['attempt']);tape=arrays(attempt/'inputs.npz')
            model=make_reference(plan['models'][group['model']])
            for record in state['records']:
                meta=read(relative(attempt,record['record']))
                raw=arrays(relative(attempt,record['raw']))
                check(model,meta['config'],tape,meta,raw,
                      'mechanism/'+device+'/'+group['id']+'/'+record['raw'])
        print('Replayed mechanism '+device,flush=True)

    runtime=evidence/'runtime/output/windows-runtime-technical-v1'
    protocol=read(runtime/'protocol.json');cache_protocol=read(runtime/'cache-protocol.json')
    base_models=read(runtime/'source/benchmark/protocols/windows-native-v1.json')['models']
    targets={}
    for t in protocol['targets']:
        base=make_reference(base_models[t['name']])
        assert base.target_id==t['base_target_id']
        targets[t['name']]=affine_model(base,t['geometry']['center'],t['geometry']['factor'])
    for phase,p in [('main',protocol),('cache',cache_protocol)]:
        for task in p['tasks']:
            if task['kernel']=='nuts':
                continue
            model=targets[task['model']];master=arrays(runtime/'inputs'/task['input'])
            n=task['budget']+p['controls']['mh_discard']
            tape={k:master[k][:,:n] for k in ('noise','log_uniform','directions')}
            attempt=runtime/phase/'tasks'/task['id']/'attempt-0001'
            if phase=='main':
                paths=[attempt/'fit.json']
            else:
                binding=read(attempt/'cache/binding.json')
                assert binding['input_file_sha256']==sha(runtime/'inputs'/task['input'])
                paths=[attempt/'cache'/('execution-'+str(i)+'.json') for i in range(4)]
                assert all(path.is_file() for path in paths)
            for path in paths:
                meta=read(path);config=meta['config']
                assert np.array_equal(np.asarray(config['initial']),master['initial'])
                assert config['kernel']==task['kernel'] and config['executor']==task['executor']
                assert config['draws']==n and config['chains']==p['controls']['chains']
                check(model,config,tape,meta,arrays(path.with_suffix('.npz')),
                      'runtime/'+phase+'/'+task['id']+'/'+path.name)
        print('Replayed runtime '+phase,flush=True)
    assert 'torch' not in sys.modules and 'jax' not in sys.modules
    summary=dict(scope='Deterministic replay of archived actual arrays; no new inference repetitions or device timing',
        groups={phase:dict(records=len(rows),failed=sum(not r['passed'] for r in rows),
                           acceptance_mismatches=sum(r['acceptance_mismatches'] for r in rows),
                           maximum_path_error=max(r['maximum_path_error'] for r in rows),
                           maximum_error_over_frozen_limit=max(r['maximum_error_over_frozen_limit'] for r in rows))
                for phase in ('mechanism','runtime/main','runtime/cache')
                if (rows:=[r for r in records if r['label'].startswith(phase+'/')])},
        total_records=len(records),unique_reference_calculations=len(reference_cache),
        imported_sampler_backends=False,python=sys.version,numpy=np.__version__,
        reference_sha256=sha(source/'r-package/inst/python/parallelbayes/reference.py'),
        affine_sha256=sha(source/'examples/affine_target.py'),reader_sha256=sha(__file__),
        frozen_rule='zero accept mismatches and max_abs_error(chain) <= 100*(atol+rtol*max(1,maxabs(saved_chain)))',
        saved_transforms_reported_separately=True)
    for name,obj in [('summary',summary),('paths',records),('references',{
            k:{f:v for f,v in r.items() if f not in ('q','a')} for k,r in reference_cache.items()})]:
        (output/(name+'.json')).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence-root',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.evidence_root.resolve(),a.source_root.resolve(),a.output.resolve())
