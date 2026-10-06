"""New Windows lifecycle schema; no Mac process-group claims or sampler edits."""
import copy
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_runtime import atomic_json,file_hash,fingerprint,host_lease,HostBusy,ResourceWait,ResumeConflict,task_artifact_kind,validate_worker_eligibility
from job_objects import Job,observe_named_job,identity

SCHEMA='windows-owned-runtime-v1'
TERMINAL=('valid','measurement_available','numerical_failure','resource_failure','output_failure_unclassified')


def assets(directory):
    directory=Path(directory)
    return {p.relative_to(directory).as_posix():file_hash(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and p.name not in ('state.json','completion.json')}


def environment_identity():
    return dict(python=sys.version,executable=str(Path(sys.executable).resolve()),platform=sys.platform,
                packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions()})


def validate_files(request):
    for group in ('input_files','source_files'):
        for path,digest in request.get(group,{}).items():
            if not Path(path).is_file() or file_hash(path)!=digest:
                raise ResumeConflict('Bound '+group+' changed: '+path)


class Coordinator:
    def __init__(self,host_lock):
        if sys.platform!='win32':raise RuntimeError('Native Windows required')
        self.lock=Path(host_lock).resolve()
        self.registry=self.lock.with_suffix('.windows-registry.json')

    def _read(self):
        if not self.registry.exists():return dict(schema=SCHEMA,tasks={},events=[])
        data=json.loads(self.registry.read_text());digest=data.pop('sha256')
        if fingerprint(data)!=digest or data['schema']!=SCHEMA:raise ResumeConflict('Registry checksum/schema differs')
        previous=None
        for index,event in enumerate(data['events']):
            unsigned=dict(event);signed=unsigned.pop('sha256')
            if event['index']!=index or event['previous']!=previous or fingerprint(unsigned)!=signed:
                raise ResumeConflict('Registry event chain differs')
            previous=signed
        return data

    def _save(self,data,kind,key,details=None):
        e=dict(index=len(data['events']),previous=data['events'][-1]['sha256'] if data['events'] else None,
               kind=kind,task_key=key,details=copy.deepcopy(details),recorded_ns=time.time_ns())
        e['sha256']=fingerprint(e);data['events'].append(e)
        atomic_json(self.registry,dict(data,sha256=fingerprint(data)))

    def _verify_terminal(self,attempt):
        folder=Path(attempt['directory'])
        if not (folder/'state.json').exists() and attempt.get('recovery'):
            record=json.loads((folder.parent/'recovery'/attempt['recovery']).read_text())
            if record['original_assets']!=assets(folder):raise ResumeConflict('Reconciled assets changed')
            return dict(outcome=attempt['outcome'],samples_eligible=False,measurement_available=False,
                        status='failed',artifact_kind=record['artifact_kind'],invocation_seconds=None,recovery=record)
        state=json.loads((folder/'state.json').read_text())
        if file_hash(folder/'state.json')!=json.loads((folder/'completion.json').read_text())['state_sha256']:
            raise ResumeConflict('Terminal state checksum differs')
        if state['assets']!=assets(folder) or state['outcome']!=attempt['outcome']:
            raise ResumeConflict('Terminal assets/outcome differ')
        return state

    def _failed_evidence(self,folder):
        folder=Path(folder)
        for name in ('worker-result.json','candidate.json','ordinary-output.json'):
            path=folder/name
            if path.exists():
                value=json.loads(path.read_text())
                if value.get('status',value.get('candidate_status'))=='failed':
                    category=value.get('failure_category','numerical_failure')
                    return category if category in TERMINAL else 'output_failure_unclassified'
        for path in folder.rglob('cache-result.json'):
            value=json.loads(path.read_text())
            states=value.get('observation',{}).get('execution_outcomes',[])
            if 'numerical_failure' in states:return 'numerical_failure'
            if 'resource_failure' in states:return 'resource_failure'
        return None

    def _reconcile(self,data):
        for key,entry in data['tasks'].items():
            for attempt in entry['attempts']:
                if attempt['outcome']!='active':continue
                if entry['binding']['runtime_sha256']!=file_hash(__file__) or entry['binding']['job_api_sha256']!=file_hash(ROOT/'scripts/windows/job_objects.py'):
                    raise ResumeConflict('Resolve an active registration using its own frozen Windows runtime source')
                proof=observe_named_job(attempt['job_name'])
                if proof['state']!='absent' and proof['active_processes']:
                    raise HostBusy('Registered Windows job is still active: '+attempt['job_name'])
                folder=Path(attempt['directory'])
                failed=self._failed_evidence(folder)
                outcome=failed or 'infrastructure_interruption'
                # Reconciliation sidecar is outside original unsealed assets.
                recovery=Path(entry['output'])/'recovery'
                recovery.mkdir(exist_ok=True)
                record=dict(schema=SCHEMA,proof=proof,original_assets=assets(folder),outcome=outcome,
                            invocation_seconds=None,unknown_time_imputed=False,
                            failed_output_prevents_retry=bool(failed),artifact_kind=entry['task'].get('artifact_kind','posterior'),samples_eligible=False,measurement_available=False)
                destination=recovery/(attempt['id']+'.json')
                if destination.exists():raise ResumeConflict('Existing recovery sidecar not overwritten')
                atomic_json(destination,record)
                attempt.update(outcome=outcome,recovery=destination.name,
                               original_assets_sha256=fingerprint(record['original_assets']),exit_confirmed_by=proof)
                for call in entry['calls']:
                    if call['attempt_id']==attempt['id'] and call['seconds'] is None:
                        call['outcome']=outcome
                self._save(data,'reconciled',key,record)

    def run(self,*,task,request,worker,output,limits,resume=False,retry=False):
        kind=task_artifact_kind(task) # Unknown kind rejected before registration.
        validate_files(request)
        if set(limits)!={'rss_bytes','job_commit_bytes','disk_start_bytes','disk_floor_bytes','poll_seconds'}:
            raise ValueError('Explicit Windows resource policy required')
        for name in ('rss_bytes','job_commit_bytes','disk_start_bytes','disk_floor_bytes'):
            if type(limits[name]) is not int or limits[name]<1:raise ValueError('Positive byte guards required')
        if not 0<limits['poll_seconds']<=1:raise ValueError('Bounded observation interval required, no total timeout')
        worker=Path(worker).resolve();output=Path(output).resolve()
        binding=dict(schema=SCHEMA,task=task,request=request,worker_sha256=file_hash(worker),
            runtime_sha256=file_hash(__file__),job_api_sha256=file_hash(ROOT/'scripts/windows/job_objects.py'),
            environment=environment_identity(),limits=limits,output=str(output),host_lock=str(self.lock))
        key=fingerprint(dict(protocol=task['protocol_sha256'],id=task['id']))
        start=time.perf_counter()
        with host_lease(self.lock,output):
            data=self._read();self._reconcile(data)
            entry=data['tasks'].get(key)
            if entry:
                if entry['binding']!=binding:raise ResumeConflict('Task/config/source/environment/input/limits/destination changed')
                last=entry['attempts'][-1] if entry['attempts'] else None
                if last and last['outcome'] in TERMINAL:
                    if retry:raise ResumeConflict('Existing terminal failure or success cannot be retried')
                    if not resume:raise FileExistsError('Explicit terminal resume required')
                    state=self._verify_terminal(last)
                    value=dict(state,newly_executed=False,attempt_id=last['id'])
                    entry['calls'].append(dict(seconds=time.perf_counter()-start,attempt_id=last['id'],
                                              newly_executed=False,outcome=last['outcome']))
                    self._save(data,'verification_only',key)
                    return value
                if last:
                    if not retry or kind=='cache_measurement' or last['outcome']!='infrastructure_interruption' or len(entry['attempts'])>=2:
                        raise ResumeConflict('At most one explicit posterior infrastructure retry; cache interruption never retried')
                    proof=observe_named_job(last['job_name'])
                    if proof['state']!='absent' and proof['active_processes']:raise HostBusy('Old cohort not ended')
                    if last.get('recovery'):
                        sidecar=json.loads((output/'recovery'/last['recovery']).read_text())
                        if assets(Path(last['directory']))!=sidecar['original_assets']:
                            raise ResumeConflict('Interrupted original assets changed')
                    else:self._verify_terminal(last)
                elif not resume:raise ResumeConflict('Resource-wait identity already registered; explicit resume required')
            else:
                if resume or retry:raise ResumeConflict('Cannot resume an unregistered task')
                if output.exists():raise FileExistsError('Never overwrite an output directory')
                entry=dict(binding=binding,output=str(output),attempts=[],calls=[],task=task)
                data['tasks'][key]=entry
                self._save(data,'registered',key)
            output.parent.mkdir(parents=True,exist_ok=True)
            free=shutil.disk_usage(output.parent).free
            if free<limits['disk_start_bytes']:
                entry['calls'].append(dict(seconds=time.perf_counter()-start,attempt_id=None,
                    newly_executed=False,outcome='not_run',reason='disk_start_refused',free_bytes=free))
                self._save(data,'resource_wait',key)
                raise ResourceWait('Disk budget refused before child creation')
            output.mkdir(exist_ok=True)
            number=len(entry['attempts'])+1
            folder=output/('attempt-%04d'%number);folder.mkdir(exist_ok=False)
            attempt=dict(id='attempt-%04d'%number,directory=str(folder),outcome='active',
                         job_name='Local\\ParallelBayes-'+uuid.uuid4().hex)
            entry['attempts'].append(attempt)
            call=dict(seconds=None,attempt_id=attempt['id'],newly_executed=True,outcome='active')
            entry['calls'].append(call)
            self._save(data,'launch_intent',key,attempt)
            atomic_json(folder/'binding.json',binding);atomic_json(folder/'request.json',request)
            reserve=folder/'failure-reserve.bin'
            with reserve.open('wb') as stream:
                stream.write(bytes(1024**2));stream.flush();os.fsync(stream.fileno())
            atomic_json(folder/'job.json',dict(name=attempt['job_name'],launch='PROC_THREAD_ATTRIBUTE_JOB_LIST + CREATE_SUSPENDED',
                kill_on_last_close=True,job_handle_inherited=False,breakaway_permitted=False,
                manager=identity(os.getpid()),limits=limits))
            peak=0;observations=0;outcome='infrastructure_interruption';error=None;worker_result=None
            with Job(attempt['job_name'],limits['job_commit_bytes']) as job:
                stage='launch'
                try:
                    with (folder/'stdout.log').open('wb') as stdout,(folder/'stderr.log').open('wb') as stderr, (folder/'ownership.ndjson').open('w',encoding='utf-8') as journal:
                        child_env=dict(os.environ,PB_OWNED_JOB=attempt['job_name'])
                        primary=job.launch_suspended([sys.executable,str(worker),str(folder/'request.json'),str(folder)],ROOT,stdout,stderr,child_env)
                        atomic_json(folder/'primary.json',primary)
                        job.resume()
                        stage='observation'
                        while True:
                            observed=job.observe();observations+=1;peak=max(peak,observed['sampled_rss_bytes'])
                            observed.update(observed_ns=time.time_ns(),disk_free_bytes=shutil.disk_usage(folder).free)
                            journal.write(json.dumps(observed)+'\n');journal.flush()
                            if observed['active_processes']==0:break
                            if peak>limits['rss_bytes'] or observed['disk_free_bytes']<limits['disk_floor_bytes']:
                                with reserve.open('r+b') as reserve_stream:reserve_stream.truncate(0)
                                outcome='resource_failure';error='sampled_job_RSS_or_disk_guard';job.terminate()
                            time.sleep(limits['poll_seconds'])
                    return_code=job.poll()
                    stage='classification'
                    if outcome!='resource_failure':
                        result_path=folder/'worker-result.json'
                        if result_path.exists():
                            worker_result=json.loads(result_path.read_text())
                            try:
                                validate_worker_eligibility(task,worker_result)
                                outcome=('measurement_available' if kind=='cache_measurement' else 'valid') if worker_result['status']=='completed' and return_code==0 else worker_result.get('failure_category','output_failure_unclassified')
                                if outcome not in TERMINAL:outcome='output_failure_unclassified'
                            except ValueError as exc:outcome='output_failure_unclassified';error=str(exc)
                        else:
                            outcome=self._failed_evidence(folder) or ('output_failure_unclassified' if (folder/'candidate.json').exists() or list(folder.rglob('execution-*.npz')) else 'infrastructure_interruption')
                            error='Worker did not write an eligible terminal result; exit '+str(return_code)
                    final=job.observe()
                except BaseException as exc:
                    with reserve.open('r+b') as reserve_stream:reserve_stream.truncate(0)
                    error=type(exc).__name__+': '+str(exc)
                    outcome=self._failed_evidence(folder) or ('resource_failure' if stage=='observation' else 'infrastructure_interruption' if stage=='launch' else 'output_failure_unclassified')
                    job.terminate()
                    while job.observe()['active_processes']:time.sleep(limits['poll_seconds'])
                    final=job.observe();return_code=job.poll() if job.process else None
            attempt.update(outcome=outcome)
            state=dict(schema=SCHEMA,task=task,outcome=outcome,status='completed' if outcome in ('valid','measurement_available') else 'failed' if outcome in TERMINAL else 'interrupted',
                artifact_kind=kind,samples_eligible=outcome=='valid',measurement_available=outcome=='measurement_available',
                worker_result=worker_result,error=error,exit_code=return_code,job_final=final,
                observed_rss_peak_bytes=peak,ownership_observations=observations,
                invocation_seconds=time.perf_counter()-start,unknown_time_imputed=False,
                assets=assets(folder),binding_sha256=fingerprint(binding))
            atomic_json(folder/'state.json',state)
            atomic_json(folder/'completion.json',dict(state_sha256=file_hash(folder/'state.json')))
            call.update(seconds=time.perf_counter()-start,outcome=outcome)
            self._save(data,'sealed',key,dict(outcome=outcome,job_ended=final['active_processes']==0))
            return dict(state,newly_executed=True,attempt_id=attempt['id'])

    def snapshot(self,destination):
        with host_lease(self.lock,'quiescent registry snapshot'):
            data=self._read();self._reconcile(data)
            for entry in data['tasks'].values():
                for attempt in entry['attempts']:
                    if attempt['outcome'] in TERMINAL:self._verify_terminal(attempt)
            if Path(destination).exists():raise FileExistsError('No snapshot overwrite')
            atomic_json(destination,dict(data,sha256=fingerprint(data),snapshot_is_live_registry=False))
            return len(data['tasks'])
