"""One-input-at-a-time preparation and sealing for the complete formal study.

This module neither runs samplers nor certifies a native execution gate.
Callers hold the shared host lease while creating/resuming a preparation.
An interrupted input is retained and refused, never silently regenerated.
"""
import copy
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import time
import zipfile

import numpy as np
from formal_inputs import build_payload, nuts_seed
from formal_runtime import atomic_json, file_hash, fingerprint, ResourceWait
from formal_streaming import read_member
from formal_study_plan import validate_study_plan


class FreezeConflict(ValueError):
    pass


def relative_file(root, name):
    if not isinstance(name, str) or '\\' in name:
        raise FreezeConflict('Canonical relative archive path required')
    p = PurePosixPath(name)
    if p.as_posix() != name or p.is_absolute() or not p.parts or any(v in ('..', '.') for v in p.parts) or ':' in name:
        raise FreezeConflict('Archive path escapes the bundle')
    root = Path(root).resolve()
    result = root.joinpath(*p.parts)
    if root not in result.resolve().parents:
        raise FreezeConflict('Archive path escapes the bundle')
    if any(q.is_symlink() for q in [result, *result.parents] if q != root and root in q.parents):
        raise FreezeConflict('Symlinks are not frozen evidence')
    return result


def input_bytes(requirement):
    r = requirement
    return 8 * (r['chains'] * r['dimension'] +
                r['chains'] * r['steps'] * (2 * r['dimension'] + 1) + r['chains'])


def validate_payload(values, identity, requirement):
    r = requirement
    shapes = dict(initial=(r['chains'], r['dimension']),
                  noise=(r['chains'], r['steps'], r['dimension']),
                  log_uniform=(r['chains'], r['steps']),
                  directions=(r['chains'], r['steps'], r['dimension']),
                  nuts_seeds=(r['chains'],))
    if set(values) != set(shapes):
        raise FreezeConflict('Actual input roles differ')
    for name, shape in shapes.items():
        a = values[name]
        dtype = np.dtype('int64' if name == 'nuts_seeds' else 'float64')
        if a.shape != shape or a.dtype != dtype or not np.isfinite(a).all():
            raise FreezeConflict('Actual input shape/type/finite check failed: ' + name)
    if np.any(values['log_uniform'] > 0):
        raise FreezeConflict('Log-uniform input exceeds zero')
    if not np.isin(values['directions'], [-1., 1.]).all():
        raise FreezeConflict('Solver directions are not Rademacher inputs')
    expected = [nuts_seed(identity, r['model'], r['replicate'], ch) for ch in range(r['chains'])]
    if not np.array_equal(values['nuts_seeds'], expected):
        raise FreezeConflict('NUTS seeds differ from the declared addresses')
    if r['model'] == 'M1' and not np.array_equal(values['initial'][:, 0],
                                               [-5. if ch % 2 == 0 else 5. for ch in range(r['chains'])]):
        raise FreezeConflict('Prespecified M1 initial modes differ')
    # Existing workers use this exact array-hash convention, including seeds.
    from mechanism_runner import actual_hash
    return actual_hash(values)


