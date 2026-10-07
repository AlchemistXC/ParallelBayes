"""Native Windows preparation of all formal inputs and immutable evidence.

No sampler is launched. Native formal-worker/runtime acceptance is a separate
gate that the future execution entry must establish even for a sealed bundle.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/completion'), str(ROOT/'scripts/windows'),
                str(ROOT/'r-package/inst/python'), str(ROOT/'examples')]
from formal_runtime import atomic_json, file_hash, host_lease, ResourceWait
from formal_freeze import InputArchive, FreezeConflict, input_bytes, seal_study, relative_file, verify_sealed_study
from formal_study_plan import create_study_plan

CATALOG = 'benchmark/protocols/inference-budget-pilot-mac-v1.json'
REFERENCE_FILES = [
    'benchmark/protocols/windows-native-v1.json', CATALOG,
    'models/external/wells/source-manifest.json',
    'benchmark/analysis/outputs/completion-f3/reference-reuse.json',
    'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis/reference-contract.json',
    'benchmark/analysis/outputs/wells-quadrature-v1/R12-n96.json',
    'benchmark/analysis/outputs/wells-quadrature-v1/result.json']
LIMITS = dict(rss_bytes=8*1024**3, job_commit_bytes=12*1024**3,
              disk_start_bytes=4*1024**3, disk_floor_bytes=1024**3, poll_seconds=.2)


def sources():
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise FreezeConflict('Commit source and canonical line endings before preparation')
    names = subprocess.check_output(['git', 'ls-files', 'r-package/inst/python', 'scripts/completion',
                                    'scripts/windows', 'examples'], cwd=ROOT, text=True).splitlines()
    names = sorted(set(n for n in names if n.endswith(('.py', '.R'))) | set(REFERENCE_FILES))
    found = {}
    for name in names:
        digest = file_hash(ROOT/name)
        canonical = hashlib.sha256(subprocess.check_output(['git', 'show', 'HEAD:'+name], cwd=ROOT)).hexdigest()
        if digest != canonical:
            raise FreezeConflict('Working source differs from canonical committed bytes: '+name)
        found[name] = digest
    return found


def snapshot_file(destination, source, expected):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_file() or destination.is_symlink() or file_hash(destination) != expected:
            raise FreezeConflict('Existing snapshot differs; retained without overwrite: '+str(destination))
    else:
        # A failed partial copy remains visible and will be refused on resume.
        with Path(source).open('rb') as src, destination.open('xb') as dst:
            shutil.copyfileobj(src, dst, length=1024*1024)
            dst.flush(); os.fsync(dst.fileno())
        if file_hash(destination) != expected:
            raise FreezeConflict('Copied snapshot differs: '+str(destination))


def write_once(path, content):
    content = content.encode('utf-8')
    if path.exists():
        if path.is_symlink() or path.read_bytes() != content:
            raise FreezeConflict('Existing preparation metadata differs: '+path.name)
        return
    with path.open('xb') as stream:
        stream.write(content); stream.flush(); os.fsync(stream.fileno())


def gather_environment(rscript, r_library):
    if sys.platform != 'win32':
        raise FreezeConflict('Actual native Windows required; Mac/Linux/WSL cannot freeze this experiment')
    import psutil
    import torch
    from probe_environment import probe
    report = probe(require_windows=True, require_cuda=True, expected_device='RTX 5080')
    if report['status'] != 'passed' or report.get('capability') != [12, 0]:
        raise FreezeConflict('Required float64 RTX5080 framework probe failed: '+json.dumps(report))
    env = dict(os.environ, R_LIBS_USER=str(r_library))
    code = 'cat(jsonlite::toJSON(list(R=R.version.string,posterior=as.character(packageVersion("posterior"))),auto_unbox=TRUE))'
    r = json.loads(subprocess.check_output([str(rscript), '--vanilla', '-e', code], env=env, text=True))
    pip_lock = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze', '--all'], text=True)
    check = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True)
    if check.returncode:
        raise FreezeConflict('Environment pip check failed: '+check.stdout+check.stderr)
    gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=uuid,name,driver_version,memory.total',
                                   '--format=csv,noheader'], text=True).strip()
    venv_marker = Path(sys.executable).resolve().parent.parent/'PARALLELBAYES-FROZEN.json'
    stable = dict(python=sys.version, executable=str(Path(sys.executable).resolve()), platform=sys.platform,
                  os=platform.platform(), host=platform.node(), gpu=gpu, torch_cuda=torch.version.cuda,
                  required_R_version=r['R'], required_R_posterior=r['posterior'],
                  rscript=str(rscript), r_library=str(r_library),
                  packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
                  pip_freeze_sha256=hashlib.sha256(pip_lock.encode()).hexdigest(),
                  original_venv_marker_sha256=file_hash(venv_marker) if venv_marker.exists() else None)
    resources = dict(ram_total=psutil.virtual_memory().total, ram_available=psutil.virtual_memory().available,
                     gpu_free_bytes=torch.cuda.mem_get_info()[0], gpu_total_bytes=torch.cuda.mem_get_info()[1],
                     observed_ns=time.time_ns(), resource_observation_is_not_a_guarantee=True)
    return stable, report, resources, pip_lock, check.stdout+check.stderr


def prepare(output, identity, external, host_lock, rscript, r_library, *, resume=False, recover_input=None, recovery_reason=None):
    if sys.platform != 'win32':
        raise FreezeConflict('Only native Windows may prepare the formal execution bundle')
    if bool(recover_input) != bool(recovery_reason) or (recover_input and not resume):
        raise FreezeConflict('Named input recovery requires explicit resume and a reason')
    output, external, host_lock, rscript, r_library = map(lambda p: Path(p).resolve(),
                                                        (output, external, host_lock, rscript, r_library))
    if not output.parent.is_dir():
        raise FreezeConflict('Create the intended parent volume/directory before preparation')
    with host_lease(host_lock, output):
        # Observe both indexed v2 and possible legacy cohorts through native Jobs.
        from formal_owned_runtime import Coordinator
        coordinator = Coordinator(host_lock)
        active = coordinator._read(); coordinator._reconcile(active)
        source_files = sources()
        catalog = json.loads((ROOT/CATALOG).read_text())
        plan = create_study_plan(identity, catalog)
        env, probe, resources, pip_lock, pip_check = gather_environment(rscript, r_library)
        from external_wells import load_wells, propriety_certificate
        data = load_wells(external)
        if not propriety_certificate(data)['certified']:
            raise FreezeConflict('W1 source/propriety check failed')
        manifest = json.loads((ROOT/'models/external/wells/source-manifest.json').read_text())
        external_files = {r['path']: r['sha256'] for r in manifest['files']}
        binding = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                       source_files=source_files, external_files=external_files, environment=env,
                       required_versions={n: importlib.metadata.version(n) for n in ('numpy','scipy','torch','pyro-ppl','psutil')},
                       required_R_version=env['required_R_version'], required_R_posterior=env['required_R_posterior'],
                       windows_limits=LIMITS, minimum_available_ram_bytes=12*1024**3,
                       shared_host_lock=str(host_lock), study_design_sha256=plan['design_sha256'])
        if resources['ram_available'] < binding['minimum_available_ram_bytes'] or resources['gpu_free_bytes'] < plan['controls']['minimum_gpu_free_bytes']:
            raise ResourceWait('Preparation resource observation is below the declared reserve')
        required_inputs = sum(input_bytes(r) + 65536 for r in plan['input_requirements'].values())
        if not resume and shutil.disk_usage(output.parent).free < required_inputs + 8*1024**3:
            raise ResourceWait('Insufficient space for uncompressed master inputs plus 8 GiB reserve')
        archive = InputArchive(output, identity, plan['input_requirements'], binding, resume=resume)
        if recover_input:
            archive.recover_unsealed_input(recover_input, reason=recovery_reason)
        if (output/'FROZEN.json').exists():
            marker, protocol = verify_sealed_study(output)
            return dict(marker, newly_generated_inputs=0, previously_sealed=True)
        # Scientific inputs/protocol are not written until source/data/dependency
        # snapshots have been made. Old environment markers are never modified.
        documents = {'study-plan.json': plan, 'catalog.json': catalog, 'environment.json': env}
        for name, value in documents.items():
            write_once(output/name, json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n')
        write_once(output/'pip-freeze.txt', pip_lock)
        write_once(output/'pip-check.txt', pip_check)
        files = {name: file_hash(output/name) for name in [*documents, 'pip-freeze.txt', 'pip-check.txt']}
        for prefix, original, inventory in [('source/', ROOT, source_files), ('external/', external, external_files)]:
            for name, digest in inventory.items():
                target = relative_file(output, prefix+name)
                snapshot_file(target, original/name, digest)
                files[prefix+name] = digest
        observations = output/'preparation-calls'; observations.mkdir(exist_ok=True)
        call = observations/('call-'+str(time.time_ns())); call.mkdir()
        atomic_json(call/'probe.json', probe)
        resources['disk'] = shutil.disk_usage(output)._asdict()
        resources['all_master_logical_bytes'] = sum(input_bytes(r) for r in plan['input_requirements'].values())
        resources['scope'] = 'Preparation and per-task reserves only; not a guarantee that all outputs/archives will fit'
        atomic_json(call/'resources.json', resources)
        start = time.perf_counter(); generated = 0
        try:
            from formal_inputs import validate_addresses
            addresses = validate_addresses(identity, [t['name'] for t in plan['targets']], range(128), 4)
            write_once(output/'address-check.json', json.dumps(addresses, sort_keys=True, indent=2)+'\n')
            files['address-check.json'] = file_hash(output/'address-check.json')
            import psutil
            for i, name in enumerate(sorted(plan['input_requirements'])):
                if psutil.virtual_memory().available < binding['minimum_available_ram_bytes']:
                    raise ResourceWait('Available RAM below preparation reserve at input boundary')
                existed = (output/'receipts'/(name+'.json')).exists()
                receipt = archive.prepare(name, maximum_member_bytes=plan['controls']['maximum_member_bytes'])
                generated += not existed
                print(json.dumps(dict(input=i+1, total=1152, name=name, sha256=receipt['sha256'], reused=existed)), flush=True)
            # All attempted preparation costs and probes are retained as evidence.
            atomic_json(call/'completed.json', dict(seconds=time.perf_counter()-start, generated_inputs=generated,
                                                    sampler_calls=0, sampling_authorized=False))
            for path in sorted(observations.rglob('*')):
                if path.is_file(): files[path.relative_to(output).as_posix()] = file_hash(path)
            for path in sorted((output/'preparation-recovery').rglob('*')):
                if path.is_file(): files[path.relative_to(output).as_posix()] = file_hash(path)
            return seal_study(output, plan, catalog, archive, binding, files)
        except BaseException as exc:
            atomic_json(call/'failed.json', dict(seconds=time.perf_counter()-start, generated_inputs=generated,
                                                error=type(exc).__name__+': '+str(exc), sampler_calls=0))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare')
    for name in ('output', 'external', 'host-lock', 'rscript', 'r-library'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--identity', required=True); p.add_argument('--resume', action='store_true')
    p.add_argument('--recover-input'); p.add_argument('--recovery-reason')
    v = commands.add_parser('verify'); v.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'verify':
        result, _ = verify_sealed_study(args.bundle)
    else:
        result = prepare(args.output, args.identity, args.external, args.host_lock, args.rscript, args.r_library,
                         resume=args.resume, recover_input=args.recover_input, recovery_reason=args.recovery_reason)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
