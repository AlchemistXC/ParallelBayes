"""Read the finite native acceptance evidence required before formal sampling.

The producer is a separate, predeclared native validation run. This reader
checks complete frames and immutable artifacts; it does not rerun Windows,
recompute an oracle, prove convergence, or grant validity to formal samples.
"""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from batch_contract import BatchPlan, create_tasks, WORKFLOWS
from formal_execution import VALIDATION_ID
from formal_freeze import relative_file
from formal_measurement_plan import create_measurement_plan
from formal_runtime import file_hash, fingerprint
from task_journal import read_task_export

RUNTIME_CASES = dict(
    test_completion_zero_recompute_and_kind_separation=2,
    test_identity_input_source_and_unknown_kind_refusal=1,
    test_worker_source_and_task_configuration_changes_refused=1,
    test_existing_failure_and_contradictory_measurement_are_not_retried=1,
    test_disk_refusal_before_process_and_low_rss_only_kills_fixture=1,
    test_one_explicit_infrastructure_retry_and_no_cache_retry=1,
    test_real_manager_crash_cooperative_lock_descendants_and_safe_continue=1,
    test_cuda_synchronization_and_recoverable_resource_error=1,
    test_saved_numeric_failure_before_manager_seal_cannot_retry=1,
    test_memory_observer_failure_stops_owned_job=1,
    test_portable_cost_policy_accepts_native_call_ledger=1,
    test_cuda_manager_death_ends_owned_descendants_preserves_other_context=1,
    test_kernel_commit_limit_denies_small_owned_allocation=2,
    test_legacy_registration_reconciled_before_v2_launch=1)


def validation_groups():
    return [dict(models=['G1', 'W1'], replicates=[0], budgets=[64], workflows=list(WORKFLOWS)),
            dict(models=['G2'], replicates=[0], budgets=[16384], workflows=list(WORKFLOWS))]


