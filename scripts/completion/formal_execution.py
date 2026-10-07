"""Complete study dispatch and compact worker contracts, without OS ownership.

The native controller verifies the whole sealed study and acceptance evidence
once per invocation. Each worker checks its own marker, source, environment,
actual input and capsule. Neither a planning file nor this reducer proves that
a Windows Job has ended or that a posterior has converged.
"""
import copy
import importlib.metadata
import json
from pathlib import Path
import sys

from batch_contract import BatchPlan, validate_capsule
from formal_measurement_plan import validate_measurement_plan
from formal_runtime import file_hash, fingerprint
from formal_study_plan import create_study_plan

SCHEMA = 'windows-owned-runtime-v2'
VALIDATION_ID = 'windows-formal-adapter-validation-v1'
PHASES = tuple((b, p) for b in range(4) for p in ('main', 'cache'))
ENDED = {'valid', 'measurement_available', 'numerical_failure', 'resource_failure',
         'output_failure_unclassified', 'infrastructure_interruption'}


def validate_worker_scope(capsule, request, marker, gate=None):
    """Pure identity checks, not an OS/platform or full-evidence certificate."""
    if request.get('native_runtime_schema') != SCHEMA or capsule['required_platform'] != 'win32':
        raise ValueError('Explicit v2 native Windows execution contract required')
    if request.get('phase') not in ('main', 'cache'):
        raise ValueError('Separate posterior/cache phase required')
    if marker['protocol_sha256'] != capsule['protocol_sha256'] or marker['identity'] != capsule['identity']:
        raise ValueError('Worker capsule and sealed protocol identity differ')
    if marker['source_commit'] != capsule['source_commit']:
        raise ValueError('Worker source and marker differ')
    if capsule['scope_kind'] == 'formal_inference':
        if (not capsule['identity'].startswith('windows-formal-') or capsule['identity'] == VALIDATION_ID or
                marker.get('schema') != 'formal-study-freeze-v1' or marker.get('inputs') != 1152 or
                marker.get('sampling_authorized_by_this_document') is not False or
                marker.get('native_execution_gate_required') is not True):
            raise ValueError('Complete formal freeze marker required')
        # This is a compact worker-side binding. The native controller must
        # verify the gate's underlying artifacts; a JSON claim is insufficient.
        if (gate is None or gate.get('schema') != 'formal-native-acceptance-v1' or gate.get('passed') is not True or
                gate.get('platform') != 'win32' or gate.get('source_files') != capsule['source_files'] or
                gate.get('required_versions') != capsule['required_versions'] or
                gate.get('required_R_version') != capsule['required_R_version'] or
                gate.get('required_R_posterior') != capsule['required_R_posterior']):
            raise ValueError('Matching native acceptance evidence binding required')
    elif capsule['scope_kind'] == 'technical_batch_validation':
        t = capsule['task']
        if (capsule['identity'] != VALIDATION_ID or marker.get('schema') != 'formal-adapter-validation-freeze-v1' or
                t['model'] not in ('G1', 'G2', 'W1') or t['replicate'] != 0 or t['batch'] != 0 or
                t['budget'] != (16384 if t['model'] == 'G2' else 64) or marker.get('main_tasks') != 27 or
                marker.get('cache_probes') != 24 or marker.get('formal_scientific_repetitions') != 0):
            raise ValueError('Only the separately identified bounded adapter validation is permitted')
    else:
        raise ValueError('Unsupported scientific scope')
    if request['phase'] == 'cache' and capsule['task']['kernel'] == 'nuts':
        raise ValueError('NUTS has no cached-execution workflow')
    return capsule


def load_worker_request(path, source_root):
    if sys.platform != 'win32':
        raise ValueError('This worker requires actual native Windows')
    request = json.loads(Path(path).read_text())
    c = validate_capsule(request['capsule'], request['capsule_sha256'])
    marker_path = Path(request['sealed_marker'])
    if file_hash(marker_path) != request['sealed_marker_sha256']:
        raise ValueError('Sealed marker changed')
    marker = json.loads(marker_path.read_text())
    gate = None
    if c['scope_kind'] == 'formal_inference':
        gate_path = Path(request['native_acceptance'])
        if file_hash(gate_path) != request['native_acceptance_sha256']:
            raise ValueError('Native acceptance binding changed')
        gate = json.loads(gate_path.read_text())
    validate_worker_scope(c, request, marker, gate)
    for name, digest in c['source_files'].items():
        if file_hash(Path(source_root)/name) != digest:
            raise ValueError('Frozen source changed: '+name)
    for name, version in c['required_versions'].items():
        if importlib.metadata.version(name) != version:
            raise ValueError('Dependency differs: '+name)
    # W1 is always loaded from the copied, hash-verified external snapshot.
    if c['task']['model'] == 'W1' and not request.get('source_directory'):
        raise ValueError('Explicit frozen W1 source directory required')
    return request, c


