"""Read one archived v2 task through its actual inputs and original outputs.

No Windows APIs or torch/JAX samplers are imported. Lifecycle verification is
separate from scientific reconstruction. Receiver errors do not relabel the
original outcome or erase known costs. This is not a formal-study launcher.
"""
import ast
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/completion'), str(ROOT/'r-package/inst/python'), str(ROOT/'examples')]
from batch_contract import validate_capsule, mh_config
from cache_probe_execution import read_cached_probe, _probe
from formal_freeze import relative_file, validate_payload
from formal_native_evidence import read_native_task
from formal_runtime import atomic_json, file_hash, fingerprint
from formal_streaming import read_member, extract_functions, array_hash
from formal_measurement_plan import summarize_probe
from parallelbayes.reference import make_reference, numpy_reference
from affine_target import affine_model
from replay_windows_followup import tape_hash


def compare(left, right, atol, rtol):
    differences = []
    def visit(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            return a.keys() == b.keys() and all(visit(a[k], b[k]) for k in a)
        if isinstance(a, list) and isinstance(b, list):
            return len(a) == len(b) and all(visit(x, y) for x, y in zip(a, b))
        if type(a) in (int, float) and type(b) in (int, float):
            if not math.isfinite(a) or not math.isfinite(b): return False
            differences.append(abs(a-b))
            return math.isclose(a, b, abs_tol=atol, rel_tol=rtol)
        return type(a) is type(b) and a == b
    passed = visit(left, right)
    return dict(passed=passed, exact=left == right,
                maximum_absolute_difference=max(differences, default=0.), atol=atol, rtol=rtol)


def _defaults(source):
    # Read only the literal frozen DEFAULTS. Importing its module loads torch
    # and the implementation whose outputs this reader independently checks.
    assignments = [n.value for n in ast.parse(source.read_text()).body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'DEFAULTS' for t in n.targets)]
    if len(assignments) != 1: raise ValueError('One literal settings declaration required')
    call = assignments[0]
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != 'dict' or call.args:
        raise ValueError('Unsupported frozen settings declaration')
    if any(k.arg is None for k in call.keywords): raise ValueError('Nonliteral settings expansion')
    return {k.arg: ast.literal_eval(k.value) for k in call.keywords}


