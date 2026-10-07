"""Storage companion for the verified finite-v2 return and v0.2 formal design.

Reads file sizes and NPZ headers only, never arrays or samplers. Named-array
scenario totals are not allocated disk bytes, compressed predictions or bounds
on logs/failures. No permission to freeze, sample, delete or change a protocol.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import sys
import zipfile

import numpy as np

MANIFEST_HASH = 'b6bc221c724f05a14b1bb9782140b7536e0b03a0250820c4810c649091b679bd'
DESIGN_HASH = '68a1cba1b9309216d237ac4613531216f167ff344dfdfcb72dc3aaca0ca0baa5'
IDENTITY = 'windows-formal-adapter-validation-v1'
GIB = 1024**3


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def local(root, name):
    p = PurePosixPath(name)
    if (not p.parts or p.as_posix() != name or p.is_absolute() or
            '..' in p.parts or '\\' in name or ':' in name):
        raise ValueError('Noncanonical evidence path')
    q = root.joinpath(*p.parts)
    if root not in q.resolve().parents or any(x.is_symlink() for x in [q, *q.parents] if x != root and root in x.parents):
        raise ValueError('Redirected evidence path')
    return q


def category(name):
    p = Path(name)
    if p.name == 'failure-reserve.bin': return 'failure_reserve'
    if p.suffix == '.npz': return 'npz_stored'
    if p.suffix in ('.bin', '.roundtrip'): return 'function_binaries'
    if p.suffix in ('.json', '.ndjson'): return 'json_and_observation_logs'
    return 'other'


def npz_headers(path):
    rows = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if not info.filename.endswith('.npy') or info.filename in rows:
                raise ValueError('Unexpected NPZ member')
            with archive.open(info) as stream:
                version = np.lib.format.read_magic(stream)
                if version == (1, 0): shape, order, dtype = np.lib.format.read_array_header_1_0(stream)
                elif version == (2, 0): shape, order, dtype = np.lib.format.read_array_header_2_0(stream)
                else: raise ValueError('Unreviewed NPY header version')
                if dtype.hasobject: raise ValueError('Object arrays are not numerical storage evidence')
                header_bytes = stream.tell()
            nbytes = math.prod(shape)*dtype.itemsize
            if header_bytes+nbytes != info.file_size: raise ValueError('NPY length differs from declared shape')
            rows[info.filename] = dict(shape=list(shape), dtype=str(dtype), array_bytes=nbytes,
                member_uncompressed_bytes=info.file_size, member_compressed_bytes=info.compress_size,
                header_bytes=header_bytes)
    return rows


def main_array_bytes(task, dimension, controls, rng_bytes):
    c=controls['chains']; b=task['budget']; w=controls['nuts_warmup']
    if task['kernel'] != 'nuts':
        steps=b+controls['mh_discard']
        return dict(MH_two_coordinates=2*c*steps*dimension*8, MH_two_accept_arrays=2*c*steps)
    return dict(NUTS_two_coordinates_and_warmup=c*(2*b+w)*dimension*8,
                NUTS_step_sizes=c*(b+w)*8,
                NUTS_initial=c*dimension*8, NUTS_rng_states=2*c*rng_bytes)


def cache_array_bytes(probe, dimension, controls):
    c=controls['chains']; steps=probe['budget']+controls['mh_discard']
    calls=probe['initial_calls']+probe['prepared_replays']
    return calls*c*steps*(dimension*8+1)


def audit(root, delivery, output):
    root, delivery, output = [Path(p).resolve() for p in (root,delivery,output)]
    if output.exists(): raise FileExistsError('Existing storage analysis is retained')
    if output.is_relative_to(delivery) or delivery.is_relative_to(output):
        raise ValueError('Output must be separate from received evidence')
    manifest_path=delivery/'WINDOWS-RETURN-MANIFEST.json'
    if digest(manifest_path) != MANIFEST_HASH: raise ValueError('This companion requires the independently received finite-v2 manifest')
    manifest=read(manifest_path)['files']
    actual={p.relative_to(delivery).as_posix() for p in delivery.rglob('*') if p.is_file() and p!=manifest_path}
    if actual != set(manifest): raise ValueError('Received file inventory differs')
    total=Counter(); file_rows=[]
    for name,row in sorted(manifest.items()):
        p=local(delivery,name)
        if not p.is_file() or p.stat().st_size != row['bytes']: raise ValueError('Received file length differs: '+name)
        kind=category(name); total[kind]+=row['bytes']
        file_rows.append(dict(file=name,bytes=row['bytes'],category=kind))
    def authenticated_json(name):
        p=local(delivery,name)
        if digest(p) != manifest[name]['sha256']: raise ValueError('Metadata hash differs: '+name)
        return read(p)
    protocol=authenticated_json('validation/protocol.json')
    design=authenticated_json('validation/validation-design.json')
    if protocol['identity']!=IDENTITY: raise ValueError('Not the finite technical identity')
    dimensions={t['name']:t['dimension'] for t in protocol['targets']}
    ctrl=protocol['controls']; observed=[]; npz_records=[]; rng_lengths=set()
    for task in protocol['tasks']:
        if task['kernel']=='nuts':
            h=npz_headers(delivery/'validation/main/tasks'/task['id']/'attempt-0001/fit.npz')
            for n in ('initial_torch_rng_states.npy','final_torch_rng_states.npy'):
                if h[n]['shape'][0]!=ctrl['chains'] or h[n]['dtype']!='uint8': raise ValueError('NUTS RNG storage type differs')
                rng_lengths.add(h[n]['shape'][1])
    if len(rng_lengths)!=1: raise ValueError('Native NUTS RNG state length differs across targets')
    rng_bytes=rng_lengths.pop()
    for phase,tasks in [('main',protocol['tasks']),('cache',design['cache_allocation']['probes'])]:
        for task in tasks:
            prefix='validation/'+phase+'/tasks/'+task['id']+'/'
            members=[row for row in file_rows if row['file'].startswith(prefix)]
            kinds=Counter(); logical=0; npz_count=0; reserve=0
            for row in members:
                kinds[row['category']]+=row['bytes']
                if row['category']=='failure_reserve':
                    reserve+=1
                    if row['bytes']!=1024**2: raise ValueError('Finite successful-task reserve differs')
                if row['category']=='npz_stored':
                    headers=npz_headers(delivery/row['file']);payload=sum(h['array_bytes'] for h in headers.values())
                    logical+=payload;npz_count+=1
                    npz_records.append(dict(file=row['file'],file_bytes=row['bytes'],members=headers))
            if reserve!=1: raise ValueError('Finite task attempt/reserve count differs')
            expected=(sum(main_array_bytes(task,dimensions[task['model']],ctrl,rng_bytes).values()) if phase=='main'
                      else cache_array_bytes(task,dimensions[task['model']],ctrl))
            if logical != expected: raise ValueError('Observed NPZ arrays disagree with named-array calculation: '+task['id'])
            expected_files=5 if phase=='main' and task['kernel']=='nuts' else 1 if phase=='main' else 4
            if npz_count!=expected_files: raise ValueError('Finite task NPZ count differs')
            observed.append(dict(phase=phase,id=task['id'],model=task['model'],budget=task['budget'],workflow=task['workflow'],
                files=len(members),file_bytes=sum(kinds.values()),components=dict(kinds),npz_array_bytes=logical,
                npz_stored_over_array_bytes=kinds['npz_stored']/logical,source_schema_bytes_match=True))
    # Build only deterministic plan metadata: never prepare actual random arrays.
    sys.path.insert(0,str(root/'scripts/completion'))
    from formal_study_plan import create_study_plan
    plan=create_study_plan('windows-formal-inference-v1',read(root/'benchmark/protocols/inference-budget-pilot-mac-v1.json'))
    if plan['design_sha256']!=DESIGN_HASH: raise ValueError('Formal design differs from the reviewed v0.2 frame')
    if plan['controls']!=ctrl: raise ValueError('Finite and planned numerical controls differ')
    dims={t['name']:t['dimension'] for t in plan['targets']}
    reference=read(root/'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis/reference-contract.json')
    functions={name:len(reference[name]['names']) for name in dims}
    costs=Counter();c=ctrl['chains'];rebuild=0
    for req in plan['input_requirements'].values():
        costs['master_inputs']+=8*(req['chains']*req['dimension']+req['chains']*req['steps']*(2*req['dimension']+1)+req['chains'])
    for task in plan['tasks']:
        costs.update(main_array_bytes(task,dims[task['model']],ctrl,rng_bytes))
        one_binary=task['budget']*c*functions[task['model']]*8
        costs['original_two_function_binaries']+=2*one_binary;rebuild+=3*one_binary
    for probe in plan['cache_allocation']['probes']:costs['cache_four_calls_arrays']+=cache_array_bytes(probe,dims[probe['model']],ctrl)
    n=len(plan['tasks'])+len(plan['cache_allocation']['probes'])
    reserve=n*1024**2;arrays=sum(costs.values());base=arrays+reserve
    source_names=['scripts/windows/formal_owned_runtime.py','scripts/windows/formal_cache_worker.py',
        'scripts/completion/formal_study_plan.py','scripts/analysis/formal_science.py',
        'benchmark/protocols/inference-budget-pilot-mac-v1.json',
        'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis/reference-contract.json']
    report=dict(schema='formal-storage-companion-v1',scope='Actual finite file lengths and all-success no-retry formal storage scenarios, not disk sufficiency, runtime, compression or convergence forecasts',
        received_manifest_sha256=MANIFEST_HASH,received_inventory_files=len(manifest),received_inventory_file_bytes=sum(total.values()),
        observed_components=dict(total),observed_tasks=observed,observed_task_schema_checks=len(observed),
        native_rng_state_bytes=rng_bytes,formal_design_sha256=DESIGN_HASH,
        planned_inputs=len(plan['input_requirements']),planned_main=len(plan['tasks']),planned_cache=len(plan['cache_allocation']['probes']),
        formal_named_array_bytes=dict(costs),formal_named_arrays_total=arrays,
        successful_attempt_reserve_bytes=reserve,receiver_three_function_binaries_bytes=rebuild,
        no_compression_no_retry_scenarios={
            'one_execution_tree_named_arrays_and_reserves':base,
            'execution_tree_plus_tar_plus_extracted_delivery':3*base,
            'three_copies_plus_receiver_function_binaries':3*base+rebuild,
            'one_received_delivery_plus_receiver_function_binaries':base+rebuild},
        scenario_exclusions=['NPY/ZIP/TAR headers and filesystem allocation','JSON and runtime-dependent observation logs','SQLite journals and indexes','failure/retry partial outputs','analysis metadata, extra verification/archive copies, environments and history'],
        actual_file_lengths_not_Windows_allocated_clusters=True,all_success_no_retry_assumption=True,
        compression_ratio_not_extrapolated=True,full_content_hashing_repeated=False,
        provenance='Manifest identity, file inventory/sizes and consumed metadata hashes checked here; prior independent intake authenticated all original file contents. NPZ data are not decompressed/replayed.',
        source_files={name:digest(root/name) for name in source_names},analysis_script_sha256=digest(Path(__file__)),
        new_sampler_calls=0,new_R_diagnostic_calls=0,
        actual_formal_inputs_generated=0,new_formal_repetitions=0)
    output.mkdir(parents=True)
    for name,data in [('summary.json',report),('file-footprint.json',file_rows),('npz-headers.json',npz_records)]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    files={p.name:digest(p) for p in sorted(output.iterdir())}
    (output/'SHA256.json').write_text(json.dumps(files,indent=2)+'\n')
    print(json.dumps(dict(status='passed',files=len(manifest),task_schema_checks=len(observed),
        named_arrays_GiB=arrays/GIB,reserves_GiB=reserve/GIB,receiver_binary_GiB=rebuild/GIB,
        three_copies_and_receiver_scenario_GiB=(3*base+rebuild)/GIB,new_sampler_calls=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--delivery',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();audit(args.root,args.delivery,args.output)
