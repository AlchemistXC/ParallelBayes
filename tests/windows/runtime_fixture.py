"""Artificial owned-process and CUDA fixtures, never scientific evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/windows'),str(ROOT/'scripts/completion')]
from formal_runtime import atomic_json
from job_objects import identity


def worker(request_path,output):
    request=json.loads(Path(request_path).read_text());output=Path(output)
    atomic_json(output/'fixture-actual-process.json',identity(os.getpid()))
    mode=request.get('mode','ok')
    if mode=='failed_then_wait':
        atomic_json(output/'worker-result.json',dict(status='failed',artifact_kind='posterior',samples_eligible=False,measurement_available=False,failure_category='numerical_failure'))
        while True:time.sleep(.05)
    if mode=='descendants':
        child=subprocess.Popen([sys.executable,str(Path(__file__)),'cuda-child' if request.get('cuda_fixture') else 'child',str(output)])
        atomic_json(output/'child-launch.json',dict(pid=child.pid))
        while not (output/'grandchild.json').exists():time.sleep(.02)
        while not (Path(request['release'])).exists():time.sleep(.03)
        child.wait()
    elif mode=='memory':
        data=bytearray(128*1024**2);time.sleep(20)
    elif mode=='interrupted':
        sys.exit(17)
    elif mode=='commit-limit':
        try:data=bytearray(128*1024**2)
        except MemoryError:
            atomic_json(output/'commit-proof.json',dict(requested_bytes=128*1024**2,allocation_denied=True))
            atomic_json(output/'worker-result.json',dict(status='failed',samples_eligible=False,measurement_available=False,
                failure_category='resource_failure',artifact_kind='posterior'))
            return
        atomic_json(output/'commit-proof.json',dict(requested_bytes=len(data),allocation_denied=False))
    elif mode=='cuda':
        import torch
        x=torch.ones(128,device='cuda',dtype=torch.float64)
        torch.cuda.synchronize();start=time.perf_counter();result=x.sin().square()
        torch.cuda.synchronize();elapsed=time.perf_counter()-start
        atomic_json(output/'cuda.json',dict(device=str(x.device),dtype=str(x.dtype),
            synchronized_seconds=elapsed,free_bytes=torch.cuda.mem_get_info()[0],
            allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved(),value=float(result.sum())))
        if request.get('reject_free_bytes',0)>torch.cuda.mem_get_info()[0]:
            atomic_json(output/'worker-result.json',dict(status='failed',samples_eligible=False,
                measurement_available=False,failure_category='resource_failure',artifact_kind='posterior'))
            return
    kind=request.get('artifact_kind','posterior');failed=mode=='numerical_failure'
    atomic_json(output/'worker-result.json',dict(status='failed' if failed else 'completed',
        artifact_kind=kind,samples_eligible=False if kind=='cache_measurement' else not failed,
        measurement_available=not failed and kind=='cache_measurement',
        failure_category='numerical_failure' if failed else None))
    if mode=='contradiction':
        atomic_json(output/'worker-result.json',dict(status='completed',artifact_kind='cache_measurement',
            samples_eligible=True,measurement_available=True))


if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='manager':
        from owned_runtime import Coordinator
        spec=json.loads(Path(sys.argv[2]).read_text())
        atomic_json(Path(spec['output']).parent/'manager.json',identity(os.getpid()))
        Coordinator(spec.pop('host_lock')).run(**spec)
    elif mode in ('child','cuda-child'):
        output=Path(sys.argv[2]);p=subprocess.Popen([sys.executable,str(Path(__file__)),'cuda-grandchild' if mode=='cuda-child' else 'grandchild',str(output)])
        p.wait()
    elif mode in ('grandchild','cuda-grandchild'):
        output=Path(sys.argv[2]);record=identity(os.getpid())
        if mode=='cuda-grandchild':
            import torch
            tensor=torch.ones(128,device='cuda',dtype=torch.float64);torch.cuda.synchronize()
            record.update(device=str(tensor.device),dtype=str(tensor.dtype),allocated=torch.cuda.memory_allocated())
        atomic_json(output/'grandchild.json',record)
        while not (output/'fixture-release').exists():
            if mode=='cuda-grandchild':tensor.square().sum().item()
            time.sleep(.05)
    else:worker(sys.argv[1],sys.argv[2])
