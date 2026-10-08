"""Immutable compact protocol sealing, separate from historical full-grid sealing."""
import copy
import json
from pathlib import Path

from compact_contract import CONTRACT, PROTOCOL_SCHEMA, CompactPlan, validate_plan
from formal_freeze import FreezeConflict, InputArchive, relative_file
from formal_runtime import atomic_json, file_hash, fingerprint

MARKER_SCHEMA='compact-study-freeze-v1'


def protocol_document(plan,inventory,binding,root):
    validate_plan(plan,root)
    if set(inventory)!=set(plan['input_requirements']):raise FreezeConflict('Complete compact actual input inventory required')
    for name,r in plan['input_requirements'].items():
        if any(inventory[name].get(k)!=r[k] for k in ('model','replicate','dimension','chains','steps')):
            raise FreezeConflict('Compact input address/shape differs')
    p=dict(schema=PROTOCOL_SCHEMA,compact_execution_contract=CONTRACT,identity=plan['identity'],
        scope_kind=plan['scope_kind'],required_platform='win32',batch_size=8,
        study_design_sha256=plan['compact_design_sha256'],execution_plan_sha256=plan['plan_sha256'],
        native_runtime_schema='windows-owned-runtime-v2',
        groups=copy.deepcopy(plan['groups']),tasks=copy.deepcopy(plan['tasks']),targets=copy.deepcopy(plan['targets']),
        inputs=copy.deepcopy(inventory),controls=copy.deepcopy(plan['controls']),
        analysis_policy=copy.deepcopy(plan['analysis_policy']),execution_policy=copy.deepcopy(plan['execution_policy']),
        cost_policy=copy.deepcopy(plan['cost_policy']),cache_allocation_sha256=plan['cache_allocation']['allocation_sha256'],
        source_commit=binding['source_commit'],source_files=copy.deepcopy(binding['source_files']),
        required_versions=copy.deepcopy(binding['required_versions']),required_R_version=binding['required_R_version'],
        required_R_posterior=binding['required_R_posterior'],windows_limits=copy.deepcopy(binding['windows_limits']),
        process_tree_rss_limit_bytes=binding['windows_limits']['rss_bytes'],
        required_disk_bytes_per_task=binding['windows_limits']['disk_start_bytes'],
        minimum_available_ram_bytes=binding['minimum_available_ram_bytes'],
        external_files=copy.deepcopy(binding['external_files']),preparation_binding_sha256=fingerprint(binding),
        storage_policy=copy.deepcopy(binding.get('storage_policy',{})),
        native_execution_gate_required=not plan['technical'],sampling_authorized_by_this_document=False,
        formal_inference_complete=False,no_total_time_cutoff=True)
    p['protocol_sha256']=fingerprint(p)
    CompactPlan(p)
    return p


def seal(directory,plan,archive,binding,bound_files):
    directory=Path(directory).resolve()
    for name in ('protocol.json','freeze-manifest.json','FROZEN.json'):
        if (directory/name).exists():raise FreezeConflict('Compact complete/partial seal is immutable')
    if (archive.directory.resolve()!=directory or archive.identity!=plan['identity'] or
        archive.requirements!=plan['input_requirements'] or archive.descriptor['binding']!=binding):
        raise FreezeConflict('Compact archive/plan/binding conflict')
    expected={'study-plan.json','environment.json','catalog.json','pip-freeze.txt','pip-check.txt','address-check.json'}
    expected.update('source/'+n for n in binding['source_files'])
    expected.update('external/'+n for n in binding['external_files'])
    if not expected<=set(bound_files):raise FreezeConflict('Compact source/environment/data evidence missing')
    for name,h in bound_files.items():
        if file_hash(relative_file(directory,name))!=h:raise FreezeConflict('Bound compact snapshot changed: '+name)
    inventory=archive.inventory()
    protocol=protocol_document(plan,inventory,binding,directory/'source')
    atomic_json(directory/'protocol.json',protocol)
    manifest=dict(bound_files)
    for name in ['archive.json','protocol.json',*['inputs/'+n for n in inventory],
                 *['receipts/'+n+'.json' for n in inventory],*['intents/'+n+'.json' for n in inventory]]:
        manifest[name]=file_hash(relative_file(directory,name))
    atomic_json(directory/'freeze-manifest.json',manifest)
    marker=dict(schema=MARKER_SCHEMA,identity=plan['identity'],protocol_sha256=protocol['protocol_sha256'],
        manifest_sha256=file_hash(directory/'freeze-manifest.json'),source_commit=binding['source_commit'],
        source_files_sha256=fingerprint(binding['source_files']),inputs=len(inventory),main_tasks=len(plan['tasks']),
        cache_probes=len(plan['cache_allocation']['probes']),formal_scientific_repetitions=plan['formal_scientific_repetitions'],
        native_execution_gate_required=not plan['technical'],sampling_authorized_by_this_document=False,
        formal_inference_complete=False)
    atomic_json(directory/'FROZEN.json',marker)
    return marker


def verify(directory):
    directory=Path(directory).resolve()
    marker=json.loads((directory/'FROZEN.json').read_text())
    if marker.get('schema')!=MARKER_SCHEMA or marker.get('sampling_authorized_by_this_document') is not False:
        raise FreezeConflict('Only compact freeze supported; historical/new schemas cannot be mixed')
    if file_hash(directory/'freeze-manifest.json')!=marker['manifest_sha256']:
        raise FreezeConflict('Compact frozen manifest changed')
    files=json.loads((directory/'freeze-manifest.json').read_text())
    for name,digest in files.items():
        if file_hash(relative_file(directory,name))!=digest:raise FreezeConflict('Frozen compact evidence changed: '+name)
    plan=json.loads((directory/'study-plan.json').read_text());binding=json.loads((directory/'archive.json').read_text())['binding']
    archive=InputArchive(directory,plan['identity'],plan['input_requirements'],binding,resume=True)
    expected=protocol_document(plan,archive.inventory(),binding,directory/'source')
    wanted=dict(schema=MARKER_SCHEMA,identity=plan['identity'],protocol_sha256=expected['protocol_sha256'],
        manifest_sha256=file_hash(directory/'freeze-manifest.json'),source_commit=binding['source_commit'],
        source_files_sha256=fingerprint(binding['source_files']),inputs=len(plan['input_requirements']),
        main_tasks=len(plan['tasks']),cache_probes=len(plan['cache_allocation']['probes']),
        formal_scientific_repetitions=plan['formal_scientific_repetitions'],native_execution_gate_required=not plan['technical'],
        sampling_authorized_by_this_document=False,formal_inference_complete=False)
    if marker!=wanted or json.loads((directory/'protocol.json').read_text())!=expected:
        raise FreezeConflict('Compact marker/protocol differs from full prescribed frame')
    required={'archive.json','protocol.json','study-plan.json','catalog.json','environment.json','pip-freeze.txt','pip-check.txt','address-check.json'}
    for name in plan['input_requirements']:
        required.update(('inputs/'+name,'receipts/'+name+'.json','intents/'+name+'.json'))
    for prefix,values in [('source/',binding['source_files']),('external/',binding['external_files'])]:
        required.update(prefix+n for n in values)
        if any(files.get(prefix+n)!=h for n,h in values.items()):raise FreezeConflict('Frozen source/data binding differs')
    if not required<=set(files):raise FreezeConflict('Compact manifest omitted required evidence')
    return marker,expected,plan,binding
