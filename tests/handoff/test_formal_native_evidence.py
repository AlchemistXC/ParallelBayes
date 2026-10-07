"""Artificial retained-file fixtures, not execution of a Windows Job or MCMC."""
import copy
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/completion'))
from formal_runtime import atomic_json, file_hash, fingerprint
from formal_native_evidence import read_native_task
from task_journal import TaskJournal


class Fixture:
    def __init__(self, base, kind='posterior'):
        self.root = base / 'received'; self.root.mkdir()
        self.base = base
        self.sources = {n: fingerprint(n) for n in (
            'scripts/windows/formal_batch_worker.py', 'scripts/windows/formal_cache_worker.py',
            'scripts/windows/formal_owned_runtime.py', 'scripts/completion/task_journal.py',
            'scripts/windows/job_objects.py', 'scripts/windows/formal_measured_runtime.py',
            'scripts/windows/run_owned_command.py')}
        self.task = dict(id='artificial-native-reader', protocol_sha256='a'*64, batch=0,
                         artifact_kind=kind, model='G1', replicate=0)
        self.identity = dict(schema='windows-owned-runtime-v2', platform='win32', host_lock=r'D:\fixture\host.lock')
        self.binding = dict(schema=self.identity['schema'], task=self.task, request={'fixture_only': True},
            environment={'platform': 'win32'}, output=r'D:\fixture\task', host_lock=self.identity['host_lock'],
            worker_sha256=self.sources['scripts/windows/formal_batch_worker.py' if kind == 'posterior' else 'scripts/windows/formal_cache_worker.py'],
            runtime_sha256=self.sources['scripts/windows/formal_owned_runtime.py'],
            journal_sha256=self.sources['scripts/completion/task_journal.py'],
            job_api_sha256=self.sources['scripts/windows/job_objects.py'])
        self.entry = dict(binding=self.binding, task=self.task, output=self.binding['output'], attempts=[], calls=[])

    def add(self, outcome='valid', *, recovery=False, saved_failure=None):
        identifier = 'attempt-%04d' % (len(self.entry['attempts'])+1)
        p = self.root / 'task' / identifier; p.mkdir(parents=True)
        attempt = dict(id=identifier, directory=self.binding['output']+'\\'+identifier,
                       outcome=outcome, job_name='Local\\ParallelBayes-fixture-'+identifier)
        atomic_json(p/'binding.json', self.binding); atomic_json(p/'request.json', self.binding['request'])
        atomic_json(p/'job.json', {'name': attempt['job_name']})
        success = outcome in ('valid', 'measurement_available')
        result = dict(status='completed' if success else 'failed', artifact_kind=self.task['artifact_kind'],
                      samples_eligible=outcome=='valid', measurement_available=outcome=='measurement_available')
        if success or saved_failure:
            if saved_failure: result['failure_category'] = saved_failure
            atomic_json(p/'worker-result.json', result)
        if not recovery: atomic_json(p/'ordinary-process.json', {'ordinary_process_wall_seconds': 1.5})
        assets = {x.name: file_hash(x) for x in p.iterdir()}
        if recovery:
            proof = dict(state='absent', job_name=attempt['job_name'], proof='Artificial reader fixture, no Windows observation')
            record = dict(schema=self.identity['schema'], proof=proof, original_assets=assets,
                outcome=outcome, invocation_seconds=None, unknown_time_imputed=False,
                failed_output_prevents_retry=bool(saved_failure), artifact_kind=self.task['artifact_kind'],
                samples_eligible=False, measurement_available=False)
            (self.root/'task/recovery').mkdir(exist_ok=True)
            atomic_json(self.root/'task/recovery'/(identifier+'.json'), record)
            attempt.update(recovery=identifier+'.json', original_assets_sha256=fingerprint(assets), exit_confirmed_by=proof)
        else:
            state = dict(schema=self.identity['schema'], task=self.task, outcome=outcome,
                status='completed' if success else 'interrupted' if outcome=='infrastructure_interruption' else 'failed',
                artifact_kind=self.task['artifact_kind'], samples_eligible=outcome=='valid',
                measurement_available=outcome=='measurement_available', worker_result=result if success else None,
                job_final={'job_name': attempt['job_name'], 'active_processes': 0},
                invocation_seconds=2., unknown_time_imputed=False, exit_code=0 if success else 1,
                assets=assets, binding_sha256=fingerprint(self.binding))
            atomic_json(p/'state.json', state)
            atomic_json(p/'completion.json', {'state_sha256': file_hash(p/'state.json')})
        self.entry['attempts'].append(attempt)
        return p

    def export(self):
        # A fresh artificial journal avoids mutating a previously closed record.
        number = len(list(self.base.glob('journal-*')))
        destination = self.root / ('history-%d.json' % number)
        with TaskJournal(self.base / ('journal-%d' % number), self.identity) as journal:
            key = TaskJournal.key(self.task)
            journal.save(key, self.entry, 'artificial-fixture')
            journal.export(key, destination)
        self.history = destination.name

    def ledger(self, calls):
        identity = dict(schema=1, original=self.entry['output'], task=self.task,
            host_lock=self.identity['host_lock'], native_schema=self.identity['schema'],
            recorder_source_sha256=self.sources['scripts/windows/formal_measured_runtime.py'])
        (self.root/'ledger').mkdir()
        atomic_json(self.root/'ledger/identity.json', identity)
        for i, values in enumerate(calls):
            p = self.root/'ledger'/('call-%06d' % i)
            p.mkdir()
            atomic_json(p/'started.json', dict(index=i, action='run' if i==0 else 'retry', identity_sha256=fingerprint(identity)))
            if values is not None:
                duration, attempt, newly = values
                end = dict(seconds=duration, started_sha256=file_hash(p/'started.json'), error=None,
                    result=dict(task=self.task, outcome=self.entry['attempts'][int(attempt[-4:])-1]['outcome'],
                                attempt_id=attempt, newly_executed=newly))
                atomic_json(p/'finished.json', dict(end, receipt_sha256=fingerprint(end)))

    def manifest(self):
        return {p.relative_to(self.root).as_posix(): file_hash(p) for p in self.root.rglob('*') if p.is_file()}

    def read(self, *, manifest=None, ledger=None):
        return read_native_task(self.root, task=self.task, history_export=self.history, directory='task',
            manifest=self.manifest() if manifest is None else manifest, source_files=self.sources, ledger=ledger)


