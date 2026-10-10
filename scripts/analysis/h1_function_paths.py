#!/usr/bin/env python3
"""Bounded immutable-input H1 companion. Never promotes failed paths."""
import argparse
from collections import Counter
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import psutil
from h1_path_metrics import functions, compare_functions, NAMES

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, obj):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def guard(output, controls):
    rss = psutil.Process().memory_info().rss
    if rss > controls['rss_limit_bytes']:
        raise MemoryError('Companion RSS limit reached')
    size = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    if size > controls['working_bytes_limit']-controls['one_task_reserve_bytes']:
        raise MemoryError('Companion working-data limit reached')
    if shutil.disk_usage(output).free < controls['free_disk_floor_bytes']:
        raise MemoryError('Free-disk safety floor reached')
    return dict(rss_bytes=rss, working_bytes=size)


class Evidence:
    def __init__(self, root, manifest, expected):
        self.root = Path(root).resolve()
        if sha(manifest) != expected:
            raise ValueError('Original manifest checksum differs')
        self.members = json.loads(Path(manifest).read_text())['files']
        self.seen = {}

    def path(self, name):
        path = (self.root/name).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Path outside evidence')
        item = self.members[name]
        if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise ValueError('Original evidence changed: '+name)
        self.seen[name] = item['sha256']
        return path

    def read(self, name):
        return json.loads(self.path(name).read_text())


def verified_resume(folder, task, protocol_sha, evidence):
    result = json.loads((folder/'result.json').read_text())
    if result['task'] != task or result['protocol_sha256'] != protocol_sha:
        raise ValueError('Resume task/protocol differs')
    for name, digest in result['source_assets_sha256'].items():
        if sha(evidence.path(name)) != digest:
            raise ValueError('Resume source differs')
    for name, digest in result['outputs_sha256'].items():
        if sha(folder/name) != digest:
            raise ValueError('Resume output differs')
    if result['original_classification_changed'] or result['new_formal_repetitions']:
        raise ValueError('Companion classification contract differs')
    return result


