"""Bounded companion localization of the observed H1 budget-pilot failure.

Saved inputs and original validity rules are immutable. Replays, common-state
checks and +/- one-ULP probes are technical investigations, not new repetitions.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'r-package/inst/python'),str(ROOT/'examples'),str(ROOT/'scripts/completion')]
from parallelbayes.reference import numpy_reference
from parallelbayes.torch_backend.kernels import transition
from parallelbayes.torch_backend.sampling import sample
from affine_target import affine_model
from inference_readiness import build_target
from inference_budget_pilot import validate
from mechanism_runner import sha,write,actual_hash


def first_index(mask):
    indices=np.flatnonzero(mask)
    return int(indices[0]) if indices.size else None


def inspect(run,inputs,protocol,output):
    run,inputs,output=Path(run).resolve(),Path(inputs).resolve(),Path(output).resolve()
    if output.exists() or run in output.parents or inputs in output.parents:
        raise ValueError('Use a fresh separate companion output directory')
    p=validate(protocol,inputs);torch.set_num_threads(p['torch_threads'])
    failures=[]
    for task in p['tasks']:
        folder=run/task['model']/task['id'];state=json.loads((folder/'state.json').read_text())
        if state['task']!=task or state['protocol_sha256']!=p['protocol_sha256']:
            raise ValueError('Task identity differs')
        for name,h in state['assets'].items():
            if sha(folder/name)!=h:raise ValueError('Task asset differs')
        if state['status']=='failed':failures.append((folder,state))
    if len(failures)!=1 or failures[0][1]['task']['id']!='4dc55fe41afd7ee147b2':
        raise ValueError('This companion only covers the single observed H1/MALA failure')
    folder,state=failures[0];task=state['task'];item=next(x for x in p['targets'] if x['name']=='H1')
    g=item['geometry'];model=affine_model(build_target('H1',None),g['center'],g['factor'])
    if model.target_id!=state['target_id']:raise ValueError('Target identity differs')
    attempt=folder/state['attempt'];meta=json.loads((attempt/'fit.json').read_text())
    c=meta['config'];steps=c['draws'];scale=c['step_size']
    with np.load(inputs/task['input'],allow_pickle=False) as z:
        initial=z['initial'].copy();tape={k:z[k][:,:steps].copy() for k in ['noise','log_uniform','directions']}
    if actual_hash(tape)!=meta['tape_sha256'] or not np.array_equal(initial,c['initial']):
        raise ValueError('Actual initial state/tape differs')
    with np.load(attempt/'fit.npz',allow_pickle=False) as z:
        path=z['failed_trajectory'].copy();accept=z['accept'].copy()
    if meta['status']!='failed' or meta['draws'] is not None or c['on_failure']!='error':
        raise ValueError('Original quarantine contract differs')
    before={str(f.relative_to(folder)):sha(f) for f in folder.rglob('*') if f.is_file()}
    output.mkdir(parents=True)
    write(output/'analysis-contract.json',dict(scope=__doc__,original_protocol_sha256=p['protocol_sha256'],
        original_source_commit=p['source_commit'],analysis_source_sha256=sha(Path(__file__)),
        original_task=task,numpy=np.__version__,torch=torch.__version__,threads=torch.get_num_threads(),
        probes='One full identical replay; common-state transitions at all 18432 saved previous states; independent NumPy initial coordinate 0 perturbed toward +inf and -inf by one ULP.',
        gates='Original scalar per-chain path limit = 100*(atol+rtol*max(1,max(abs(saved_path)))); exact acceptance events. No relaxation or relabelling.'))
    started=time.perf_counter();replay=sample(model,c,tape)
    if replay['status']!='failed' or replay['draws'] is not None or not np.array_equal(path,replay['failed_trajectory']) or not np.array_equal(accept,replay['accept']):
        raise ValueError('Identical replay differs; preserve attempt and avoid causal inference')
    previous=np.concatenate([initial[:,None,:],path[:,:-1]],axis=1)
    step=transition(model.log_density,'mala')
    batch=torch.func.vmap(torch.func.vmap(step,in_dims=(0,0,0,None)),in_dims=(0,0,0,None))
    local,local_accept,finite=batch(*(torch.tensor(x,dtype=torch.float64) for x in (previous,tape['noise'],tape['log_uniform'])),scale)
    local=local.numpy();local_accept=local_accept.numpy()
    arrays=dict(anchored_torch=local,anchored_torch_accept=local_accept)
    oracle=[];oracle_accept=[];anchored=[];anchored_accept=[];probes=[];probe_accept=[];chains=[]
    for ch in range(p['chains']):
        noise,logu=tape['noise'][ch],tape['log_uniform'][ch]
        ref,events=numpy_reference(model,'mala',initial[ch],noise,logu,scale)
        oracle.append(ref);oracle_accept.append(events)
        one=[];one_events=[]
        for i,prior in enumerate(previous[ch]):
            q,a=numpy_reference(model,'mala',prior,noise[i:i+1],logu[i:i+1],scale)
            one.append(q[0]);one_events.append(a[0])
        anchored.append(one);anchored_accept.append(one_events)
        errors=np.max(abs(ref-path[ch]),axis=1)
        limit=100*(c['atol']+c['rtol']*max(1.,float(np.max(abs(path[ch])))))
        original_max=float(errors.max())
        if original_max!=meta['audit']['max_abs_path_error'][ch] or int(np.sum(events!=accept[ch]))!=meta['audit']['acceptance_mismatches'][ch]:
            raise ValueError('Original independent audit does not reproduce')
        location=np.unravel_index(np.argmax(abs(ref-path[ch])),ref.shape)
        perturbations=[];chain_probes=[];chain_probe_events=[]
        for direction in [np.inf,-np.inf]:
            changed=initial[ch].copy();changed[0]=np.nextafter(changed[0],direction)
            alt,alt_events=numpy_reference(model,'mala',changed,noise,logu,scale)
            chain_probes.append(alt);chain_probe_events.append(alt_events)
            diff=np.max(abs(alt-ref),axis=1)
            perturbations.append(dict(direction='positive' if direction>0 else 'negative',
                initial_delta=float(changed[0]-initial[ch,0]),max_path_difference=float(diff.max()),
                acceptance_mismatches=int(np.sum(alt_events!=events)),first_acceptance_mismatch_zero_based=first_index(alt_events!=events),
                first_nonzero_path_difference_zero_based=first_index(diff>0),first_above_original_limit_zero_based=first_index(diff>limit)))
        probes.append(chain_probes);probe_accept.append(chain_probe_events)
        chains.append(dict(chain=ch,original_limit=limit,max_path_difference=original_max,ratio_to_original_limit=original_max/limit,
            max_location_zero_based=[int(v) for v in location],torch_value_at_max=float(path[ch][location]),numpy_value_at_max=float(ref[location]),
            first_nonzero_difference_zero_based=first_index(errors>0),first_above_original_limit_zero_based=first_index(errors>limit),
            path_difference_at_retained_budget={str(b):float(errors[:p['mh_warmup']+b].max()) for b in p['budgets']},
            acceptance_mismatches=int(np.sum(events!=accept[ch])),accepted_transitions=int(accept[ch].sum()),
            repeated_state_transitions=int((~accept[ch]).sum()),initial_ulp_probes=perturbations))
    oracle=np.asarray(oracle);anchored=np.asarray(anchored);anchored_accept=np.asarray(anchored_accept)
    arrays.update(oracle=oracle,oracle_accept=np.asarray(oracle_accept),anchored_numpy=anchored,anchored_numpy_accept=anchored_accept,
        initial_ulp_numpy=np.asarray(probes),initial_ulp_accept=np.asarray(probe_accept),
        errors_by_step=np.max(abs(oracle-path),axis=2),local_numpy_errors=np.max(abs(anchored-path),axis=2))
    np.savez_compressed(output/'localization.npz',**arrays)
    after={str(f.relative_to(folder)):sha(f) for f in folder.rglob('*') if f.is_file()}
    if before!=after:raise RuntimeError('Original evidence was changed')
    summary=dict(original_task=task,original_failed=True,identical_full_replay=True,ordinary_samples_returned=False,
        inspected_transitions=accept.size,original_acceptance_mismatches=int(np.sum(np.asarray(oracle_accept)!=accept)),
        same_state_torch_max_abs_residual=float(np.max(abs(local-path))),same_state_numpy_max_abs_residual=float(np.max(abs(anchored-path))),
        same_state_torch_acceptance_mismatches=int(np.sum(local_accept!=accept)),same_state_numpy_acceptance_mismatches=int(np.sum(anchored_accept!=accept)),
        same_state_torch_all_finite=bool(finite.all()),chains=chains,original_task_files_unchanged=len(before),
        technical_replays_do_not_add_independent_replicates=True,original_failure_remains_failed=True,
        elapsed_seconds=time.perf_counter()-started,arrays_sha256=sha(output/'localization.npz'),
        limitation='Common-state agreement and ULP probes describe finite-precision recurrence sensitivity on this tape; they cannot certify an invariant distribution, general correctness or relax the original full-path gate.')
    write(output/'summary.json',summary)
    write(output/'manifest.json',{f.name:sha(f) for f in sorted(output.iterdir()) if f.is_file()})
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['run','inputs','protocol','output']:parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();print(json.dumps(inspect(a.run,a.inputs,a.protocol,a.output),indent=2))
