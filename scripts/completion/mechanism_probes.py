"""Separate fixed-input operation probes; never additive executor profiling."""
import hashlib
import json
from pathlib import Path
import time
import traceback
import numpy as np
import torch
from parallelbayes.reference import numpy_reference
from parallelbayes.torch_backend.kernels import transition
from parallelbayes.torch_backend.executors import affine_scan
from parallelbayes.torch_backend.sampling import sync


def probe_fixed_batch(model,q,z,logu,directions,scale,kernel,output,repeats=3,block=5):
    output=Path(output)
    if output.exists():raise FileExistsError('Preserve existing cost probes')
    if q.ndim!=3 or q.numel()>1000000 or q.shape!=z.shape or q.shape!=directions.shape or logu.shape!=q.shape[:2]:
        raise ValueError('Probe dimensions/workspace guard')
    output.mkdir(parents=True)
    arrays={k:x.detach().cpu().numpy() for k,x in [('q',q),('z',z),('logu',logu),('directions',directions)]}
    np.savez_compressed(output/'inputs.npz',**arrays)
    shape=q.shape;qf=q.reshape(-1,shape[-1]);zf=z.reshape_as(qf);uf=logu.reshape(-1);vf=directions.reshape_as(qf)
    step=transition(model.log_density,kernel)
    mapped=torch.func.vmap(step,in_dims=(0,0,0,None))
    density=torch.func.vmap(model.log_density)
    def jvp_one(x,noise,u,v):
        return torch.func.jvp(lambda a:step(a,noise,u,scale,True)[0],(x,),(v,))
    jvps=torch.func.vmap(jvp_one)
    def loop_step():
        values=[step(a,b,c,scale) for a,b,c in zip(qf,zf,uf)]
        return tuple(torch.stack([v[i] for v in values]) for i in range(3))
    def loop_jvp():
        values=[jvp_one(a,b,c,d) for a,b,c,d in zip(qf,zf,uf,vf)]
        return tuple(torch.stack([v[i] for v in values]) for i in range(2))
    report=dict(status='failed',shape=list(shape),kernel=kernel,step_size=scale,
        components_are_additive=False,
        scope='Separate synchronized fixed-state probes; not actual solver-state occupation or an exclusive wall-time decomposition',
        repetition='Block calls and timing rounds reuse these exact states; they are technical repetitions')
    try:
        batch=mapped(qf,zf,uf,scale);serial=loop_step()
        npq=arrays['q'].reshape(-1,shape[-1]);npz=arrays['z'].reshape(npq.shape)
        expected=[];events=[]
        for a,b,c in zip(npq,npz,arrays['logu'].ravel()):
            path,acc=numpy_reference(model,kernel,a,b[None,:],np.array([c]),scale)
            expected.append(path[0]);events.append(acc[0])
        path=batch[0].detach().cpu().numpy();accept=batch[1].detach().cpu().numpy()
        error=float(np.max(np.abs(path-np.array(expected))));mismatches=int(np.sum(accept!=np.array(events)))
        dloop=torch.stack([model.log_density(a) for a in qf]);dbatch=density(qf)
        dref=np.array([model.reference(a) for a in npq])
        if error>1e-7 or mismatches or not bool(batch[2].all()):raise ValueError('Probe transition differs from independent NumPy')
        if not torch.allclose(batch[0],serial[0],atol=1e-9,rtol=1e-10) or not torch.equal(batch[1],serial[1]):raise ValueError('Serial/batch transition differs')
        if not torch.allclose(dloop,dbatch,atol=1e-9,rtol=1e-10) or not np.allclose(dbatch.detach().cpu().numpy(),dref,atol=1e-8,rtol=1e-10):raise ValueError('Density batching differs')
        value,jv=jvps(qf,zf,uf,vf);svalue,sjv=loop_jvp()
        if not torch.allclose(value,svalue,atol=1e-9,rtol=1e-10) or not torch.allclose(jv,sjv,atol=1e-8,rtol=1e-9):raise ValueError('Surrogate JVP batching differs')
        a=(vf*jv).reshape(shape).clamp(-1.,1.);b=value.reshape(shape)-a*q;initial=q[:,0,:]
        def serial_scan():
            x=initial;out=[]
            for i in range(shape[1]):
                x=a[:,i]*x+b[:,i];out.append(x)
            return torch.stack(out,dim=1)
        if not torch.allclose(affine_scan(a,b,initial),serial_scan(),atol=1e-8,rtol=1e-9):raise ValueError('Affine scan differs from serial recurrence')
        accepts=batch[1].reshape(shape[:2]);agree=(accepts==torch.roll(accepts,1,dims=1));agree[:,0]=True
        functions={
            'density_loop':lambda:torch.stack([model.log_density(a) for a in qf]),
            'density_batch':lambda:density(qf),
            'transition_loop':loop_step,'transition_batch':lambda:mapped(qf,zf,uf,scale),
            'surrogate_jvp_loop':loop_jvp,'surrogate_jvp_batch':lambda:jvps(qf,zf,uf,vf),
            'affine_scan':lambda:affine_scan(a,b,initial),'affine_serial':serial_scan,
            'prefix_scalar_read':lambda:int(torch.cumprod(agree.to(torch.int64),dim=1).sum(1).min().item())}
        first={}
        for name,fn in functions.items():first[name]=fn()
        sync(model.device)
        def same(x,y):
            if isinstance(x,tuple):return all(same(a,b) for a,b in zip(x,y))
            return torch.equal(x,y) if isinstance(x,torch.Tensor) else x==y
        timings={k:[] for k in functions};report['measurements']=timings;names=list(functions)
        for rep in range(repeats):
            for name in names[rep%len(names):]+names[:rep%len(names)]:
                sync(model.device);cpu0=time.process_time();start=time.perf_counter()
                for _ in range(block):last=functions[name]()
                sync(model.device);wall=time.perf_counter()-start;cpu=time.process_time()-cpu0
                if not same(first[name],last):raise ValueError('Repeated probe value changed')
                timings[name].append(dict(block_calls=block,wall_seconds=wall,
                    seconds_per_call=wall/block,process_cpu_seconds=cpu,process_cpu_percent=100*cpu/wall))
        np.savez_compressed(output/'checked-values.npz',transition=path,accept=accept,
            numpy_transition=np.array(expected),numpy_accept=np.array(events),
            density=dbatch.detach().cpu().numpy(),surrogate_jvp=jv.detach().cpu().numpy(),
            affine_scan=affine_scan(a,b,initial).detach().cpu().numpy(),prefix_agreement=agree.detach().cpu().numpy())
        report.update(status='passed',numerical_checks=dict(accepted=int(accept.sum()),
            acceptance_mismatches=mismatches,transition_max_abs_error=error,
            density_max_abs_error=float(np.max(np.abs(dbatch.detach().cpu().numpy()-dref))),
            serial_batch_and_scan_agree=True),measurements=timings,
            prefix_scope='Synthetic agreement flags from shifted fixed-batch acceptance; cost probe only, not observed solver prefix statistics')
    except Exception as exc:
        report.update(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
    (output/'result.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    checks={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
    (output/'checksums.json').write_text(json.dumps(checks,indent=2)+'\n')
    return report
