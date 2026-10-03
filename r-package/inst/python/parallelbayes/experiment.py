"""Frozen manifests, atomic per-task receipts, raw arrays and resumable execution."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import os
import platform
import threading
import time
import traceback
import uuid
import numpy as np
import psutil
from .models import fingerprint, make_model
from .sampling import sample, environment, random_tape


def plain(value):
    if isinstance(value, np.ndarray): return plain(value.tolist())
    if isinstance(value, np.generic): return plain(value.item())
    if isinstance(value, dict): return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [plain(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value): return None
    return value


def write_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(plain(value),ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
    temp.replace(path)


def file_hash(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hash(root):
    root=Path(root); h=hashlib.sha256()
    files=list((root/'r-package/inst/python/parallelbayes').glob('*.py'))
    files+=list((root/'r-package/R').glob('*.R'))
    files+=list((root/'models/stan').glob('*.stan'))
    for p in sorted(files):
        h.update(str(p.relative_to(root)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


class ResourceMonitor:
    """Sample host process RSS; not a device-allocation or whole-system peak."""
    def __enter__(self):
        self.stop=threading.Event(); self.peak=0; self.process=psutil.Process()
        def monitor():
            while not self.stop.is_set():
                self.peak=max(self.peak,self.process.memory_info().rss)
                self.stop.wait(.02)
        self.worker=threading.Thread(target=monitor,daemon=True); self.worker.start()
        return self
    def __exit__(self,*args):
        self.peak=max(self.peak,self.process.memory_info().rss)
        self.stop.set(); self.worker.join()


def freeze(path,protocol,root):
    path=Path(path)
    if path.exists(): raise FileExistsError('Frozen protocol already exists; create a new version')
    result=dict(protocol,source_sha256=source_hash(root),frozen_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                runtime_lock_sha256=file_hash(Path(root)/'environment/locks/python-core.txt'))
    for name,key in [('python-runtime-transitive.txt','transitive_lock_sha256'),('gpu-candidate.txt','gpu_lock_sha256')]:
        lock=Path(root)/'environment/locks'/name
        if lock.exists():result[key]=file_hash(lock)
    result['protocol_sha256']=fingerprint(result)
    write_json(path,result)
    return result


def load_protocol(path,root):
    p=json.loads(Path(path).read_text()); expected=p.pop('protocol_sha256')
    if fingerprint(p)!=expected: raise ValueError('Protocol content was modified after freeze')
    p['protocol_sha256']=expected
    if p['source_sha256']!=source_hash(root):
        raise ValueError('Source differs from frozen protocol. Preserve diff and create a new protocol version')
    if p["runtime_lock_sha256"]!=file_hash(Path(root)/"environment/locks/python-core.txt"):
        raise ValueError("Runtime requirements differ from frozen lock")
    check_installed_lock(Path(root)/'environment/locks/python-core.txt')
    if 'transitive_lock_sha256' in p:
        path=Path(root)/'environment/locks/python-runtime-transitive.txt'
        if file_hash(path)!=p['transitive_lock_sha256']:raise ValueError('Transitive runtime lock changed')
        check_installed_lock(path)
    return p


def check_installed_lock(path):
    import importlib.metadata
    for line in Path(path).read_text().splitlines():
        if "==" in line and not line.startswith("#"):
            name,version=line.strip().split("==")
            if importlib.metadata.version(name)!=version:
                raise ValueError(f"Installed {name} differs from frozen dependency {version}")


def run_protocol(path,output,root,platform_name='cpu',retry_failed=False,limit=None):
    import jax
    protocol=load_protocol(path,root)
    if platform_name not in protocol['platforms']: raise ValueError('Platform not authorized by protocol')
    if platform_name=='gpu' and 'gpu_lock_sha256' in protocol:
        lock=Path(root)/'environment/locks/gpu-candidate.txt'
        if file_hash(lock)!=protocol['gpu_lock_sha256']:raise ValueError('GPU dependency lock changed')
        check_installed_lock(lock)
    devices=jax.devices(platform_name)
    if not devices: raise RuntimeError('Required device unavailable')
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    lock=output/'.runner.lock'
    try: fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError: raise RuntimeError('Runner lock exists; verify previous process ended before recovery')
    os.write(fd,str(os.getpid()).encode()); os.close(fd)
    try:
        return _run(protocol,output,root,platform_name,retry_failed,limit)
    finally:
        lock.unlink(missing_ok=True)


def _run(protocol,output,root,platform_name,retry_failed,limit):
    import jax
    identity=dict(protocol_sha256=protocol['protocol_sha256'],source_sha256=protocol['source_sha256'],platform=platform_name)
    current_environment=environment()
    threads={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','XLA_FLAGS','JAX_ENABLE_X64']}
    manifest=output/'manifest.json'
    if manifest.exists():
        old=json.loads(manifest.read_text())
        if old['identity']!=identity: raise ValueError('Output belongs to a different protocol/source/platform')
        if old['environment']!=current_environment or old['thread_environment']!=threads:
            raise ValueError('Execution environment changed during resume; use a distinct run and document the change')
    else: write_json(manifest,dict(identity=identity,environment=current_environment,
        nonfinite_json='null; raw .npz retains IEEE values',resource_scope='one device; one task at a time; host thread pools recorded',
        thread_environment=threads,
        task_count=len(protocol['tasks'])))
    session=uuid.uuid4().hex
    write_json(output/'sessions'/f'{session}.json',dict(environment=current_environment,
        thread_environment=threads,pid=os.getpid(),started=time.time(),identity=identity))
    done=0
    for index,task in enumerate(protocol['tasks']):
        tid=fingerprint(task)[:20]; folder=output/'tasks'/tid; receipt=folder/'state.json'
        if receipt.exists():
            state=json.loads(receipt.read_text())
            if state['status'] in ('completed','failed') and not (retry_failed and state['status']=='failed'):
                # A successful receipt is reusable only if raw files still match.
                for name,digest in state.get('checksums',{}).items():
                    if file_hash(folder/state['attempt']/name)!=digest: raise ValueError('Existing task output checksum mismatch')
                continue
        folder.mkdir(parents=True,exist_ok=True)
        attempt=f'attempt-{len(list(folder.glob("attempt-*")))+1:03d}'
        target=folder/attempt; target.mkdir()
        write_json(receipt,dict(status='running',task=task,attempt=attempt,pid=os.getpid(),execution_session=session))
        write_json(target/'task.json',task)
        start=time.perf_counter()
        try:
            model=make_model(protocol['models'][task['model']])
            config=dict(protocol['defaults'],**task['config'],platform=platform_name)
            with ResourceMonitor() as monitor:
                result=sample(model,config)
            result['host_process_peak_rss_bytes_sampled']=monitor.peak
            result['device_memory_stats']=jax.devices(platform_name)[0].memory_stats()
            raw={k:result.pop(k) for k in ['draws','unconstrained','failed_trajectory','primary_failed_trajectory'] if result.get(k) is not None}
            if config['kernel']!='nuts':
                for name,values in random_tape(result['config'],model.dimension).items():
                    raw['tape__'+name]=values
            # Arrays and acceptance events remain available without rounding or summary-only exports.
            for group in ['diagnostics','primary_diagnostics']:
                for name,value in (result.get(group) or {}).items():
                    if isinstance(value,np.ndarray): raw[f'{group}__{name}']=value
            np.savez_compressed(target/'raw.npz',**raw)
            result['task_elapsed_before_output']=time.perf_counter()-start
            write_json(target/'result.json',result)
            status=result['status']
        except Exception as exc:
            status='failed'
            write_json(target/'result.json',dict(status=status,exception=type(exc).__name__,message=str(exc),
                       traceback=traceback.format_exc(),elapsed=time.perf_counter()-start))
        checks={p.name:file_hash(p) for p in target.iterdir() if p.is_file()}
        write_json(receipt,dict(status=status,task=task,attempt=attempt,checksums=checks,
                              elapsed_including_output=time.perf_counter()-start,execution_session=session))
        done+=1
        print(f'{index+1}/{len(protocol["tasks"])} {task["model"]} {task["config"]} -> {status}',flush=True)
        jax.clear_caches()
        if limit is not None and done>=limit: break
    states=[]
    for task in protocol['tasks']:
        tid=fingerprint(task)[:20]; path=output/'tasks'/tid/'state.json'
        states.append(json.loads(path.read_text()) if path.exists() else dict(status='pending',task=task))
    write_json(output/'registry.json',dict(identity=identity,tasks=states))
    return states


def recover_lock(output):
    path=Path(output)/'.runner.lock'
    if not path.exists(): return
    pid=int(path.read_text())
    if psutil.pid_exists(pid): raise RuntimeError('Previous PID still exists; inspect it manually')
    path.unlink()
