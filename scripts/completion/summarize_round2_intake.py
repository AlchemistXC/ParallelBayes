"""Summarize retained cross-host differences without replacing original checks."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(batch,intake,output):
    if output.exists():raise FileExistsError('Preserve existing intake summary')
    record=read(intake/'independent-receipt/receipt.json')
    old=read(batch/'nuts-diagnostics/posterior.json')
    folder=intake/'independent-receipt/same-binary-mac-diagnostics'
    new=read(folder/'posterior.json');transport=read(folder/'transport.json')
    assert old['posterior']==new['posterior']=='1.7.0'
    rows=[];missing=[]
    for fit in transport['fits']:
        assert sha(folder/fit['input'])==fit['input_sha256']==sha(folder/(fit['input']+'.roundtrip'))
        a=old['results'][fit['id']];b=new['results'][fit['id']]
        assert len(a)==len(b)==len(fit['names'])
        for name,x,y in zip(fit['names'],a,b):
            assert x['variable']==y['variable']==name
            deltas={}
            for key in ('mean','sd','rhat','ess_bulk','ess_tail','mcse_mean'):
                u,v=x[key],y[key]
                assert (u is None)==(v is None),(fit['id'],name,key)
                if u is None:missing.append(dict(fit=fit['id'],function=name,metric=key));deltas[key]=None
                else:
                    assert np.isfinite(u) and np.isfinite(v)
                    deltas[key]=abs(u-v)
            rows.append(dict(fit=fit['id'],function=name,absolute_differences=deltas))
    m=record['MH'];n=record['NUTS_binary'];f2=read(intake/'mechanism-component-differences.json')
    result=dict(scope='Read-only cross-host reception and same-received-binary R companion; no new posterior fits or independent repetitions.',
        archive=read(intake/'archive-verification.json'),source_return_commit='ced54ef6ce945198339a138142dcdfede84f06bc',
        raw_assets_verified=record['raw_assets_verified'],curated_files_verified=record['curated_files_verified'],
        received_files_unchanged=record['received_files_unchanged'],
        MH=dict(workflows=len(m),paths_within_original_tolerance=sum(x['trajectory_within_frozen_tolerance'] for x in m),
            acceptance_mismatches=sum(x['acceptance_mismatches'] for x in m),exact_outputs=sum(x['original_exact_output_check'] for x in m),
            nonexact_outputs=sum(not x['original_exact_output_check'] for x in m),
            max_absolute_output_difference=max(x['output_max_abs_difference'] for x in m),
            max_scaled_output_difference=max(x['output_max_scaled_difference'] for x in m),
            strict_original_Mac_audit_passed=record['Mac_strict_MH_audit_passed'],
            Windows_same_host_audit_passed=record['Windows_same_host_MH_passed'],
            cross_device_pairs=len(record['cross_device_pairs']),cross_device_passed=sum(x['passed'] for x in record['cross_device_pairs']),
            interpretation='The original exact transform check remains failed on 60 cross-host outputs. Small descriptive residuals do not redefine it or invalidate the separate Windows same-host receipt.'),
        NUTS=dict(targets=len(record['NUTS']),exact_serial_spawn_array_pairs=sum(len(x['six_arrays_exact']) for x in record['NUTS']),
            preserved_Windows_binary_roundtrips=len(n),local_function_vectors_bitwise_equal=sum(x['local_functions_exact'] for x in n),
            max_local_function_difference=max(x['local_function_max_abs_difference'] for x in n),
            interpretation='Transport hashes are exact on received binary data; recomputation of functions on another host is not assumed bitwise identical.'),
        R_companion=dict(Windows_R=old['R'],Mac_R=new['R'],posterior=new['posterior'],fits=len(transport['fits']),function_rows=len(rows),
            missingness_matches=True,undefined_metric_entries=len(missing),
            max_absolute_differences={key:max((r['absolute_differences'][key] for r in rows if r['absolute_differences'][key] is not None),default=None) for key in ('mean','sd','rhat','ess_bulk','ess_tail','mcse_mean')},
            rows=rows,undefined=missing,Windows_result_sha256=sha(batch/'nuts-diagnostics/posterior.json'),Mac_result_sha256=sha(folder/'posterior.json')),
        F2=dict(original_files_verified=6,noise_and_directions_exact=all(r['components'][k]['equal'] for r in f2['rows'] for k in ('noise','directions')),
            differing_log_uniform_elements=sum(r['components']['log_uniform']['unequal'] for r in f2['rows']),
            max_log_uniform_difference=max(r['components']['log_uniform']['max_absolute_difference'] for r in f2['rows']),
            completed_workflows=0,pending_workflows=192,
            interpretation='Component localization; no specific libm/compiler causal claim. Original arrays supplied, no protocol hash or tolerance changed.'),
        new_MCMC_fits=0,new_independent_repetitions=0,formal_inference_complete=False)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:({j:v for j,v in value.items() if j not in ('rows','undefined')} if isinstance(value,dict) else value) for k,value in result.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('batch','intake','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();summarize(a.batch,a.intake,a.output)
