"""Frozen selected-MH/device readiness, separate from formal inference.

Same actual random inputs, selected steps and coordinates for sequential and
two finite-window executions. Every attempt, invalid path and cost is retained.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'r-package/inst/python'), str(ROOT/'examples'), str(ROOT/'scripts/completion')]
from mechanism_runner import identity, sha, actual_hash, write, experiment_lease
from inference_budget_pilot import source_files as budget_sources
from inference_readiness import save_result
from inference_targets import build_target


def source_files():
    files = budget_sources()
    for n in ['scripts/completion/inference_targets.py', 'scripts/completion/selected_mh_readiness.py',
              'benchmark/protocols/inference-budget-pilot-mac-v1.json']:
        files[n] = sha(ROOT/n)
    return dict(sorted(files.items()))


def freeze(profile, protocol, inputs):
    from parallelbayes.torch_backend.sampling import settings, random_tape
    protocol, inputs = Path(protocol), Path(inputs)
    if protocol.exists():
        raise FileExistsError('New protocol path required')
    if profile not in ('mac-v1', 'windows-cpu-v1', 'windows-cuda-v1'):
        raise ValueError('Unknown native profile')
    files = source_files()
    for name, h in files.items():
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest() != h:
            raise ValueError('Commit source first: '+name)
    old = json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    windows = profile.startswith('windows')
    p = dict(identity='selected-mh-readiness-'+profile, required_platform='win32' if windows else 'darwin',
        device='cuda:0' if profile == 'windows-cuda-v1' else 'cpu', torch_threads=4,
        required_versions={'torch':'2.13.0+cu130' if windows else '2.13.0', 'numpy':'2.2.6', 'scipy':'1.15.3'},
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_files=files, targets=old['targets'], geometry_step_source_protocol_sha256=old['protocol_sha256'],
        chains=4, draws=256, windows=[8,32], max_iter=2048, memory_limit_mb=2048,
        atol=1e-10, rtol=1e-10, initial_seed_base=7391000, tape_seed_base=7392000, solver_seed_base=7393000,
        inputs={}, statistical_repetitions=1, formal_inference_complete=False,
        scope='Device/target and selected-kernel time-executor readiness. Not formal inference, convergence or performance evidence.',
        geometry='Exact previously selected steps and frozen affine coordinates; no retuning or geometry fitting in this run.',
        inputs_policy='One new actual four-chain tape per target, shared by both kernels and every window; same fixtures across native profiles. Shared executions/hosts/windows do not increase independent n.',
        outputs='Full 256-step path and rejection self-transitions, independent NumPy audit, exact acceptance comparison and original numerical tolerances. Failed pairs are ineligible; no fallback/redraw.',
        initialization='N(0,4I) in fixed coordinates; M1 first coordinate -5,+5,-5,+5. These short validation paths are not posterior estimators.',
        timing='Synchronize device in the existing sampler; retain input, sampling, host transfer, audit, transform and archival costs. No warmed replay, timer ranking, exclusive-core or speed claim.',
        future='Readiness at 256 steps cannot certify longer formal paths. Every later path must still pass the original full audit.',
        stopping='Nine targets, six workflows per target; existing numerical/array-workspace guards; no total time cutoff.')
    inputs.mkdir(parents=True, exist_ok=True)
    for i, item in enumerate(p['targets']):
        tape = random_tape(settings(dict(chains=p['chains'], draws=p['draws'], seed=p['tape_seed_base']+i,
                                        solver_seed=p['solver_seed_base']+i)), item['dimension'])
        tape['initial'] = 2*np.random.Generator(np.random.Philox(p['initial_seed_base']+i)).standard_normal((p['chains'],item['dimension']))
        if item['name'] == 'M1':
            tape['initial'][:,0] = [-5,5,-5,5]
        name = item['name']+'.npz'; item['input'] = name
        path = inputs/name
        if path.exists():
            with np.load(path, allow_pickle=False) as z:
                if actual_hash(dict(z)) != actual_hash(tape):
                    raise ValueError('Existing fixture differs; never overwrite')
        else:
            np.savez_compressed(path, **tape)
        p['inputs'][name] = dict(sha256=sha(path), actual_sha256=actual_hash(tape))
    p['protocol_sha256'] = identity(p)
    protocol.parent.mkdir(parents=True, exist_ok=True); write(protocol, p)
    return dict(protocol_sha256=p['protocol_sha256'], source_commit=p['source_commit'],
                targets=len(p['targets']), workflows=6*len(p['targets']), device=p['device'])


def validate(protocol, inputs):
    import torch
    p = json.loads(Path(protocol).read_text()); unsigned = dict(p); digest = unsigned.pop('protocol_sha256')
    if identity(unsigned) != digest:
        raise ValueError('Protocol checksum differs')
    if sys.platform != p['required_platform']:
        raise ValueError('Native platform mismatch; do not substitute another profile')
    for name, version in p['required_versions'].items():
        if importlib.metadata.version(name) != version:
            raise ValueError('Dependency differs: '+name)
    if p['device'] not in ('cpu','cuda:0'):
        raise ValueError('Explicit device required')
    if p['device'] == 'cuda:0' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; CPU substitution forbidden')
    for name, h in p['source_files'].items():
        if sha(ROOT/name) != h:
            raise ValueError('Frozen source checksum differs: '+name)
    if len({t['name'] for t in p['targets']}) != len(p['targets']):
        raise ValueError('Duplicate target')
    for item in p['targets']:
        name = item['input']; row = p['inputs'][name]
        if sha(Path(inputs)/name) != row['sha256']:
            raise ValueError('Input file checksum differs')
        with np.load(Path(inputs)/name, allow_pickle=False) as z:
            if actual_hash(dict(z)) != row['actual_sha256']:
                raise ValueError('Actual arrays differ')
    return p


def workflows(p):
    rows = []
    for kernel, executor in [('rwm','online_picard'), ('mala','quasi_deer')]:
        rows.append(dict(name=kernel+'-sequential', kernel=kernel, executor='sequential', window=p['windows'][0]))
        for window in p['windows']:
            rows.append(dict(name=f'{kernel}-{executor}-w{window}', kernel=kernel, executor=executor, window=window))
    return rows


def compare(a, b, p):
    if a.get('status') != 'completed' or b.get('status') != 'completed':
        return dict(passed=False, reason='At least one workflow failed; no ordinary paired samples')
    x, y = a['unconstrained'], b['unconstrained']
    limits = 100*(p['atol']+p['rtol']*np.maximum(1.,np.max(np.abs(x),axis=(1,2))))
    errors = np.max(np.abs(x-y), axis=(1,2))
    events = np.sum(a['accept'] != b['accept'], axis=1)
    return dict(passed=bool(np.all(errors<=limits) and not np.any(events)),
        max_abs_path_error=errors.tolist(), allowed_path_error=limits.tolist(), acceptance_mismatches=events.tolist(),
        max_abs_output_error=np.max(np.abs(a['draws']-b['draws']),axis=(1,2)).tolist(),
        scope='Within-device same actual tape; each path also passes independent NumPy audit. Not a general guarantee.')


def run(protocol, inputs, source, output, resume=False):
    import torch, psutil
    from parallelbayes.torch_backend.models import validate_model
    from parallelbayes.torch_backend.sampling import sample
    p = validate(protocol, inputs); inputs, out = Path(inputs), Path(output)
    if any(t['name'] == 'W1' for t in p['targets']):
        from external_wells import load_wells
        load_wells(source)  # Source asset checks also apply to resume.
    torch.set_num_threads(p['torch_threads'])
    runtime = dict(protocol_sha256=p['protocol_sha256'], python=sys.version, platform=platform.platform(),
        machine=platform.machine(), device=p['device'], torch_threads=torch.get_num_threads(),
        torch_interop_threads=torch.get_num_interop_threads(), cpu_physical=psutil.cpu_count(logical=False),
        cpu_logical=psutil.cpu_count(), ram_bytes=psutil.virtual_memory().total,
        thread_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']},
        packages=dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())),
        cuda_build=torch.version.cuda, gpu=None)
    if p['device'] == 'cuda:0':
        prop = torch.cuda.get_device_properties(0)
        runtime['gpu'] = dict(name=prop.name, major=prop.major, minor=prop.minor, total_memory=prop.total_memory)
    if out.exists():
        if not resume: raise FileExistsError('Explicit resume required')
        if json.loads((out/'runtime.json').read_text()) != runtime:
            raise ValueError('Resume environment differs')
    else:
        out.mkdir(parents=True); write(out/'runtime.json', runtime)
    rows = workflows(p); states = []; new = 0; began = time.perf_counter(); invocation = str(time.time_ns())
    with experiment_lease(out):
        for item in p['targets']:
            folder = out/item['name']; statefile = folder/'state.json'
            if statefile.exists():
                state = json.loads(statefile.read_text())
                if state['target'] != item or state['protocol_sha256'] != p['protocol_sha256'] or state['status'] not in ('completed','failed'):
                    raise ValueError('Terminal identity differs')
                for name, h in state['assets'].items():
                    if sha(folder/name) != h:
                        raise ValueError('Terminal asset checksum differs')
                states.append(state); continue
            folder.mkdir(parents=True, exist_ok=True); attempt = folder/('attempt-'+str(time.time_ns())); attempt.mkdir()
            state = dict(target=item, protocol_sha256=p['protocol_sha256'], attempt=attempt.name, status='started',
                         workflows={}, pairs={}, samples_eligible_for_inference=False)
            write(attempt/'started.json', state); start = time.perf_counter()
            print(json.dumps(dict(starting=item['name'], device=p['device'])), flush=True)
            try:
                model = build_target(item, source, p['device'])
                with np.load(inputs/item['input'], allow_pickle=False) as z:
                    tape = {k:z[k].copy() for k in z.files}
                initial = tape.pop('initial')
                points = np.vstack([np.zeros(model.dimension), initial, np.full(model.dimension,.25), np.full(model.dimension,-.25)])
                check = validate_model(model, points); write(attempt/'target-check.json', check)
                state.update(target_id=model.target_id, actual_device=str(model.device), model_check=check)
                if not check['passed']:
                    raise ValueError('Model density/gradient/HVP/transform check failed')
                results = {}
                for row in rows:
                    name = row['name']; before = time.perf_counter()
                    try:
                        config = dict(kernel=row['kernel'], executor=row['executor'], device=p['device'],
                            chains=p['chains'], draws=p['draws'], initial=initial.tolist(),
                            step_size=item['step_'+row['kernel']], window=row['window'], max_iter=p['max_iter'],
                            atol=p['atol'], rtol=p['rtol'], memory_limit_mb=p['memory_limit_mb'], audit=True, on_failure='error')
                        fit = sample(model, config, tape); save_result(attempt, name, fit); results[name] = fit
                        state['workflows'][name] = dict(status=fit['status'], audit=fit['audit'], stopping_reason=fit['stopping_reason'],
                            tape_sha256=fit['tape_sha256'], timing=fit['timing'], memory=fit['memory'],
                            accepted_per_chain=np.sum(fit['accept'],axis=1).tolist(), total_transitions=p['chains']*p['draws'])
                    except Exception as exc:
                        failure = dict(status='failed', error=type(exc).__name__+': '+str(exc), traceback=traceback.format_exc())
                        write(attempt/(name+'-failure.json'), failure); results[name] = failure; state['workflows'][name] = failure
                    state['workflows'][name]['whole_workflow_seconds_including_archive'] = time.perf_counter()-before
                for row in rows:
                    if row['executor'] != 'sequential':
                        state['pairs'][row['name']] = compare(results[row['kernel']+'-sequential'], results[row['name']], p)
                state['status'] = 'completed' if all(v['status']=='completed' for v in state['workflows'].values()) and all(v['passed'] for v in state['pairs'].values()) else 'failed'
            except Exception as exc:
                state.update(status='failed', setup_error=type(exc).__name__+': '+str(exc), traceback=traceback.format_exc())
                write(attempt/'setup-failure.json', dict(error=state['setup_error'],traceback=state['traceback']))
                for row in rows:
                    state['workflows'].setdefault(row['name'], dict(status='failed', reason='target setup failed; no draws'))
            state['whole_target_seconds_including_archive'] = time.perf_counter()-start
            state['assets'] = {f.relative_to(folder).as_posix():sha(f) for f in sorted(attempt.rglob('*')) if f.is_file()}
            write(folder/'state.tmp', state); (folder/'state.tmp').replace(statefile)
            states.append(state); new += 1
            print(json.dumps(dict(done=item['name'], status=state['status'])), flush=True)
        completed = sum(v['status']=='completed' for s in states for v in s['workflows'].values())
        summary = dict(protocol_sha256=p['protocol_sha256'], device=p['device'], planned_targets=len(p['targets']),
            completed_targets=sum(s['status']=='completed' for s in states), failed_targets=sum(s['status']=='failed' for s in states),
            planned_workflows=len(p['targets'])*len(rows), completed_workflows=completed,
            failed_workflows=len(p['targets'])*len(rows)-completed,
            passed_pairs=sum(v['passed'] for s in states for v in s['pairs'].values()),
            planned_pairs=len(p['targets'])*(len(rows)-2), newly_executed_targets=new,
            invocation_seconds=time.perf_counter()-began, scope=p['scope'], formal_inference_complete=False)
        history = out/'invocations'; history.mkdir(exist_ok=True)
        write(history/(invocation+'.json'), dict(summary, resume=resume)); write(out/'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='action',required=True)
    f = sub.add_parser('freeze'); f.add_argument('--profile',required=True)
    f.add_argument('--protocol',type=Path,required=True); f.add_argument('--inputs',type=Path,required=True)
    r = sub.add_parser('run'); r.add_argument('--protocol',type=Path,required=True); r.add_argument('--inputs',type=Path,required=True)
    r.add_argument('--source',type=Path,required=True); r.add_argument('--output',type=Path,required=True); r.add_argument('--resume',action='store_true')
    args = parser.parse_args()
    result = freeze(args.profile,args.protocol,args.inputs) if args.action=='freeze' else run(args.protocol,args.inputs,args.source,args.output,args.resume)
    print(json.dumps(result,indent=2))
