#!/usr/bin/env python3
"""Portable evidence reconstruction for technical NUTS localization only."""
import argparse
import csv
import itertools
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote
import numpy as np
from nuts_events import atomic_json,sha
from nuts_runtime import verify
from nuts_evidence import read_events,phase_path,paired_prefixes,failure_stage,qualification_check
from nuts_registry import MODELS


def read(path):return json.loads(Path(path).read_text())


def records_from(root):
    db=sqlite3.connect('file:'+quote(str((root/'calls.sqlite').resolve()),safe='/')+'?mode=ro',uri=True)
    try:
        records=[dict(id=i,phase=p,request=json.loads(r),request_sha256=s,registered_ns=t,outcome=json.loads(o) if o else None)
            for i,p,r,s,t,o in db.execute('SELECT * FROM calls ORDER BY registered_ns,id')]
    finally:db.close()
    return records


def resource_summary(directory):
    rows,truncated=read_events(directory/'ownership.ndjson')
    rss=[];commit=[];private=[];memory_messages=[];exit_codes={};private_incomplete=0
    for row in rows:
        rss.append(row['sampled_rss_bytes']);commit.append(row['kernel_peak_job_commit_bytes'])
        processes=row.get('retained_process_handles',[]);running=[x for x in processes if x['state']=='running']
        observed=[x['private_bytes'] for x in running if x.get('private_bytes') is not None]
        if len(observed)!=len(running) or len(running)!=row['active_processes']:private_incomplete+=1
        if observed:private.append(sum(observed))
        for item in processes:
            if item['exit_code'] is not None:exit_codes[f"{item['pid']}:{item['creation_filetime']}"]=item['exit_code']
        memory_messages.extend(m for m in row.get('completion_messages',[]) if m['message'] in (9,10))
    return dict(max_sampled_tree_rss_bytes=max(rss) if rss else None,
        kernel_peak_job_commit_bytes=max(commit) if commit else None,
        max_sampled_available_private_sum_bytes=max(private) if private else None,
        private_incomplete_observations=private_incomplete,observations=len(rows),truncated_last_observation=truncated,
        memory_limit_messages=memory_messages,captured_exit_codes=exit_codes,
        missing_messages_exclude_resource_failure=False)


def analyze(root,output):
    root=root.resolve();output=output.resolve()
    if output.exists():raise FileExistsError('Use a new companion analysis directory')
    records=records_from(root)
    if any(r['outcome'] is None for r in records):raise RuntimeError('Recover/verify registered calls on Windows before portable analysis')
    if len([r for r in records if r['phase']!='diagnostic'])>48:raise ValueError('Technical call limit exceeded')
    task_rows=[];chains=[];resources={};comparisons=[]
    for record in records:
        directory=root/'calls'/record['id'];verify(directory,record['outcome'])
        request=record['request'];resource=resource_summary(directory);resources[record['id']]=resource
        outcome=record['outcome']
        task_rows.append(dict(id=record['id'],phase=record['phase'],model=request['model'],workers=request['workers'],
            legacy_diagnostics=request.get('diagnostics_enabled'),status=outcome['status'],
            original_task=request.get('case',{}).get('original_task',{}).get('id'),
            original_outcome=request.get('case',{}).get('original_outcome'),seconds=outcome.get('seconds'),
            max_sampled_tree_rss_bytes=resource['max_sampled_tree_rss_bytes'],
            kernel_peak_job_commit_bytes=resource['kernel_peak_job_commit_bytes'],
            memory_limit_messages=len(resource['memory_limit_messages']),posterior_samples_eligible=False))
        if record['phase']=='diagnostic':continue
        for stage in failure_stage(directory):
            chain=stage['chain'];folder=directory/f'chain-{chain}'
            warm=phase_path(folder,'warmup');sample=phase_path(folder,'sample')
            metadata=read(folder/'result-metadata.json') if (folder/'result-metadata.json').exists() else None
            chains.append(dict(id=record['id'],**stage,warmup_persisted=0 if warm is None else len(warm),
                sample_persisted=0 if sample is None else len(sample),
                baseline_status=metadata['status'] if metadata else None,
                diagnostic_record_available=bool(metadata and metadata.get('chain_records')),
                metadata_file=(folder/'result-metadata.json').relative_to(root).as_posix() if metadata else None))
    for model in MODELS:
        selected=[r for r in records if r['phase']=='main' and r['request']['model']==model]
        for left,right in itertools.combinations(selected,2):
            comparisons.append(dict(model=model,left=left['id'],right=right['id'],
                rows=paired_prefixes(root/'calls'/left['id'],root/'calls'/right['id'])))
    qualifications=[]
    for round_id in sorted({r['request']['round'] for r in records if r['phase']=='qualification'}):
        selected=[r for r in records if r['phase']=='qualification' and r['request']['round']==round_id]
        qualifications.append(dict(round=round_id,**qualification_check(root,selected)))
    output.mkdir(parents=True)
    for name,rows in [('calls.csv',task_rows),('chains.csv',chains)]:
        if rows:
            with (output/name).open('w',encoding='utf-8',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    atomic_json(output/'resources.json',resources);atomic_json(output/'paired-prefixes.json',comparisons)
    atomic_json(output/'qualification-reconstruction.json',qualifications)
    result=dict(identity='windows-nuts-localization-analysis-v1',calls=len(records),
        new_registered_four_chain_calls=sum(r['phase']!='diagnostic' for r in records),
        diagnostic_jobs=sum(r['phase']=='diagnostic' for r in records),
        main_registered=sum(r['phase']=='main' for r in records),
        main_completed=sum(r['phase']=='main' and r['outcome']['status']=='completed' for r in records),
        registry_sha256=sha(root/'calls.sqlite'),new_sampler_calls_by_analysis=0,
        historical_failures_reclassified=0,posterior_samples_added=0,
        protocol_sha256=sha(root/'protocol.json') if (root/'protocol.json').exists() else None,
        inference='Stage evidence and selected technical contrasts; not a population failure rate, convergence check or performance benchmark')
    atomic_json(output/'SUMMARY.json',result)
    (output/'README.md').write_text('''# NUTS technical localization companion

`calls.csv` retains every registered call, including qualification, failures and interruptions. `chains.csv` reports the last durable stage and available prefix, not a root-cause verdict. `paired-prefixes.json` compares only shared saved states and actual RNG snapshots; missing evidence remains missing.

`resources.json` separates sampled tree RSS, kernel Job peak commitment and available private-memory observations. Private sums with incomplete coverage are lower-information observations, not full peaks. Missing Job messages cannot exclude a resource limit event. Captured process handles bind available exit codes; fast exits may lack a captured code.

New instrumentation changes I/O, object lifetime and scheduling. A successful diagnostics-bypassed condition can support association with that stage; it cannot by itself identify ESS as the cause. A failure not reproduced remains unresolved. All 105 historical failures retain their original labels. These selected cases and confirmation calls add no formal independent repetitions or eligible posterior samples.
''',encoding='utf-8')
    atomic_json(output/'checksums.json',{p.name:sha(p) for p in output.iterdir() if p.is_file()})
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analyze(a.study,a.output)