def run(protocol_path, evidence_root, manifest_path, selection_path, output):
    protocol_path, output = Path(protocol_path), Path(output).resolve()
    protocol = json.loads(protocol_path.read_text()); ph = sha(protocol_path)
    if protocol['identity'] != 'h1-function-path-companion-v1' or not protocol['frozen']:
        raise ValueError('Frozen H1 protocol required')
    if sys.version.split()[0] != protocol['python_version']:
        raise ValueError('Python version differs from frozen analysis')
    for name, version in protocol['required_versions'].items():
        if importlib.metadata.version(name) != version:
            raise ValueError('Dependency version differs: '+name)
    for name, digest in protocol['source_files'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('Companion source changed: '+name)
    if sha(selection_path) != protocol['selection_sha256']:
        raise ValueError('Selected inputs changed')
    selection = json.loads(Path(selection_path).read_text())['H1']
    if len(selection) != 80 or len({t['id'] for t in selection}) != 80:
        raise ValueError('Full 80-task frame required')
    evidence = Evidence(evidence_root, manifest_path, protocol['original_manifest_sha256'])
    if output.is_relative_to(evidence.root) or evidence.root.is_relative_to(output):
        raise ValueError('Output must be separate from immutable evidence')
    frozen = evidence.read('protocol.json')['source_files']
    for name, digest in frozen.items():
        if sha(evidence.path('source/'+name)) != digest:
            raise ValueError('Frozen dependency changed')
    # This fresh process imports the independently frozen reader, not current samplers.
    sys.path.insert(0, str(evidence.root/'source/scripts/analysis'))
    science = importlib.import_module('formal_science')
    if Path(science.__file__).resolve() != evidence.root/'source/scripts/analysis/formal_science.py':
        raise ValueError('Wrong reference reader imported')
    if any(x in sys.modules for x in ('torch', 'jax')):
        raise ValueError('Sampler backend loaded into independent companion')
    reader = science.ScientificReader(evidence.root, frozen, rscript='unused', r_library='unused', cross_platform=True)
    output.mkdir(parents=True, exist_ok=True)
    identity = dict(protocol_sha256=ph, selection_sha256=sha(selection_path),
                    original_manifest_sha256=protocol['original_manifest_sha256'])
    if (output/'IDENTITY.json').exists():
        if json.loads((output/'IDENTITY.json').read_text()) != identity:
            raise ValueError('Output belongs to another run')
    else:
        if any(output.iterdir()): raise ValueError('Nonempty unbound output directory')
        save(output/'IDENTITY.json', identity)
    rows=[]; new=0; reused=0; peak=0; started=time.time()
    for task in selection:
        folder=output/task['id']
        resource=guard(output, protocol['controls']); peak=max(peak, resource['rss_bytes'])
        if (folder/'result.json').exists():
            result=verified_resume(folder, task, ph, evidence); reused+=1
        else:
            if folder.exists(): raise ValueError('Incomplete task retained; inspect before explicit recovery: '+task['id'])
            evidence.seen={}
            prefix=f"formal-runs/batch-{task['batch']:02d}/main/tasks/{task['id']}/attempt-0001/"
            state=evidence.read(prefix+'state.json'); req=evidence.read(prefix+'request.json')
            meta=evidence.read(prefix+'fit.json'); candidate=evidence.read(prefix+'candidate.json')
            audit=evidence.read(prefix+'external-audit.json'); end=evidence.read(prefix+'completion.json')
            c=req['capsule']; t=c['task']
            if (req['capsule_sha256'] != science.fingerprint(c) or c['source_files'] != frozen or
                any(t[k] != task[k] for k in t) or state['outcome'] != task['original_outcome'] or
                state['samples_eligible'] != (task['original_outcome']=='valid') or
                end['state_sha256'] != evidence.members[prefix+'state.json']['sha256'] or
                meta['external_audit'] != audit or meta['audit'] != audit['audit'] or
                audit['samples_eligible'] != state['samples_eligible']):
                raise ValueError('Task/capsule/classification binding differs')
            raw=evidence.path(prefix+'fit.npz')
            if (meta['ordinary_candidate_arrays_sha256'] != sha(raw) or
                meta['ordinary_candidate_metadata_sha256'] != sha(evidence.path(prefix+'candidate.json'))):
                raise ValueError('Candidate binding differs')
            evidence.path('inputs/'+t['input'])
            model, values=reader._context(c)
            config=dict(reader.defaults, **science.mh_config(c, values['initial'].tolist()))
            if meta['config'] != config or candidate['config'] != config or model.target_id != meta['target_id']:
                raise ValueError('Model or transition configuration differs')
            tape={k:values[k][:,:config['draws']] for k in ('noise','log_uniform','directions')}
            if meta['tape_sha256'] != science.tape_hash(tape) or candidate['tape_sha256'] != science.tape_hash(tape):
                raise ValueError('Actual random arrays differ')
            if c['controls']['mh_discard'] != protocol['discard'] or t['model'] != 'H1' or config['kernel'] != 'mala':
                raise ValueError('Wrong target/kernel/discard')
            q=science.read_member(raw,'unconstrained',128*1024**2)
            saved=science.read_member(raw,'draws',128*1024**2)
            accept=science.read_member(raw,'accept',128*1024**2)
            shape=(config['chains'],config['draws'],model.dimension)
            if q.shape != shape or saved.shape != shape or q.dtype != np.float64 or saved.dtype != np.float64 or accept.shape != shape[:2] or accept.dtype != np.bool_:
                raise ValueError('Original path shape or type differs')
            if not np.isfinite(q).all() or not np.isfinite(saved).all():
                raise ValueError('Unexpected nonfinite original path')
            reference=[]; branches=[]
            for chain in range(config['chains']):
                ref, branch=science.numpy_reference(model,config['kernel'],values['initial'][chain],
                    tape['noise'][chain],tape['log_uniform'][chain],config['step_size'])
                reference.append(ref);branches.append(branch)
                resource=guard(output,protocol['controls']);peak=max(peak,resource['rss_bytes'])
            reference=np.stack(reference);branches=np.stack(branches)
            with np.errstate(over='ignore',invalid='ignore'):
                original=model.constrain(q);original_reference=model.constrain(reference)
                transform_delta=np.abs(original-saved);coordinate_delta=np.abs(q-reference)
            a,b=functions(original),functions(original_reference)
            metrics,delta=compare_functions(a,b,protocol['discard'])
            # Cross-check all finite function entries against the original mathematical definitions.
            from inference_estimands import evaluate
            if np.isfinite(a).all():
                historical=evaluate(model.spec,original)
                if historical['names'] != list(NAMES) or not np.array_equal(historical['values'],a):
                    raise ValueError('Independent companion function differs from frozen definition')
            folder.mkdir()
            np.savez_compressed(folder/'differences.npz', reference_unconstrained=reference,
                function_candidate=a, function_reference=b, function_delta=delta,
                coordinate_absolute_delta=coordinate_delta, original_transform_absolute_delta=transform_delta,
                acceptance_mismatch=branches != accept)
            result=dict(task=task,protocol_sha256=ph,original_classification_changed=False,
                samples_eligible_original=state['samples_eligible'],companion_arrays_are_posterior_samples=False,
                new_formal_repetitions=0,new_random_inputs=0,new_sampler_workflow_calls=0,
                deterministic_reference_transitions=int(accept.size),discard=protocol['discard'],
                reference='frozen independent NumPy float64; not an exact-arithmetic oracle',
                acceptance_mismatches=int(np.count_nonzero(branches != accept)),
                maximum_coordinate_difference_by_chain_coordinate=coordinate_delta.max(axis=1).tolist(),
                maximum_saved_transform_difference_by_coordinate=transform_delta.max(axis=(0,1)).tolist(),
                metrics=metrics,original_solver_status=candidate['diagnostics']['status'],
                original_solver_residual=candidate['diagnostics']['residual'],original_audit=meta['audit'],
                source_assets_sha256=dict(evidence.seen),outputs_sha256={'differences.npz':sha(folder/'differences.npz')})
            save(folder/'result.json',result);new+=1
        rows.append(result)
        print(json.dumps(dict(visited=len(rows),new_analyses=new,reused=reused,id=task['id'])),flush=True)
    summary=dict(identity=protocol['identity'],protocol_sha256=ph,total=len(rows),
        original_outcomes=dict(Counter(r['task']['original_outcome'] for r in rows)),
        original_input_labels=len({r['task']['replicate'] for r in rows}),
        acceptance_mismatches=sum(r['acceptance_mismatches'] for r in rows),
        deterministic_reference_transitions=sum(r['deterministic_reference_transitions'] for r in rows),
        new_formal_repetitions=0,new_random_inputs=0,new_sampler_workflow_calls=0,
        classifications_changed=0,failed_paths_promoted=0,
        function_metrics_with_nonfinite=sum(x['status']!='finite' for r in rows for x in r['metrics']),
        results_sha256={r['task']['id']:sha(output/r['task']['id']/'result.json') for r in rows})
    if (output/'SUMMARY.json').exists():
        if json.loads((output/'SUMMARY.json').read_text()) != summary: raise ValueError('Resume summary differs')
    else:save(output/'SUMMARY.json',summary)
    invocation=dict(new_analyses=new,reused=reused,observed_rss_bytes=peak,elapsed_seconds=time.time()-started,
                    scientific_sampler_calls=0,scope='companion analysis/replay; no formal sampling')
    calls=output/'invocations';calls.mkdir(exist_ok=True)
    save(calls/f'{time.time_ns()}.json',invocation)
    return dict(summary=summary,invocation=invocation)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('protocol','evidence','manifest','selection','output'):p.add_argument('--'+n,required=True)
    a=p.parse_args()
    try:
        result=run(a.protocol,a.evidence,a.manifest,a.selection,a.output)
        print(json.dumps(result['invocation']),flush=True)
    except Exception as exc:
        print(json.dumps(dict(status='stopped',error=type(exc).__name__,message=str(exc))),file=sys.stderr,flush=True)
        raise