def verify_native_acceptance(path, formal_protocol, source_root, *, environment):
    path = Path(path).resolve(); root = path.parent
    gate = json.loads(path.read_text()); unsigned = dict(gate); digest = unsigned.pop('gate_sha256')
    if (fingerprint(unsigned) != digest or gate['schema'] != 'formal-native-acceptance-v1' or
            gate['platform'] != 'win32' or gate['passed'] is not True):
        raise ValueError('A complete native acceptance record is required')
    for key in ('source_files', 'required_versions', 'required_R_version', 'required_R_posterior'):
        if gate[key] != formal_protocol[key]:
            raise ValueError('Native acceptance source/environment differs: '+key)
    if gate['environment'] != environment:
        raise ValueError('Full native Python/dependency/device environment differs')
    if gate['runtime_test_sha256'] != file_hash(Path(source_root)/'tests/windows/test_formal_owned_runtime.py'):
        raise ValueError('Native test source differs')
    for name, expected in gate['files'].items():
        p = relative_file(root, name)
        if not p.is_file() or file_hash(p) != expected:
            raise ValueError('Acceptance evidence changed: '+name)
    def artifact(name):
        if name not in gate['files']:
            raise ValueError('Unbound acceptance artifact: '+name)
        return relative_file(root, name)
    cases = list(ET.parse(artifact(gate['runtime_xml'])).iter('testcase'))
    if (len({c.attrib['name'] for c in cases}) != len(cases) or
            Counter(c.attrib['name'].split('[')[0] for c in cases) != RUNTIME_CASES or
            any(c.find(k) is not None for c in cases for k in ('failure', 'error', 'skipped'))):
        raise ValueError('Every declared native runtime case must pass without skips')
    protocol = json.loads(artifact(gate['validation_protocol']).read_text())
    plan = BatchPlan(protocol)
    expected_tasks = create_tasks(VALIDATION_ID, validation_groups())
    if (protocol['identity'] != VALIDATION_ID or protocol['scope_kind'] != 'technical_batch_validation' or
            protocol['required_platform'] != 'win32' or protocol['tasks'] != expected_tasks or
            protocol['native_runtime_schema'] != 'windows-owned-runtime-v2'):
        raise ValueError('Native adapter validation grid differs')
    if protocol['validation_environment'] != environment:
        raise ValueError('Original adapter validation environment differs')
    for key in ('source_files', 'required_versions', 'required_R_version', 'required_R_posterior', 'controls'):
        if protocol[key] != formal_protocol[key]:
            raise ValueError('Adapter validation does not use the formal implementation/controls: '+key)
    wanted = {t['name']: t for t in formal_protocol['targets'] if t['name'] in ('G1', 'G2', 'W1')}
    if {t['name']:t for t in protocol['targets']} != wanted:
        raise ValueError('Adapter validation target/geometry differs')
    allocation = create_measurement_plan(VALIDATION_ID, expected_tasks)
    primary = {t['id']:t for t in expected_tasks}
    cache = {}
    for probe in allocation['probes']:
        cache[probe['id']] = dict(primary[probe['primary_task_id']], id=probe['id'])
    report = json.loads(artifact(gate['integration_report']).read_text())
    if (report['schema'] != 'formal-native-adapter-integration-v1' or
            report['protocol_sha256'] != plan.protocol_sha256 or report['formal_scientific_repetitions'] != 0):
        raise ValueError('Integration evidence identity differs')
    for phase, frame, outcome in [('main', primary, 'valid'), ('cache', cache, 'measurement_available')]:
        rows = report[phase]
        if len(rows) != len(frame) or {r['task_id'] for r in rows} != set(frame):
            raise ValueError('All finite native integration tasks must be present')
        for row in rows:
            exported = read_task_export(artifact(row['history_export']))
            entry = exported['entry']; task = entry['task']
            expected = dict(frame[row['task_id']], protocol_sha256=plan.protocol_sha256,
                            artifact_kind='posterior' if phase == 'main' else 'cache_measurement')
            if task != expected or len(entry['attempts']) != 1 or entry['attempts'][0]['outcome'] != outcome:
                raise ValueError('Native integration task did not pass on its declared attempt')
            worker_name = 'formal_batch_worker.py' if phase == 'main' else 'formal_cache_worker.py'
            for field, source in [('worker_sha256', 'scripts/windows/'+worker_name),
                                  ('runtime_sha256','scripts/windows/formal_owned_runtime.py'),
                                  ('journal_sha256','scripts/completion/task_journal.py'),
                                  ('job_api_sha256','scripts/windows/job_objects.py')]:
                if entry['binding'][field] != protocol['source_files'][source]:
                    raise ValueError('Native integration implementation differs')
            capsule, capsule_sha = plan.capsule(row['task_id'] if phase == 'main' else
                next(p['primary_task_id'] for p in allocation['probes'] if p['id'] == row['task_id']))
            request = entry['binding']['request']
            if request['capsule'] != capsule or request['capsule_sha256'] != capsule_sha:
                raise ValueError('Integration task used a different numerical capsule')
            folder = relative_file(root, row['attempt_directory'])
            state = json.loads(artifact(row['attempt_directory']+'/state.json').read_text())
            completion = json.loads(artifact(row['attempt_directory']+'/completion.json').read_text())
            if (completion['state_sha256'] != file_hash(folder/'state.json') or state['outcome'] != outcome or
                    state['task'] != task or state['binding_sha256'] != fingerprint(entry['binding']) or
                    state['job_final']['active_processes'] != 0):
                raise ValueError('Native terminal identity or Job end proof differs')
            for member, expected_sha in state['assets'].items():
                if gate['files'].get(row['attempt_directory']+'/'+member) != expected_sha:
                    raise ValueError('Integration terminal assets omitted or changed')
            from formal_runtime import validate_worker_eligibility
            validate_worker_eligibility(task, state['worker_result'])
            if state['worker_result']['status'] != 'completed':
                raise ValueError('Native worker eligibility differs')
    return gate
