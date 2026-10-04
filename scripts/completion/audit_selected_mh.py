"""Rebuild selected-MH validation from saved arrays with independent NumPy.

No torch transition, new fitting, timing comparison or silent failure repair.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import warnings
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'r-package/inst/python'),str(ROOT/'examples'),str(ROOT/'scripts/completion')]
from mechanism_runner import identity, sha, actual_hash, write


def audit(protocol, inputs, run, source, output):
    from parallelbayes.reference import make_reference, numpy_reference
    from affine_target import affine_model
    inputs, run, output = Path(inputs).resolve(), Path(run).resolve(), Path(output).resolve()
    if output.exists() or run in output.parents or inputs in output.parents:
        raise ValueError('A fresh separate audit directory is required')
    p = json.loads(Path(protocol).read_text()); unsigned = dict(p); digest = unsigned.pop('protocol_sha256')
    if identity(unsigned) != digest:
        raise ValueError('Protocol checksum differs')
    for n,h in p['source_files'].items():
        if sha(ROOT/n) != h:
            raise ValueError('Source checksum differs: '+n)
    specs = json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())['models']
    all_states = []; assets = 0
    for item in p['targets']:
        f = run/item['name']/'state.json'; state = json.loads(f.read_text())
        if state['target'] != item or state['protocol_sha256'] != digest or state['status'] not in ('completed','failed'):
            raise ValueError('Terminal identity differs')
        for n,h in state['assets'].items():
            if sha(f.parent/n) != h:
                raise ValueError('Terminal asset checksum differs: '+n)
            assets += 1
        inp = inputs/item['input']
        if sha(inp) != p['inputs'][item['input']]['sha256']:
            raise ValueError('Input file checksum differs')
        with np.load(inp,allow_pickle=False) as z:
            if actual_hash(dict(z)) != p['inputs'][item['input']]['actual_sha256']:
                raise ValueError('Actual array checksum differs')
        all_states.append(state)
    output.mkdir(parents=True)
    checked = 0; failed = 0; mismatches = 0; passed = True; targets = []
    for item,state in zip(p['targets'],all_states):
        record = dict(name=item['name'],original_status=state['status'],workflows={},geometry_check=None)
        failed += sum(v['status'] != 'completed' for v in state['workflows'].values())
        if not any(v['status'] == 'completed' for v in state['workflows'].values()):
            record['scope'] = 'Original setup failed; all planned failures retained, no normal samples to replay'
            targets.append(record); continue
        if item['name'] == 'W1':
            from external_wells import load_wells,make_wells
            base = make_wells(load_wells(source))
        else:
            base = make_reference(specs[item['name']])
        if base.target_id != item['base_target_id']:
            raise ValueError('Base target identity differs')
        g = item['geometry']; factor = np.asarray(g['factor'])
        # Frozen F3 factors are positive lower-triangular. This scalar formula
        # is an independent check on NumPy LAPACK slogdet, not a replacement.
        if np.any(np.triu(factor,1) != 0) or np.any(np.diag(factor) <= 0):
            raise ValueError('This companion expects the frozen triangular factors')
        expected_logdet = math.fsum(math.log(float(x)) for x in np.diag(factor))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            model = affine_model(base,g['center'],g['factor'])
        if model.target_id != state['target_id']:
            raise ValueError('Saved coordinate target identity differs')
        discrepancy = abs(model.spec['log_abs_determinant']-expected_logdet)
        record['geometry_check'] = dict(slogdet=model.spec['log_abs_determinant'],
            independent_diagonal_log_sum=expected_logdet,absolute_difference=discrepancy,
            passed=math.isfinite(discrepancy) and discrepancy<=1e-12,
            warnings=[dict(category=w.category.__name__,message=str(w.message)) for w in caught])
        passed = passed and record['geometry_check']['passed']
        with np.load(inputs/item['input'],allow_pickle=False) as z:
            tape = {k:z[k].copy() for k in z.files}
        initial = tape.pop('initial'); references = {}
        for kernel in ('rwm','mala'):
            paths=[]; events=[]
            for ch in range(p['chains']):
                path,accept = numpy_reference(model,kernel,initial[ch],tape['noise'][ch],tape['log_uniform'][ch],item['step_'+kernel])
                paths.append(path); events.append(accept)
            references[kernel] = (np.asarray(paths),np.asarray(events))
        for name,row in state['workflows'].items():
            if row['status'] != 'completed':
                record['workflows'][name] = dict(original_status='failed',replayed=False)
                continue
            with np.load(run/item['name']/state['attempt']/(name+'.npz'),allow_pickle=False) as z:
                arrays = dict(z)
            path,accept = references[name.split('-')[0]]
            observed = arrays['unconstrained']
            errors = np.max(np.abs(path-observed),axis=(1,2))
            limits = 100*(p['atol']+p['rtol']*np.maximum(1.,np.max(np.abs(observed),axis=(1,2))))
            events = np.sum(accept != arrays['accept'],axis=1)
            transformed = model.constrain(observed)
            output_equal = np.array_equal(transformed,arrays['draws'])
            valid = bool(np.isfinite(observed).all() and np.all(errors<=limits) and not np.any(events) and output_equal)
            record['workflows'][name] = dict(original_status='completed',replayed=True,passed=valid,
                max_abs_path_error=errors.tolist(),allowed_path_error=limits.tolist(),acceptance_mismatches=events.tolist(),
                original_outputs_value_exact=bool(output_equal),accepted_per_chain=np.sum(arrays['accept'],axis=1).tolist())
            passed = passed and valid; checked += 1; mismatches += int(np.sum(events))
        targets.append(record)
    receipt = dict(protocol_sha256=digest,source_run_summary_sha256=sha(run/'summary.json'),
        task_asset_hashes_verified=assets,checked_completed_workflows=checked,retained_failed_workflows=failed,
        acceptance_mismatches=mismatches,saved_array_replay_passed=bool(passed),targets=targets,
        new_independent_replicates=0,new_MCMC_fits=0,
        scope='Saved-array NumPy replay and triangular log-determinant companion. No posterior convergence, general numerical proof or fresh performance measurement.')
    write(output/'receipt.json',receipt)
    return receipt


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','inputs','run','source','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args(); receipt=audit(args.protocol,args.inputs,args.run,args.source,args.output)
    print(json.dumps({k:v for k,v in receipt.items() if k!='targets'},indent=2))