class InputArchive:
    """Resume verified input files without invoking their RNG again.

    A minimal inventory is useful for storage tests. Only seal_study accepts
    an executable-sized scientific frame, and it always reconstructs all of
    v0.2. A small InputArchive cannot stand in for the formal input inventory.
    """
    def __init__(self, directory, identity, requirements, binding, *, resume=False):
        self.directory = Path(directory)
        self.identity = identity
        self.requirements = copy.deepcopy(requirements)
        for name, r in requirements.items():
            if not re.fullmatch(r'[A-Z][0-9]-rep[0-9]{4}\.npz', name):
                raise FreezeConflict('Noncanonical input name')
            if name != f"{r['model']}-rep{r['replicate']:04d}.npz":
                raise FreezeConflict('Input name and address differ')
            if any(type(r[k]) is not int or r[k] < 1 for k in ('dimension', 'steps', 'chains')):
                raise FreezeConflict('Positive declared input shape required')
            if set(r['roles']) != {'initial', 'noise', 'log_uniform', 'directions', 'nuts_seeds'}:
                raise FreezeConflict('Complete actual input roles required')
        descriptor = dict(schema='formal-input-archive-v1', identity=identity,
                          requirements=self.requirements, binding=copy.deepcopy(binding))
        descriptor['binding_sha256'] = fingerprint(descriptor)
        self.descriptor = descriptor
        if self.directory.exists():
            if not resume:
                raise FileExistsError('Explicit preparation resume required')
            path = self.directory / 'archive.json'
            if not path.is_file() or json.loads(path.read_text()) != descriptor:
                raise FreezeConflict('Preparation source/environment/design binding differs')
            for name in ('inputs', 'receipts', 'intents'):
                if not (self.directory / name).is_dir() or (self.directory / name).is_symlink():
                    raise FreezeConflict('Incomplete or redirected preparation directory')
        else:
            if resume:
                raise FreezeConflict('Cannot resume absent preparation')
            self.directory.mkdir(parents=True)
            for name in ('inputs', 'receipts', 'intents'):
                (self.directory / name).mkdir()
            atomic_json(self.directory / 'archive.json', descriptor)

    def _read(self, name):
        receipt = relative_file(self.directory, 'receipts/' + name + '.json')
        if not receipt.is_file():
            return None
        record = json.loads(receipt.read_text())
        unsigned = dict(record)
        digest = unsigned.pop('receipt_sha256')
        if fingerprint(unsigned) != digest or record['archive_binding_sha256'] != self.descriptor['binding_sha256']:
            raise FreezeConflict('Input receipt binding/checksum differs')
        requirement = self.requirements[name]
        if record['requirement'] != requirement or record['name'] != name:
            raise FreezeConflict('Input receipt address differs')
        raw = relative_file(self.directory, 'inputs/' + name)
        if not raw.is_file() or raw.stat().st_size != record['file_bytes'] or file_hash(raw) != record['sha256']:
            raise FreezeConflict('Sealed actual input changed or is missing')
        intent = relative_file(self.directory, 'intents/' + name + '.json')
        if not intent.is_file() or file_hash(intent) != record['intent_sha256']:
            raise FreezeConflict('Input preparation intent changed')
        return record

    def prepare(self, name, *, disk_floor_bytes=4 * 1024**3, maximum_member_bytes=128 * 1024**2):
        if name not in self.requirements:
            raise FreezeConflict('Undeclared input cannot be generated')
        recoveries = self.directory/'preparation-recovery'/name
        if recoveries.exists():
            for recovery in recoveries.iterdir():
                if not (recovery/'completed.json').exists():
                    raise FreezeConflict('Unfinished input recovery; complete the explicit recovery first')
                proof = json.loads((recovery/'completed.json').read_text())
                if proof['archive_binding_sha256'] != self.descriptor['binding_sha256']:
                    raise FreezeConflict('Preparation recovery binding differs')
                for original, digest in proof['retained_files'].items():
                    if file_hash(relative_file(recovery, original)) != digest:
                        raise FreezeConflict('Retained preparation failure changed')
        existing = self._read(name)
        if existing is not None:
            return existing
        r = self.requirements[name]
        raw = relative_file(self.directory, 'inputs/' + name)
        partial = raw.with_name(raw.name + '.partial')
        intent = relative_file(self.directory, 'intents/' + name + '.json')
        if any(p.exists() for p in (raw, partial, intent)):
            raise FreezeConflict('Interrupted input retained; no silent regeneration or overwrite: ' + name)
        if type(disk_floor_bytes) is not int or disk_floor_bytes < 1:
            raise ValueError('Positive disk reserve required')
        if shutil.disk_usage(self.directory).free < disk_floor_bytes + input_bytes(r) + 65536:
            raise ResourceWait('Input preparation disk reserve refused before RNG or intent')
        if max(r['chains'] * r['steps'] * r['dimension'] * 8, r['chains'] * 8) > maximum_member_bytes:
            raise MemoryError('Declared actual input member exceeds the frozen allowance')
        start = time.perf_counter()
        atomic_json(intent, dict(name=name, requirement=r, archive_binding_sha256=self.descriptor['binding_sha256'],
                                 started_ns=time.time_ns(), timestamp_is_not_duration=True))
        values = build_payload(self.identity, r['model'], r['replicate'], r['dimension'], r['steps'], r['chains'])
        actual = validate_payload(values, self.identity, r)
        with partial.open('xb') as stream:
            np.savez_compressed(stream, **values)
            stream.flush()
            os.fsync(stream.fileno())
        del values
        # Reopen what was written, including every role, before promoting it.
        with zipfile.ZipFile(partial) as archive:
            if set(archive.namelist()) != {n + '.npy' for n in r['roles']} or len(archive.namelist()) != 5:
                raise FreezeConflict('Unexpected actual input archive members')
        saved = {n: read_member(partial, n, maximum_member_bytes) for n in r['roles']}
        if validate_payload(saved, self.identity, r) != actual:
            raise FreezeConflict('Written actual input arrays differ')
        del saved
        # Caller holds the preparation/host lease; no concurrent writer allowed.
        if raw.exists():
            raise FreezeConflict('Destination appeared during preparation')
        partial.rename(raw)
        record = dict(name=name, requirement=r, archive_binding_sha256=self.descriptor['binding_sha256'],
                      intent_sha256=file_hash(intent), sha256=file_hash(raw), actual_sha256=actual,
                      file_bytes=raw.stat().st_size, logical_array_bytes=input_bytes(r),
                      preparation_seconds=time.perf_counter() - start,
                      sampler_calls=0, statistical_repetitions=0)
        record['receipt_sha256'] = fingerprint(record)
        atomic_json(self.directory / 'receipts' / (name + '.json'), record)
        return record

    def recover_unsealed_input(self, name, *, reason):
        """Explicitly retain a failed preparation before repeating its fixed RNG.

        This is only before protocol sealing, never a retry of a sampler or a
        verified input. The source/environment/address binding cannot change.
        No input is generated here. Interrupted file moves can be continued.
        """
        if name not in self.requirements or not isinstance(reason, str) or not reason.strip():
            raise FreezeConflict('Declared input and explicit recovery reason required')
        if any((self.directory/n).exists() for n in ('protocol.json', 'freeze-manifest.json', 'FROZEN.json')):
            raise FreezeConflict('Sealed/partly sealed protocols cannot recover preparation inputs')
        if (self.directory/'receipts'/(name+'.json')).exists():
            raise FreezeConflict('A verified input cannot be regenerated, including after corruption')
        base = self.directory/'preparation-recovery'/name
        base.mkdir(parents=True, exist_ok=True)
        pending = [p for p in base.iterdir() if not (p/'completed.json').exists()]
        if len(pending) > 1:
            raise FreezeConflict('Multiple incomplete recoveries require investigation')
        if pending:
            destination = pending[0]
            report = json.loads((destination/'requested.json').read_text())
            if report['archive_binding_sha256'] != self.descriptor['binding_sha256'] or report['reason'] != reason:
                raise FreezeConflict('Pending recovery identity/reason differs')
        else:
            candidates = ['inputs/'+name, 'inputs/'+name+'.partial', 'intents/'+name+'.json']
            retained = {p: file_hash(relative_file(self.directory,p)) for p in candidates
                        if relative_file(self.directory,p).is_file()}
            if not retained:
                raise FreezeConflict('There is no interrupted preparation to recover')
            destination = base/str(time.time_ns()); destination.mkdir()
            report = dict(name=name, reason=reason, retained_files=retained,
                          archive_binding_sha256=self.descriptor['binding_sha256'],
                          action='Retain unsealed files, then permit regeneration at the identical declared addresses',
                          sampler_calls=0, scientific_repetitions_added=0)
            atomic_json(destination/'requested.json', report)
        for original, digest in report['retained_files'].items():
            source = relative_file(self.directory,original)
            target = relative_file(destination,original)
            if target.exists():
                if source.exists() or file_hash(target) != digest:
                    raise FreezeConflict('Recovery source/destination conflict')
            else:
                if not source.is_file() or file_hash(source) != digest:
                    raise FreezeConflict('Interrupted preparation changed during recovery')
                target.parent.mkdir(parents=True,exist_ok=True); source.rename(target)
        atomic_json(destination/'completed.json', report)
        return report

    def inventory(self):
        expected = set(self.requirements)
        for folder, names in [('inputs', expected), ('receipts', {n + '.json' for n in expected}),
                              ('intents', {n + '.json' for n in expected})]:
            if {p.name for p in (self.directory / folder).iterdir()} != names:
                raise FreezeConflict('Incomplete or extra actual inputs/receipts/intents')
        records = {name: self._read(name) for name in sorted(expected)}
        if any(r is None for r in records.values()):
            raise FreezeConflict('Full input inventory required before sealing')
        return {name: dict(model=r['requirement']['model'], replicate=r['requirement']['replicate'],
                           dimension=r['requirement']['dimension'], chains=r['requirement']['chains'],
                           steps=r['requirement']['steps'], sha256=r['sha256'], actual_sha256=r['actual_sha256'])
                for name, r in records.items()}


