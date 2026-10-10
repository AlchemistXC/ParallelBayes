#!/usr/bin/env python3
"""Replay archived numerical failures without changing eligibility or tolerances.

This companion complements the formal reader, which replays eligible paths only.
No new random input, sampler workflow, R diagnostic or performance timing is run.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def review(delivery, manifest, manifest_sha256, tasks, output):
    root, out = Path(delivery).resolve(), Path(output)
    if out.exists(): raise FileExistsError(out)
    if sha(manifest) != manifest_sha256: raise ValueError('Original manifest differs')
    members=json.loads(Path(manifest).read_text())['files'];provenance={}
    def verified(name):
        p=root/name;expected=members[name]
        if p.stat().st_size!=expected['bytes'] or sha(p)!=expected['sha256']:
            raise ValueError('Original member differs: '+name)
        provenance[name]=expected['sha256'];return p
    def read(name): return json.loads(verified(name).read_text())
    protocol=read('protocol.json');sources=protocol['source_files']
    for name,digest in sources.items():
        p=verified('source/'+name)
        if sha(p)!=digest: raise ValueError('Protocol/source binding differs')
    # Import the archived independent reader only after checking all bound sources.
    sys.path.insert(0,str(root/'source/scripts/analysis'))
    from formal_science import ScientificReader, fingerprint, mh_config, tape_hash
    reader=ScientificReader(root,sources,rscript='unused',r_library='unused',cross_platform=True)
    frame=list(csv.DictReader(Path(tasks).open()))
    if len(frame)!=4144 or len({r['id'] for r in frame})!=4144:
        raise ValueError('Complete compact frame required')
    selected=[r for r in frame if r['outcome']=='numerical_failure']
    if len(selected)!=42 or {r['model'] for r in selected}!={'H1'}:
        raise ValueError('Frozen numerical failure frame differs')
    records=[];out.mkdir(parents=True)
    for task in selected:
        prefix=f"formal-runs/batch-{int(task['batch']):02d}/main/tasks/{task['id']}/attempt-0001/"
        state=read(prefix+'state.json');end=read(prefix+'completion.json');req=read(prefix+'request.json')
        c=req['capsule'];t=c['task'];candidate=read(prefix+'candidate.json');meta=read(prefix+'fit.json');audit=read(prefix+'external-audit.json')
        if (req['capsule_sha256']!=fingerprint(c) or c['source_files']!=sources or
                any(t[k]!=task[k] for k in ('id','workflow','model')) or
                t['budget']!=int(task['budget']) or t['replicate']!=int(task['replicate']) or
                state['outcome']!='numerical_failure' or state['samples_eligible'] is not False or
                end['state_sha256']!=members[prefix+'state.json']['sha256'] or
                meta['external_audit']!=audit or meta['audit']!=audit['audit'] or
                meta['audit']['passed'] is not False or audit['samples_eligible'] is not False):
            raise ValueError('Failure identity/eligibility differs')
        raw=verified(prefix+'fit.npz')
        if (meta['ordinary_candidate_arrays_sha256']!=sha(raw) or
                meta['ordinary_candidate_metadata_sha256']!=sha(root/(prefix+'candidate.json'))):
            raise ValueError('Candidate array binding differs')
        verified('inputs/'+t['input'])
        model,values=reader._context(c)
        config=dict(reader.defaults,**mh_config(c,values['initial'].tolist()))
        if (config!=candidate['config'] or config!=meta['config'] or
                meta['target_id']!=model.target_id or candidate['target_id']!=model.target_id):
            raise ValueError('Original numerical configuration/target differs')
        tape={k:values[k][:,:config['draws']] for k in ('noise','log_uniform','directions')}
        if candidate['tape_sha256']!=tape_hash(tape) or meta['tape_sha256']!=tape_hash(tape):
            raise ValueError('Archived actual random input binding differs')
        replay=reader._replay(model,config,values,raw)
        record=dict(id=t['id'],workflow=t['workflow'],budget=t['budget'],replicate=t['replicate'],
            original_outcome=state['outcome'],original_candidate_status=candidate['status'],
            original_stop=candidate['stopping_reason'],original_solver_status=candidate['diagnostics']['status'],
            original_residual=candidate['diagnostics']['residual'],original_audit=meta['audit'],
            original_transform_passed=audit['independent_transform_passed'],
            independent_mac_replay=replay,original_classification_changed=False,samples_eligible=False)
        records.append(record)
        (out/(t['id']+'.json')).write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
        print(json.dumps(dict(visited=len(records),id=t['id'],replay_passed=replay['passed'])),flush=True)
    summary=dict(schema='compact-numerical-failure-companion-v1',scope='Retrospective replay of original excluded paths; no reclassification',
        archived_source_files=len(sources),original_manifest_sha256=manifest_sha256,task_table_sha256=sha(tasks),
        source_assets_sha256=provenance,original_failure_count=len(records),
        original_candidate_statuses=dict(Counter(r['original_candidate_status'] for r in records)),
        original_stop_reasons=dict(Counter(r['original_stop'] for r in records)),
        original_solver_statuses=dict(Counter(str(r['original_solver_status']) for r in records)),
        original_event_mismatches=sum(sum(r['original_audit']['acceptance_mismatches']) for r in records),
        mac_replay_passed=sum(r['independent_mac_replay']['passed'] for r in records),
        mac_replay_failed=sum(not r['independent_mac_replay']['passed'] for r in records),
        mac_event_mismatches=sum(sum(r['independent_mac_replay']['acceptance_mismatches']) for r in records),
        mac_checked_transitions=sum(r['independent_mac_replay']['transitions'] for r in records),
        mac_maximum_path_error=max(max(r['independent_mac_replay']['maximum_path_error']) for r in records),
        original_maximum_path_error=max(max(r['original_audit']['max_abs_path_error']) for r in records),
        new_sampler_calls=0,new_formal_repetitions=0,new_R_diagnostic_calls=0,
        original_classifications_changed=0,excluded_paths_promoted_to_posterior=0)
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('delivery','manifest','manifest-sha256','tasks','output'):p.add_argument('--'+name,required=True)
    result=review(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in result.items() if k!='source_assets_sha256'},indent=2))
