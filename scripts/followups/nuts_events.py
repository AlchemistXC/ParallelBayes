"""Durable stage evidence for the bounded NUTS localization study.

No sampler or RNG imports. One chain writes its own directory; partial chunks
are evidence, not newly eligible posterior samples.
"""
import hashlib
import json
import os
from pathlib import Path
import time
import numpy as np
import psutil


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()



def portable_manifest(hashes):
    """Interpret archived Windows separators without rewriting signed files.

    New manifests use POSIX paths. Legacy backslashes are accepted only for
    unambiguous relative names; aliases, drives and traversal are rejected.
    """
    result = {}
    for name, digest in hashes.items():
        if not isinstance(name, str):
            raise ValueError('Unsafe relative path: non-string name')
        canonical = name.replace('\\', '/')
        if ':' in canonical or any(part in ('', '.', '..') for part in canonical.split('/')):
            raise ValueError('Unsafe relative path: ' + name)
        if canonical in result:
            raise ValueError('Duplicate portable path: ' + canonical)
        result[canonical] = digest
    return result

def jsonable(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {str(k):jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [jsonable(v) for v in value]
    return value


def atomic_json(path,value):
    p=Path(path);tmp=p.with_suffix(p.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='\n') as f:
        json.dump(jsonable(value),f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    tmp.replace(p)


def snapshot_memory():
    p=psutil.Process();m=p.memory_info()
    return dict(pid=os.getpid(),creation_time=p.create_time(),rss_bytes=m.rss,vms_bytes=m.vms,
                private_bytes=getattr(m,'private',None),private_scope='psutil native private field when available; missing is not zero')


class ChainRecorder:
    def __init__(self,directory,chain,warmup,draws,block=128):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        if (self.directory/'events.ndjson').exists():raise FileExistsError('Do not overwrite a prior chain attempt')
        self.chain=chain;self.limits=dict(warmup=warmup,sample=draws);self.block=block
        self.buffers={s:[] for s in self.limits};self.counts={s:0 for s in self.limits};self.steps={s:[] for s in self.limits};self.sequence=0
        self.event('chain_enter',durable=True)

    def event(self,name,durable=False,**fields):
        value=dict(sequence=self.sequence,event=name,chain=self.chain,utc_ns=time.time_ns(),monotonic_ns=time.perf_counter_ns(),**snapshot_memory(),**jsonable(fields));self.sequence+=1
        with (self.directory/'events.ndjson').open('a',encoding='utf-8',newline='\n') as f:
            f.write(json.dumps(value,allow_nan=False)+'\n');f.flush()
            if durable:os.fsync(f.fileno())
        return value

    def persist_array(self,name,array):
        destination=self.directory/name
        if destination.exists():raise FileExistsError('Existing array is immutable: '+name)
        temp=destination.with_suffix(destination.suffix+'.tmp')
        with temp.open('wb') as f:np.save(f,np.asarray(array),allow_pickle=False);f.flush();os.fsync(f.fileno())
        temp.replace(destination)
        record=dict(name=name,sha256=sha(destination),shape=list(np.asarray(array).shape),dtype=str(np.asarray(array).dtype))
        atomic_json(destination.with_suffix('.json'),record);return record

    def hook(self,stage,index,state,step_size):
        label='warmup' if stage.startswith('Warmup') else 'sample'
        if index!=self.counts[label] or index>=self.limits[label]:raise ValueError('Nonsequential or out-of-range hook index')
        state=np.array(state,dtype=float,copy=True)
        if state.ndim!=1 or not np.isfinite(state).all() or not np.isfinite(step_size):raise ValueError('Nonfinite hook state/step size')
        self.buffers[label].append(state);self.steps[label].append(float(step_size));self.counts[label]+=1
        if len(self.buffers[label])==self.block or self.counts[label]==self.limits[label]:self.flush(label)
        if self.counts[label]==self.limits[label]:self.event(label+'_completed',durable=True,steps=self.counts[label])

    def flush(self,label):
        if not self.buffers[label]:return
        stop=self.counts[label];start=stop-len(self.buffers[label]);tag=f'{label}-{start:06d}-{stop:06d}'
        state=self.persist_array(tag+'.npy',np.stack(self.buffers[label]))
        size=self.persist_array(tag+'-step-size.npy',np.asarray(self.steps[label]))
        self.event('chunk_persisted',durable=True,phase=label,start=start,stop=stop,state=state,step_size=size)
        self.buffers[label].clear();self.steps[label].clear()

    def partial(self):
        for label in self.buffers:self.flush(label)
        self.event('partial_state_preserved',durable=True,counts=self.counts)
