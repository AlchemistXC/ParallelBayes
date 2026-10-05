"""Prepared eager MH execution, separately synchronized from transfer/audit.

The existing transition and executor are unchanged. No random arrays are
generated, no fallback is performed, and replay outputs are never independently
eligible posterior samples. The caller must retain failures and audit outputs.
"""
import copy
import time
import numpy as np
import torch

from parallelbayes.torch_backend.sampling import settings,sync,tape_hash
from parallelbayes.torch_backend.kernels import transition
from parallelbayes.torch_backend.executors import execute


class PreparedExecutor:
    def __init__(self,model,config,tape):
        start=time.perf_counter();c=settings(copy.deepcopy(config))
        if c['audit'] or c['on_failure']!='error':
            raise ValueError('Prepared measurement requires explicit audit=False and on_failure=error')
        requested=torch.device(c['device'])
        if model.backend!='torch' or model.device.type!=requested.type or (requested.index is not None and model.device.index not in (None,requested.index)):
            raise ValueError('Prepared target and requested device differ')
        d=model.dimension;shape=(c['chains'],c['draws'],d)
        estimate=c['chains']*(c['draws']+c['window'])*d*8*40
        if estimate>c['memory_limit_mb']*1024**2:raise MemoryError('Prepared workspace estimate exceeds limit')
        # Exactly the sampler's three required roles; no hidden RNG or prefixes.
        if set(tape)!={'noise','log_uniform','directions'}:raise ValueError('Actual tape roles differ')
        saved={k:np.array(v,dtype=np.float64,copy=True) for k,v in tape.items()}
        for k,s in (('noise',shape),('directions',shape),('log_uniform',shape[:2])):
            if saved[k].shape!=s or not np.isfinite(saved[k]).all():raise ValueError('Invalid actual tape: '+k)
        if (saved['log_uniform']>0).any() or not np.isin(saved['directions'],[-1.,1.]).all():
            raise ValueError('Invalid log uniform or Rademacher direction')
        q0=np.zeros((c['chains'],d)) if c['initial'] is None else np.asarray(c['initial'],dtype=float)
        if q0.shape==(d,):q0=np.broadcast_to(q0,(c['chains'],d)).copy()
        if q0.shape!=(c['chains'],d) or not np.isfinite(q0).all():raise ValueError('Invalid initial coordinates')
        self._args=tuple(torch.tensor(a,dtype=torch.float64,device=model.device) for a in
                         (q0,saved['noise'],saved['log_uniform'],saved['directions']))
        self._model=model;self._c=c;self._step=transition(model.log_density,c['kernel']);self._count=0
        self._tape_hash=tape_hash(saved);self._estimate=estimate
        sync(model.device);self._prepare_seconds=time.perf_counter()-start

    def run(self):
        sync(self._model.device)
        start=time.perf_counter()
        path,accept,stats=execute(self._step,*self._args,self._c)
        sync(self._model.device);elapsed=time.perf_counter()-start
        transfer_start=time.perf_counter()
        pn=path.detach().cpu().numpy().copy();an=accept.detach().cpu().numpy().copy()
        sync(self._model.device);transfer_seconds=time.perf_counter()-transfer_start
        ordinal=self._count;self._count+=1
        valid=stats['status']==0 and np.isfinite(pn).all()
        return dict(status='candidate' if valid else 'failed',samples_eligible=False,
            unconstrained=pn,accept=an,diagnostics=stats,has_prior_execution=ordinal>0,execution_index=ordinal,
            executor_wall_seconds=elapsed,transfer_seconds=transfer_seconds,prepare_seconds=self._prepare_seconds,
            config=copy.deepcopy(self._c),target_id=self._model.target_id,tape_sha256=self._tape_hash,
            estimated_array_workspace_bytes=self._estimate,transfer_included_in_executor_wall=False,
            audit_included_in_executor_wall=False,transform_included_in_executor_wall=False,
            implementation='Unchanged torch eager executor, prepared inputs, no new explicit compilation or device-control fusion',
            boundary='Pre-synchronized prepared execute call through post-execution device synchronization; allocation and existing host-control telemetry included',
            statistical_repetitions_added=0)
