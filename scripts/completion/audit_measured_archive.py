"""Rebuild measured-workflow evidence from a moved, read-only bundle.

No sampler, operating-system process query, or R fit is launched. Stored R
inputs are compared with reconstructed bytes; actual R runs remain separately
documented evidence in the bundle.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from formal_runtime import file_hash,fingerprint,atomic_json
from formal_evidence import RuntimeEvidence,inside
from formal_runtime_analysis import extract_task
from inference_targets import build_target
from audit_measured_workflow import phase_checks


def audit(bundle,output):
    bundle=bundle.resolve();output=output.resolve()
    if output.exists() or output.is_relative_to(bundle) or bundle.is_relative_to(output):
        raise ValueError('Fresh analysis output outside source bundle required')
    manifest=json.loads((bundle/'MANIFEST.json').read_text())
    for name,h in manifest.items():
        if file_hash(inside(bundle,name))!=h:raise ValueError('Bundle asset differs: '+name)
    m=json.loads((bundle/'measurement-profile.json').read_text())
    p=json.loads((bundle/'scientific-protocol.json').read_text())
    for doc,key in ((m,'measurement_sha256'),(p,'protocol_sha256')):
        unsigned=dict(doc);digest=unsigned.pop(key)
        if fingerprint(unsigned)!=digest:raise ValueError('Protocol checksum differs')
    if m['identity']!='measured-workflow-technical-mac-v1' or m['dependency_protocol_sha256']!=p['protocol_sha256']:
        raise ValueError('Unsupported measurement dependency')
    for source in (m['source_files'],p['source_files']):
        for name,h in source.items():
            if file_hash(ROOT/name)!=h:raise ValueError('Required source differs: '+name)
    prior=json.loads((bundle/'initial-receipt.json').read_text())
    if prior['measurement_sha256']!=m['measurement_sha256']:raise ValueError('Measurement receipt differs')
    locations={h['original']:'run/tasks/'+h['task']['id'] for h in prior['histories']}
    snapshot=bundle/'registry/registry.sqlite3';output.mkdir(parents=True)
    rows=[];diagnostics=[]
    with RuntimeEvidence(snapshot,manifest['registry/registry.sqlite3'],bundle,locations) as evidence:
        for history,task in zip(prior['histories'],m['tasks'],strict=True):
            if history['task']!=dict(task,protocol_sha256=m['measurement_sha256']):raise ValueError('Task receipt differs')
            item=next(x for x in p['targets'] if x['name']==task['model']);model=build_target(item,None,'cpu')
            discard=0 if task['kernel']=='nuts' else p['mh_discard'];total=discard+p['draws']
            config={} if task['kernel']=='nuts' else dict(kernel=task['kernel'],executor=task['executor'],device='cpu',
                draws=total,chains=p['chains'],step_size=item['step_'+task['kernel']],window=p['window'],
                atol=p['atol'],rtol=p['rtol'],max_iter=total if task['executor']=='online_picard' else p['quasi_deer_max_iter'],
                audit=False,on_failure='error',memory_limit_mb=p['memory_limit_mb'])
            contract=dict(task=history['task'],original=history['original'],model=task['model'],
                workflow='cpu-'+task['kernel']+'-'+task['executor'],budget=p['draws'],replicate=str(task['replicate']),
                scientific_task=task,scientific_protocol_sha256=p['protocol_sha256'],science_directory='attempt-0001',
                target_id=model.target_id,chains=p['chains'],discard=discard,nuts_warmup=p['nuts_warmup'],expected_config=config,
                input_relative='dependency-inputs/'+item['input'],input_sha256=p['inputs'][item['input']]['sha256'],
                actual_input_sha256=p['inputs'][item['input']]['actual_sha256'])
            destination=output/task['id'];row=extract_task(evidence,contract,model,destination)
            if row['outcome']!='valid' or row['function_status']!='completed':raise ValueError('Ineligible task in validation')
            attempt=inside(bundle,locations[history['original']])/'attempt-0001'
            old=json.loads((attempt/'diagnostics/estimates.json').read_text())
            if row['means']!=old['means'] or row['names']!=old['names']:raise ValueError('Function values differ')
            if row['history']['attempts']!=history['attempts'] or row['history']['summary']!=history['summary']:
                raise ValueError('Original history/cost differs')
            if file_hash(destination/'functions.bin')!=file_hash(attempt/'diagnostics/functions.bin'):
                raise ValueError('Reconstructed R input differs')
            metadata=json.loads((attempt/'fit.json').read_text());candidate=json.loads((attempt/'candidate.json').read_text())
            ordinary=json.loads((attempt/'ordinary-output.json').read_text());worker=json.loads((attempt/'worker-result.json').read_text())
            external=json.loads((attempt/'external-audit.json').read_text())
            if ordinary['samples_eligible'] is not False or not external['samples_eligible'] or external!=metadata['external_audit']:
                raise ValueError('Delayed audit eligibility differs')
            if file_hash(attempt/'candidate.json')!=metadata['ordinary_candidate_metadata_sha256'] or file_hash(attempt/'fit.npz')!=metadata['ordinary_candidate_arrays_sha256']:
                raise ValueError('Original candidate changed')
            if task['kernel']!='nuts' and (candidate['audit'] is not None or candidate['config']['audit'] is not False):
                raise ValueError('Ordinary candidate contained a trajectory audit')
            measured=json.loads((bundle/'run'/(task['id']+'-measurement.json')).read_text())
            if measured['task']!=task or measured['measurement_sha256']!=m['measurement_sha256']:
                raise ValueError('External timing identity differs')
            phases={x['name']:x for x in phase_checks(attempt/'phases.json')};phase_checks(attempt/'ordinary-phases.json')
            ordinary_wall=worker['ordinary_process']['ordinary_process_wall_seconds'];audit_wall=measured['audited_task_invocation_wall_seconds']
            if not 0<ordinary_wall<=phases['ordinary_process_startup_through_exit']['wall_seconds']<audit_wall:
                raise ValueError('Timing containment differs')
            diagnostics.extend(json.loads((attempt/'diagnostics/posterior.json').read_text())['results'][task['id']])
            rows.append(dict(task=task,means_exact=True,R_input_bytes_exact=True,historical_costs_exact=True,
                ordinary_process_wall_seconds=ordinary_wall,audited_task_invocation_wall_seconds=audit_wall,
                independent_audit_phase_seconds=phases['independent_research_audit_after_ordinary_exit']['wall_seconds'],
                costs_are_nested=True,cached_execution_measured=False))
    result=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_manifest_sha256=file_hash(bundle/'MANIFEST.json'),measurement_sha256=m['measurement_sha256'],
        archive_assets_checked=len(manifest),tasks_rebuilt=len(rows),rows=rows,
        finite_function_rhat_above_1_01=sum(x.get('rhat') is not None and x['rhat']>1.01 for x in diagnostics),
        stored_diagnostic_rows=len(diagnostics),new_MCMC_fits=0,new_R_invocations=0,
        formal_inference_complete=False,native_Windows_validated=False,
        scope='Moved archive with explicit historical-ID mapping; saved costs, values and R bytes reconstructed. No new precision/coverage claim.')
    atomic_json(output/'receipt.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(audit(**vars(parser.parse_args())),indent=2))
