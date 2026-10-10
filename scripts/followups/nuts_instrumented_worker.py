"""Native Windows instrumentation around the frozen CPU Pyro baseline.

Kernel construction, adaptation and hooks delegate to the existing sampler.
The new intervention is durable state capture and an optional whole diagnostics
bypass, applied identically across worker configurations. This is not a fix or
an eligible replacement for any historical failed task.
"""
from pathlib import Path
import json
import os
import random
import sys
import time
import traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from nuts_events import ChainRecorder,atomic_json,sha,jsonable,snapshot_memory


def require_windows():
    if sys.platform!='win32':raise RuntimeError('Native Windows execution required; Mac tests are portable components only')


def nested_tuple(value):return tuple(nested_tuple(v) for v in value) if isinstance(value,list) else value


def rng_snapshot(torch):
    n=np.random.get_state()
    return dict(python=jsonable(random.getstate()),numpy=dict(generator=n[0],keys=n[1].tolist(),position=n[2],has_gauss=n[3],cached_gaussian=n[4]),torch_cpu=torch.get_rng_state().tolist())


def restore_rng(torch,state):
    random.setstate(nested_tuple(state['python']));n=state['numpy']
    np.random.set_state((n['generator'],np.asarray(n['keys'],dtype=np.uint32),n['position'],n['has_gauss'],n['cached_gaussian']))
    torch.set_rng_state(torch.tensor(state['torch_cpu'],dtype=torch.uint8,device='cpu'))
    if rng_snapshot(torch)!=state:raise ValueError('Actual RNG restoration differs')


def prepare_rng_states(seeds,destination):
    require_windows()
    import torch,pyro
    destination=Path(destination)
    if destination.exists():raise FileExistsError('Native RNG preparation is immutable')
    saved=rng_snapshot(torch);states=[]
    try:
        for seed in seeds:
            pyro.set_rng_seed(int(seed));states.append(rng_snapshot(torch))
    finally:restore_rng(torch,saved)
    atomic_json(destination,dict(seeds=list(map(int,seeds)),states=states,torch=torch.__version__,pyro=pyro.__version__,
        schema='actual-python-numpy-torch-cpu-rng-v1',scope='These actual states are shared across all four new conditions; old equality is not inferred from seeds alone'))
    return sha(destination)


def initialize_worker(directory=None):
    require_windows()
    import torch
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    if directory is not None:
        from multiprocessing.util import Finalize
        destination=Path(directory);destination.mkdir(parents=True,exist_ok=True)
        atomic_json(destination/f'{os.getpid()}-enter.json',snapshot_memory())
        Finalize(None,worker_finalizer,args=(str(destination),),exitpriority=0)


def worker_finalizer(directory):
    atomic_json(Path(directory)/f'{os.getpid()}-finalizer.json',dict(**snapshot_memory(),
        phase='normal multiprocessing finalizer; actual exit is observed separately by the parent Job'))