def reseal_state(p, update):
    state = json.loads((p/'state.json').read_text()); update(state)
    atomic_json(p/'state.json', state)
    atomic_json(p/'completion.json', {'state_sha256': file_hash(p/'state.json')})


def test_relocated_success_and_three_nonadditive_cost_scopes(tmp_path):
    f = Fixture(tmp_path); f.add(); f.export()
    f.ledger([(3., 'attempt-0001', True), (.25, 'attempt-0001', False)])
    manifest = f.manifest(); moved = tmp_path/'copied'
    shutil.copytree(f.root, moved); shutil.rmtree(f.root); f.root = moved
    h = f.read(manifest=manifest, ledger='ledger')
    assert h['summary']['outcome']=='valid'
    assert h['eligible_directory']==str(moved/'task/attempt-0001') and h['measurement_directory'] is None
    phases = h['costs']['phases']
    assert phases['ordinary_workflow']['complete_seconds']==1.5
    assert phases['research_execution']['complete_seconds']==3.
    assert phases['additional_verification']['complete_seconds']==.25
    assert phases['all_invocations']['complete_seconds']==3.25
    assert h['live_processes_observed_by_reader'] is False and h['numerical_audit_reexecuted'] is False
    assert f.manifest()==manifest


@pytest.mark.parametrize('outcome', ['numerical_failure', 'resource_failure', 'output_failure_unclassified', 'infrastructure_interruption'])
def test_every_ended_failure_keeps_known_cost_and_no_samples(tmp_path, outcome):
    f = Fixture(tmp_path); f.add(outcome); f.export(); h = f.read()
    assert h['summary']['outcome']==outcome and h['summary']['known_seconds']==2.
    assert h['eligible_directory'] is h['measurement_directory'] is None


def test_cache_output_is_measurement_only_and_cannot_retry(tmp_path):
    f = Fixture(tmp_path, 'cache_measurement'); p = f.add('measurement_available'); f.export()
    h = f.read(); assert h['eligible_directory'] is None and h['measurement_directory']==str(p)
    f.add('measurement_available'); f.export()
    with pytest.raises(ValueError, match='retry allowance'): f.read()


def test_reconciled_interruption_retry_preserves_unknown_time(tmp_path):
    f = Fixture(tmp_path); f.add('infrastructure_interruption', recovery=True); f.add(); f.export()
    f.ledger([None, (4., 'attempt-0002', True)])
    h = f.read(ledger='ledger')
    assert h['summary']['outcome']=='valid' and h['summary']['total_seconds'] is None
    assert h['summary']['known_seconds']==2. and h['summary']['unknown_cost_attempts']==1
    p = h['costs']['phases']
    assert p['ordinary_workflow']['complete_seconds'] is None
    assert p['research_execution']['complete_seconds'] is None and p['research_execution']['known_seconds']==4.


def test_saved_numeric_failure_cannot_be_relabelled_or_retried(tmp_path):
    f = Fixture(tmp_path); f.add('numerical_failure', recovery=True, saved_failure='numerical_failure'); f.export()
    assert f.read()['summary']['outcome']=='numerical_failure'
    f.add(); f.export()
    with pytest.raises(ValueError, match='Only infrastructure'): f.read()


