"""Bounded, per-fit extraction from immutable MCMC evidence.

The caller must establish task/protocol eligibility before extraction. Arrays
are bounded by one fit, not the full experiment; this is not chunked sampling.
"""
import hashlib
import json
import math
from pathlib import Path
import zipfile

import numpy as np

from formal_runtime import atomic_json, file_hash
from inference_estimands import evaluate


def read_member(path, name, maximum_member_bytes=128*1024**2):
    """Reject oversized/object NPY members before allocating their array."""
    if maximum_member_bytes <= 0:
        raise ValueError('Positive member byte allowance required')
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or len(names)>1024:
            raise ValueError('Duplicate or excessive archive members')
        member=name+'.npy';info=archive.getinfo(member)
        if info.file_size>maximum_member_bytes+65536:
            raise MemoryError('NPZ member exceeds configured byte allowance')
        with archive.open(member) as stream:
            version=np.lib.format.read_magic(stream)
            if version==(1,0):shape,order,dtype=np.lib.format.read_array_header_1_0(stream)
            elif version==(2,0):shape,order,dtype=np.lib.format.read_array_header_2_0(stream)
            else:raise ValueError('Unsupported NPY version')
            if dtype.hasobject or dtype.kind not in 'fibu':
                raise ValueError('Only plain numeric array members are supported')
            size=math.prod(shape)*dtype.itemsize
            if size>maximum_member_bytes:
                raise MemoryError('NPZ member exceeds configured byte allowance')
            if stream.tell()+size!=info.file_size:
                raise ValueError('NPY declared shape and member length differ')
        with archive.open(member) as stream:
            result=np.load(stream,allow_pickle=False)
        return result


def array_hash(array):
    """C-order array identity with bounded temporary copies for sliced rows."""
    a=np.asarray(array)
    h=hashlib.sha256(json.dumps(dict(shape=list(a.shape),dtype=a.dtype.str),
                                sort_keys=True,separators=(',',':')).encode())
    # Arrays here have a chain-leading dimension; at most a chain copy lives.
    for row in a:
        h.update(memoryview(np.ascontiguousarray(row)).cast('B'))
    return h.hexdigest()


def extract_functions(raw, expected_sha256, model, shape, discard, output,
                      maximum_member_bytes=128*1024**2, prefix_lengths=()):
    """Read one validated fit and save original-coordinate function transport.

    Shape is (chains,total_steps,parameters); discard removes a leading MH
    prefix. R transport is iterations x chains x functions, little-endian F.
    Return scalars/hashes only: no trajectory can leak into a study-wide cache.
    """
    raw=Path(raw);output=Path(output);shape=tuple(shape)
    if output.exists():raise FileExistsError('Use a fresh extraction directory')
    if file_hash(raw)!=expected_sha256:raise ValueError('Raw array checksum differs')
    if len(shape)!=3 or shape[0]<1 or shape[2]!=model.dimension or not 0<=discard<shape[1]:
        raise ValueError('Invalid expected shape/discard')
    if any(not isinstance(n,int) or not 0<n<=shape[1] for n in prefix_lengths):
        raise ValueError('Prefix outside trajectory')
    draws=read_member(raw,'draws',maximum_member_bytes)
    q=read_member(raw,'unconstrained',maximum_member_bytes)
    if draws.shape!=shape or q.shape!=shape or draws.dtype!=np.float64 or q.dtype!=np.float64:
        raise ValueError('Original/unconstrained array shape or precision differs')
    for start in range(0,shape[1],128):
        section=slice(start,start+128)
        if not np.isfinite(draws[:,section]).all() or not np.isfinite(q[:,section]).all():
            raise ValueError('Completed trajectory contains nonfinite values')
        np.testing.assert_allclose(draws[:,section],model.constrain(q[:,section]),rtol=1e-10,atol=1e-12)
    paths={str(n):array_hash(q[:,:n]) for n in prefix_lengths}
    del q
    functions=evaluate(model.spec,draws[:,discard:])
    del draws
    values=functions['values']
    if values.size>10000000:raise MemoryError('Function array exceeds R transport allowance')
    with zipfile.ZipFile(raw) as archive:has_accept='accept.npy' in archive.namelist()
    accept_rate=None;accept_hashes={}
    if has_accept:
        accept=read_member(raw,'accept',maximum_member_bytes)
        if accept.shape!=shape[:2] or accept.dtype!=np.bool_:
            raise ValueError('Acceptance array shape/type differs')
        accept_rate=float(accept[:,discard:].mean())
        accept_hashes={str(n):array_hash(accept[:,:n]) for n in prefix_lengths}
        del accept
    if file_hash(raw)!=expected_sha256:raise ValueError('Raw checksum changed during extraction')
    output.mkdir(parents=True)
    binary=output/'functions.bin'
    transport=values.transpose(1,0,2)
    np.asarray(transport,dtype='<f8').ravel(order='F').tofile(binary)
    report=dict(names=functions['names'],means=values.mean(axis=(0,1)).tolist(),
        shape=list(transport.shape),input_sha256=file_hash(binary),raw_sha256=expected_sha256,
        retained_acceptance_rate=accept_rate,path_prefix_sha256=paths,
        acceptance_prefix_sha256=accept_hashes,maximum_member_bytes=maximum_member_bytes,
        memory_policy='One fit at a time, at most two raw members plus bounded transform blocks; no study-wide trajectory cache')
    atomic_json(output/'extraction.json',report)
    return report