def execute_chain(payload):
    require_windows()
    import torch,pyro
    import inference_nuts as original
    from inference_parallel_nuts import restore_model
    directory=Path(payload['directory']);chain=payload['chain'];config=payload['config'];seed=int(payload['seed'])
    recorder=ChainRecorder(directory,chain,config['warmup'],config['draws'])
    import faulthandler
    fault=(directory/'fault.log').open('a');faulthandler.enable(file=fault,all_threads=True)
    old_mcmc=original.MCMC;old_seed=pyro.set_rng_seed;sample_call_complete=False
    try:
        recorder.event('target_prepare_enter',durable=True)
        model=restore_model(payload['spec'])
        if model.target_id!=payload['target_id']:raise ValueError('Native restored target differs from original target identity')
        recorder.event('target_prepare_exit',durable=True,target_id=model.target_id)
        if torch.get_num_threads()!=1 or torch.get_num_interop_threads()!=1:raise ValueError('Unexpected worker thread allocation')
        state=payload['initial_rng_state']
        def seed_from_saved(requested):
            if requested!=seed:raise ValueError('Unexpected seed call')
            restore_rng(torch,state)
            atomic_json(directory/'initial-rng.json',rng_snapshot(torch))
            recorder.event('actual_rng_restored',durable=True,sha256=sha(directory/'initial-rng.json'))
        pyro.set_rng_seed=seed_from_saved
        class RecordedMCMC(old_mcmc):
            def __init__(self,*args,**kwargs):
                self._localization_run_returned=False;self._localization_arrays_saved=False
                hook=kwargs['hook_fn']
                def observed(kernel,params,stage,index):
                    hook(kernel,params,stage,index)
                    recorder.hook(stage,index,params['q'].detach().numpy(),float(kernel.step_size))
                kwargs['hook_fn']=observed
                super().__init__(*args,**kwargs)
            def run(self,*args,**kwargs):
                recorder.event('mcmc_run_enter',durable=True)
                result=super().run(*args,**kwargs);self._localization_run_returned=True
                recorder.event('mcmc_run_returned',durable=True);return result
            def get_samples(self,*args,**kwargs):
                result=super().get_samples(*args,**kwargs)
                if self._localization_run_returned and not self._localization_arrays_saved:
                    values=result['q'].detach().numpy().copy()
                    record=recorder.persist_array('samples-before-diagnostics.npy',values)
                    atomic_json(directory/'rng-after-sampling.json',rng_snapshot(torch))
                    recorder.event('samples_persisted_before_diagnostics',durable=True,array=record,
                        rng_after_sampling_sha256=sha(directory/'rng-after-sampling.json'))
                    self._localization_arrays_saved=True
                return result
            def diagnostics(self,*args,**kwargs):
                if not self._localization_arrays_saved:raise RuntimeError('Diagnostics entered before durable sampled arrays')
                if not payload['diagnostics_enabled']:
                    recorder.event('legacy_diagnostics_bypassed',durable=True)
                    return {}
                recorder.event('legacy_diagnostics_enter',durable=True)
                result=super().diagnostics(*args,**kwargs)
                recorder.event('legacy_diagnostics_exit',durable=True)
                return result
        original.MCMC=RecordedMCMC
        recorder.event('baseline_call_enter',durable=True,configuration=config,diagnostics_enabled=payload['diagnostics_enabled'])
        result=original.sample_nuts(model,[payload['initial']],[seed],**config)
        sample_call_complete=True
        # Snapshot before the original fork_rng restores torch only describes
        # sampling if captured by get_samples above. This after-return state is
        # explicitly separated, since the baseline restores caller state.
        recorder.event('baseline_call_returned',durable=True,status=result['status'])
        recorder.partial()
        def transport(x):
            if isinstance(x,torch.Tensor):return x.detach().cpu().numpy().copy()
            if isinstance(x,dict):return {k:transport(v) for k,v in x.items()}
            if isinstance(x,list):return [transport(v) for v in x]
            if isinstance(x,tuple):return tuple(transport(v) for v in x)
            return x
        recorder.event('transport_conversion_enter',durable=True)
        result=transport(result)
        recorder.event('transport_conversion_exit',durable=True)
        # Return exactly the existing NumPy/plain result content through the
        # process pool. Durable diagnostic JSON encodes nonfinite numbers below
        # as explicit records; IPC preserves the original values.
        def safe(x):
            if isinstance(x,np.ndarray):return dict(array_shape=list(x.shape),dtype=str(x.dtype),omitted_here=True)
            if isinstance(x,np.generic):return safe(x.item())
            if isinstance(x,float) and not np.isfinite(x):return dict(nonfinite=str(x))
            if isinstance(x,dict):return {str(k):safe(v) for k,v in x.items()}
            if isinstance(x,(list,tuple)):return [safe(v) for v in x]
            return x
        diagnostic_counter=[0]
        def retain_diagnostics(value):
            if isinstance(value,np.ndarray):
                index=diagnostic_counter[0];diagnostic_counter[0]+=1
                return recorder.persist_array(f'diagnostic-array-{index:04d}.npy',value)
            if isinstance(value,dict):return {str(k):retain_diagnostics(v) for k,v in value.items()}
            if isinstance(value,(list,tuple)):return [retain_diagnostics(v) for v in value]
            return safe(value)
        metadata=safe({k:v for k,v in result.items() if k not in ('partial_chains','chain_records')})
        metadata['chain_records']=retain_diagnostics(result.get('chain_records',[]))
        metadata['partial_chains_scope']='Actual prefixes retained in chunk files; original full IPC result is unchanged'
        atomic_json(directory/'result-metadata.json',metadata)
        recorder.event('serialization_ready',durable=True,result_status=result['status'])
        return dict(chain=chain,worker_pid=os.getpid(),result=result,stage_directory=str(directory),threads=1)
    except BaseException as exc:
        recorder.partial();recorder.event('chain_exception',durable=True,error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
        raise
    finally:
        original.MCMC=old_mcmc;pyro.set_rng_seed=old_seed
        recorder.event('chain_function_exit',durable=True,baseline_returned=sample_call_complete)
        faulthandler.disable();fault.close()
