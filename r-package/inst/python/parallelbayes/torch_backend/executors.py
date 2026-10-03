"""Eager torch time executors. Tensors remain on-device; Python controls rounds.

No claim of efficient device-side control flow or torch.compile support.
Each scalar control read is explicitly counted and timed, including its CUDA wait.
"""
import time
import torch


def affine_scan(a, b, q0):
    """Hillis-Steele inclusive scan: right(left(q)), along the time axis -2."""
    stride = 1
    while stride < a.shape[-2]:
        aa = a[...,stride:,:]*a[...,:-stride,:]
        bb = a[...,stride:,:]*b[...,:-stride,:]+b[...,stride:,:]
        a = torch.cat((a[...,:stride,:],aa),dim=-2)
        b = torch.cat((b[...,:stride,:],bb),dim=-2)
        stride *= 2
    return a*q0.unsqueeze(-2)+b


class Control:
    def __init__(self):
        self.reads, self.seconds = 0, 0.

    def read(self, x):
        t = time.perf_counter()
        value = x.detach().item()
        self.seconds += time.perf_counter()-t
        self.reads += 1
        return value


def execute(step, q0, noise, logu, directions, c):
    chains,n,d = noise.shape
    control = Control()
    batch = torch.func.vmap(step, in_dims=(0,0,0,None))
    mapped = torch.func.vmap(batch, in_dims=(0,0,0,None))
    scale = c["step_size"]
    paths = torch.full_like(noise,float("nan"))
    accepts = torch.zeros_like(logu,dtype=torch.bool)
    finite_all = torch.ones((),device=q0.device,dtype=torch.bool)
    trace = []; forward = jvps = clips = rounds = confirmed = 0
    status = 0
    residual_max = 0.
    if c["executor"] == "sequential":
        q = q0
        for i in range(n):
            q, acc, finite = batch(q,noise[:,i],logu[:,i],scale)
            paths[:,i] = q; accepts[:,i] = acc
            finite_all = finite_all & finite.all()
        forward = confirmed = chains*n; rounds = n
        if not control.read(finite_all):
            status = 2; confirmed = 0
    elif c["executor"] == "quasi_deer":
        base = q0
        def jvp_one(q,z,u,v):
            return torch.func.jvp(lambda x: step(x,z,u,scale,True)[0],(q,),(v,))
        jvp_batch = torch.func.vmap(torch.func.vmap(jvp_one))
        for offset in range(0,n,c["window"]):
            # Only real transitions: the shortened final window has no fictitious suffix.
            stop = min(n,offset+c["window"]); width = stop-offset
            z,u,v = noise[:,offset:stop],logu[:,offset:stop],directions[:,offset:stop]
            path = base[:,None,:].expand(-1,width,-1).clone()
            err = float("inf")
            for it in range(c["max_iter"]):
                prev = torch.cat((base[:,None,:],path[:,:-1,:]),dim=1)
                values,jv = jvp_batch(prev,z,u,v)
                diag = v*jv
                clipped = diag.clamp(-c["jacobian_clip"],c["jacobian_clip"])
                clips += int(control.read((diag.abs()>c["jacobian_clip"]).sum()))
                path = affine_scan(clipped,values-clipped*prev,base)
                prev = torch.cat((base[:,None,:],path[:,:-1,:]),dim=1)
                out,acc,finite = mapped(prev,z,u,scale)
                err = control.read(((path-out).abs()/(c["atol"]+c["rtol"]*out.abs())).max())
                good = control.read(finite.all() & torch.isfinite(path).all() & torch.isfinite(diag).all())
                rounds += 1; forward += 2*chains*width; jvps += chains*width
                trace.append(dict(offset=offset,iteration=it+1,residual=err,confirmed=confirmed))
                if not good:
                    status = 2; break
                if err <= 1:
                    break
            else:
                status = 1
            paths[:,offset:stop] = path; accepts[:,offset:stop] = acc
            residual_max = max(residual_max,err)
            if status:
                break
            confirmed += chains*width
            base = path[:,-1,:]
    else:  # Online Picard: shared offset uses minimum consistent prefix over chains.
        offset = 0
        guess = q0[:,None,:].expand(-1,c["window"],-1).clone()
        while offset < n and rounds < c["max_iter"]:
            width = min(c["window"],n-offset)
            guess = guess[:,:width]
            z,u = noise[:,offset:offset+width],logu[:,offset:offset+width]
            _,old,finite1 = mapped(guess,z,u,scale)
            increments = torch.where(old[:,:,None],scale*z,torch.zeros_like(z))
            path = guess[:,:1,:]+torch.cumsum(increments,dim=1)
            prev = torch.cat((guess[:,:1,:],path[:,:-1,:]),dim=1)
            _,new,finite2 = mapped(prev,z,u,scale)
            prefix = int(control.read(torch.cumprod((old==new).to(torch.int64),dim=1).sum(1).min()))
            good = control.read(finite1.all() & finite2.all() & torch.isfinite(path).all())
            rounds += 1; forward += 2*chains*width
            trace.append(dict(offset=offset,iteration=rounds,confirmed_prefix=prefix))
            paths[:,offset:offset+width] = path; accepts[:,offset:offset+width] = old
            if not good or prefix == 0:
                status = 2; break
            offset += prefix; confirmed = chains*offset
            indices = torch.arange(c["window"],device=q0.device)+prefix
            shifted = prev[:,indices.clamp(max=width-1),:]
            guess = torch.where((indices>=width)[None,:,None],path[:,-1:,:],shifted)
        if status == 0 and offset < n:
            status = 1
    return paths, accepts, dict(status=status,iterations=rounds,residual=residual_max,
        clips=clips,confirmed=confirmed,forward_evals=forward,jvp_evals=jvps,rounds=trace,
        host_scalar_reads=control.reads,host_scalar_wait_seconds=control.seconds,
        control_policy="eager Python; scalar reads synchronize CUDA; chain-shared minimum Picard prefix",
        tensor_device=str(paths.device),tensor_dtype=str(paths.dtype))
