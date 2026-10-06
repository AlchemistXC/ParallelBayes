"""Describe every frozen F2 cell, with raw identities and adverse outcomes retained."""
import argparse
import csv
import hashlib
import importlib.metadata as md
import json
from pathlib import Path
import statistics
import sys
import xml.etree.ElementTree as ET
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from mechanism_runner import read_plan,actual_hash


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def write(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();batch=a.batch.resolve();out=a.output.resolve()
    if out.exists() or out==batch or batch in out.parents:
        raise ValueError('Use a fresh separate summary directory')
    plan=read_plan(ROOT/'benchmark/protocols/mechanism-windows-pilot-v1.json')
    preflight=read(batch/'preflight.json')
    assert dict(sorted((d.metadata['Name'],d.version) for d in md.distributions() if d.metadata['Name']))==preflight['all_distributions']
    assert sha(Path(sys.executable).parents[1]/'PARALLELBAYES-FROZEN.json')==preflight['original_frozen_marker_sha256']
    inputs={}
    for key,expected in plan['inputs'].items():
        path=batch/'original-inputs'/(key+'.npz');assert sha(path)==expected['file_sha256']
        with np.load(path,allow_pickle=False) as z:assert actual_hash(dict(z))==expected['actual_sha256']
        inputs[key]=expected
    devices={};details=[];first_arrays={};raw_assets=0
    for device in ('cpu','cuda'):
        run=batch/('mechanism-'+device);analysis=batch/('analysis-'+device)
        summary=read(analysis/'summary.json')
        for name,h in read(analysis/'checksums.json').items():assert sha(analysis/name)==h
        assert summary['protocol_sha256']==plan['protocol_sha256'] and summary['input_verification']['mode']=='frozen_files'
        with (analysis/'workflows.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
        assert len(rows)==96
        counts={s:sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})}
        pairing=[];probes=[];replay_records=[];group_statuses=[];dtype_device=[];all_memory=[];all_rss=[]
        for g in plan['groups']:
            folder=run/'groups'/g['id'];state=read(folder/'state.json');group_statuses.append(state['status'])
            assert state['group']==g and state['device']==device
            for name,h in state['assets'].items():assert sha(folder/name)==h;raw_assets+=1
            attempt=folder/state['attempt']
            if (attempt/'comparison.json').exists():pairing+=read(attempt/'comparison.json')['pairs']
            for probe in sorted(attempt.glob('probe-w*/result.json')):
                p=read(probe);probes.append(dict(group=g['id'],width=p['shape'][1],status=p['status'],
                    numerical_checks=p.get('numerical_checks'),components_are_additive=p['components_are_additive']))
            for record in state['records']:
                meta=read(attempt/record['record']);replay_records.append(meta['status'])
                if meta['status']=='completed':
                    all_memory.append(meta['memory'])
                    all_rss += [meta['measurement']['rss_before'],meta['measurement']['rss_after']]
                if record['phase']!=0:continue
                row=dict(device=device,group=g['id'],model=g['model'],kernel=g['kernel'],replicate=g['replicate'],
                    chains=g['chains'],draws=g['draws'],step_size=g['step_size'],role=g['role'],label=record['label'],
                    status=meta['status'],raw_sha256=sha(attempt/record['raw']),record_sha256=sha(attempt/record['record']))
                if meta['status']=='completed':
                    diag=meta['diagnostics'];audit=meta['audit'];assert audit['passed']
                    assert all(v==0 for v in audit['acceptance_mismatches'])
                    dtype_device.append(dict(device=diag['tensor_device'],dtype=diag['tensor_dtype']))
                    assert diag['tensor_dtype']=='torch.float64'
                    assert (diag['tensor_device'].startswith('cuda') if device=='cuda' else diag['tensor_device']=='cpu')
                    with np.load(attempt/record['raw'],allow_pickle=False) as z:
                        arrays={k:z[k].copy() for k in ('unconstrained','draws','accept')}
                    assert all(np.isfinite(arrays[k]).all() for k in ('unconstrained','draws'))
                    first_arrays[(device,g['id'],record['label'])]=arrays
                    row.update(audit_passed=True,path_oracle_max_error=max(audit['max_abs_path_error']),
                        constrained_oracle_max_error=max(audit['max_abs_constrained_error']),acceptance_mismatches=0,
                        accepted=int(arrays['accept'].sum()),total_transitions=arrays['accept'].size,
                        all_rejected_chain_count=int(np.sum(np.sum(arrays['accept'],axis=1)==0)),
                        forward_maps=diag['forward_evals'],JVPs=diag['jvp_evals'],confirmed=diag['confirmed'],
                        solver_iterations=diag['iterations'],host_scalar_reads=diag['host_scalar_reads'],
                        host_scalar_wait_seconds=diag['host_scalar_wait_seconds'],residual=diag['residual'],
                        clips=diag['clips'],fallback=meta['fallback'],state_repairs=meta['state_repairs'],
                        memory=meta['memory'],timing=meta['timing'],measurement=meta['measurement'],
                        stopping_reason=meta['stopping_reason'],implementation=meta['implementation'])
                else:row.update(error=meta.get('error'),stopping_reason=meta.get('stopping_reason'))
                details.append(row)
        ratios=[float(r['paired_cached_ratio']) for r in rows if r['label']!='sequential' and r.get('paired_cached_ratio')]
        device_details=[r for r in details if r['device']==device and r['status']=='completed']
        cached=[r for r in rows if r['status']=='completed']
        devices[device]=dict(runtime=read(run/'run.json')['runtime'],groups_planned=36,
            groups_completed=group_statuses.count('completed'),groups_failed=group_statuses.count('failed'),groups_pending=36-len(group_statuses),
            workflows_planned=96,workflow_status_counts=counts,
            technical_execution_records=len(replay_records),technical_execution_status_counts={s:replay_records.count(s) for s in sorted(set(replay_records))},
            paired_path_checks=len(pairing),paired_path_checks_passed=sum(p['passed'] for p in pairing),
            acceptance_mismatches=sum(p.get('acceptance_mismatches',0) for p in pairing),
            maximum_paired_path_error=max((p['max_path_error'] for p in pairing if 'max_path_error' in p),default=None),
            maximum_oracle_path_error=max((r['path_oracle_max_error'] for r in device_details),default=None),
            probes=probes,probe_batches=len(probes),probe_batches_passed=sum(p['status']=='passed' for p in probes),
            initial_forward_maps=sum(r['forward_maps'] for r in device_details),initial_JVPs=sum(r['JVPs'] for r in device_details),
            initial_confirmed_transitions=sum(r['confirmed'] for r in device_details),
            initial_all_rejected_chain_records=sum(r['all_rejected_chain_count'] for r in device_details),
            cached_ratio_observations=len(ratios),cached_ratios_above_one=sum(x>1 for x in ratios),
            cached_ratio_range=[min(ratios),max(ratios)] if ratios else None,
            cached_sample_seconds_range=[min(float(r['cached_sample_seconds']) for r in cached),max(float(r['cached_sample_seconds']) for r in cached)] if cached else None,
            cached_api_wall_seconds_range=[min(float(r['api_wall_seconds']) for r in cached),max(float(r['api_wall_seconds']) for r in cached)] if cached else None,
            cached_host_wait_seconds_range=[min(float(r['host_scalar_wait_seconds']) for r in cached),max(float(r['host_scalar_wait_seconds']) for r in cached)] if cached else None,
            cached_process_CPU_percent_range=[min(float(r['process_cpu_percent']) for r in cached),max(float(r['process_cpu_percent']) for r in cached)] if cached else None,
            per_call_peak_allocated_bytes_max=max((m.get('peak_allocated_bytes',0) for m in all_memory),default=None) if device=='cuda' else None,
            per_call_peak_reserved_bytes_max=max((m.get('peak_reserved_bytes',0) for m in all_memory),default=None) if device=='cuda' else None,
            RSS_endpoint_bytes_range=[min(all_rss),max(all_rss)] if all_rss else None,
            memory_scope='Allocator peaks across recorded sampling calls; not a whole-process/probe peak. CPU RSS endpoints only.',
            terminal_resume=read(batch/(device+'-resume-verification.json')))
    cross=[]
    for g in plan['groups']:
        labels=['sequential']+[('quasi_deer' if g['kernel']=='mala' else 'online_picard')+f'-w{w}' for w in g['windows']]
        for label in labels:
            cpu=first_arrays.get(('cpu',g['id'],label));gpu=first_arrays.get(('cuda',g['id'],label))
            row=dict(group=g['id'],model=g['model'],kernel=g['kernel'],replicate=g['replicate'],label=label)
            if cpu is None or gpu is None:row.update(passed=False,status='unavailable_original_workflow_failed')
            else:
                error=float(np.max(np.abs(cpu['unconstrained']-gpu['unconstrained'])))
                events=int(np.sum(cpu['accept']!=gpu['accept']))
                row.update(status='checked',passed=error<=plan['tolerance']['paired_atol'] and events==0,
                    path_max_abs_error=error,constrained_max_abs_error=float(np.max(np.abs(cpu['draws']-gpu['draws']))),acceptance_mismatches=events)
            cross.append(row)
    command_index=[]
    for path in sorted((batch/'commands').glob('*/receipt.json')):
        rec=read(path)
        if 'exit_code' not in rec:
            assert any(Path(str(x)).name==Path(__file__).name for x in rec['command'])
            continue  # The enclosing recorder completes after this read-only summary.
        assert sha(path.parent/'stdout-stderr.log')==rec['log_sha256']
        command_index.append(dict(name=path.parent.name,exit_code=rec['exit_code'],elapsed_seconds=rec['elapsed_seconds'],
            source_commit=rec['source_commit'],command=rec['command'],receipt_sha256=sha(path),log_sha256=rec['log_sha256']))
    suite=ET.parse(batch/'tests.xml').getroot().find('testsuite');tests={k:int(suite.attrib[k]) for k in ('tests','failures','errors','skipped')}
    result=dict(status='complete_finite_pilot',protocol_sha256=plan['protocol_sha256'],
        frozen_source_commit=plan['source_commit'],execution_commit=preflight['execution_commit'],
        summary_source_sha256=sha(Path(__file__)),
        command_index_scope='Completed receipts at summary start. Full command tree, including the enclosing summary recorder, remains in the archive.',
        original_inputs=inputs,tests=tests,raw_assets_verified=raw_assets,devices=devices,
        cross_device_pairs=len(cross),cross_device_pairs_passed=sum(r['passed'] for r in cross),
        independent_tapes_per_model=2,technical_replays=3,
        scope='Finite F2 mechanism pilot; paired technical executions reuse actual arrays. No general speedup, stable ranking, convergence or formal accuracy conclusion.',
        formal_grid_started=False,Windows_process_collection_and_long_running_resource_guards_verified=False,
        cost_warning='Fixed-state operations overlap and are not additive. RSS endpoints are not peaks. Host waits include pending device work.',
        original_environment_unchanged=True)
    out.mkdir(parents=True)
    write(out/'SUMMARY.json',result);write(out/'first-audits.json',details);write(out/'cross-device-pairs.json',cross)
    write(out/'command-index.json',command_index)
    files={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write(out/'summary-SHA256.json',files)
    print(json.dumps({k:v for k,v in result.items() if k not in ('devices','original_inputs')},indent=2))


if __name__=='__main__':main()