class StudyDispatch:
    """Use the full prespecified frame; cache IDs never replace posterior IDs."""
    def __init__(self, protocol, allocation, catalog):
        if protocol['scope_kind'] != 'formal_inference' or protocol['native_runtime_schema'] != SCHEMA:
            raise ValueError('A complete formal v2 protocol is required')
        design = create_study_plan(protocol['identity'], catalog)
        for key in ('groups', 'tasks', 'targets', 'controls', 'analysis_policy', 'cost_policy', 'execution_policy'):
            if protocol[key] != design[key]:
                raise ValueError('Formal protocol differs from full fixed scientific design: '+key)
        if (protocol['study_design_sha256'] != design['design_sha256'] or allocation != design['cache_allocation'] or
                protocol['cache_allocation_sha256'] != allocation['allocation_sha256']):
            raise ValueError('Formal task/measurement allocation identity differs')
        self.plan = BatchPlan(protocol)
        validate_measurement_plan(allocation, protocol['tasks'])
        self.protocol = copy.deepcopy(protocol)
        self._primary = {t['id']: t for t in protocol['tasks']}
        self._probes = copy.deepcopy(allocation['probes'])

    def _records(self, batch, phase):
        if (batch, phase) not in PHASES or type(batch) is not int:
            raise ValueError('One of four prespecified main/cache phases is required')
        return list(self.plan.tasks(batch)) if phase == 'main' else [p for p in self._probes if p['batch'] == batch]

    def tasks(self, batch, phase):
        """Small owned task identities, without materializing target capsules."""
        for record in self._records(batch,phase):
            primary = record if phase=='main' else self._primary[record['primary_task_id']]
            yield dict(primary, id=record['id'], protocol_sha256=self.plan.protocol_sha256,
                       artifact_kind='posterior' if phase=='main' else 'cache_measurement')

    def slots(self, batch, phase):
        records = self._records(batch,phase)
        for record in records:
            primary = record if phase == 'main' else self._primary[record['primary_task_id']]
            task = dict(primary, id=record['id'], protocol_sha256=self.plan.protocol_sha256,
                        artifact_kind='posterior' if phase == 'main' else 'cache_measurement')
            # Cache retains the original posterior capsule; only its owned job ID
            # differs. The probe explicitly binds that original primary_task_id.
            capsule, digest = self.plan.capsule(primary['id'])
            yield dict(task=task, capsule=capsule, capsule_sha256=digest,
                       probe=None if phase == 'main' else copy.deepcopy(record))

    def predecessors(self, batch, phase):
        if (batch, phase) not in PHASES or type(batch) is not int:
            raise ValueError('Unknown formal phase')
        return PHASES[:PHASES.index((batch, phase))]

    def request(self, slot, *, bundle, source_root, rscript, r_library, sealed_marker, native_acceptance):
        bundle, source_root = Path(bundle).resolve(), Path(source_root).resolve()
        c = slot['capsule']; task = slot['task']; phase = 'main' if task['artifact_kind'] == 'posterior' else 'cache'
        marker, acceptance = Path(sealed_marker).resolve(), Path(native_acceptance).resolve()
        source_files = {str(source_root/n): h for n, h in self.protocol['source_files'].items()}
        source_files.update({str(bundle/'external'/n): h for n, h in self.protocol['external_files'].items()})
        inputs = {str(bundle/'inputs'/c['task']['input']): c['input']['sha256'],
                  str(marker): file_hash(marker), str(acceptance): file_hash(acceptance)}
        request = dict(capsule=c, capsule_sha256=slot['capsule_sha256'], phase=phase,
                       inputs=str(bundle/'inputs'), source_directory=str(bundle/'external'),
                       rscript=str(Path(rscript).resolve()), r_library=str(Path(r_library).resolve()),
                       native_runtime_schema=SCHEMA, required_gpu_free_bytes=c['controls']['minimum_gpu_free_bytes'],
                       sealed_marker=str(marker), sealed_marker_sha256=inputs[str(marker)],
                       native_acceptance=str(acceptance), native_acceptance_sha256=inputs[str(acceptance)],
                       input_files=inputs, source_files=source_files)
        if slot['probe'] is not None:
            request['probe'] = slot['probe']
        return request

    def summarize_phase(self, batch, phase, rows):
        """Complete-frame bookkeeping after native inspection, not OS proof.

        Each row must come from the owned runtime and an exported checked task
        history. Failed and interrupted slots remain in the planned denominator.
        Missing/not-run rows prevent closing a phase, never become failures.
        """
        slots = {t['id']: t for t in self.tasks(batch, phase)}
        scheduled = {identifier:i+1 for i,identifier in enumerate(slots)}
        observed = {}; counts = {k: 0 for k in sorted(ENDED | {'not_run', 'active'})}
        for row in rows:
            task = row['task']; identifier = task['id']
            if identifier in observed or slots.get(identifier) != task:
                raise ValueError('Duplicate, foreign or altered phase task')
            if row.get('scheduled_index') != scheduled[identifier]:
                raise ValueError('Recorded task position differs from frozen schedule')
            outcome = row['outcome']
            if outcome not in counts:
                raise ValueError('Unknown phase outcome')
            if ((phase == 'cache' and (outcome == 'valid' or row['samples_eligible'])) or
                    (phase == 'main' and (outcome == 'measurement_available' or row['measurement_available'])) or
                    row['samples_eligible'] is not (outcome == 'valid') or
                    row['measurement_available'] is not (outcome == 'measurement_available')):
                raise ValueError('Outcome/phase/output eligibility conflicts')
            if outcome in ENDED:
                digest = row.get('history_export_sha256', '')
                if len(digest) != 64 or any(ch not in '0123456789abcdef' for ch in digest):
                    raise ValueError('Checked native history export required for ended slots')
            observed[identifier] = row; counts[outcome] += 1
        missing = len(slots) - len(observed)
        return dict(protocol_sha256=self.plan.protocol_sha256, batch=batch, phase=phase, planned=len(slots),
                    visited=len(observed), missing=missing, counts=counts,
                    closed=missing == 0 and counts['not_run'] == 0 and counts['active'] == 0,
                    outcome_frame_sha256=fingerprint(sorted(rows,key=lambda r:r['task']['id'])),
                    status_summary_is_process_proof=False,
                    closed_is_convergence=False, cache_replays_add_statistical_repetitions=False)
