"""Actual framework probe, independent of the currently JAX-only project package."""
from pathlib import Path
import argparse,json,os,platform,subprocess,sys,time,traceback,uuid

def command(args):
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=20)
        return {'returncode':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
    except (OSError,subprocess.TimeoutExpired) as exc:return {'error':str(exc)}

def probe(require_windows=False,require_cuda=False,expected_device='RTX 5080'):
    r={'scope':'Framework operations only; no MCMC/backend/performance certification',
       'python':sys.version,'python_executable':sys.executable,'platform':platform.platform(),
       'machine':platform.machine(),'processor':platform.processor(),'os_cpu_count':os.cpu_count(),
       'requested':{'native_windows':require_windows,'cuda':require_cuda,'expected_device':expected_device},
       'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'failed','gpu_verified':False}
    try:
        if require_windows and sys.platform!='win32':raise RuntimeError('Native Windows required; WSL/Linux/macOS is not accepted')
        import numpy as np,psutil,torch
        r.update(torch=torch.__version__,torch_cuda=torch.version.cuda,numpy=np.__version__,ram_bytes=psutil.virtual_memory().total,cpu_logical=psutil.cpu_count(),cpu_physical=psutil.cpu_count(logical=False))
        r['nvidia_smi']=command(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'])
        have_cuda=torch.cuda.is_available()
        if require_cuda and not have_cuda:raise RuntimeError('CUDA unavailable; refusing CPU fallback')
        device=torch.device('cuda:0' if have_cuda else 'cpu')
        torch.set_default_dtype(torch.float64)
        if have_cuda:
            name=torch.cuda.get_device_name(0)
            if expected_device and expected_device.casefold() not in name.casefold():raise RuntimeError('Expected '+expected_device+', detected '+name)
            r.update(gpu_name=name,capability=list(torch.cuda.get_device_capability(0)),compiled_arches=torch.cuda.get_arch_list(),device_memory_bytes=torch.cuda.get_device_properties(0).total_memory)
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize()
        a=np.arange(1,65,dtype=np.float64).reshape(8,8)/64;a=a.T@a+np.eye(8)
        qn=np.linspace(-.8,.8,8);vn=np.linspace(.1,1,8)
        A=torch.tensor(a,device=device);q=torch.tensor(qn,device=device);v=torch.tensor(vn,device=device)
        def f(x):return -.5*x@A@x+.1*torch.cos(x).sum()
        grad=torch.func.grad(f);values=torch.func.vmap(f)(torch.stack([q,q*2,q*.5]))
        g=grad(q);_,hv=torch.func.jvp(grad,(q,),(v,))
        chol=torch.linalg.cholesky(A);reconstructed=chol@chol.T
        if have_cuda:torch.cuda.synchronize()
        assert all(x.device==device and x.dtype==torch.float64 for x in [values,g,hv,reconstructed])
        np.testing.assert_allclose(g.cpu().numpy(),-a@qn-.1*np.sin(qn),rtol=1e-10,atol=1e-12)
        np.testing.assert_allclose(hv.cpu().numpy(),-a@vn-.1*np.cos(qn)*vn,rtol=1e-10,atol=1e-12)
        np.testing.assert_allclose(reconstructed.cpu().numpy(),a,rtol=1e-10,atol=1e-12)
        expected=np.array([-.5*x@a@x+.1*np.cos(x).sum() for x in [qn,2*qn,.5*qn]])
        np.testing.assert_allclose(values.cpu().numpy(),expected,rtol=1e-10,atol=1e-12)
        r.update(status='passed',gpu_verified=have_cuda,device=str(device),dtype=str(q.dtype),checks=['fp64 algebra','grad','jvp_of_grad','vmap','Cholesky','independent NumPy equality','device and dtype assertions'],gradient_max_abs_error=float(np.max(np.abs(g.cpu().numpy()-(-a@qn-.1*np.sin(qn))))))
        if have_cuda:r.update(peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
    except Exception as exc:r.update(error=str(exc),traceback=traceback.format_exc())
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--require-windows',action='store_true');p.add_argument('--require-cuda',action='store_true');p.add_argument('--expected-device',default='RTX 5080');p.add_argument('--output',type=Path,default=Path('execution/windows-native/environment.json'));a=p.parse_args()
    r=probe(a.require_windows,a.require_cuda,a.expected_device);a.output.parent.mkdir(parents=True,exist_ok=True)
    attempt=a.output.with_name(a.output.stem+'-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:8]+'.json')
    body=json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n';attempt.write_text(body,encoding='utf-8')
    temp=a.output.with_suffix('.tmp');temp.write_text(body,encoding='utf-8');temp.replace(a.output)
    print(json.dumps({'status':r['status'],'report':str(a.output),'attempt':str(attempt),'scope':r['scope']}))
    return 0 if r['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
