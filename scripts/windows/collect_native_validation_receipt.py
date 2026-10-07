"""Read retained finite-v2 outputs only; no sampler, random generator or CUDA import."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def collect(bundle, commands):
    import numpy as np
    protocol = read(bundle/'protocol.json')
    result = dict(schema='windows-finite-v2-delivery-summary-v1',
                  source_commit=protocol['source_commit'],
                  protocol_sha256=protocol['protocol_sha256'],
                  formal_scientific_repetitions=0,
                  new_sampler_calls_from_reader=0,
                  environment=read(bundle/'environment.json'),
                  freeze_manifest_sha256=digest(bundle/'freeze-manifest.json'))
    behavior = []
    for xml in sorted((bundle/'runtime-tests').glob('*/runtime.xml')):
        cases = list(ET.parse(xml).getroot().iter('testcase'))
        behavior.append(dict(directory=xml.parent.relative_to(bundle).as_posix(),
            tests=len(cases), failed=sum(c.find('failure') is not None or c.find('error') is not None for c in cases),
            skipped=sum(c.find('skipped') is not None for c in cases),
            case_names=[c.attrib['name'] for c in cases], xml_sha256=digest(xml)))
    result['behavior_attempts'] = behavior
    rows = []
    diagnostics = []
    paths = {}
    for attempt in sorted((bundle/'main/tasks').glob('*/attempt-*')):
        state = read(attempt/'state.json'); task = state['task']; fit = read(attempt/'fit.json')
        worker = read(attempt/'worker-result.json')
        row = dict(task=task, outcome=state['outcome'], samples_eligible=state['samples_eligible'],
            job_final=state['job_final'], sampled_job_rss_peak_bytes=state['observed_rss_peak_bytes'],
            managed_invocation_seconds=state['invocation_seconds'], ordinary_process=worker['ordinary_process'],
            worker_phases=read(attempt/'phases.json'), timing=fit.get('timing'),
            memory=fit.get('memory'), full_MH_audit=worker.get('full_MH_audit'),
            tape_sha256=fit.get('tape_sha256'), independent_audit=read(attempt/'external-audit.json'))
        row['actual_process_environment'] = read(attempt/'environment.json')
        members = {}
        for line in (attempt/'ownership.ndjson').read_text().splitlines():
            for m in json.loads(line)['members']:
                members[(m['pid'],m['creation_filetime'])] = m
        row['observed_owned_process_identities'] = list(members.values())
        if task['kernel'] != 'nuts':
            raw = np.load(attempt/'fit.npz', allow_pickle=False)
            row['array_shapes'] = {k:list(raw[k].shape) for k in raw.files}
            row['retained_acceptance_rate'] = float(raw['accept'][:,protocol['controls']['mh_discard']:].mean())
            row['all_rejection_chains'] = [i for i,a in enumerate(raw['accept']) if not a.any()]
            raw.close()
            row['diagnostics'] = {k:v for k,v in fit['diagnostics'].items() if k != 'rounds'}
            paths[(task['model'],task['device'],task['kernel'],task['executor'])] = (attempt,row)
        else:
            row['NUTS'] = {k:fit[k] for k in ('observed_worker_pids','workers_requested','workers_allocated',
                'threads_per_worker','process_start_method','chain_seeds','worker_records')}
        post = read(attempt/'diagnostics/posterior.json')
        diagnostics.extend(dict(task_id=task['id'],model=task['model'],workflow=task['workflow'],**d)
                           for records in post['results'].values() for d in records)
        rows.append(row)
    pairs=[]
    for model in ('G1','G2','W1'):
        for device in ('cpu','cuda'):
            for kernel, executor in (('rwm','online_picard'),('mala','quasi_deer')):
                a,ra=paths[(model,device,kernel,'sequential')]; b,rb=paths[(model,device,kernel,executor)]
                with np.load(a/'fit.npz',allow_pickle=False) as x,np.load(b/'fit.npz',allow_pickle=False) as y:
                    pairs.append(dict(model=model,device=device,kernel=kernel,
                        tape_sha256_equal=ra['tape_sha256']==rb['tape_sha256'],
                        acceptance_mismatches=int(np.count_nonzero(x['accept'] != y['accept'])),
                        maximum_unconstrained_difference=float(np.max(np.abs(x['unconstrained']-y['unconstrained']))),
                        maximum_constrained_difference=float(np.max(np.abs(x['draws']-y['draws']))),
                        both_frozen_independent_oracles_passed=ra['full_MH_audit']['passed'] and rb['full_MH_audit']['passed'],
                        differences_are_descriptive_no_new_tolerance=True))
    cache=[]
    for attempt in sorted((bundle/'cache/tasks').glob('*/attempt-*')):
        state=read(attempt/'state.json'); data=read(attempt/'cache/cache-result.json')
        calls=[]
        for record in data['observation']['records']:
            call = {k:v for k,v in record.items() if k not in ('config','diagnostics')}
            call['diagnostics'] = {k:v for k,v in record.get('diagnostics',{}).items() if k != 'rounds'}
            calls.append(call)
        cache.append(dict(task=state['task'],outcome=state['outcome'],job_final=state['job_final'],
            sampled_job_rss_peak_bytes=state['observed_rss_peak_bytes'],managed_invocation_seconds=state['invocation_seconds'],
            samples_eligible=state['samples_eligible'],measurement_available=state['measurement_available'],
            binding=data['binding'],summary=data['summary'],execution_outcomes=data['observation']['execution_outcomes'],
            calls=calls,phases=read(attempt/'cache/phases.json')))
    result.update(main=rows,main_outcomes=dict(Counter(r['outcome'] for r in rows)),
        cache=cache,cache_outcomes=dict(Counter(r['outcome'] for r in cache)),
        cache_calls=sum(len(r['calls']) for r in cache),paired_paths=pairs,R_diagnostics=diagnostics,
        R_diagnostic_rows=len(diagnostics),
        R_unavailable={k:sum(r.get(k) is None for r in diagnostics) for k in ('rhat','ess_bulk','ess_tail','mcse_mean')},
        R_rhat_over_1_01=sum(r.get('rhat') is not None and r['rhat']>1.01 for r in diagnostics),
        counts_are_not_statistical_convergence=True)
    result['CLI_commands'] = {d.name:dict(started=read(d/'started.json'),finished=read(d/'finished.json'))
        for d in sorted(commands.iterdir()) if d.is_dir() and (d/'finished.json').exists()}
    result['terminal_verification']={phase:read(bundle/read(bundle/phase/'latest-verified.json')['result'])
                                    for phase in ('main','cache')}
    gate=bundle/'native-acceptance.json'
    if gate.exists():
        result['native_acceptance_sha256']=digest(gate)
        result['native_acceptance_gate_sha256']=read(gate)['gate_sha256']
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--commands',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or a.output.resolve().is_relative_to(a.bundle.resolve()):
        raise ValueError('Use a new summary file outside the immutable bundle')
    data=collect(a.bundle,a.commands)
    a.output.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:data[k] for k in ('source_commit','protocol_sha256','main_outcomes','cache_outcomes','cache_calls','R_diagnostic_rows','R_unavailable','R_rhat_over_1_01')},indent=2))
