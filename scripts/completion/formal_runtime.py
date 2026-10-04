"""Native host/task lifecycle helpers; never modify frozen samplers."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time


class HostBusy(RuntimeError):
    pass


class ResumeConflict(RuntimeError):
    pass


class ResourceWait(RuntimeError):
    pass


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def atomic_json(path,value):
    path=Path(path)
    temporary=path.with_name(path.name+'.'+str(os.getpid())+'.tmp')
    with temporary.open('w',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)


class PhaseLedger:
    """Nonoverlapping worker phases, with explicit synchronization boundaries."""
    def __init__(self,path,synchronise=None):
        self.path=Path(path);self.synchronise=synchronise
        self.started=time.perf_counter();self.phases=[];self.active=None

    @contextmanager
    def phase(self,name):
        if self.active is not None:raise RuntimeError('Phase overlap is forbidden')
        if not isinstance(name,str) or not name:raise ValueError('Named phase required')
        self.active=name;start=time.perf_counter();cpu=time.process_time()
        status='completed';error=None
        try:
            if self.synchronise is not None:self.synchronise()
            yield
            if self.synchronise is not None:self.synchronise()
        except BaseException as exc:
            status='failed';error=type(exc).__name__+': '+str(exc)
            raise
        finally:
            end=time.perf_counter()
            self.phases.append(dict(name=name,status=status,error=error,
                start_offset_seconds=start-self.started,end_offset_seconds=end-self.started,
                wall_seconds=end-start,process_cpu_seconds=time.process_time()-cpu,
                synchronization_included=self.synchronise is not None))
            self.active=None
            atomic_json(self.path,dict(phases=self.phases,
                scope='Disjoint worker phases; journal writes and gaps are outside phase sums. Nested sampler timings must not be added to these inclusive phases.'))


@contextmanager
def host_lease(path,owner):
    """All cooperating runs on this host/user use the same absolute path.

    Kernel locking is authoritative. Persisted owner metadata is never used
    to infer process liveness; unrelated programs are not excluded by a lease.
    """
    path=Path(path).resolve();path.parent.mkdir(parents=True,exist_ok=True)
    stream=os.fdopen(os.open(path,os.O_RDWR|os.O_CREAT,0o600),'r+b')
    acquired=False
    try:
        if stream.seek(0,2)==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        try:
            if sys.platform=='win32':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            acquired=True
        except OSError as exc:raise HostBusy('Another cooperating process holds the shared host lease') from exc
        atomic_json(path.with_suffix(path.suffix+'.owner.json'),dict(pid=os.getpid(),owner=str(owner),
            host=platform.node(),state='held',recorded_ns=time.time_ns(),metadata_is_liveness_proof=False))
        yield
    finally:
        if acquired:
            try:
                atomic_json(path.with_suffix(path.suffix+'.owner.json'),dict(pid=os.getpid(),owner=str(owner),state='released',recorded_ns=time.time_ns()))
            finally:
                stream.seek(0)
                if sys.platform=='win32':
                    import msvcrt
                    msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        stream.close()


def disk_preflight(directory,required_bytes):
    if isinstance(required_bytes,bool) or not isinstance(required_bytes,int) or required_bytes<0:
        raise ValueError('Nonnegative required disk bytes required')
    usage=shutil.disk_usage(directory)
    if usage.free<required_bytes:
        raise ResourceWait(f'Disk free {usage.free} is below required {required_bytes}; no task launched')
    return dict(free_bytes=usage.free,required_bytes=required_bytes,total_bytes=usage.total,
        scope='Observed free bytes at task boundary; not a promise about other processes or later writes')


def _stop_tree(process,observed):
    import psutil
    try:
        parent=psutil.Process(process.pid)
        for child in parent.children(recursive=True):observed[child.pid]=child
        observed[parent.pid]=parent
    except (psutil.Error,OSError):pass
    victims=[]
    for child in reversed(list(observed.values())):
        try:
            if child.is_running():child.terminate();victims.append(child)
        except (psutil.Error,OSError):pass
    _,alive=psutil.wait_procs(victims,timeout=2)
    for child in alive:
        try:child.kill()
        except (psutil.Error,OSError):pass
    psutil.wait_procs(alive,timeout=2)
    if process.poll() is None:
        if sys.platform!='win32':
            # This Popen created a fresh session, so only its owned group is
            # targeted if process-tree inspection itself became unavailable.
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        else:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
        process.kill()
    process.wait()


def _resume(output,binding):
    statefile=output/'state.json';receiptfile=output/'completion.json'
    if not statefile.exists() or not receiptfile.exists():
        # Never infer death from a stale JSON or start a second task after a
        # timeout. Incomplete attempts need explicit classification/recovery.
        raise ResumeConflict('Incomplete attempt; inspect its actual process before a separately recorded recovery')
    state=json.loads(statefile.read_text());receipt=json.loads(receiptfile.read_text())
    if state['binding_sha256']!=binding or receipt['state_sha256']!=file_hash(statefile):
        raise ResumeConflict('Terminal identity or state checksum differs')
    if state['status'] not in ('completed','failed'):
        raise ResumeConflict('Interrupted attempt requires explicit classification; no automatic rerun')
    for name,h in state['assets'].items():
        path=output/name
        if not path.resolve().is_relative_to(output.resolve()) or not path.is_file() or file_hash(path)!=h:
            raise ResumeConflict('Terminal asset checksum differs: '+name)
    return dict(state,completion=receipt,resumed=True,newly_executed=False)


def execute_task(task,request,worker,output,host_lock,required_disk_bytes,max_tree_rss_bytes,resume=False):
    """Run one isolated worker and seal both success and numerical failure.

    Worker argv is [request.json, attempt_directory]. It must write
    worker-result.json with status and samples_eligible. This generic layer
    verifies lifecycle evidence; the worker must verify scientific identities.
    """
    invocation_started=time.perf_counter()
    import psutil
    worker=Path(worker).resolve();output=Path(output).resolve()
    if isinstance(max_tree_rss_bytes,bool) or not isinstance(max_tree_rss_bytes,int) or max_tree_rss_bytes<=0:
        raise ValueError('Positive process-tree RSS guard required')
    binding_fields=dict(task=task,request=request,worker_sha256=file_hash(worker),
        runtime_helper_sha256=file_hash(Path(__file__)),python=sys.version,executable=str(Path(sys.executable).resolve()),
        platform=sys.platform,host_lock=str(Path(host_lock).resolve()),psutil=psutil.__version__,
        required_disk_bytes=required_disk_bytes,max_tree_rss_bytes=max_tree_rss_bytes)
    binding=fingerprint(binding_fields)
    with host_lease(host_lock,output):
        if output.exists():
            if not resume:raise FileExistsError('Use explicit resume; never overwrite an attempt')
            return _resume(output,binding)
        output.parent.mkdir(parents=True,exist_ok=True)
        disk=disk_preflight(output.parent,required_disk_bytes+1024*1024)
        # Fail before starting a sampler when the required resource observer
        # cannot inspect this process tree (e.g. restricted desktop sandbox).
        psutil.Process().children(recursive=True)
        psutil.Process().memory_info()
        output.mkdir();attempt=output/'attempt-0001';attempt.mkdir()
        atomic_json(output/'binding.json',binding_fields)
        reserve=output/'failure-reserve.bin'
        with reserve.open('wb') as f:f.write(bytes(1024*1024));f.flush();os.fsync(f.fileno())
        atomic_json(attempt/'request.json',request)
        began=time.perf_counter();cpu_start=time.process_time()
        observed={};process=None;peak=0;samples=0;child_cpu={}
        status='interrupted';failure_kind=None;result=None;error=None
        try:
            with (attempt/'stdout.log').open('wb') as stdout,(attempt/'stderr.log').open('wb') as stderr:
                process=subprocess.Popen([sys.executable,str(worker),str(attempt/'request.json'),str(attempt)],
                    stdout=stdout,stderr=stderr,start_new_session=sys.platform!='win32',
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform=='win32' else 0)
                atomic_json(attempt/'process.json',dict(pid=process.pid,command_role='owned_task_worker',
                    worker=str(worker),request=str(attempt/'request.json'),started_ns=time.time_ns(),
                    note='PID metadata alone is not a liveness check'))
                while process.poll() is None:
                    rss=0
                    try:
                        parent=psutil.Process(process.pid)
                        family=[parent,*parent.children(recursive=True)]
                        for child in family:
                            try:
                                observed[child.pid]=child;rss+=child.memory_info().rss
                                cpu=child.cpu_times();child_cpu[str(child.pid)]=dict(user=cpu.user,system=cpu.system)
                            except psutil.NoSuchProcess:pass
                        samples+=1;peak=max(peak,rss)
                    except psutil.NoSuchProcess:pass
                    if rss>max_tree_rss_bytes:
                        failure_kind='process_tree_memory_guard';status='failed'
                        _stop_tree(process,observed);break
                    time.sleep(.05)
                code=process.wait()
            if failure_kind is None:
                if code!=0:
                    failure_kind='worker_process_exit';error=f'worker exit code {code}'
                else:
                    result=json.loads((attempt/'worker-result.json').read_text())
                    if result.get('status') not in ('completed','failed') or result.get('samples_eligible')!=(result['status']=='completed'):
                        raise ValueError('Worker result has inconsistent numerical output eligibility')
                    status=result['status']
                    if status=='failed':failure_kind='worker_output_standard'
        except BaseException as exc:
            status='interrupted';failure_kind='infrastructure_exception';error=type(exc).__name__+': '+str(exc)
            if process is not None and process.poll() is None:_stop_tree(process,observed)
            if isinstance(exc,(KeyboardInterrupt,SystemExit)):
                reserve.unlink(missing_ok=True)
                atomic_json(attempt/'interruption.json',dict(error=error,known_process_stopped=True))
                raise
        finally:
            if process is not None and process.poll() is None:_stop_tree(process,observed)
        # Release a real allocated reserve before failure/finalization writes.
        reserve.unlink(missing_ok=True)
        worker_wall=time.perf_counter()-began
        hash_begin=time.perf_counter()
        files=[p for p in sorted(attempt.rglob('*')) if p.is_file()]
        if any(p.is_symlink() for p in files):raise ResumeConflict('Worker artifacts may not be symlinks')
        assets={p.relative_to(output).as_posix():file_hash(p) for p in files}
        assets['binding.json']=file_hash(output/'binding.json')
        hash_seconds=time.perf_counter()-hash_begin
        state=dict(task=task,binding_sha256=binding,status=status,failure_kind=failure_kind,error=error,
            samples_eligible=status=='completed',attempt=attempt.name,assets=assets,
            worker_result=result,return_code=process.returncode if process is not None else None,
            disk_preflight=disk,memory=dict(sampled_peak_tree_rss_bytes=peak,observation_samples=samples,
                limit_bytes=max_tree_rss_bytes,interval_seconds=.05,
                scope='Sampled sum of worker/descendant RSS, may double-count shared pages; not a strict allocator or VRAM bound'),
            cpu_observations=child_cpu,
            retry_policy='No implicit retry. Completed and failed terminals are immutable; interruption recovery is a separate explicit action.')
        commit_begin=time.perf_counter();atomic_json(output/'state.json',state)
        terminal_seconds=time.perf_counter()-commit_begin
        through_terminal=time.perf_counter()-began
        receipt=dict(state_sha256=file_hash(output/'state.json'),
            preparation_seconds=began-invocation_started,
            worker_lifecycle_seconds=worker_wall,asset_hash_seconds=hash_seconds,
            terminal_write_seconds=terminal_seconds,through_terminal_seconds=through_terminal,
            inclusive_preflight_through_terminal_seconds=(began-invocation_started)+through_terminal,
            supervisor_cpu_seconds=time.process_time()-cpu_start,
            boundary='Starts immediately before worker spawn; includes worker imports/shutdown, artifact hashing and durable terminal state write. Excludes preflight/request/reserve setup and this final receipt hash/write.',
            nested_worker_phases_are_not_additive_to_parent_wall=True)
        atomic_json(output/'completion.json',receipt)
        return dict(state,completion=receipt,resumed=False,newly_executed=True)