def protocol_document(plan, catalog, inventory, binding):
    """Assemble the complete scientific protocol; this is not launch authority."""
    validate_study_plan(plan, catalog)
    if set(inventory) != set(plan['input_requirements']):
        raise FreezeConflict('All 1152 original inputs are required')
    for name, requirement in plan['input_requirements'].items():
        expected = {k: requirement[k] for k in ('model', 'replicate', 'dimension', 'chains', 'steps')}
        if any(inventory[name].get(k) != v for k, v in expected.items()):
            raise FreezeConflict('Formal input coverage differs')
    p = dict(schema=1, identity=plan['identity'], scope_kind='formal_inference', required_platform='win32',
             study_design_sha256=plan['design_sha256'], batch_size=plan['batch_size'],
             groups=copy.deepcopy(plan['groups']), tasks=copy.deepcopy(plan['tasks']),
             targets=copy.deepcopy(plan['targets']), inputs=copy.deepcopy(inventory),
             controls=copy.deepcopy(plan['controls']), cost_policy=copy.deepcopy(plan['cost_policy']),
             analysis_policy=copy.deepcopy(plan['analysis_policy']),
             execution_policy=copy.deepcopy(plan['execution_policy']),
             cache_allocation_sha256=plan['cache_allocation']['allocation_sha256'],
             native_runtime_schema='windows-owned-runtime-v2',
             source_commit=binding['source_commit'], source_files=copy.deepcopy(binding['source_files']),
             required_versions=copy.deepcopy(binding['required_versions']),
             required_R_version=binding['required_R_version'], required_R_posterior=binding['required_R_posterior'],
             process_tree_rss_limit_bytes=binding['windows_limits']['rss_bytes'],
             required_disk_bytes_per_task=binding['windows_limits']['disk_start_bytes'],
             windows_limits=copy.deepcopy(binding['windows_limits']),
             minimum_available_ram_bytes=binding['minimum_available_ram_bytes'],
             preparation_binding_sha256=fingerprint(binding), external_files=copy.deepcopy(binding['external_files']),
             no_total_time_cutoff=True, native_execution_gate_required=True,
             sampling_authorized_by_this_document=False, formal_inference_complete=False)
    p['protocol_sha256'] = fingerprint(p)
    return p


