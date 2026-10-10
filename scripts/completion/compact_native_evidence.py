# Explicit compact adapter of formal_native_evidence.py; lifecycle/cost semantics retained.
# The preserved historical reader continues to require its original worker sources.
"""Portable v2 task evidence: one exported history and its retained attempts.

The caller supplies the checksum manifest from a separately verified delivery
and the frozen task/source contract. Windows absolute paths are historical IDs,
never local read locations. No live journal, Windows API or sampler is loaded.
This verifies recorded lifecycle and costs, not numerical correctness anew.
"""
import json
import math
from pathlib import Path, PureWindowsPath

from formal_freeze import relative_file
from formal_runtime import file_hash, fingerprint, task_artifact_kind, validate_worker_eligibility
from formal_outcomes import summarize_attempts
from formal_cost_policy import summarize_task_costs
from measured_coordinator import read_calls
from task_journal import read_task_export

SCHEMA = 'windows-owned-runtime-v2'
ENDED = {'valid', 'measurement_available', 'numerical_failure', 'resource_failure',
         'output_failure_unclassified', 'infrastructure_interruption'}


class _Assets:
    def __init__(self, root, manifest):
        self.root = Path(root).resolve()
        self.manifest = manifest

    def path(self, name):
        p = relative_file(self.root, name)
        if name not in self.manifest or not p.is_file() or file_hash(p) != self.manifest[name]:
            raise ValueError('Missing, unbound or changed native evidence: ' + name)
        return p

    def json(self, name):
        return json.loads(self.path(name).read_text())

    def tree(self, name):
        root = relative_file(self.root, name)
        if not root.is_dir():
            raise ValueError('Native evidence directory is missing: ' + name)
        result = {}
        for p in sorted(root.rglob('*')):
            if p.is_symlink():
                raise ValueError('Native evidence may not contain symlinks')
            if p.is_file():
                member = p.relative_to(root).as_posix()
                result[member] = file_hash(self.path(name + '/' + member))
        expected = {p[len(name)+1:]: h for p, h in self.manifest.items() if p.startswith(name + '/')}
        if result != expected:
            raise ValueError('Native evidence inventory differs: ' + name)
        return result


def _duration(value):
    if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
        raise ValueError('Unknown or finite nonnegative seconds required')
    return value


def _job_end(proof, job_name, *, recovery=False):
    if proof.get('job_name') != job_name:
        raise ValueError('Recorded Windows Job identity differs')
    if recovery and proof.get('state') == 'absent':
        if not proof.get('proof'):
            raise ValueError('Missing recorded Job absence observation')
        return
    if recovery and proof.get('state') != 'present':
        raise ValueError('Unknown Job observation cannot prove termination')
    if type(proof.get('active_processes')) is not int or proof['active_processes'] != 0:
        raise ValueError('Recorded Job has unresolved active processes')


def _failed_output(files, folder, inventory):
    # Preserve the runtime's classification from saved output, without importing
    # its Windows observer or invoking a numerical implementation.
    for name in ('worker-result.json', 'candidate.json', 'ordinary-output.json'):
        if name in inventory:
            value = files.json(folder + '/' + name)
            if value.get('status', value.get('candidate_status')) == 'failed':
                kind = value.get('failure_category', 'numerical_failure')
                return kind if kind in ENDED - {'infrastructure_interruption'} else 'output_failure_unclassified'
    for name in sorted(inventory):
        if Path(name).name == 'cache-result.json':
            states = files.json(folder + '/' + name).get('observation', {}).get('execution_outcomes', [])
            for kind in ('numerical_failure', 'resource_failure'):
                if kind in states:
                    return kind
    return None


