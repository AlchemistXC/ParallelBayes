"""Read-only reception of the second Windows return, with explicit host limits.

No sampling, timing comparison, tolerance relaxation or modification of returned
assets. Same-host transform equality and cross-host residuals stay separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import warnings
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/completion'), str(ROOT/'r-package/inst/python'), str(ROOT/'examples')]
from mechanism_runner import identity, sha, actual_hash


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def inside(root, name):
    p = Path(name)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('Unsafe evidence path')
    result = (root/p).resolve()
    if root.resolve() not in result.parents:
        raise ValueError('Evidence escaped root')
    return result


def protocol(path):
    p = read(path); unsigned = dict(p); digest = unsigned.pop('protocol_sha256')
    assert identity(unsigned) == digest
    for name, expected in p['source_files'].items():
        assert sha(inside(ROOT, name)) == expected, name
    return p


def audit(batch, prior_audits, output):
    from affine_target import affine_model
    from parallelbayes.reference import make_reference
    from external_wells import make_wells, load_wells
    from inference_estimands import evaluate
    batch, prior_audits, output = map(lambda p: Path(p).resolve(), (batch, prior_audits, output))
    if output.exists() or batch in output.parents:
        raise ValueError('Use a fresh output outside received evidence')
    # Hash all received files before and after, including failures and logs.
    before = {p.relative_to(batch).as_posix():sha(p) for p in batch.rglob('*') if p.is_file()}
    protocols = []
    for r in read(batch/'environment-preflight.json')['protocols']:
        p=protocol(ROOT/r['path'])
        assert p==read(inside(batch.parents[2],r['path']))
        assert p['protocol_sha256']==r['identity']
        protocols.append(p)
    small = ROOT/'benchmark/analysis/outputs/windows-completion-v2'
    for name, h in read(small/'SHA256.json').items():assert sha(inside(small,name)) == h
    commands = []
    for path in sorted((batch/'commands').glob('*/receipt.json')):
        r = read(path); assert sha(path.parent/'stdout-stderr.log') == r['log_sha256']
        assert r['source_commit'] == 'f5148ee39868a657809f400bf1755d083c744fc8'
        commands.append(dict(step=path.parent.name, exit_code=r['exit_code']))
    # This checks the saved before/after receipts against the actual return;
    # no --resume is executed on this different host.
    resumes = []
    assets = 0
    for name in ('nuts', 'mh-cpu', 'mh-cuda'):
        run = batch/(name+'-run'); old = read(batch/(name+'-before-resume.json'))
        current = {}
        for state_path in sorted(run.glob('*/state.json')):
            s = read(state_path); assert s['status'] in ('completed','failed')
            for f,h in s['assets'].items():assert sha(inside(state_path.parent,f)) == h; assets += 1
            for f in state_path.parent.rglob('*'):
                if f.is_file():current[f.relative_to(run).as_posix()] = sha(f)
        assert current == old['files']
        final=read(run/'summary.json')
        assert {k:v for k,v in old['summary'].items() if k not in ('newly_executed_targets','invocation_seconds')} == {k:v for k,v in final.items() if k not in ('newly_executed_targets','invocation_seconds')}
        assert final['newly_executed_targets'] == 0
        resumes.append(dict(run=name, immutable_terminal_files=len(current), newly_executed_targets=0))
    f1 = read(batch/'rhat-windows/result.json')
    assert f1['input']['fixture_sha256'] == sha(batch/'rhat-windows/roundtrip-f64le.bin') == sha(ROOT/'benchmark/fixtures/rhat-midpoint-v1/q2-f64le.bin')
    assert all(f1['checks'].values()) and f1['changed_rank_count'] == 5
    assert f1['centers_hex']['native_median'] == '0x1.7701bac434f11p-10'
    # Each NUTS comparison is one paired technical fixture, not two replicates.
    p = protocol(ROOT/'benchmark/protocols/nuts-native-readiness-windows-v1.json')
    specs = read(ROOT/'benchmark/protocols/windows-native-v1.json')['models']
    nuts = []; binary = []; transport = read(batch/'nuts-diagnostics/transport.json')
    records = {r['id']:r for r in transport['fits']}
    for item in p['targets']:
        run = batch/'nuts-run'/item['name']; state = read(run/'state.json')
        assert state['target'] == item and state['protocol_sha256'] == p['protocol_sha256']
        assert state['status'] == 'completed'
        attempt = run/state['attempt']
        with np.load(ROOT/'benchmark/fixtures/nuts-native-readiness-windows-v1'/item['input'],allow_pickle=False) as inp:
            initial=inp['initial'].copy(); seeds=inp['chain_seeds'].tolist()
            assert actual_hash(dict(inp)) == p['inputs'][item['input']]['actual_sha256']
        assert sha(ROOT/'benchmark/fixtures/nuts-native-readiness-windows-v1'/item['input']) == p['inputs'][item['input']]['sha256']
        with np.load(attempt/'serial/fit.npz',allow_pickle=False) as a, np.load(attempt/'parallel/fit.npz',allow_pickle=False) as b:
            keys=('draws','unconstrained','warmup_states','initial_torch_rng_states','final_torch_rng_states','initial')
            equal={k:a[k].shape==b[k].shape and a[k].dtype==b[k].dtype and a[k].tobytes()==b[k].tobytes() for k in keys}
            assert all(equal.values()) and np.array_equal(a['initial'], initial)
            assert a['draws'].shape==(4,p['draws'],item['dimension'])
            assert a['warmup_states'].shape==(4,p['warmup'],item['dimension'])
            assert all(np.isfinite(a[k]).all() for k in ('draws','unconstrained','warmup_states'))
            values=evaluate(dict(kind='external_wells_distance') if item['name']=='W1' else specs[item['name']],a['draws'])
            rebuilt=np.asarray(values['values'].transpose(1,0,2),dtype='<f8').ravel(order='F')
        for mode in ('serial','parallel'):
            meta=read(attempt/mode/'fit.json');assert meta['status']=='completed' and meta['chain_seeds']==seeds
            assert meta['target_id']==state['target_id']
            fit=records[item['name']+'-'+mode]; orig=batch/'nuts-diagnostics'/fit['input']
            assert sha(orig)==fit['input_sha256']==sha(orig.with_suffix(orig.suffix+'.roundtrip'))
            assert sha(attempt/mode/'fit.npz')==fit['source_raw_sha256']
            assert fit['names']==values['names']
            old=np.fromfile(orig,dtype='<f8');assert old.shape==rebuilt.shape
            binary.append(dict(id=fit['id'],transport_exact=True,
                local_functions_exact=old.tobytes()==rebuilt.tobytes(),
                local_function_max_abs_difference=float(np.max(np.abs(old-rebuilt)))))
        meta=read(attempt/'parallel/fit.json')
        assert meta['process_start_method']=='spawn' and len(set(meta['observed_worker_pids']))==4
        assert all(r['threads']==r['interop_threads']==1 for r in meta['worker_records'])
        # Valid full paths are stored once in the aggregate NPZ; each child
        # separately preserves metadata and adaptation traces, not duplicate paths.
        for r in meta['worker_records']:
            child=attempt/'parallel'/r['result_directory']
            childmeta=read(child/'metadata.json')
            assert childmeta['target_id']==state['target_id'] and childmeta['status']=='completed'
            assert childmeta['chain_seeds']==[seeds[r['chain']]]
            assert childmeta['warmup_per_chain']==p['warmup'] and childmeta['draws_per_chain']==p['draws']
            assert childmeta['max_tree_depth']==p['max_tree_depth'] and childmeta['full_mass']==p['full_mass']
            with np.load(child/'adaptation.npz',allow_pickle=False) as z:
                assert z['warmup_step_size'].shape==(p['warmup'],) and z['sample_step_size'].shape==(p['draws'],)
                assert all(np.isfinite(z[k]).all() and np.all(z[k]>0) for k in z.files)
                with np.load(attempt/'serial/fit.npz',allow_pickle=False) as serial:
                    for key in z.files:assert np.array_equal(z[key],serial[f"chain{r['chain']}_{key}"])
        nuts.append(dict(target=item['name'],six_arrays_exact=equal,workers=4))
    # Quantify, rather than relabel, failed cross-host exact-transform checks.
    mh=[];cross=[]
    pc=protocol(ROOT/'benchmark/protocols/selected-mh-readiness-windows-cpu-v1.json')
    for device in ('cpu','cuda'):
        strict=read(prior_audits/('mac-mh-'+device+'-audit')/'receipt.json')
        for item, check in zip(pc['targets'],strict['targets']):
            assert item['name']==check['name']
            base=make_wells(load_wells(batch/'wells-source')) if item['name']=='W1' else make_reference(specs[item['name']])
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                model=affine_model(base,item['geometry']['center'],item['geometry']['factor'])
            run=batch/('mh-'+device+'-run')/item['name'];state=read(run/'state.json')
            for name,w in check['workflows'].items():
                with np.load(run/state['attempt']/(name+'.npz'),allow_pickle=False) as z:
                    recomputed=model.constrain(z['unconstrained']); observed=z['draws']
                    delta=np.abs(recomputed-observed); denom=np.maximum(1.,np.abs(observed))
                    mh.append(dict(device=device,target=item['name'],workflow=name,
                        trajectory_within_frozen_tolerance=all(x<=y for x,y in zip(w['max_abs_path_error'],w['allowed_path_error'])),
                        acceptance_mismatches=sum(w['acceptance_mismatches']),
                        original_exact_output_check=w['original_outputs_value_exact'],
                        output_unequal_elements=int(np.sum(recomputed!=observed)),
                        output_max_abs_difference=float(delta.max()),
                        output_max_scaled_difference=float(np.max(delta/denom)),
                        geometry_warnings=[str(v.message) for v in caught]))
                if device=='cpu':
                    other=batch/'mh-cuda-run'/item['name'];s=read(other/'state.json')
                    with np.load(run/state['attempt']/(name+'.npz'),allow_pickle=False) as a,np.load(other/s['attempt']/(name+'.npz'),allow_pickle=False) as b:
                        err=np.max(np.abs(a['unconstrained']-b['unconstrained']),axis=(1,2))
                        limit=100*(pc['atol']+pc['rtol']*np.maximum(1,np.max(np.abs(a['unconstrained']),axis=(1,2))))
                        events=int(np.sum(a['accept']!=b['accept']))
                        cross.append(dict(target=item['name'],workflow=name,passed=bool(np.all(err<=limit) and events==0),max_abs_path_difference=float(err.max()),acceptance_mismatches=events))
    after={p.relative_to(batch).as_posix():sha(p) for p in batch.rglob('*') if p.is_file()}
    assert before==after
    output.mkdir(parents=True)
    # Recompute R on the *received* binary values, keeping Windows results intact.
    diagnostics=output/'same-binary-mac-diagnostics';diagnostics.mkdir()
    shutil.copyfile(batch/'nuts-diagnostics/transport.json',diagnostics/'transport.json')
    for fit in transport['fits']:shutil.copyfile(batch/'nuts-diagnostics'/fit['input'],diagnostics/fit['input'])
    result=dict(scope='Independent reception; no new MCMC or statistical repetitions. Cross-host exact transform failures retained without relaxing their checks.',
        receiver_source_sha256=sha(Path(__file__)),receiver_python=sys.version,receiver_numpy=np.__version__,
        source_commit=read(batch/'commands/environment-preflight/receipt.json')['source_commit'],
        protocol_identities=[p['protocol_sha256'] for p in protocols],raw_assets_verified=assets,
        received_files_unchanged=len(before),curated_files_verified=len(read(small/'SHA256.json')),
        commands=commands,resume_evidence=resumes,F1=dict(native_median=f1['centers_hex']['native_median'],rhat=f1['rhat'],changed_ranks=5),
        NUTS=nuts,NUTS_binary=binary,MH=mh,cross_device_pairs=cross,
        Windows_same_host_MH_passed=all(read(batch/('mh-'+d+'-audit')/'receipt.json')['saved_array_replay_passed'] for d in ('cpu','cuda')),
        Mac_strict_MH_audit_passed=all(read(prior_audits/('mac-mh-'+d+'-audit')/'receipt.json')['saved_array_replay_passed'] for d in ('cpu','cuda')),
        new_MCMC_fits=0,formal_inference_complete=False)
    (output/'receipt.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('batch','prior-audits','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=audit(a.batch,a.prior_audits,a.output)
    print(json.dumps({k:v for k,v in r.items() if k not in ('commands','NUTS','NUTS_binary','MH','cross_device_pairs')},indent=2))