def seal_study(directory, plan, catalog, archive, binding, bound_files):
    """Seal actual files and the complete plan, with no sampler launch privilege.

    bound_files includes the source snapshot, external data/license, dependency
    lock and environment records. The final marker is written last. A partial
    seal is retained/refused rather than overwritten on another invocation.
    """
    directory = Path(directory).resolve()
    if archive.directory.resolve() != directory or archive.identity != plan['identity'] or \
            archive.requirements != plan['input_requirements'] or archive.descriptor['binding'] != binding:
        raise FreezeConflict('Archive and full scientific plan differ')
    for name in ('protocol.json', 'freeze-manifest.json', 'FROZEN.json'):
        if (directory / name).exists():
            raise FreezeConflict('Existing complete/partial seal is immutable')
    for name, digest in bound_files.items():
        path = relative_file(directory, name)
        if not path.is_file() or file_hash(path) != digest:
            raise FreezeConflict('Bound preparation file differs: ' + name)
    required = {'study-plan.json', 'catalog.json', 'environment.json', 'pip-freeze.txt', 'pip-check.txt'}
    required.update('source/' + n for n in binding['source_files'])
    required.update('external/' + n for n in binding['external_files'])
    required.update(p.relative_to(directory).as_posix() for p in (directory/'preparation-recovery').rglob('*') if p.is_file())
    if not required <= set(bound_files):
        raise FreezeConflict('Source, dependency, design or external files are absent')
    if json.loads((directory/'study-plan.json').read_text()) != plan or json.loads((directory/'catalog.json').read_text()) != catalog:
        raise FreezeConflict('Saved design/catalog differs')
    for prefix, files in [('source/', binding['source_files']), ('external/', binding['external_files'])]:
        if any(bound_files.get(prefix + n) != h for n, h in files.items()):
            raise FreezeConflict('Saved snapshot differs from binding')
    inventory = archive.inventory()
    protocol = protocol_document(plan, catalog, inventory, binding)
    atomic_json(directory/'protocol.json', protocol)
    manifest = dict(bound_files)
    for name in ['archive.json', 'protocol.json', *['inputs/' + n for n in inventory],
                 *['receipts/' + n + '.json' for n in inventory], *['intents/' + n + '.json' for n in inventory]]:
        manifest[name] = file_hash(relative_file(directory, name))
    atomic_json(directory/'freeze-manifest.json', manifest)
    marker = dict(schema='formal-study-freeze-v1', identity=plan['identity'],
                  protocol_sha256=protocol['protocol_sha256'], design_sha256=plan['design_sha256'],
                  manifest_sha256=file_hash(directory/'freeze-manifest.json'),
                  source_commit=binding['source_commit'], inputs=len(inventory),
                  native_execution_gate_required=True, sampling_authorized_by_this_document=False,
                  formal_inference_complete=False)
    atomic_json(directory/'FROZEN.json', marker)
    return marker