def test_registered_prelaunch_is_not_run_but_missing_export_is_an_error(tmp_path):
    f = Fixture(tmp_path); f.export(); h = f.read()
    assert h['summary']['outcome']=='not_run' and h['summary']['total_seconds'] is None
    manifest = f.manifest(); (f.root/f.history).unlink()
    with pytest.raises(ValueError, match='Missing'): f.read(manifest=manifest)


def test_active_history_cannot_be_promoted_to_ended_by_a_status_summary(tmp_path):
    f = Fixture(tmp_path); f.add(); f.entry['attempts'][0]['outcome']='active'; f.export()
    with pytest.raises(ValueError, match='reconciliation'): f.read()


@pytest.mark.parametrize('change', ['source', 'job', 'eligibility', 'binding', 'lineage'])
def test_consistently_rehashed_but_incompatible_metadata_is_rejected(tmp_path, change):
    f = Fixture(tmp_path); p = f.add()
    if change=='source': f.binding['worker_sha256']='f'*64
    elif change=='job': reseal_state(p, lambda s: s['job_final'].update(job_name='unrelated'))
    elif change=='eligibility': reseal_state(p, lambda s: s.update(measurement_available=True))
    elif change=='binding': reseal_state(p, lambda s: s.update(binding_sha256='f'*64))
    else: f.entry['attempts'][0]['directory']=r'C:\unrelated\attempt-0001'
    f.export()
    with pytest.raises(ValueError): f.read()


def test_missing_and_unlisted_files_and_escape_paths_are_rejected(tmp_path):
    f = Fixture(tmp_path); p = f.add(); f.export(); manifest=f.manifest()
    (p/'extra.txt').write_text('unlisted')
    with pytest.raises(ValueError, match='Missing, unbound'): f.read(manifest=manifest)
    (p/'extra.txt').unlink(); (p/'ordinary-process.json').unlink()
    with pytest.raises(ValueError, match='inventory'): f.read(manifest=manifest)
    with pytest.raises(ValueError):
        read_native_task(f.root, task=f.task, history_export='../outside', directory='task',
                         manifest=manifest, source_files=f.sources)


def test_recovery_unknown_observation_and_imputed_seconds_rejected(tmp_path):
    f=Fixture(tmp_path); f.add('infrastructure_interruption', recovery=True); f.export()
    p=f.root/'task/recovery/attempt-0001.json'; record=json.loads(p.read_text())
    record['invocation_seconds']=0.; atomic_json(p,record)
    with pytest.raises(ValueError, match='imputes'): f.read()
    record['invocation_seconds']=None; record['proof']['state']='unknown'; atomic_json(p,record)
    f.entry['attempts'][0]['exit_confirmed_by']=record['proof']; f.export()
    with pytest.raises(ValueError, match='Unknown Job'): f.read()


