"""Native finite adapter validation: prepare, test, run, verify-only, seal.

Never launches the formal grid or retries a scientific fit. Every attempt and
failed command remains in its original directory. Run `--help` for commands.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/completion'), str(ROOT/'scripts/windows'),
                str(ROOT/'r-package/inst/python'), str(ROOT/'examples')]
from formal_runtime import atomic_json, file_hash, fingerprint, host_lease, ResourceWait
from formal_freeze import InputArchive, FreezeConflict, relative_file, input_bytes
from formal_execution import VALIDATION_ID
from formal_validation import (TEST_FILES, validation_design, validation_slots, validation_request,
                               seal_validation, verify_validation_bundle, file_inventory)
from formal_acceptance import verify_runtime_cases, verify_native_acceptance
from formal_native_evidence import read_native_task
from prepare_formal_study import sources, snapshot_file, write_once, gather_environment, CATALOG, LIMITS


def require_native():
    if sys.platform != 'win32':
        raise FreezeConflict('Actual native Windows required before writing or running validation')


def prepare(output, external, host_lock, rscript, r_library, *, resume=False, recover_input=None, recovery_reason=None):
    require_native()
    if bool(recover_input) != bool(recovery_reason) or (recover_input and not resume):
        raise FreezeConflict('Named input recovery requires explicit resume and reason')
    output, external, host_lock, rscript, r_library = map(lambda p: Path(p).resolve(),
        (output, external, host_lock, rscript, r_library))
    if not output.parent.is_dir():
        raise FreezeConflict('Create the intended parent directory/volume first')
    if host_lock.is_relative_to(output):
        raise FreezeConflict('Shared host lease must be outside the immutable evidence bundle')
    with host_lease(host_lock, 'prepare finite adapter validation'):
        from formal_owned_runtime import Coordinator
        coordinator = Coordinator(host_lock)
        coordinator._reconcile(coordinator._read())
        source_files = sources()
        tests = {}
        import hashlib
        for name in TEST_FILES:
            tests[name] = file_hash(ROOT/name)
            if tests[name] != hashlib.sha256(subprocess.check_output(['git', 'show', 'HEAD:'+name], cwd=ROOT)).hexdigest():
                raise FreezeConflict('Committed canonical test bytes required: '+name)
        catalog = json.loads((ROOT/CATALOG).read_text()); design = validation_design(catalog)
        env, probe, resources, pip_lock, pip_check = gather_environment(rscript, r_library)
        from external_wells import load_wells, propriety_certificate
        if not propriety_certificate(load_wells(external))['certified']:
            raise FreezeConflict('External W1 source/propriety validation failed')
        external_files = {r['path']: r['sha256'] for r in json.loads((ROOT/'models/external/wells/source-manifest.json').read_text())['files']}
        binding = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            source_branch=subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
            source_files=source_files, validation_test_sources=tests, external_files=external_files, environment=env,
            required_versions={n: importlib.metadata.version(n) for n in ('numpy', 'scipy', 'torch', 'pyro-ppl', 'psutil')},
            required_R_version=env['required_R_version'], required_R_posterior=env['required_R_posterior'],
            windows_limits=LIMITS, minimum_available_ram_bytes=12*1024**3, shared_host_lock=str(host_lock),
            validation_design_sha256=design['design_sha256'])
        if resources['ram_available'] < binding['minimum_available_ram_bytes'] or resources['gpu_free_bytes'] < design['controls']['minimum_gpu_free_bytes']:
            raise ResourceWait('Native validation RAM/device reserve refused')
        needed = sum(input_bytes(r)+65536 for r in design['input_requirements'].values())
        if shutil.disk_usage(output.parent).free < needed + 8*1024**3:
            raise ResourceWait('Input preparation plus 8 GiB reserve refused; not a bound on all future outputs')
        archive = InputArchive(output, VALIDATION_ID, design['input_requirements'], binding, resume=resume)
        if recover_input:
            archive.recover_unsealed_input(recover_input, reason=recovery_reason)
        if (output/'FROZEN.json').exists():
            marker, _, _, _ = verify_validation_bundle(output)
            return dict(marker, newly_generated_inputs=0, previously_sealed=True)
        for name, value in {'catalog.json': catalog, 'validation-design.json': design, 'environment.json': env}.items():
            write_once(output/name, json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n')
        write_once(output/'pip-freeze.txt', pip_lock); write_once(output/'pip-check.txt', pip_check)
        for prefix, original, inventory in [('source/', ROOT, source_files), ('source/', ROOT, tests), ('external/', external, external_files)]:
            for name, digest in inventory.items():
                snapshot_file(relative_file(output, prefix+name), original/name, digest)
        calls = output/'preparation-calls'; calls.mkdir(exist_ok=True)
        call = calls/uuid.uuid4().hex; call.mkdir()
        atomic_json(call/'probe.json', probe); atomic_json(call/'resources.json', resources)
        start = time.perf_counter(); generated = 0
        try:
            from formal_inputs import validate_addresses
            addresses = validate_addresses(VALIDATION_ID, ['G1', 'G2', 'W1'], [0], 4)
            write_once(output/'address-check.json', json.dumps(addresses, sort_keys=True, indent=2)+'\n')
            for name in sorted(design['input_requirements']):
                existed = (output/'receipts'/(name+'.json')).exists()
                archive.prepare(name, maximum_member_bytes=design['controls']['maximum_member_bytes'])
                generated += not existed
            atomic_json(call/'finished.json', dict(input_loop_seconds=time.perf_counter()-start,
                generated_inputs=generated, sampler_calls=0, formal_scientific_repetitions=0))
            return seal_validation(output, archive, catalog, binding)
        except BaseException as exc:
            atomic_json(call/'failed.json', dict(input_loop_seconds=time.perf_counter()-start,
                generated_inputs=generated, error=type(exc).__name__+': '+str(exc), sampler_calls=0))
            raise


def preflight(bundle, *, require_unsealed=True):
    require_native()
    bundle = Path(bundle).resolve()
    if require_unsealed and (bundle/'native-acceptance.json').exists():
        raise FreezeConflict('Accepted evidence is immutable; use read-only verify/export')
    marker, p, design, binding = verify_validation_bundle(bundle)
    from formal_owned_runtime import Coordinator
    coordinator = Coordinator(Path(binding['shared_host_lock']))
    with host_lease(coordinator.lock, 'validate finite source and environment'):
        coordinator._reconcile(coordinator._read())
        for group in ('source_files', 'validation_test_sources'):
            for name, digest in binding[group].items():
                if file_hash(ROOT/name) != digest:
                    raise FreezeConflict('Frozen validation implementation changed: '+name)
        env = binding['environment']
        current, _, resources, _, _ = gather_environment(Path(env['rscript']), Path(env['r_library']))
        if current != env:
            raise FreezeConflict('Frozen native validation environment changed')
    return marker, p, design, binding, coordinator, resources


def _runtime_pass(bundle, p):
    pointer = json.loads((bundle/'runtime-tests/latest-passed.json').read_text())
    result_file = relative_file(bundle, pointer['result'])
    if file_hash(result_file) != pointer['sha256']:
        raise FreezeConflict('Native runtime command result changed')
    result = json.loads(result_file.read_text()); root = result_file.parent
    finished = json.loads((root/'owned/finished.json').read_text())
    started = json.loads((root/'owned/started.json').read_text())
    intent = json.loads((root/'owned/job-intent.json').read_text())
    if (result['protocol_sha256'] != p['protocol_sha256'] or result['exit_code'] != 0 or
            result['passed'] is not True or
            finished['exit_code'] != 0 or finished['error'] is not None or
            finished['job_final']['active_processes'] != 0 or finished['job_final']['job_name'] != intent['name'] or
            started['source_sha256'] != p['source_files']['scripts/windows/run_owned_command.py'] or
            started['job_api_sha256'] != p['source_files']['scripts/windows/job_objects.py']):
        raise FreezeConflict('Actual native test command did not finish successfully')
    expected = [p['validation_environment']['executable'], '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                'tests/windows/test_formal_owned_runtime.py']
    if (started['command'][:7] != expected or len(started['command']) != 9 or
            not started['command'][7].startswith('--basetemp=') or not started['command'][8].startswith('--junitxml=')):
        raise FreezeConflict('Recorded native runtime test command differs')
    for name, digest in result['files'].items():
        if file_hash(relative_file(root, name)) != digest:
            raise FreezeConflict('Native runtime test evidence changed: '+name)
    verify_runtime_cases(root/'runtime.xml')
    return result, root


def runtime_tests(bundle, *, repeat_reason=None):
    require_native(); bundle = Path(bundle).resolve()
    with host_lease(bundle.with_name(bundle.name+'.validation-driver.lock'), 'native validation tests'):
        _, p, _, binding, _, _ = preflight(bundle)
        base = bundle/'runtime-tests'; base.mkdir(exist_ok=True)
        previous = list(base.glob('attempt-*'))
        if previous and (not isinstance(repeat_reason,str) or not repeat_reason.strip()):
            raise FreezeConflict('Native test rerun needs an explicit reason; preserve all prior attempts')
        # An old ancillary command has its own recorded Job identity. Observe
        # it on Windows; a missing finished.json alone is not process death.
        from job_objects import observe_named_job
        observed = {}
        with host_lease(Path(binding['shared_host_lock']), 'inspect prior validation test Jobs'):
            for old in previous:
                intent = old/'owned/job-intent.json'
                if intent.exists():
                    proof = observe_named_job(json.loads(intent.read_text())['name'])
                    if proof['state'] != 'absent' and proof['active_processes'] != 0:
                        raise FreezeConflict('Prior native runtime test Job is still active')
                    observed[old.name] = proof
        folder = base/('attempt-'+uuid.uuid4().hex); folder.mkdir()
        atomic_json(folder/'request.json', dict(protocol_sha256=p['protocol_sha256'], repeat_reason=repeat_reason,
            prior_attempts=[x.name for x in previous], prior_job_observations=observed,
            runtime_cases=16, formal_scientific_repetitions=0))
        # The outer ancillary Job owns pytest and any nested fixture managers.
        # Its shared host lease excludes scientific work during these tests.
        from run_owned_command import run
        code = run([str(Path(sys.executable).resolve()), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                    'tests/windows/test_formal_owned_runtime.py', '--basetemp='+str(folder/'artifacts'),
                    '--junitxml='+str(folder/'runtime.xml')], ROOT, folder/'owned', Path(binding['shared_host_lock']))
        valid = False; error = None
        try:
            if code != 0:
                raise FreezeConflict('Native behavior command failed; all logs retained')
            verify_runtime_cases(folder/'runtime.xml'); valid = True
        except (ValueError, OSError) as exc:
            error = type(exc).__name__+': '+str(exc)
        result = dict(protocol_sha256=p['protocol_sha256'], exit_code=code, passed=valid, error=error,
                      files=file_inventory(folder), formal_scientific_repetitions=0)
        atomic_json(folder/'result.json', result)
        if not valid:
            raise FreezeConflict(error)
        atomic_json(base/'latest-passed.json', dict(result=(folder/'result.json').relative_to(bundle).as_posix(),
                                                   sha256=file_hash(folder/'result.json')))
        return dict(passed=True, tests=16, new_formal_repetitions=0, artifacts=str(folder))


def phase_receipt(bundle, p, phase, *, verified=False):
    name = 'latest-verified.json' if verified else 'latest-complete.json'
    pointer = json.loads((bundle/phase/name).read_text()); path = relative_file(bundle, pointer['result'])
    if file_hash(path) != pointer['sha256']:
        raise FreezeConflict('Finite phase completion record changed')
    result = json.loads(path.read_text()); slots = {s['task']['id']: s for s in validation_slots(p, phase)}
    rows = result['rows']
    if (result['protocol_sha256'] != p['protocol_sha256'] or result['phase'] != phase or
            len(rows) != len(slots) or {r['task_id'] for r in rows} != set(slots)):
        raise FreezeConflict('All finite phase rows are required')
    if verified and (result['verify_only'] is not True or result['newly_executed'] != 0 or
                     result['task_assets_unchanged'] is not True):
        raise FreezeConflict('Actual zero-recomputation verification required')
    from task_journal import read_task_export
    for row in rows:
        history = relative_file(bundle, row['history_export'])
        if file_hash(history) != row['history_export_sha256']:
            raise FreezeConflict('Phase history export changed')
        entry = read_task_export(history)['entry']
        if entry['task'] != slots[row['task_id']]['task'] or not entry['attempts'] or entry['attempts'][-1]['outcome'] != row['outcome']:
            raise FreezeConflict('Finite phase task/outcome differs from history')
    return result


def run_phase(bundle, phase, *, resume=False, verify_only=False):
    require_native(); bundle = Path(bundle).resolve()
    if phase not in ('main', 'cache'):
        raise FreezeConflict('Main or cache phase required')
    with host_lease(bundle.with_name(bundle.name+'.validation-driver.lock'), 'finite validation '+phase):
        _, p, _, binding, coordinator, _ = preflight(bundle)
        _runtime_pass(bundle, p)
        if phase == 'cache':
            phase_receipt(bundle, p, 'main')
        root = bundle/phase; root.mkdir(exist_ok=True)
        visits = root/'visits'; visits.mkdir(exist_ok=True)
        visit = visits/uuid.uuid4().hex; visit.mkdir()
        slots = list(validation_slots(p, phase)); rows = []; new = 0
        from task_journal import TaskJournal
        from formal_measured_runtime import invoke
        registered = set(coordinator.task_keys(p['protocol_sha256'], 0))
        if verify_only and any(TaskJournal.key(s['task']) not in registered for s in slots):
            raise FreezeConflict('Verify-only cannot launch an unregistered slot')
        if verify_only:
            for slot in slots:
                history = coordinator.task_history(slot['task'])
                if history is None or not history['attempts']:
                    raise FreezeConflict('Verify-only cannot launch a registered but unstarted slot')
        before = file_inventory(root/'tasks') if verify_only else None
        atomic_json(visit/'started.json', dict(protocol_sha256=p['protocol_sha256'], phase=phase,
            resume=resume, verify_only=verify_only, task_assets_before=before,
            started_ns=time.time_ns(), timestamp_is_not_duration=True))
        start = time.perf_counter()
        try:
            import psutil
            for index, slot in enumerate(slots, 1):
                task = slot['task']; identifier = task['id']
                if psutil.virtual_memory().available < binding['minimum_available_ram_bytes']:
                    raise ResourceWait('Available RAM refused at task boundary; unvisited tasks remain unvisited')
                request = validation_request(slot, p, bundle, ROOT)
                kwargs = dict(task=task, request=request, output=root/'tasks'/identifier,
                    worker=ROOT/'scripts/windows'/('formal_batch_worker.py' if phase=='main' else 'formal_cache_worker.py'),
                    limits=p['windows_limits'])
                print(json.dumps(dict(index=index, total=len(slots), task=task)), flush=True)
                result = invoke(coordinator, kwargs, root/'call-costs'/identifier,
                    resume=(resume or verify_only) and TaskJournal.key(task) in registered)
                if verify_only and result['newly_executed']:
                    raise FreezeConflict('Verify-only unexpectedly executed a task')
                export = visit/(identifier+'.history.json'); coordinator.export_task(task, export)
                row = dict(task_id=identifier, outcome=result['outcome'], newly_executed=result['newly_executed'],
                    samples_eligible=result['samples_eligible'], measurement_available=result['measurement_available'],
                    history_export=export.relative_to(bundle).as_posix(), history_export_sha256=file_hash(export),
                    attempt_directory=(root/'tasks'/identifier/result['attempt_id']).relative_to(bundle).as_posix(),
                    ledger=(root/'call-costs'/identifier).relative_to(bundle).as_posix())
                atomic_json(visit/(identifier+'.json'), row); rows.append(row); new += int(result['newly_executed'])
                atomic_json(root/'progress.json', dict(visited=len(rows), planned=len(slots), newly_executed=new,
                    last_task=identifier, last_outcome=row['outcome'], not_a_liveness_or_convergence_proof=True))
            same = before == file_inventory(root/'tasks') if verify_only else None
            if verify_only and not same:
                raise FreezeConflict('Verify-only changed retained task assets')
            result = dict(protocol_sha256=p['protocol_sha256'], phase=phase, verify_only=verify_only,
                rows=rows, newly_executed=new, task_assets_unchanged=same, phase_body_seconds=time.perf_counter()-start,
                formal_scientific_repetitions=0, nested_task_costs_not_additive=True,
                controller_time_excludes_preflight_and_final_write=True)
            atomic_json(visit/'result.json', result)
            pointer = dict(result=(visit/'result.json').relative_to(bundle).as_posix(), sha256=file_hash(visit/'result.json'))
            atomic_json(root/'latest-complete.json', pointer)
            if verify_only:
                atomic_json(root/'latest-verified.json', pointer)
            return dict(phase=phase, planned=len(slots), newly_executed=new, verify_only=verify_only,
                        outcome_counts={k:sum(r['outcome']==k for r in rows) for k in sorted({r['outcome'] for r in rows})})
        except BaseException as exc:
            atomic_json(visit/'failed.json', dict(error=type(exc).__name__+': '+str(exc), traceback=traceback.format_exc(),
                phase_body_seconds=time.perf_counter()-start, visited=len(rows), newly_executed=new,
                automatic_retry=False, unvisited_tasks_are_not_failures=True))
            raise


def seal(bundle):
    require_native(); bundle = Path(bundle).resolve()
    with host_lease(bundle.with_name(bundle.name+'.validation-driver.lock'), 'seal native acceptance'):
        _, p, _, binding, coordinator, _ = preflight(bundle)
        _, runtime_root = _runtime_pass(bundle, p)
        records = {phase: phase_receipt(bundle, p, phase, verified=True) for phase in ('main','cache')}
        report = dict(schema='formal-native-adapter-integration-v1', protocol_sha256=p['protocol_sha256'],
                      formal_scientific_repetitions=0)
        # Confirm every ended history once more through its native observer.
        # This does not rerun sampling or silently retry a failed task.
        for phase in ('main','cache'):
            for slot in validation_slots(p, phase):
                entry = coordinator.task_history(slot['task'])
                if entry is None:
                    raise FreezeConflict('An integration registration is missing')
            report[phase] = records[phase]['rows']
        if (bundle/'integration.json').exists():
            raise FreezeConflict('Partial acceptance seal retained; do not overwrite it')
        inventory = file_inventory(bundle)
        for phase in ('main','cache'):
            slots = {s['task']['id']:s for s in validation_slots(p, phase)}
            for row in report[phase]:
                history = read_native_task(bundle, task=slots[row['task_id']]['task'], history_export=row['history_export'],
                    directory=str(Path(row['attempt_directory']).parent).replace('\\','/'),
                    manifest=inventory, source_files=p['source_files'], ledger=row['ledger'])
                wanted = 'valid' if phase=='main' else 'measurement_available'
                if history['summary']['outcome'] != wanted or len(history['attempts']) != 1:
                    raise FreezeConflict('Finite validation failed; preserve outputs, diagnose, and do not authorize the formal grid')
        atomic_json(bundle/'integration.json', report)
        gate = {k:p[k] for k in ('source_files','required_versions','required_R_version','required_R_posterior')}
        gate.update(schema='formal-native-acceptance-v1', platform='win32', passed=True, environment=binding['environment'],
            runtime_test_sha256=p['validation_test_sources'][TEST_FILES[0]],
            runtime_xml=(runtime_root/'runtime.xml').relative_to(bundle).as_posix(),
            runtime_command=(runtime_root/'owned').relative_to(bundle).as_posix(),
            validation_protocol='protocol.json', integration_report='integration.json',
            files=file_inventory(bundle), formal_scientific_repetitions=0,
            scope='Actual finite native adapter validation; not formal inference or convergence')
        gate['gate_sha256'] = fingerprint(gate)
        # A candidate is preserved if final read-back fails. Never emit the
        # accepting filename until the same portable receiver has checked it.
        candidate = bundle/'native-acceptance.candidate.json'
        atomic_json(candidate, gate)
        verify_native_acceptance(candidate, p, ROOT, environment=binding['environment'])
        candidate.rename(bundle/'native-acceptance.json')
        return dict(passed=True, main_tasks=27, cache_probes=24, behavior_tests=16,
                    formal_scientific_repetitions=0, acceptance_sha256=file_hash(bundle/'native-acceptance.json'))


def verify(bundle):
    bundle = Path(bundle).resolve(); _, p, _, binding = verify_validation_bundle(bundle)
    gate = verify_native_acceptance(bundle/'native-acceptance.json', p, bundle/'source', environment=binding['environment'])
    return dict(passed=True, acceptance_sha256=file_hash(bundle/'native-acceptance.json'),
                artifacts=len(gate['files']), reader_did_not_execute_Windows_or_sampler=True)


def export(bundle, output):
    """Portable immutable tar; the returned manifest covers every retained file."""
    import io
    import tarfile
    bundle = Path(bundle).resolve(); output = Path(output).resolve()
    if output.exists() or output.is_relative_to(bundle) or not output.parent.is_dir():
        raise FreezeConflict('Use a fresh archive outside the accepted evidence directory')
    checked = verify(bundle); inventory = file_inventory(bundle)
    p = json.loads((bundle/'protocol.json').read_text())
    binding = json.loads((bundle/'archive.json').read_text())['binding']
    manifest = dict(scope='Finite native acceptance evidence, not a claim of formal research completion',
        source_commit=p['source_commit'], branch=binding['source_branch'],
        files={'validation/'+n:dict(bytes=(bundle/n).stat().st_size,sha256=h) for n,h in inventory.items()})
    start = time.perf_counter()
    with tarfile.open(output,'x') as archive:
        for name in sorted(inventory):
            archive.add(relative_file(bundle,name),arcname='validation/'+name,recursive=False)
        data=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
        info=tarfile.TarInfo('WINDOWS-RETURN-MANIFEST.json');info.size=len(data);archive.addfile(info,io.BytesIO(data))
    if file_inventory(bundle)!=inventory:
        raise FreezeConflict('Evidence changed during export; retain the partial archive, do not deliver it')
    result=dict(checked,archive_sha256=file_hash(output),bytes=output.stat().st_size,files=len(inventory),
                export_seconds=time.perf_counter()-start,source_commit=p['source_commit'])
    write_once(output.with_suffix(output.suffix+'.sha256'), result['archive_sha256']+'  '+output.name+'\n')
    atomic_json(output.with_suffix(output.suffix+'.receipt.json'),result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('prepare')
    for name in ('output','external','host-lock','rscript','r-library'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume',action='store_true');p.add_argument('--recover-input');p.add_argument('--recovery-reason')
    p=commands.add_parser('test');p.add_argument('--bundle',type=Path,required=True);p.add_argument('--repeat-reason')
    p=commands.add_parser('run');p.add_argument('--bundle',type=Path,required=True);p.add_argument('--phase',choices=['main','cache'],required=True)
    p.add_argument('--resume',action='store_true');p.add_argument('--verify-only',action='store_true')
    for name in ('seal','verify','export'):
        p=commands.add_parser(name);p.add_argument('--bundle',type=Path,required=True)
        if name=='export':p.add_argument('--output',type=Path,required=True)
    args=vars(parser.parse_args());command=args.pop('command')
    action={'prepare':prepare,'test':runtime_tests,'run':run_phase,'seal':seal,'verify':verify,'export':export}[command]
    print(json.dumps(action(**args),indent=2),flush=True)


if __name__=='__main__':main()