def verify_sealed_study(directory):
    """Read-only portable verification; never asserts native execution readiness."""
    directory = Path(directory)
    marker = json.loads((directory/'FROZEN.json').read_text())
    if marker['schema'] != 'formal-study-freeze-v1' or marker['sampling_authorized_by_this_document'] is not False:
        raise FreezeConflict('Freeze marker is not an execution authorization')
    if file_hash(directory/'freeze-manifest.json') != marker['manifest_sha256']:
        raise FreezeConflict('Freeze manifest differs')
    manifest = json.loads((directory/'freeze-manifest.json').read_text())
    for name, digest in manifest.items():
        path = relative_file(directory, name)
        if not path.is_file() or file_hash(path) != digest:
            raise FreezeConflict('Frozen evidence differs: ' + name)
    descriptor = json.loads((directory/'archive.json').read_text())
    plan = json.loads((directory/'study-plan.json').read_text())
    catalog = json.loads((directory/'catalog.json').read_text())
    archive = InputArchive(directory, plan['identity'], plan['input_requirements'], descriptor['binding'], resume=True)
    expected = protocol_document(plan, catalog, archive.inventory(), descriptor['binding'])
    if json.loads((directory/'protocol.json').read_text()) != expected or marker['protocol_sha256'] != expected['protocol_sha256'] or \
            marker['identity'] != plan['identity'] or marker['design_sha256'] != plan['design_sha256'] or marker['inputs'] != 1152 or \
            marker['source_commit'] != expected['source_commit'] or marker['native_execution_gate_required'] is not True or \
            marker['formal_inference_complete'] is not False:
        raise FreezeConflict('Sealed protocol differs from complete scientific design')
    required = {'archive.json', 'protocol.json', 'study-plan.json', 'catalog.json', 'environment.json', 'pip-freeze.txt', 'pip-check.txt'}
    required.update('source/' + n for n in expected['source_files'])
    required.update('external/' + n for n in expected['external_files'])
    for name in plan['input_requirements']:
        required.update(('inputs/' + name, 'receipts/' + name + '.json', 'intents/' + name + '.json'))
    required.update(p.relative_to(directory).as_posix() for p in (directory/'preparation-recovery').rglob('*') if p.is_file())
    if not required <= set(manifest):
        raise FreezeConflict('Frozen manifest omitted required evidence')
    for prefix, files in [('source/', expected['source_files']), ('external/', expected['external_files'])]:
        if any(manifest.get(prefix + n) != h for n, h in files.items()):
            raise FreezeConflict('Frozen source/external binding differs')
    return marker, expected