def read_native_task(root, *, task, history_export, directory, manifest, source_files, ledger=None):
    """Read a registered task, including prelaunch refusal and retained failure.

    `history_export`, `directory`, and optional `ledger` are explicit relative
    archive locations. A missing export is an evidence gap, not proof that a
    task never ran. An exported registration with zero attempts is not_run.
    Unresolved active attempts are refused; reconcile them on their own host.
    Returned sample/measurement locations only identify recorded eligibility;
    numerical raw-array auditing remains a separate required operation.
    """
    files = _Assets(root, manifest)
    exported = read_task_export(files.path(history_export))
    entry = exported['entry']; binding = entry['binding']
    kind = task_artifact_kind(task)
    if (entry['task'] != task or binding['schema'] != SCHEMA or
            binding['environment']['platform'] != 'win32' or
            exported['live_identity'] != dict(schema=SCHEMA, platform='win32', host_lock=binding['host_lock'])):
        raise ValueError('Native task, source platform or journal identity differs')
    original = PureWindowsPath(entry['output'])
    if not original.is_absolute():
        raise ValueError('Original native output identity must be absolute')
    if binding['request']['capsule'].get('compact_execution_contract') != 'windows-compact-contract-v1':
        raise ValueError('Explicit compact worker contract required')
    worker = 'compact_worker.py'
    for field, source in (
        ('worker_sha256', 'scripts/windows/' + worker),
        ('runtime_sha256', 'scripts/windows/formal_owned_runtime.py'),
        ('journal_sha256', 'scripts/completion/task_journal.py'),
        ('job_api_sha256', 'scripts/windows/job_objects.py')):
        if binding[field] != source_files[source]:
            raise ValueError('Native implementation binding differs: ' + field)
    attempts = entry['attempts']
    if len(attempts) > (1 if kind == 'cache_measurement' else 2):
        raise ValueError('Native retry allowance exceeded')
    rows = []; ordinary = {}; last_directory = None; last_state = None
    if attempts:
        folder = relative_file(files.root, directory)
        actual_dirs = {p.name for p in folder.glob('attempt-*') if p.is_dir()}
        if actual_dirs != {a['id'] for a in attempts}:
            raise ValueError('Retained attempt directories differ from exported history')
    elif relative_file(files.root, directory).exists():
        raise ValueError('Prelaunch registration unexpectedly has output evidence')
    for index, attempt in enumerate(attempts, 1):
        identifier = f'attempt-{index:04d}'
        if attempt['id'] != identifier or PureWindowsPath(attempt['directory']) != original / identifier:
            raise ValueError('Native attempt lineage or original path differs')
        if attempt['outcome'] not in ENDED:
            raise ValueError('Active or unknown native attempt requires original-host reconciliation')
        folder = directory + '/' + identifier
        inventory = files.tree(folder)
        if files.json(folder + '/binding.json') != binding or files.json(folder + '/request.json') != binding['request']:
            raise ValueError('Archived native binding/request differs from exported history')
        if files.json(folder + '/job.json')['name'] != attempt['job_name']:
            raise ValueError('Native launch Job identity differs')
        if 'state.json' in inventory:
            if attempt.get('recovery'):
                raise ValueError('Sealed state conflicts with a reconciliation sidecar')
            state = files.json(folder + '/state.json')
            completion = files.json(folder + '/completion.json')
            if (completion['state_sha256'] != inventory['state.json'] or state['schema'] != SCHEMA or
                    state['task'] != task or state['binding_sha256'] != fingerprint(binding)):
                raise ValueError('Native terminal identity/checksum differs')
            assets = {n: h for n, h in inventory.items() if Path(n).name not in ('state.json', 'completion.json')}
            if assets != state['assets']:
                raise ValueError('Native terminal assets differ')
            _job_end(state['job_final'], attempt['job_name'])
            seconds = _duration(state['invocation_seconds'])
            success = attempt['outcome'] in ('valid', 'measurement_available')
            wanted_status = 'completed' if success else 'interrupted' if attempt['outcome'] == 'infrastructure_interruption' else 'failed'
            if state['status'] != wanted_status or state['unknown_time_imputed'] is not False:
                raise ValueError('Native terminal status or timing semantics differ')
            if success:
                result = state['worker_result']
                if result != files.json(folder + '/worker-result.json') or result['status'] != 'completed':
                    raise ValueError('Completed native worker evidence differs')
                validate_worker_eligibility(task, result)
                if state['exit_code'] != 0:
                    raise ValueError('Successful native result has a nonzero exit code')
            evidence_sha = inventory['state.json']
        else:
            if 'completion.json' in inventory or attempt.get('recovery') != identifier + '.json':
                raise ValueError('Unsealed native attempt needs an explicit reconciliation record')
            name = directory + '/recovery/' + attempt['recovery']
            state = files.json(name)
            if (state['schema'] != SCHEMA or state['original_assets'] != inventory or
                    attempt['original_assets_sha256'] != fingerprint(inventory) or
                    state['proof'] != attempt['exit_confirmed_by']):
                raise ValueError('Reconciled original assets or termination observation differs')
            _job_end(state['proof'], attempt['job_name'], recovery=True)
            failed = _failed_output(files, folder, inventory)
            if (state['outcome'] != (failed or 'infrastructure_interruption') or
                    state['failed_output_prevents_retry'] is not bool(failed) or
                    state['invocation_seconds'] is not None or state['unknown_time_imputed'] is not False):
                raise ValueError('Reconciliation changes a saved failure or imputes lost time')
            seconds = None; evidence_sha = manifest[name]
        if (state['outcome'] != attempt['outcome'] or state['artifact_kind'] != kind or
                state['samples_eligible'] is not (attempt['outcome'] == 'valid') or
                state['measurement_available'] is not (attempt['outcome'] == 'measurement_available')):
            raise ValueError('Native outcome contradicts artifact eligibility')
        if (kind == 'cache_measurement' and state['samples_eligible']) or (kind == 'posterior' and state['measurement_available']):
            raise ValueError('Native cache and posterior eligibility cannot be exchanged')
        rows.append(dict(attempt_id=identifier, binding_sha256=fingerprint(binding), outcome=attempt['outcome'],
                         seconds=seconds, artifact_kind=kind, evidence_sha256=evidence_sha,
                         cost_scope='Native v2 invocation through terminal state, excludes final seal/journal writes',
                         unknown_time_imputed=False))
        ordinary[identifier] = (_duration(files.json(folder + '/ordinary-process.json')['ordinary_process_wall_seconds'])
                                if 'ordinary-process.json' in inventory else None)
        last_directory = str(relative_file(files.root, folder)); last_state = state
    summary = summarize_attempts(rows)
    history = dict(task=task, original=entry['output'], attempts=rows, summary=summary,
                   eligible_directory=last_directory if summary['outcome'] == 'valid' else None,
                   measurement_directory=last_directory if summary['outcome'] == 'measurement_available' else None,
                   history_export_sha256=manifest[history_export], binding=binding,
                   last_state=last_state, attempts_are_statistical_replicates=False,
                   live_processes_observed_by_reader=False, numerical_audit_reexecuted=False)
    if ledger is not None:
        files.tree(ledger)
        identity, calls = read_calls(relative_file(files.root, ledger))
        if (identity.get('native_schema') != SCHEMA or identity['host_lock'] != binding['host_lock'] or
                identity['recorder_source_sha256'] != source_files['scripts/windows/formal_measured_runtime.py']):
            raise ValueError('Native external call recorder identity differs')
        history['costs'] = summarize_task_costs(history, identity, calls, ordinary)
    else:
        history['costs'] = None
    return history


