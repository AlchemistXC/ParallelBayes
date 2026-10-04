"""Follow the actual first observed roundoff discrepancy in independent NumPy.

This post hoc controlled suffix replay does not revise validity or add samples.
It is intentionally distinct from the initial-coordinate ULP probes, which did
not reproduce the failing chain's amplification in the first companion.
"""
import argparse,json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'r-package/inst/python'),str(ROOT/'examples'),str(ROOT/'scripts/completion')]
from parallelbayes.reference import numpy_reference,make_reference
from affine_target import affine_model
from mechanism_runner import identity,sha,actual_hash,write


def inspect(run,inputs,protocol,companion,output):
    run,inputs,companion,output=map(lambda p:Path(p).resolve(),[run,inputs,companion,output])
    if output.exists() or any(p in output.parents for p in [run,inputs,companion]):raise ValueError('Fresh separate output required')
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if identity(unsigned)!=digest:raise ValueError('Protocol differs')
    for name,h in p['source_files'].items():
        if sha(ROOT/name)!=h:raise ValueError('Frozen source changed')
    contract=json.loads((companion/'analysis-contract.json').read_text())
    for name,h in json.loads((companion/'manifest.json').read_text()).items():
        if sha(companion/name)!=h:raise ValueError('Companion differs')
    if contract['original_protocol_sha256']!=digest:raise ValueError('Companion protocol differs')
    task=contract['original_task'];folder=run/task['model']/task['id'];state=json.loads((folder/'state.json').read_text())
    if state['task']!=task or task['id']!='4dc55fe41afd7ee147b2':raise ValueError('Unexpected task')
    for name,h in state['assets'].items():
        if sha(folder/name)!=h:raise ValueError('Original asset differs')
    item=next(t for t in p['targets'] if t['name']=='H1')
    old=json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())
    base=make_reference(old['models']['H1']);g=item['geometry'];model=affine_model(base,g['center'],g['factor'])
    if model.target_id!=state['target_id']:raise ValueError('Target differs')
    meta=json.loads((folder/state['attempt']/'fit.json').read_text());c=meta['config']
    with np.load(folder/state['attempt']/'fit.npz',allow_pickle=False) as z:path=z['failed_trajectory'].copy()
    with np.load(companion/'localization.npz',allow_pickle=False) as z:oracle=z['oracle'].copy();events=z['oracle_accept'].copy()
    name=task['input']
    if sha(inputs/name)!=p['master_inputs'][name]['sha256']:raise ValueError('Input differs')
    with np.load(inputs/name,allow_pickle=False) as z:tape={k:z[k][:,:c['draws']].copy() for k in ['noise','log_uniform','directions']}
    if actual_hash(tape)!=meta['tape_sha256']:raise ValueError('Tape differs')
    output.mkdir(parents=True);rows=[];arrays={}
    for ch in range(path.shape[0]):
        differences=np.flatnonzero(np.any(path[ch]!=oracle[ch],axis=1))
        if not differences.size:
            rows.append(dict(chain=ch,probe_performed=False,reason='No original path difference'));continue
        index=int(differences[0]);noise=tape['noise'][ch,index+1:];logu=tape['log_uniform'][ch,index+1:]
        baseline,baseline_events=numpy_reference(model,'mala',oracle[ch,index],noise,logu,c['step_size'])
        if not np.array_equal(baseline,oracle[ch,index+1:]) or not np.array_equal(baseline_events,events[ch,index+1:]):
            raise ValueError('Unchanged-start suffix does not reproduce original independent oracle')
        perturbed,perturbed_events=numpy_reference(model,'mala',path[ch,index],noise,logu,c['step_size'])
        delta=path[ch,index]-oracle[ch,index];effect=np.max(abs(perturbed-baseline),axis=1)
        limit=100*(c['atol']+c['rtol']*max(1.,float(np.max(abs(path[ch])))))
        above=np.flatnonzero(effect>limit);events_changed=np.flatnonzero(perturbed_events!=baseline_events)
        rows.append(dict(chain=ch,probe_performed=True,first_original_difference_zero_based=index,
            initial_delta=delta.tolist(),initial_max_abs_delta=float(np.max(abs(delta))),
            unchanged_start_reproduces_original_oracle_exactly=True,
            max_suffix_effect=float(effect.max()),observed_amplification=float(effect.max()/np.max(abs(delta))),
            original_path_limit=limit,first_effect_above_original_limit_zero_based=int(above[0]+index+1) if above.size else None,
            acceptance_mismatches=int(events_changed.size),first_acceptance_mismatch_zero_based=int(events_changed[0]+index+1) if events_changed.size else None,
            max_distance_from_original_torch_suffix=float(np.max(abs(perturbed-path[ch,index+1:])))))
        arrays[f'chain{ch}_baseline']=baseline;arrays[f'chain{ch}_perturbed']=perturbed
        arrays[f'chain{ch}_baseline_accept']=baseline_events;arrays[f'chain{ch}_perturbed_accept']=perturbed_events
    np.savez_compressed(output/'suffixes.npz',**arrays)
    result=dict(original_task=task,protocol_sha256=digest,analysis_source_sha256=sha(Path(__file__)),
        companion_summary_sha256=sha(companion/'summary.json'),numpy=np.__version__,chains=rows,
        design='Post hoc controlled propagation of actual first observed state discrepancy; unchanged and changed starts use exactly the same independent NumPy suffix and random arrays.',
        original_failure_remains_failed=True,independent_repetitions_added=0,arrays_sha256=sha(output/'suffixes.npz'),
        limitation='This is an observed amplification under a selected tape, not a general stability bound, full decomposition of all later roundoff, or proof of chaos or invariant-distribution error.')
    write(output/'summary.json',result);write(output/'manifest.json',{f.name:sha(f) for f in sorted(output.iterdir()) if f.is_file()})
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['run','inputs','protocol','companion','output']:parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();print(json.dumps(inspect(a.run,a.inputs,a.protocol,a.companion,a.output),indent=2))