class ScientificReader:
    """One frozen source contract; one input/target cached at most.

    The caller verifies the delivery manifest and complete phase/task frame.
    Each read supplies a *task-local* manifest, so no study-wide inventory is
    rescanned for every attempt. Source compatibility is checked once here.
    """
    def __init__(self, bundle, source_files, *, rscript, r_library, cross_platform=False):
        self.root = Path(bundle).resolve()
        self.sources = dict(source_files)
        self.rscript, self.r_library = str(rscript), str(r_library)
        self.cross_platform = cross_platform
        for name, digest in self.sources.items():
            archived = relative_file(self.root/'source', name)
            if not archived.is_file() or file_hash(archived) != digest:
                raise ValueError('Archived source differs: '+name)
            if name.startswith(('scripts/completion/', 'r-package/inst/python/', 'examples/', 'models/')) or name == 'benchmark/protocols/windows-native-v1.json':
                if file_hash(ROOT/name) != digest:
                    raise ValueError('Reader dependencies differ from frozen scientific source: '+name)
        required = ('r-package/inst/python/parallelbayes/reference.py', 'examples/affine_target.py',
                    'r-package/inst/python/parallelbayes/torch_backend/sampling.py',
                    'scripts/completion/inference_estimands.py', 'scripts/completion/posterior_diagnostics.R',
                    'benchmark/protocols/windows-native-v1.json')
        if any(n not in self.sources for n in required): raise ValueError('Incomplete scientific source binding')
        self.defaults = _defaults(self.root/'source'/required[2])
        self._input = self._model = None

    def _context(self, c):
        item = c['target']; descriptor = c['input']
        model_key = fingerprint(item)
        if self._model is None or self._model[0] != model_key:
            if item['name'] == 'W1':
                from external_wells import load_wells, make_wells, propriety_certificate
                data = load_wells(self.root/'external')
                if not propriety_certificate(data)['certified']: raise ValueError('W1 integrability certificate unavailable')
                base = make_wells(data)
            else:
                specs = json.loads((self.root/'source/benchmark/protocols/windows-native-v1.json').read_text())['models']
                base = make_reference(specs[item['name']])
            if base.target_id != item['base_target_id'] or base.dimension != item['dimension']:
                raise ValueError('Frozen target differs from independent reference')
            geometry = item['geometry']
            if geometry.get('target_id', base.target_id) != base.target_id: raise ValueError('Affine base identity differs')
            self._model = (model_key, affine_model(base, geometry['center'], geometry['factor']))
        path = relative_file(self.root, 'inputs/'+c['task']['input'])
        # Recheck bytes even on a cache hit; never regenerate an input stream.
        if file_hash(path) != descriptor['sha256']: raise ValueError('Actual input file changed')
        key = fingerprint(dict(identity=c['identity'], descriptor=descriptor))
        if self._input is None or self._input[0] != key:
            self._input = None
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
            roles = ('initial', 'noise', 'log_uniform', 'directions', 'nuts_seeds')
            if len(names) != 5 or set(names) != {k+'.npy' for k in roles}: raise ValueError('Input roles differ')
            values = {k: read_member(path, k, c['controls']['maximum_member_bytes']) for k in roles}
            if validate_payload(values, c['identity'], descriptor) != descriptor['actual_sha256']:
                raise ValueError('Actual input array binding differs')
            if file_hash(path) != descriptor['sha256']: raise ValueError('Input changed while reading')
            self._input = (key, values)
        return self._model[1], self._input[1]

    def read(self, slot, *, history_export, directory, ledger, manifest, output):
        """Validate lifecycle + capsule + raw arrays, preserving original outcome.

        All failures retain their attempts/costs. Eligible MH is replayed by
        independent NumPy; NUTS uses its separate shape/RNG/adaptation contract.
        R diagnostics are rebuilt from the archived original function binary.
        """
        output = Path(output).resolve()
        if output.exists() or output.is_relative_to(self.root) or self.root.is_relative_to(output):
            raise ValueError('Fresh output separate from evidence required')
        c = validate_capsule(slot['capsule'], slot['capsule_sha256'])
        if c['source_files'] != self.sources: raise ValueError('Task and reader source contracts differ')
        expected = dict(c['task'], protocol_sha256=c['protocol_sha256'], artifact_kind='posterior')
        probe = slot.get('probe')
        if probe is not None:
            if c.get('compact_execution_contract'):
                from compact_contract import validate_probe
                validate_probe(c,slot['capsule_sha256'],probe)
            else:_probe(c, slot['capsule_sha256'], probe)
            expected.update(id=probe['id'], artifact_kind='cache_measurement')
        if slot['task'] != expected: raise ValueError('Owned and scientific task identities differ')
        lifecycle_reader=read_native_task
        if c.get('compact_execution_contract'):
            from compact_native_evidence import read_native_task as read_compact_native_task
            lifecycle_reader=read_compact_native_task
        h = lifecycle_reader(self.root, task=slot['task'], history_export=history_export,
            directory=directory, ledger=ledger, manifest=manifest, source_files=self.sources)
        request = h['binding']['request']
        if request.get('capsule') != c or request.get('capsule_sha256') != slot['capsule_sha256']:
            raise ValueError('Executed task differs from frozen scientific capsule')
        if request.get('phase') != ('main' if probe is None else 'cache') or request.get('probe') != probe:
            raise ValueError('Executed phase/probe differs')
        output.mkdir(parents=True)
        row = dict(task=slot['task'], history=h, outcome=h['summary']['outcome'],
            means=None, names=None, function_status='unavailable', diagnostics=None,
            new_sampler_calls=0, new_independent_repetitions=0, convergence_proven=False)
        try:
            model, values = self._context(c)
            if probe is not None:
                row['cache'] = self._cache(c, slot, h, model, values, directory)
            elif row['outcome'] == 'valid':
                self._main(c, h, model, values, output, row)
            row['reader_status'] = 'completed'
            atomic_json(output/'result.json', row)
        except BaseException as exc:
            atomic_json(output/'READER-FAILURE.json', dict(task=slot['task'],
                recorded_outcome=row['outcome'], history=h, error=type(exc).__name__+': '+str(exc),
                scientific_summary_available=False, original_outcome_reclassified=False))
            raise
        return row

    def _replay(self, model, config, values, raw):
        limit = config['draws']; allowance = 128*1024**2
        q = read_member(raw, 'unconstrained', allowance); accept = read_member(raw, 'accept', allowance)
        shape = (config['chains'], limit, model.dimension)
        if q.shape != shape or q.dtype != np.float64 or accept.shape != shape[:2] or accept.dtype != np.bool_ or not np.isfinite(q).all():
            raise ValueError('MH saved path shape/type/finite contract differs')
        errors, events, bounds = [], [], []
        for chain in range(config['chains']):
            ref, branch = numpy_reference(model, config['kernel'], values['initial'][chain],
                values['noise'][chain, :limit], values['log_uniform'][chain, :limit], config['step_size'])
            errors.append(float(np.max(np.abs(ref-q[chain]))))
            events.append(int(np.count_nonzero(branch != accept[chain])))
            bounds.append(100*(config['atol']+config['rtol']*max(1., float(np.max(np.abs(q[chain]))))))
        return dict(passed=all(a <= b for a, b in zip(errors, bounds)) and not any(events),
            maximum_path_error=errors, frozen_path_limits=bounds, acceptance_mismatches=events,
            reference='independent_numpy_float64', transitions=int(accept.size),
            path_sha256=array_hash(q), acceptance_sha256=array_hash(accept))

    def _main(self, c, h, model, values, output, row):
        folder = Path(h['eligible_directory']); ctrl = c['controls']; task = c['task']
        def read(name): return json.loads(relative_file(folder, name).read_text())
        meta, worker = read('fit.json'), read('worker-result.json')
        if (worker != h['last_state']['worker_result'] or worker['task'] != task or
                worker['protocol_sha256'] != c['protocol_sha256'] or worker['capsule_sha256'] != fingerprint(c) or
                worker['target_id'] != model.target_id or meta['target_id'] != model.target_id or meta['status'] != 'completed'):
            raise ValueError('Saved main output target/capsule differs')
        raw = folder/'fit.npz'; raw_hash = file_hash(raw)
        if (meta['ordinary_candidate_arrays_sha256'] != raw_hash or
                meta['ordinary_candidate_metadata_sha256'] != file_hash(folder/'candidate.json') or
                meta['external_audit'] != read('external-audit.json') or meta['external_audit']['samples_eligible'] is not True):
            raise ValueError('Candidate and final external audit bindings differ')
        discard = 0 if task['kernel'] == 'nuts' else ctrl['mh_discard']
        total = task['budget']+discard
        if task['kernel'] == 'nuts':
            row['nuts'] = self._nuts(c, model, values, raw, meta, folder)
        else:
            config = dict(self.defaults, **mh_config(c, values['initial'].tolist()))
            tape = {k: values[k][:, :total] for k in ('noise', 'log_uniform', 'directions')}
            if (meta['config'] != config or meta['tape_sha256'] != tape_hash(tape) or
                    worker['full_MH_audit'] != meta['audit'] or meta['audit']['passed'] is not True or
                    len(meta['audit']['acceptance_mismatches']) != ctrl['chains'] or any(meta['audit']['acceptance_mismatches'])):
                raise ValueError('MH saved settings/input/audit differs')
            diag = meta['diagnostics']
            if diag['tensor_device'].split(':')[0] != task['device'] or diag['tensor_dtype'] != 'torch.float64':
                raise ValueError('Actual MH device/precision differs')
            row['independent_replay'] = self._replay(model, config, values, raw)
            atomic_json(output/'independent-replay.json', row['independent_replay'])
            if not row['independent_replay']['passed']: raise ValueError('Receiver MH path/event replay failed')
            row.update(mechanism=diag, tape_sha256=meta['tape_sha256'], nested_sampler_timing=meta['timing'])
        try:
            extraction = extract_functions(raw, raw_hash, model, (ctrl['chains'], total, model.dimension),
                discard, output/'functions', maximum_member_bytes=ctrl['maximum_member_bytes'], prefix_lengths=(total,))
        except (FloatingPointError, OverflowError) as exc:
            if worker['diagnostics_status'] != 'function_failure': raise ValueError('New receiver function failure') from exc
            row.update(function_status='failed', function_error=str(exc), raw_sha256=raw_hash)
            return
        if worker['diagnostics_status'] == 'function_failure':
            # Preserve the original unavailability even if receiver arithmetic succeeds.
            row.update(function_status='failed', function_error=read('function-failure.json'),
                       receiver_extraction_available=True, raw_sha256=raw_hash)
            return
        if worker['diagnostics_status'] != 'completed': raise ValueError('Eligible fit lacks recorded function status')
        row.update(self._diagnostics(c, folder, output/'functions', extraction))
        row.update(function_status='completed', raw_sha256=raw_hash, extraction=extraction)

    def _nuts(self, c, model, values, raw, meta, folder):
        ctrl=c['controls']; task=c['task']; n=ctrl['chains']; allowance=ctrl['maximum_member_bytes']
        if (meta['provider'] != 'pyro_cpu_spawn_chains' or meta['process_start_method'] != 'spawn' or
                meta['workers_requested'] != n or meta['workers_allocated'] != n or meta['threads_per_worker'] != 1 or
                task['device'] != 'cpu' or task['executor'] != 'spawn_chains' or meta['chain_seeds'] != values['nuts_seeds'].tolist()):
            raise ValueError('NUTS provider/parallelism/seeds differ')
        if not np.array_equal(read_member(raw,'initial',allowance),values['initial']): raise ValueError('NUTS actual starts differ')
        warm=read_member(raw,'warmup_states',allowance)
        if warm.shape != (n,ctrl['nuts_warmup'],model.dimension) or warm.dtype != np.float64 or not np.isfinite(warm).all():
            raise ValueError('NUTS warmup differs')
        rng={}
        for name in ('initial_torch_rng_states','final_torch_rng_states'):
            a=read_member(raw,name,allowance)
            if a.ndim != 2 or a.shape[0] != n or a.shape[1] < 1 or a.dtype != np.uint8: raise ValueError('NUTS RNG state differs')
            rng[name]=array_hash(a)
        children=meta['worker_records']
        if len(children) != n or sorted(x['chain'] for x in children) != list(range(n)): raise ValueError('NUTS chain frame differs')
        pids=meta['observed_worker_pids']
        if len(pids) != n or len(set(pids)) != n or set(pids) != {x['worker_pid'] for x in children}: raise ValueError('NUTS worker identities differ')
        observed=set()
        with (folder/'ownership.ndjson').open() as stream:
            for line in stream:
                for member in json.loads(line)['members']:
                    if not member['member_of_owned_job']: raise ValueError('NUTS observed nonmember process')
                    observed.add(member['pid'])
        if not set(pids) <= observed: raise ValueError('NUTS children absent from saved Job observations')
        diagnostics=[]
        for child in children:
            sub=relative_file(folder,child['result_directory'])
            m=json.loads((sub/'metadata.json').read_text())
            if m['status'] != 'completed' or m['target_id'] != model.target_id or m['chain_seeds'] != [int(values['nuts_seeds'][child['chain']])]:
                raise ValueError('NUTS child identity differs')
            expected=dict(warmup_per_chain=ctrl['nuts_warmup'],draws_per_chain=task['budget'],
                max_tree_depth=ctrl['nuts_tree_depth'],target_accept_prob=ctrl['nuts_target_accept'],
                full_mass=ctrl['nuts_full_mass'],mass_matrix_adaptation=True,provider='pyro_cpu_nuts')
            if any(m.get(k)!=v for k,v in expected.items()): raise ValueError('NUTS child sampling configuration differs')
            for name,length in [('warmup_step_size',ctrl['nuts_warmup']),('sample_step_size',task['budget'])]:
                a=read_member(sub/'adaptation.npz',name,allowance)
                if a.shape != (length,) or not np.isfinite(a).all() or not (a>0).all(): raise ValueError('NUTS adaptation trace differs')
            diagnostics.append(dict(chain=child['chain'],records=m['chain_records'],
                tree_depth_hit_count=m['tree_depth_hit_count'],tree_depth_note=m.get('tree_depth_note'),
                max_tree_depth=m['max_tree_depth']))
        return dict(chain_diagnostics=diagnostics,rng_sha256=rng,worker_pids=pids,
                    MH_path_equivalence=False,receiver_reran_NUTS=False,convergence_proven=False)

    def _diagnostics(self, c, folder, dest, extraction):
        original=folder/'diagnostics'; task=c['task']; ctrl=c['controls']
        transport=json.loads((original/'transport.json').read_text())
        expected=[dict(id=task['id'],input='functions.bin',shape=extraction['shape'],names=extraction['names'])]
        if transport['fits'] != expected or (original/'functions.bin').stat().st_size != (dest/'functions.bin').stat().st_size:
            raise ValueError('Original bounded function transport identity/length differs')
        old=np.fromfile(original/'functions.bin',dtype='<f8'); new=np.fromfile(dest/'functions.bin',dtype='<f8')
        if old.shape != new.shape or not np.isfinite(old).all(): raise ValueError('Original function transport differs')
        binary=dict(exact=file_hash(original/'functions.bin')==extraction['input_sha256'],
            passed=bool(np.allclose(old,new,atol=ctrl['atol'],rtol=ctrl['rtol'])),
            maximum_absolute_difference=float(np.max(np.abs(old-new))),atol=ctrl['atol'],rtol=ctrl['rtol'])
        if not binary['passed'] or not self.cross_platform and not binary['exact']: raise ValueError('Function rebuild comparison failed')
        if file_hash(original/'functions.bin') != file_hash(original/'functions.bin.roundtrip'): raise ValueError('Original R roundtrip differs')
        estimates=json.loads((original/'estimates.json').read_text())
        comparison=compare(estimates['means'],extraction['means'],ctrl['atol'],ctrl['rtol'])
        if estimates['names'] != extraction['names'] or not comparison['passed'] or not self.cross_platform and not comparison['exact']:
            raise ValueError('Original function estimates differ')
        # Official scalars and diagnostics remain those of the frozen Windows
        # run. Receiver differences are companion checks, never replacements.
        (dest/'functions.bin').rename(dest/'functions.receiver.bin')
        shutil.copyfile(original/'functions.bin',dest/'functions.bin')
        atomic_json(dest/'transport.json',dict(fits=[dict(id=task['id'],input='functions.bin',shape=extraction['shape'],names=extraction['names'])],
            scope='Read-only reconstruction from archived original function binary',independent_unit='One complete four-chain input'))
        run=subprocess.run([self.rscript,'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(dest)],
            env=dict(os.environ,R_LIBS_USER=self.r_library),capture_output=True,text=True)
        (dest/'R.log').write_text(run.stdout+run.stderr)
        if run.returncode: raise RuntimeError('Receiver R diagnostics failed; original evidence retained')
        post=json.loads((dest/'posterior.json').read_text()); saved=json.loads((original/'posterior.json').read_text())
        if saved['R'] != c['required_R_version'] or saved['posterior'] != c['required_R_posterior']: raise ValueError('Original R environment differs')
        diag=compare(saved['results'],post['results'],ctrl['atol'],ctrl['rtol'])
        if file_hash(dest/'functions.bin') != file_hash(dest/'functions.bin.roundtrip'): raise ValueError('Receiver R roundtrip differs')
        if not diag['passed'] or not self.cross_platform and not diag['exact']: raise ValueError('Receiver R diagnostics differ')
        return dict(names=estimates['names'],means=estimates['means'],diagnostics=saved['results'][task['id']],
            receiver_means=extraction['means'],receiver_function_comparison=binary,receiver_means_comparison=comparison,
            receiver_diagnostics_comparison=diag,original_R=saved['R'],receiver_R=post['R'],
            original_posterior=saved['posterior'],receiver_posterior=post['posterior'],
            R_input_sha256=file_hash(dest/'functions.bin'),receiver_function_binary='functions.receiver.bin',
            statistical_input='Archived Windows estimates and diagnostics; receiver reconstruction retained separately')

    def _cache(self, c, slot, h, model, values, directory):
        probe=slot['probe']; config=dict(self.defaults,**mh_config(c,values['initial'].tolist()))
        tape={k:values[k][:,:config['draws']] for k in ('noise','log_uniform','directions')}
        binding=dict(input_file_sha256=c['input']['sha256'],tape_sha256=tape_hash(tape),target_id=model.target_id,config=config)
        records=[None]*4; states=['not_run']*4; replays=[]; kind='absent'
        if h['attempts']:
            folder=relative_file(self.root,directory+'/'+h['attempts'][-1]['attempt_id']+'/cache')
            request=dict(capsule=c,capsule_sha256=fingerprint(c),probe=probe)
            if (folder/'MANIFEST.json').exists():
                if c.get('compact_execution_contract'):
                    from compact_cache_evidence import read_cached_probe as read_compact_probe
                    report=read_compact_probe(folder)
                else:report=read_cached_probe(folder)
                if json.loads((folder/'request.json').read_text()) != request or report['binding'] != binding: raise ValueError('Cache actual input/capsule differs')
                records=report['observation']['records']; states=report['observation']['execution_outcomes']; kind='sealed'
            else:
                records,states=self._partial(folder,c,probe,request,binding); kind='partial'
            for i,record in enumerate(records):
                if record is not None and record['technical_output_valid']:
                    diag=record['diagnostics']
                    if diag['tensor_device'].split(':')[0] != c['task']['device'] or diag['tensor_dtype'] != 'torch.float64': raise ValueError('Cached device/precision differs')
                    replay=self._replay(model,config,values,folder/record['actual_array_file'])
                    if not replay['passed']: raise ValueError('Receiver cached path/event replay failed')
                    replays.append(dict(execution_index=i,**replay))
        reducer=summarize_probe
        if c.get('compact_execution_contract'):
            from compact_cache_summary import summarize_probe as compact_reducer
            reducer=compact_reducer
        summary=reducer(probe,records,expected_tape_sha256=binding['tape_sha256'],expected_target_id=binding['target_id'],expected_config=config)
        available=h['summary']['outcome']=='measurement_available'
        if available and not summary['all_executions_valid']: raise ValueError('Eligible measurement lacks four valid calls')
        return dict(probe=probe,binding=binding,observation=dict(records=records,execution_outcomes=states),
            numerical_summary=summary,numerical_evidence_kind=kind,independent_replays=replays,
            measurement_available=available,cached_seconds=summary['cached_seconds'] if available else None,
            samples_eligible=False,new_independent_repetitions=0)

    def _partial(self, folder, c, probe, request, binding):
        records=[None]*4; states=['not_run']*4; gap=False
        if not folder.exists(): return records,states
        for name,expected in [('request.json',request),('binding.json',binding)]:
            path=folder/name
            if path.exists() and json.loads(path.read_text()) != expected: raise ValueError('Partial cache binding differs')
        for i in range(4):
            start=folder/f'execution-{i}.started.json'; finish=folder/f'execution-{i}.json'; candidate=folder/f'candidate-{i}.json'
            if not start.exists():
                if finish.exists() or candidate.exists(): raise ValueError('Partial cache call lacks start')
                gap=True; continue
            if gap or not (folder/'request.json').exists() or not (folder/'binding.json').exists(): raise ValueError('Partial cache ordering differs')
            marker=json.loads(start.read_text())
            if marker['execution_index']!=i or marker['probe_id']!=probe['id']: raise ValueError('Partial cache marker differs')
            if not finish.exists() and not candidate.exists():
                states[i]='infrastructure_interruption'; gap=True; continue
            record=json.loads((finish if finish.exists() else candidate).read_text()); records[i]=record
            name=record['actual_array_file']
            if name is not None:
                if name!=f'execution-{i}.npz' or file_hash(folder/name)!=record['actual_array_sha256']: raise ValueError('Partial cache raw binding differs')
                q=read_member(folder/name,'unconstrained',c['controls']['maximum_member_bytes'])
                a=read_member(folder/name,'accept',c['controls']['maximum_member_bytes'])
                shape=(c['controls']['chains'],binding['config']['draws'],c['target']['dimension'])
                if q.shape!=shape or q.dtype!=np.float64 or a.shape!=shape[:2] or a.dtype!=np.bool_: raise ValueError('Partial cache raw shape/type differs')
            elif record['technical_output_valid'] or record['actual_array_sha256'] is not None: raise ValueError('Missing cache raw cannot be valid')
            if record['technical_output_valid']:
                if not finish.exists() or not record['audit']['passed'] or any(record['audit']['acceptance_mismatches']): raise ValueError('Partial cache validity lacks audit')
                states[i]='valid'
            elif record.get('post_execution_error'):
                states[i]='resource_failure' if record['post_execution_error']['type'] in ('MemoryError','OutOfMemoryError') else 'infrastructure_interruption'
            elif record['status']=='failed' or record.get('audit') is not None: states[i]='numerical_failure'
            else: states[i]='infrastructure_interruption'
            if not finish.exists(): gap=True
        return records,states