def test_complete_artificial_gate_uses_the_shared_reader_and_rejects_wrong_job(tmp_path):
    """Exercise 27/24 metadata paths. These files claim no actual Windows run."""
    import xml.etree.ElementTree as ET
    from batch_contract import BatchPlan, create_tasks
    from formal_acceptance import RUNTIME_CASES, validation_groups, verify_native_acceptance
    from formal_execution import VALIDATION_ID
    from formal_measurement_plan import create_measurement_plan

    bundle=tmp_path/'gate-fixture'; bundle.mkdir()
    catalog=json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    origin=tmp_path/'source-fixture'; origin.mkdir(); template=Fixture(origin)
    tasks=create_tasks(VALIDATION_ID,validation_groups())
    targets=[t for t in catalog['targets'] if t['name'] in ('G1','G2','W1')]
    controls=dict(chains=4,mh_discard=512,nuts_warmup=1024,nuts_tree_depth=8,nuts_workers=4,nuts_threads=1,
        torch_threads=4,window=32,quasi_deer_max_iter=2048,memory_limit_mb=2048,maximum_member_bytes=128*1024**2,
        atol=1e-10,rtol=1e-10,nuts_target_accept=.8,nuts_full_mass=False)
    env=dict(fixture_only=True,not_a_native_execution_record=True,executable=r'D:\fixture\python.exe')
    p=dict(schema=1,identity=VALIDATION_ID,scope_kind='technical_batch_validation',required_platform='win32',
        native_runtime_schema='windows-owned-runtime-v2',validation_environment=env,source_commit='b'*40,
        source_files=template.sources,required_versions={'numpy':'artificial'},required_R_version='fixture',
        required_R_posterior='fixture',controls=controls,cost_policy='fixture',groups=validation_groups(),
        batch_size=32,tasks=tasks,targets=targets,process_tree_rss_limit_bytes=1024,required_disk_bytes_per_task=1024,
        inputs={t['name']+'-rep0000.npz':dict(model=t['name'],replicate=0,chains=4,dimension=t['dimension'],
            steps=16896,sha256='a'*64,actual_sha256='b'*64) for t in targets})
    p['protocol_sha256']=fingerprint(p); plan=BatchPlan(p)
    allocation=create_measurement_plan(VALIDATION_ID,tasks)
    primary={t['id']:t for t in tasks}
    report=dict(schema='formal-native-adapter-integration-v1',protocol_sha256=p['protocol_sha256'],
                formal_scientific_repetitions=0,main=[],cache=[])
    mutated=None
    for phase,frame in [('main',tasks),('cache',allocation['probes'])]:
        for item in frame:
            parent=tmp_path/('fixture-'+item['id']); parent.mkdir()
            f=Fixture(parent,'posterior' if phase=='main' else 'cache_measurement')
            primary_id=item['id'] if phase=='main' else item['primary_task_id']
            f.task.update(primary[primary_id],id=item['id'],protocol_sha256=p['protocol_sha256'])
            capsule,digest=plan.capsule(primary_id)
            f.binding['request']=dict(capsule=capsule,capsule_sha256=digest)
            f.add('valid' if phase=='main' else 'measurement_available'); f.export()
            f.ledger([(3.,'attempt-0001',True),(.25,'attempt-0001',False)])
            relative=phase+'/'+item['id']
            shutil.copytree(f.root,bundle/relative)
            report[phase].append(dict(task_id=item['id'],history_export=relative+'/'+f.history,
                attempt_directory=relative+'/task/attempt-0001',ledger=relative+'/ledger'))
            if mutated is None: mutated=bundle/relative/'task/attempt-0001'
    suite=ET.Element('testsuite')
    for name,count in RUNTIME_CASES.items():
        for index in range(count): ET.SubElement(suite,'testcase',name=name+'['+str(index)+']')
    ET.ElementTree(suite).write(bundle/'runtime.xml')
    owned=bundle/'runtime-command';owned.mkdir()
    atomic_json(owned/'started.json',dict(command=[env['executable'],'-m','pytest','-q','-p','no:cacheprovider',
        'tests/windows/test_formal_owned_runtime.py','--basetemp=artificial','--junitxml=artificial'],
        source_sha256=template.sources['scripts/windows/run_owned_command.py'],
        job_api_sha256=template.sources['scripts/windows/job_objects.py']))
    atomic_json(owned/'job-intent.json',dict(name='artificial-native-test-job'))
    atomic_json(owned/'finished.json',dict(source_sha256=template.sources['scripts/windows/run_owned_command.py'],
        exit_code=0,error=None,job_final=dict(job_name='artificial-native-test-job',active_processes=0),logs={}))
    atomic_json(bundle/'protocol.json',p); atomic_json(bundle/'integration.json',report)
    gate={k:p[k] for k in ('source_files','required_versions','required_R_version','required_R_posterior')}
    gate.update(schema='formal-native-acceptance-v1',platform='win32',passed=True,environment=env,
        runtime_test_sha256=file_hash(ROOT/'tests/windows/test_formal_owned_runtime.py'),
        runtime_xml='runtime.xml',validation_protocol='protocol.json',integration_report='integration.json',
        runtime_command='runtime-command',
        fixture_only=True,not_a_native_execution_record=True)
    def write_gate():
        gate.pop('gate_sha256',None)
        gate['files']={x.relative_to(bundle).as_posix():file_hash(x) for x in bundle.rglob('*')
                       if x.is_file() and x.name!='gate.json'}
        gate['gate_sha256']=fingerprint(gate); atomic_json(bundle/'gate.json',gate)
    write_gate()
    assert verify_native_acceptance(bundle/'gate.json',p,ROOT,environment=env)==gate
    terminal=json.loads((owned/'finished.json').read_text());terminal['exit_code']=1
    atomic_json(owned/'finished.json',terminal);write_gate()
    with pytest.raises(ValueError,match='Actual native runtime command'):
        verify_native_acceptance(bundle/'gate.json',p,ROOT,environment=env)
    terminal['exit_code']=0;atomic_json(owned/'finished.json',terminal)
    # A successful sampling record alone does not establish a real verification
    # invocation. Missing its outer receipt keeps that requirement unproven.
    verification=bundle/report['main'][0]['ledger']/'call-000001/finished.json'
    saved=verification.read_bytes();verification.unlink();write_gate()
    with pytest.raises(ValueError,match='declared attempt'):
        verify_native_acceptance(bundle/'gate.json',p,ROOT,environment=env)
    verification.write_bytes(saved)
    reseal_state(mutated,lambda s:s['job_final'].update(job_name='unrelated'))
    write_gate()
    with pytest.raises(ValueError,match='Job identity'):
        verify_native_acceptance(bundle/'gate.json',p,ROOT,environment=env)
