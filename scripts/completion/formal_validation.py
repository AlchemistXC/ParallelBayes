"""Finite native adapter validation contract, separate from the formal study.

Pure preparation/reading helpers. Native commands own host leases and actual
execution; a frozen validation bundle grants no formal-sampling authority.
"""
import copy
import json
from pathlib import Path

from batch_contract import BatchPlan, create_tasks
from formal_acceptance import validation_groups
from formal_execution import VALIDATION_ID, SCHEMA
from formal_freeze import InputArchive, FreezeConflict, relative_file
from formal_measurement_plan import create_measurement_plan
from formal_runtime import atomic_json, file_hash, fingerprint
from formal_study_plan import DEVELOPMENT_PROTOCOL_SHA256, study_controls

TEST_FILES = ('tests/windows/test_formal_owned_runtime.py',
              'tests/windows/formal_runtime_fixture.py', 'tests/windows/runtime_fixture.py')


def validation_design(catalog):
    unsigned = copy.deepcopy(catalog); digest = unsigned.pop('protocol_sha256')
    if digest != DEVELOPMENT_PROTOCOL_SHA256 or fingerprint(unsigned) != digest:
        raise FreezeConflict('Verified development catalog required for validation')
    groups = validation_groups(); tasks = create_tasks(VALIDATION_ID, groups)
    targets = [copy.deepcopy(t) for t in catalog['targets'] if t['name'] in ('G1', 'G2', 'W1')]
    if len(targets) != 3 or {t['name'] for t in targets} != {'G1', 'G2', 'W1'}:
        raise FreezeConflict('All three finite-validation targets are required')
    controls = study_controls()
    requirements = {}
    for t in targets:
        steps = max(s['budget'] for s in tasks if s['model'] == t['name']) + controls['mh_discard']
        requirements[t['name']+'-rep0000.npz'] = dict(model=t['name'], replicate=0, dimension=t['dimension'],
            chains=4, steps=steps, roles=['initial', 'noise', 'log_uniform', 'directions', 'nuts_seeds'])
    value = dict(schema='formal-adapter-validation-design-v1', identity=VALIDATION_ID,
                 catalog_protocol_sha256=digest, groups=groups, tasks=tasks, targets=targets,
                 controls=controls, input_requirements=requirements,
                 cache_allocation=create_measurement_plan(VALIDATION_ID, tasks), formal_scientific_repetitions=0,
                 scope='Finite implementation validation, not posterior accuracy or performance inference')
    return dict(value, design_sha256=fingerprint(value))


def validation_protocol(design, catalog, inventory, binding):
    if design != validation_design(catalog):
        raise FreezeConflict('Finite validation design changed')
    if set(inventory) != set(design['input_requirements']):
        raise FreezeConflict('Exactly three actual validation inputs required')
    for name, r in design['input_requirements'].items():
        if any(inventory[name][k] != r[k] for k in ('model', 'replicate', 'dimension', 'chains', 'steps')):
            raise FreezeConflict('Finite validation input address/shape differs')
    value = dict(schema=1, identity=VALIDATION_ID, scope_kind='technical_batch_validation',
        required_platform='win32', native_runtime_schema=SCHEMA, batch_size=32,
        groups=design['groups'], tasks=design['tasks'], targets=design['targets'], controls=design['controls'],
        inputs=inventory, validation_design_sha256=design['design_sha256'],
        validation_environment=binding['environment'], validation_test_sources=binding['validation_test_sources'],
        source_commit=binding['source_commit'], source_files=binding['source_files'],
        external_files=binding['external_files'], required_versions=binding['required_versions'],
        required_R_version=binding['required_R_version'], required_R_posterior=binding['required_R_posterior'],
        windows_limits=binding['windows_limits'], minimum_available_ram_bytes=binding['minimum_available_ram_bytes'],
        process_tree_rss_limit_bytes=binding['windows_limits']['rss_bytes'],
        required_disk_bytes_per_task=binding['windows_limits']['disk_start_bytes'],
        shared_host_lock=binding['shared_host_lock'], cache_allocation_sha256=design['cache_allocation']['allocation_sha256'],
        cost_policy=dict(ordinary='Ordinary child creation through exit',
            research='External invocation ledger; includes audit and sealing',
            cached='Separate one initial and three prepared calls; zero new independent repetitions',
            nested_phases_additive=False, unknown_cost=None),
        recovery_policy='Resume verifies ended tasks; this finite acceptance command never retries a sampler',
        no_total_time_cutoff=True, formal_scientific_repetitions=0, formal_inference_complete=False)
    value = copy.deepcopy(value); value['protocol_sha256'] = fingerprint(value)
    BatchPlan(value)
    return value


def file_inventory(root):
    root = Path(root).resolve(); result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise FreezeConflict('No symlinks in frozen validation evidence')
        if path.is_file():
            name = path.relative_to(root).as_posix()
            result[name] = file_hash(relative_file(root, name))
    return result


def _required(directory, design, binding):
    names = {'archive.json', 'catalog.json', 'validation-design.json', 'environment.json',
             'pip-freeze.txt', 'pip-check.txt', 'address-check.json'}
    for prefix, key in [('source/', 'source_files'), ('external/', 'external_files'), ('source/', 'validation_test_sources')]:
        names.update(prefix+n for n in binding[key])
    for name in design['input_requirements']:
        names.update(('inputs/'+name, 'receipts/'+name+'.json', 'intents/'+name+'.json'))
    for name in names:
        if not relative_file(directory, name).is_file():
            raise FreezeConflict('Missing validation freeze asset: '+name)
    for prefix, key in [('source/', 'source_files'), ('external/', 'external_files'), ('source/', 'validation_test_sources')]:
        for name, digest in binding[key].items():
            if file_hash(relative_file(directory, prefix+name)) != digest:
                raise FreezeConflict('Validation source or data snapshot changed: '+name)
    if set(binding['validation_test_sources']) != set(TEST_FILES):
        raise FreezeConflict('All native runtime test/fixture sources are required')
    if (json.loads((directory/'validation-design.json').read_text()) != design or
            json.loads((directory/'environment.json').read_text()) != binding['environment'] or
            file_hash(directory/'pip-freeze.txt') != binding['environment']['pip_freeze_sha256']):
        raise FreezeConflict('Validation design/environment/dependency lock differs')
    return names


