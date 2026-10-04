"""Rebuild three archived coordinator tasks without executing new MCMC.

Each model has one historical independent input; report technical point checks
and modern diagnostics, never manufacture repetitions or bootstrap intervals.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from analyze_budget_pilot import references
from formal_evidence import RuntimeEvidence,inside
from formal_runtime_analysis import extract_task
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_error_summary import summarize,paired_difference


def audit(bundle,output,rscript,r_library):
    bundle=bundle.resolve();output=output.resolve()
    if output.exists() or output.is_relative_to(bundle) or bundle.is_relative_to(output):
        raise ValueError('Fresh separate analysis output required')
    manifest=json.loads((bundle/'MANIFEST.json').read_text())
    for name,h in manifest.items():
        if file_hash(inside(bundle,name))!=h:raise ValueError('Archived dependency changed: '+name)
    companion=json.loads((bundle/'realworker/companion.json').read_text())
    unsigned=dict(companion);digest=unsigned.pop('companion_sha256')
    if fingerprint(unsigned)!=digest or companion['identity']!='formal-coordinator-companion-mac-v1':
        raise ValueError('Expected fixed technical companion identity')
    protocol=ROOT/'benchmark/protocols/formal-runtime-technical-mac-v1.json'
    p=json.loads(protocol.read_text());unsigned=dict(p);science_digest=unsigned.pop('protocol_sha256')
    if fingerprint(unsigned)!=science_digest or companion['dependency_protocol_sha256']!=science_digest:
        raise ValueError('Scientific dependency identity differs')
    for name,h in p['source_files'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Frozen scientific source changed: '+name)
    names=['scripts/completion/'+x for x in ('formal_evidence.py','formal_runtime_analysis.py',
        'formal_streaming.py','formal_outcomes.py','formal_uncertainty.py','formal_error_summary.py',
        'audit_runtime_analysis.py','posterior_diagnostics.R')]
    names+=['benchmark/analysis/outputs/completion-f3/reference-reuse.json',
        'benchmark/protocols/windows-native-v1.json','benchmark/analysis/outputs/wells-quadrature-v1/R12-n96.json',
        'benchmark/analysis/outputs/wells-quadrature-v1/result.json']
    source_files={name:file_hash(ROOT/name) for name in names}
    for name,h in source_files.items():
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit analysis source first: '+name)
    models,refs=references(p,None)
    snapshot=bundle/'registry/registry.sqlite3';old=json.loads((bundle/'realworker/receipt.json').read_text())
    locations={};contracts=[]
    for history in old['histories']:
        task=history['task'];science=next(t for t in p['tasks'] if t['id']==task['id'])
        item=next(t for t in p['targets'] if t['name']==science['model'])
        locations[history['original']]='realworker/'+('nuts' if task['kernel']=='nuts' else 'mh')+'/'+task['id']
        discard=0 if task['kernel']=='nuts' else p['mh_discard']
        expected_config={} if task['kernel']=='nuts' else dict(kernel=task['kernel'],executor=task['executor'],
            device=task['device'],draws=p['draws']+discard,chains=p['chains'],step_size=item['step_'+task['kernel']],
            window=p['window'],atol=p['atol'],rtol=p['rtol'],max_iter=p['draws']+discard if task['executor']=='online_picard' else p['quasi_deer_max_iter'])
        contracts.append(dict(task=task,original=history['original'],model=task['model'],
            workflow=task['device']+'-'+task['kernel']+'-'+task['executor'],budget=p['draws'],replicate=str(task['replicate']),
            scientific_task=science,scientific_protocol_sha256=science_digest,science_directory='attempt-0001',
            target_id=models[task['model']].target_id,chains=p['chains'],discard=discard,nuts_warmup=p['nuts_warmup'],
            expected_config=expected_config,input_relative='dependency-inputs/'+item['input'],
            input_sha256=p['inputs'][item['input']]['sha256'],actual_input_sha256=p['inputs'][item['input']]['actual_sha256']))
    output.mkdir(parents=True)
    identity=dict(identity='runtime-analysis-companion-mac-v1',dependency_companion_sha256=digest,
        dependency_manifest_sha256=file_hash(bundle/'MANIFEST.json'),registry_sha256=file_hash(snapshot),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_files=source_files,locations=locations,contracts=contracts,new_MCMC_fits=0,
        scope='Raw evidence adapter validation on three archived executions; one input per model, no repeated-run uncertainty')
    identity['analysis_sha256']=fingerprint(identity);atomic_json(output/'analysis-identity.json',identity)
    atomic_json(output/'reference-contract.json',refs)
    records=[];diagnostic_rows=[];binary_exact=0;means_exact=0;history_exact=0
    env=dict(os.environ)
    if r_library:env['R_LIBS_USER']=str(r_library)
    started=time.perf_counter()
    with RuntimeEvidence(snapshot,identity['registry_sha256'],bundle,locations) as evidence:
        for contract,prior_history in zip(contracts,old['histories']):
            name=contract['task']['id'];destination=output/'tasks'/name
            row=extract_task(evidence,contract,models[contract['model']],destination)
            if row['function_status']!='completed':raise ValueError('Historical eligible task no longer produces functions')
            old_attempt=inside(bundle,locations[contract['original']])/'attempt-0001'
            old_means=json.loads((old_attempt/'diagnostics/estimates.json').read_text())
            if row['names']!=old_means['names'] or row['means']!=old_means['means']:raise ValueError('Saved function point values differ')
            means_exact+=1
            if row['history']['summary']!=prior_history['summary'] or row['history']['attempts']!=prior_history['attempts']:
                raise ValueError('Saved attempt outcomes/costs differ')
            history_exact+=1
            if file_hash(destination/'functions.bin')!=file_hash(old_attempt/'diagnostics/functions.bin'):
                raise ValueError('Function transport bytes differ')
            atomic_json(destination/'transport.json',dict(fits=[dict(id=name,input='functions.bin',shape=row['extraction']['shape'],names=row['names'])],
                scope=identity['scope'],independent_unit='one existing four-chain technical input per model'))
            run=subprocess.run([str(rscript),'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(destination)],capture_output=True,text=True,env=env)
            (destination/'R.log').write_text(run.stdout+run.stderr)
            if run.returncode:raise RuntimeError('R reanalysis failed; original evidence unchanged')
            if file_hash(destination/'functions.bin.roundtrip')!=file_hash(destination/'functions.bin'):raise ValueError('R roundtrip differs')
            binary_exact+=1
            post=json.loads((destination/'posterior.json').read_text());prior=json.loads((old_attempt/'diagnostics/posterior.json').read_text())
            if post['R']!=prior['R'] or post['posterior']!=prior['posterior'] or post['results']!=prior['results']:
                raise ValueError('Archived modern diagnostics differ')
            diagnostic_rows.extend(post['results'][name]);records.append(row)
    points=[];pairs=[]
    for model in refs:
        selected=[r for r in records if r['model']==model];ref=refs[model]
        for j,name in enumerate(ref['names']):
            reference=dict(kind=ref['kinds'][j],value=ref['means'][j],mcse=ref['mcse'][j])
            for row in selected:
                points.append(dict(model=model,workflow=row['workflow'],function=name,
                    report=summarize([row['means'][j]],reference),interpretation='One technical squared discrepancy; not a repeated-run MSE estimate'))
            if model=='G1':
                a=next(r for r in selected if r['workflow'].endswith('sequential'))
                c=next(r for r in selected if r['workflow'].endswith('online_picard'))
                pairs.append(dict(model=model,function=name,report=paired_difference([a['means'][j]],[c['means'][j]],reference),
                    interpretation='One paired technical point; no resampling or interval'))
    atomic_json(output/'technical-points.json',dict(points=points,pairs=pairs,
        resampling_performed=False,reason='One independent input per model; do not fabricate repetitions'))
    atomic_json(output/'task-records.json',records)
    summary=dict(analysis_sha256=identity['analysis_sha256'],source_commit=identity['source_commit'],
        dependency_assets_checked=len(manifest),tasks=3,means_exact=means_exact,histories_exact=history_exact,
        R_transports_exact=binary_exact,modern_diagnostic_rows_exact=len(diagnostic_rows),
        finite_function_rhat_above_1_01=sum(r.get('rhat') is not None and r['rhat']>1.01 for r in diagnostic_rows),
        undefined_function_rhat=sum(r.get('rhat') is None for r in diagnostic_rows),
        technical_point_rows=len(points),technical_pair_rows=len(pairs),available_intervals=0,
        new_MCMC_fits=0,formal_inference_complete=False,native_Windows_validated=False,
        analysis_wall_seconds=time.perf_counter()-started,analysis_is_sampler_time=False)
    import resource
    summary['Python_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    summary['largest_child_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    summary['memory_scope']='Separate Mac lifetime peaks, not simultaneous tree memory or maximum formal task validation'
    for name,h in source_files.items():
        if file_hash(ROOT/name)!=h:raise ValueError('Analysis source changed')
    atomic_json(output/'summary.json',summary)
    atomic_json(output/'manifest.json',{f.relative_to(output).as_posix():file_hash(f) for f in sorted(output.rglob('*')) if f.is_file()})
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['bundle','output','rscript','r-library']:parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();print(json.dumps(audit(a.bundle,a.output,a.rscript,a.r_library),indent=2))
