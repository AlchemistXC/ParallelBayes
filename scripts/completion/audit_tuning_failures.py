"""Post hoc failure localization. Does not change the frozen run or validity gate.

Replays identical inputs, evaluates both maps anchored to saved previous states,
and compares independent NumPy trajectories after one-ULP initial perturbations.
Technical replays and perturbations are not additional statistical replicates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'r-package/inst/python'), str(ROOT/'examples'), str(ROOT/'scripts/completion')]
from parallelbayes.reference import numpy_reference
from parallelbayes.torch_backend.kernels import transition
from parallelbayes.torch_backend.sampling import sample
from affine_target import affine_model
from inference_readiness import build_target
from inference_tuning import check_protocol
from mechanism_runner import sha, identity, write


def inspect(run, inputs, protocol, output):
    run, inputs, output = Path(run), Path(inputs), Path(output)
    p = check_protocol(protocol, inputs)
    if output.exists():
        raise FileExistsError('Use a new companion output directory')
    torch.set_num_threads(p['torch_threads'])
    states = []
    for case in p['cases']:
        folder = run/case['model']/case['id']
        state = json.loads((folder/'state.json').read_text())
        if state['case'] != case or state['protocol_sha256'] != p['protocol_sha256']:
            raise ValueError('Case identity mismatch')
        for name, digest in state['assets'].items():
            if sha(folder/name) != digest:
                raise ValueError('Task asset mismatch')
        if state['status'] == 'failed':
            states.append((folder, state))
    if any(s['case']['model'] != 'H1' or s['case']['kernel'] != 'mala' for _, s in states):
        raise ValueError('This companion diagnoses the observed H1 MALA failures only')
    output.mkdir(parents=True)
    write(output/'analysis-contract.json', dict(
        scope='post hoc failure localization, not new independent MCMC replicates or revised output acceptance',
        original_protocol_sha256=p['protocol_sha256'],
        original_source_commit=p['source_commit'],
        analysis_source_sha256=sha(Path(__file__)),
        numpy=np.__version__, torch=torch.__version__, torch_threads=torch.get_num_threads(),
        perturbation='numpy.nextafter(initial[0], +inf), exactly one float64 ULP; other coordinates and all random arrays unchanged',
        same_state_check='Both transitions evaluated at every original saved previous torch state',
        original_failures_remain_failed=True))
    rows = []
    for folder, state in states:
        case = state['case']; name = case['id']
        setup = json.loads((folder.parent/'setup.json').read_text())
        unsigned = dict(setup); checksum = unsigned.pop('setup_sha256')
        if identity(unsigned) != checksum or checksum != state['setup_sha256']:
            raise ValueError('Geometry identity mismatch')
        geometry = setup['geometry']
        model = affine_model(build_target('H1', None), geometry['center'], geometry['factor'])
        if model.target_id != state['target_id']:
            raise ValueError('Target identity mismatch')
        with np.load(inputs/case['input'], allow_pickle=False) as z:
            payload = {k:z[k].copy() for k in z.files}
        initial = payload.pop('initial')
        saved = json.loads((folder/state['attempt']/'fit.json').read_text())
        with np.load(folder/state['attempt']/'fit.npz', allow_pickle=False) as z:
            path, accept = z['failed_trajectory'].copy(), z['accept'].copy()
        started = time.perf_counter()
        replay = sample(model, saved['config'], payload)
        replay_equal = bool(np.array_equal(path,replay['failed_trajectory']) and
                            np.array_equal(accept,replay['accept']) and replay['status']=='failed')
        if not replay_equal:
            raise ValueError('Identical-input full replay changed; stop causal interpretation')
        previous = np.concatenate((initial[:,None,:],path[:,:-1,:]),axis=1)
        step = transition(model.log_density, 'mala')
        batch = torch.func.vmap(torch.func.vmap(step,in_dims=(0,0,0,None)),in_dims=(0,0,0,None))
        local, local_accept, finite = batch(
            *(torch.tensor(x,dtype=torch.float64) for x in (previous,payload['noise'],payload['log_uniform'])),
            case['step'])
        local = local.numpy(); local_accept = local_accept.numpy()
        oracle, oracle_accept, anchored, anchored_accept, perturbed, perturbed_accept = [],[],[],[],[],[]
        chain_rows = []
        for ch in range(path.shape[0]):
            noise, logu = payload['noise'][ch], payload['log_uniform'][ch]
            ref, acc = numpy_reference(model,'mala',initial[ch],noise,logu,case['step'])
            one, one_acc = [],[]
            for index, prior in enumerate(previous[ch]):
                q,a = numpy_reference(model,'mala',prior,noise[index:index+1],logu[index:index+1],case['step'])
                one.append(q[0]); one_acc.append(a[0])
            perturb_initial = initial[ch].copy()
            perturb_initial[0] = np.nextafter(perturb_initial[0],np.inf)
            alt, alt_acc = numpy_reference(model,'mala',perturb_initial,noise,logu,case['step'])
            differences = np.max(np.abs(ref-path[ch]),axis=1)
            events = np.flatnonzero(acc != accept[ch]); first = int(events[0]) if events.size else None
            alternate_events = np.flatnonzero(acc != alt_acc)
            first_above = {}
            for threshold in (1e-12,1e-8,1e-4,1e-2):
                indices = np.flatnonzero(differences>threshold)
                first_above[str(threshold)] = int(indices[0]) if indices.size else None
            chain_rows.append(dict(chain=ch,accepted=int(accept[ch].sum()),
                first_acceptance_mismatch_zero_based=first,acceptance_mismatches=int(events.size),
                max_path_difference_before_first_acceptance_mismatch=None if first is None else float(differences[:first].max(initial=0)),
                first_path_difference_above=first_above,
                perturb_initial_delta=float(perturb_initial[0]-initial[ch,0]),
                perturb_first_acceptance_mismatch_zero_based=int(alternate_events[0]) if alternate_events.size else None,
                perturb_acceptance_mismatches=int(alternate_events.size)))
            oracle.append(ref); oracle_accept.append(acc); anchored.append(one); anchored_accept.append(one_acc)
            perturbed.append(alt); perturbed_accept.append(alt_acc)
        anchored=np.asarray(anchored); anchored_accept=np.asarray(anchored_accept)
        row=dict(case=case,original_status=state['status'],identical_full_replay=replay_equal,
            original_output_remains_quarantined=replay['draws'] is None,
            same_state_torch_max_abs_residual=float(np.max(abs(local-path))),
            same_state_torch_event_mismatches=int(np.sum(local_accept!=accept)),
            same_state_torch_all_finite=bool(finite.all()),
            same_state_numpy_max_abs_residual=float(np.max(abs(anchored-path))),
            same_state_numpy_event_mismatches=int(np.sum(anchored_accept!=accept)),
            chains=chain_rows,companion_wall_seconds=time.perf_counter()-started)
        arrays=output/(name+'.npz')
        np.savez_compressed(arrays,initial=initial,oracle=np.asarray(oracle),oracle_accept=np.asarray(oracle_accept),
            anchored_numpy=anchored,anchored_numpy_accept=anchored_accept,
            anchored_torch=local,anchored_torch_accept=local_accept,
            perturbed_numpy=np.asarray(perturbed),perturbed_numpy_accept=np.asarray(perturbed_accept))
        row['arrays_sha256']=sha(arrays)
        write(output/(name+'.json'),row);rows.append(row)
        print(json.dumps(dict(case=name,replay_identical=replay_equal,
            same_state_numpy_mismatches=row['same_state_numpy_event_mismatches'],
            same_state_numpy_max_error=row['same_state_numpy_max_abs_residual'])),flush=True)
    summary=dict(cases=len(rows),chains=sum(len(x['chains']) for x in rows),
        inspected_transitions=sum(np.load(output/(x['case']['id']+'.npz'))['oracle_accept'].size for x in rows),
        identical_full_replays=sum(x['identical_full_replay'] for x in rows),
        original_full_path_mismatching_chains=sum(c['acceptance_mismatches']>0 for x in rows for c in x['chains']),
        perturbed_numpy_mismatching_chains=sum(c['perturb_acceptance_mismatches']>0 for x in rows for c in x['chains']),
        same_state_torch_event_mismatches=sum(x['same_state_torch_event_mismatches'] for x in rows),
        same_state_numpy_event_mismatches=sum(x['same_state_numpy_event_mismatches'] for x in rows),
        same_state_numpy_max_abs_residual=max(x['same_state_numpy_max_abs_residual'] for x in rows),
        same_state_torch_max_abs_residual=max(x['same_state_torch_max_abs_residual'] for x in rows),
        interpretation='Observed long-recurrence sensitivity to float64 rounding is supported by common-state checks and one-ULP perturbations. Not a general proof of mathematical correctness or chaos, and not permission to relax the fixed-path gate.',
        original_failures_remain_failed=True,independent_statistical_replicates_added=0)
    write(output/'summary.json',summary)
    files={p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    write(output/'manifest.json',files)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['run','inputs','protocol','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(inspect(args.run,args.inputs,args.protocol,args.output),indent=2))