def seal_validation(directory, archive, catalog, binding):
    directory = Path(directory).resolve(); design = validation_design(catalog)
    if (archive.directory.resolve() != directory or archive.identity != VALIDATION_ID or
            archive.requirements != design['input_requirements'] or archive.descriptor['binding'] != binding):
        raise FreezeConflict('Validation archive binding differs')
    if any((directory/n).exists() for n in ('protocol.json', 'freeze-manifest.json', 'FROZEN.json')):
        raise FreezeConflict('Existing partial or complete validation seal is immutable')
    _required(directory, design, binding)
    if json.loads((directory/'catalog.json').read_text()) != catalog:
        raise FreezeConflict('Validation catalog snapshot differs')
    p = validation_protocol(design, catalog, archive.inventory(), binding)
    atomic_json(directory/'protocol.json', p)
    inventory = file_inventory(directory)
    atomic_json(directory/'freeze-manifest.json', inventory)
    marker = dict(schema='formal-adapter-validation-freeze-v1', identity=VALIDATION_ID,
        protocol_sha256=p['protocol_sha256'], source_commit=p['source_commit'],
        manifest_sha256=file_hash(directory/'freeze-manifest.json'), main_tasks=27, cache_probes=24,
        formal_scientific_repetitions=0, formal_sampling_authorized=False)
    atomic_json(directory/'FROZEN.json', marker)
    return marker


def verify_validation_bundle(directory):
    directory = Path(directory).resolve()
    marker = json.loads((directory/'FROZEN.json').read_text())
    if file_hash(directory/'freeze-manifest.json') != marker['manifest_sha256']:
        raise FreezeConflict('Validation freeze manifest changed')
    inventory = json.loads((directory/'freeze-manifest.json').read_text())
    for name, digest in inventory.items():
        if file_hash(relative_file(directory, name)) != digest:
            raise FreezeConflict('Frozen validation file changed: '+name)
    catalog = json.loads((directory/'catalog.json').read_text()); design = validation_design(catalog)
    binding = json.loads((directory/'archive.json').read_text())['binding']
    required = _required(directory, design, binding) | {'protocol.json'}
    if not required <= set(inventory):
        raise FreezeConflict('Validation manifest omits required evidence')
    archive = InputArchive(directory, VALIDATION_ID, design['input_requirements'], binding, resume=True)
    p = validation_protocol(design, catalog, archive.inventory(), binding)
    wanted = dict(schema='formal-adapter-validation-freeze-v1', identity=VALIDATION_ID,
        protocol_sha256=p['protocol_sha256'], source_commit=p['source_commit'],
        manifest_sha256=file_hash(directory/'freeze-manifest.json'), main_tasks=27, cache_probes=24,
        formal_scientific_repetitions=0, formal_sampling_authorized=False)
    if marker != wanted or json.loads((directory/'protocol.json').read_text()) != p:
        raise FreezeConflict('Validation protocol/marker differs from finite design')
    return marker, p, design, binding


def validation_slots(protocol, phase):
    plan = BatchPlan(protocol)
    if phase not in ('main', 'cache') or protocol['identity'] != VALIDATION_ID or protocol['tasks'] != create_tasks(VALIDATION_ID, validation_groups()):
        raise FreezeConflict('Only the finite native validation frame is allowed')
    primary = {t['id']: t for t in plan.tasks()}
    frame = list(primary.values()) if phase == 'main' else create_measurement_plan(VALIDATION_ID, list(primary.values()))['probes']
    for item in frame:
        original = item['id'] if phase == 'main' else item['primary_task_id']
        capsule, digest = plan.capsule(original)
        yield dict(task=dict(primary[original], id=item['id'], protocol_sha256=plan.protocol_sha256,
                            artifact_kind='posterior' if phase == 'main' else 'cache_measurement'),
                   capsule=capsule, capsule_sha256=digest, probe=None if phase == 'main' else item)


def validation_request(slot, protocol, bundle, source_root):
    bundle = Path(bundle).resolve(); source_root = Path(source_root).resolve(); c = slot['capsule']
    env = protocol['validation_environment']; marker = bundle/'FROZEN.json'
    sources = {str(source_root/n): h for n, h in protocol['source_files'].items()}
    sources.update({str(bundle/'external'/n): h for n, h in protocol['external_files'].items()})
    request = dict(capsule=c, capsule_sha256=slot['capsule_sha256'], native_runtime_schema=SCHEMA,
        phase='main' if slot['probe'] is None else 'cache', inputs=str(bundle/'inputs'),
        source_directory=str(bundle/'external'), rscript=env['rscript'], r_library=env['r_library'],
        required_gpu_free_bytes=c['controls']['minimum_gpu_free_bytes'],
        sealed_marker=str(marker), sealed_marker_sha256=file_hash(marker),
        input_files={str(marker): file_hash(marker), str(bundle/'inputs'/c['task']['input']): c['input']['sha256']},
        source_files=sources)
    if slot['probe'] is not None:
        request['probe'] = slot['probe']
    return request