def aggregate_model(records, *, model_name, replicate_ids, workflow_names, budgets,
                    reference, namespace, output, pairs, cost_phase):
    """Aggregate one model's scalar records on the full planned repeat frame."""
    from formal_uncertainty import create_plan, save_plan, analyze_function, analyze_costs
    ids=tuple(str(x) for x in replicate_ids)
    if len(ids)!=len(set(ids)) or len(workflow_names)!=len(set(workflow_names)) or len(budgets)!=len(set(budgets)):
        raise ValueError('Duplicate planned identities')
    expected={(w,b,r) for w in workflow_names for b in budgets for r in ids}
    rows={(x['workflow'],x['budget'],str(x['replicate'])):x for x in records}
    if len(rows)!=len(records) or set(rows)!=expected:
        raise ValueError('Every planned task must appear once; missing tasks require explicit records')
    count=len(reference['names'])
    if any(len(reference[k])!=count for k in ('means','kinds','mcse')):
        raise ValueError('Reference function lengths differ')
    if any(row['means'] is not None and len(row['means'])!=count for row in records):
        raise ValueError('Function estimates differ from reference contract')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    plan=create_plan(namespace,model_name,ids)
    save_plan(plan,output/'resampling-plan')
    comparison=[(f'{a}@{b}',f'{c}@{b}') for b in budgets for a,c in pairs]
    summary=dict(model=model_name,planned=len(records),function_workflow_rows=0,
                 paired_function_rows=0,available_bca_intervals=0,unresolved_reference_rows=0,
                 function_failed_tasks=sum(x['function_status']=='failed' for x in records))
    def save(name,report):
        arrays=report.pop('bootstrap_statistics')
        if arrays:
            np.savez_compressed(output/(name+'.bootstrap.npz'),**arrays)
            report['bootstrap_statistics_sha256']=file_hash(output/(name+'.bootstrap.npz'))
        report['bootstrap_statistics_saved']=bool(arrays)
        atomic_json(output/(name+'.json'),report)
    for j,fn in enumerate(reference['names']):
        estimates={f'{w}@{b}':{r:None if rows[w,b,r]['means'] is None else rows[w,b,r]['means'][j]
                   for r in ids} for w in workflow_names for b in budgets}
        ref=dict(kind=reference['kinds'][j],value=reference['means'][j],mcse=reference['mcse'][j])
        report=analyze_function(plan,estimates,ref,comparison)
        report.update(model=model_name,function=fn)
        for row in report['workflows'].values():
            summary['function_workflow_rows']+=1
            summary['available_bca_intervals']+=row['confidence_interval'] is not None
            summary['unresolved_reference_rows']+=not row['reference_eligible']
        for row in report['pairs']:
            summary['paired_function_rows']+=1
            summary['available_bca_intervals']+=row['confidence_interval'] is not None
        save('function-'+str(j),report)
    costs={f'{w}@{b}':{r:rows[w,b,r]['seconds'] for r in ids} for w in workflow_names for b in budgets}
    outcomes={f'{w}@{b}':{r:rows[w,b,r]['outcome'] for r in ids} for w in workflow_names for b in budgets}
    report=analyze_costs(plan,costs,outcomes,comparison,phase=cost_phase)
    summary['cost_workflow_rows']=len(report['workflows']);summary['cost_pair_rows']=len(report['pairs'])
    summary['available_bca_intervals']+=sum(x['confidence_interval'] is not None for x in report['workflows'].values())
    summary['available_bca_intervals']+=sum(x['ratio_confidence_interval'] is not None for x in report['pairs'])
    save('cost',report);atomic_json(output/'summary.json',summary)
    return summary
