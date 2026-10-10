#!/usr/bin/env python3
"""Extract the planned NUTS case set from verified old evidence; never sample."""
import argparse
import importlib
import json
from pathlib import Path
import sys
import numpy as np
from h1_function_paths import Evidence,sha,save
ROOT=Path(__file__).resolve().parents[2]
EXPECTED_MANIFEST='38e68557b03e4e153a2321fe6b8e5210c99557500746c86f855480edc81ab75e'


def prepare(evidence_root,manifest,selection_path,output):
    if output.exists():raise FileExistsError('Fresh preparation output required')
    evidence=Evidence(evidence_root,manifest,EXPECTED_MANIFEST)
    if output.is_relative_to(evidence.root) or evidence.root.is_relative_to(output):raise ValueError('Separate output required')
    selection=json.loads(selection_path.read_text());cases=selection['NUTS'];diagnostics=selection['NUTS_diagnostic_only']
    if len(cases)!=9 or len(diagnostics)!=3:raise ValueError('Fixed nine-case/three-diagnostic frame required')
    frozen=evidence.read('protocol.json')['source_files']
    for name,digest in frozen.items():
        if sha(evidence.path('source/'+name))!=digest:raise ValueError('Frozen source differs')
    sys.path.insert(0,str(evidence.root/'source/scripts/analysis'))
    science=importlib.import_module('formal_science')
    if Path(science.__file__).resolve()!=evidence.root/'source/scripts/analysis/formal_science.py':raise ValueError('Archived reader required')
    reader=science.ScientificReader(evidence.root,frozen,rscript='unused',r_library='unused',cross_platform=True)
    output.mkdir(parents=True);result=[];diags=[]
    for task in cases+diagnostics:
        evidence.seen={};prefix=f"formal-runs/batch-{task['batch']:02d}/main/tasks/{task['id']}/attempt-0001/"
        request=evidence.read(prefix+'request.json');c=request['capsule'];state=evidence.read(prefix+'state.json')
        candidate=evidence.read(prefix+'candidate.json')
        if request['capsule_sha256']!=science.fingerprint(c) or c['source_files']!=frozen:raise ValueError('Old capsule differs')
        if any(c['task'][k]!=task[k] for k in c['task']):raise ValueError('Selected task differs')
        if c['task']['budget']!=4096 or c['task']['kernel']!='nuts' or c['controls']['chains']!=4:raise ValueError('Unexpected planned NUTS task')
        evidence.path('inputs/'+task['input']);model,values=reader._context(c)
        seeds=np.asarray(values['nuts_seeds']);initial=np.asarray(values['initial'])
        if initial.shape!=(4,model.dimension) or seeds.shape!=(4,) or not np.isfinite(initial).all():raise ValueError('Initial shape/value differs')
        item=dict(original_task=task,original_outcome=state['outcome'],source_capsule=c,
                  target_id=candidate['target_id'],target_spec=model.spec,initial=initial.tolist(),chain_seeds=seeds.tolist(),
                  mac_reconstructed_target_id=model.target_id,mac_target_id_exact_match=model.target_id==candidate['target_id'],
                  original_actual_input_file_sha256=evidence.members['inputs/'+task['input']]['sha256'],
                  actual_initial_torch_python_numpy_rng_states='Pending native Windows preparation, then shared across all four conditions; integer seeds alone are not an equivalence claim',
                  no_new_formal_repetition=True)
        if task in cases:
            if state['outcome']!=task['original_outcome']:raise ValueError('Original classification differs')
            save(output/(task['model']+'-case.json'),item);result.append(task['id'])
        if task in diagnostics:
            if state['outcome']!='valid':raise ValueError('Diagnostic source must be valid')
            meta=evidence.read(prefix+'fit.json');raw=evidence.path(prefix+'fit.npz')
            if sha(raw)!=meta['ordinary_candidate_arrays_sha256']:raise ValueError('Original sampled arrays differ')
            q=science.read_member(raw,'unconstrained',128*1024**2)
            theta=science.read_member(raw,'draws',128*1024**2)
            if q.shape!=(4,4096,model.dimension) or theta.shape!=q.shape or not np.isfinite(q).all() or not np.isfinite(theta).all():raise ValueError('Diagnostic path differs')
            arrays=output/(task['model']+'-diagnostic.npz');np.savez_compressed(arrays,unconstrained=q,draws=theta)
            item.update(diagnostic_arrays_sha256=sha(arrays),diagnostic_roles=dict(legacy='unconstrained coordinates, four single-chain ESS calls',modern='original parameter coordinates, joint four-chain posterior diagnostics; distinct object'))
            save(output/(task['model']+'-diagnostic.json'),item);diags.append(task['id'])
        save(output/(task['id']+'-source-assets.json'),evidence.seen)
    if any(x in sys.modules for x in ('torch','jax')):raise ValueError('Sampler backend imported into extraction')
    report=dict(identity='windows-nuts-localization-inputs-v1',status='inputs_prepared_not_native_validated',
        selection_sha256=sha(selection_path),original_manifest_sha256=EXPECTED_MANIFEST,
        original_source_commit=evidence.read('protocol.json')['source_commit'],case_ids=result,diagnostic_ids=diags,
        new_sampler_calls=0,native_rng_states_prepared=False,windows_scientific_protocol_frozen=False,
        source_files_sha256={n:sha(ROOT/n) for n in ['scripts/analysis/prepare_nuts_localization.py','scripts/analysis/h1_function_paths.py']})
    save(output/'SUMMARY.json',report)
    save(output/'checksums.json',{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()})
    print(json.dumps(dict(cases=len(result),diagnostic_paths=len(diags),new_sampler_calls=0,bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('evidence','manifest','selection','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prepare(a.evidence.resolve(),a.manifest.resolve(),a.selection.resolve(),a.output.resolve())
