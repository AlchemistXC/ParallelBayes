"""Native evidence I/O and identities, independent of historical frozen drivers."""
import hashlib
import importlib.metadata as md
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[2]


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def clean(x):
    if isinstance(x,torch.Tensor):return clean(x.detach().cpu().numpy())
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,np.generic):return clean(x.item())
    if isinstance(x,float) and not np.isfinite(x):return None
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    return x


def canonical(x):return json.dumps(clean(x),sort_keys=True,separators=(',',':'),allow_nan=False)
def fingerprint(x):return hashlib.sha256(canonical(x).encode()).hexdigest()


def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(clean(data),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temp.replace(path)


def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()


def source_files():
    paths=[]
    for name in ('r-package/inst/python/parallelbayes','scripts/windows','tests/windows','r-package/R'):
        paths.extend(p for p in (ROOT/name).rglob('*') if p.suffix in ('.py','.R','.ps1','.json') and '__pycache__' not in p.parts)
    paths.extend(ROOT/p for p in ('pyproject.toml','r-package/DESCRIPTION'))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}


def runtime():
    driver=subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],text=True).strip()
    return dict(python=sys.version,executable=sys.executable,base_executable=sys._base_executable,
        base_executable_sha256=sha(sys._base_executable),platform=platform.platform(),processor=platform.processor(),
        packages=dict(sorted((d.metadata['Name'].lower(),d.version) for d in md.distributions())),
        torch_cuda=torch.version.cuda,driver=driver,gpu=torch.cuda.get_device_name(0),
        capability=list(torch.cuda.get_device_capability(0)),cpu_threads=torch.get_num_threads(),
        interop_threads=torch.get_num_interop_threads(),float_policy='float64; TF32 disabled')


def configure():
    if sys.platform!='win32':raise RuntimeError('native Windows required')
    if sys.version_info[:2]!=(3,12):raise RuntimeError('Python 3.12 required')
    torch.set_num_threads(8)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    if not torch.cuda.is_available():raise RuntimeError('CUDA required; no CPU fallback')


def save_result(folder,result,tape=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    arrays={k:v for k,v in result.items() if isinstance(v,np.ndarray)}
    if tape is not None:arrays.update({'tape__'+k:v for k,v in tape.items()})
    start=time.perf_counter()
    np.savez_compressed(folder/'raw.npz',**arrays)
    record={k:v for k,v in result.items() if not isinstance(v,np.ndarray)}
    record['array_keys']=sorted(arrays)
    write_json(folder/'result.json',record)
    checks={p.name:sha(p) for p in (folder/'raw.npz',folder/'result.json')}
    return checks,time.perf_counter()-start


def verify_checksums(folder,checks):
    for name,digest in checks.items():
        if sha(Path(folder)/name)!=digest:raise ValueError('output checksum mismatch: '+name)
