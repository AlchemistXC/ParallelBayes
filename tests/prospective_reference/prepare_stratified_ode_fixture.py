"""Build a synthetic ODE fixture with ten central-prior stratified starts."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

os.environ['JAX_PLATFORMS']='cpu'
os.environ['JAX_ENABLE_X64']='true'
import jax
import numpy as np
from scipy.special import ndtr, ndtri

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/prospective_reference'))
from models import ODE, ode_fixture
from run import jnp


def digest(path):return sha256(path.read_bytes()).hexdigest()


def main(output):
    output.mkdir()
    if jax.default_backend()!='cpu' or not jax.config.x64_enabled:
        raise ValueError('synthetic preflight requires CPU and x64')
    fixture,center=ode_fixture(False)
    model=ODE(fixture.observations,center,prior_scale=.5)
    rng=np.random.default_rng(744211)
    bins=np.column_stack([rng.permutation(10) for _ in range(8)])
    u=rng.random((10,4,8))
    candidates=center+.5*ndtri(.1+.8*(bins[:,None,:]+u)/10)
    found=np.floor((ndtr((candidates-center)/.5)-.1)*12.5).astype(int)
    if not np.array_equal(found,np.broadcast_to(bins[:,None,:],found.shape)):
        raise ValueError('replacement left its original stratum')
    if any(sorted(bins[:,i].tolist())!=list(range(10)) for i in range(8)):
        raise ValueError('initial strata do not cover each coordinate')
    evaluate=jax.jit(jax.value_and_grad(model.log_density))
    v0,_=evaluate(jnp.asarray(center)); _,ref0,_=model.oracle(center)
    selected=[];selection=[];checks=[]
    for chain in range(10):
        chain_checks=[]; chosen=None
        for candidate in range(4):
            point=candidates[chain,candidate]
            try:
                value,grad=evaluate(jnp.asarray(point)); _,ref,refgrad=model.oracle(point)
                delta=float(abs(float(value-v0)-(ref-ref0)))
                ratio=float(np.max(np.abs(np.asarray(grad)-refgrad)/(1e-6+1e-5*np.abs(refgrad))))
                valid=bool(np.isfinite(float(value)) and np.isfinite(np.asarray(grad)).all()
                           and np.isfinite(delta) and np.isfinite(ratio) and delta<=1e-5 and ratio<=1)
                if not np.isfinite([delta,ratio]).all():raise FloatingPointError('nonfinite preflight')
                chain_checks.append({'candidate':candidate+1,'passed':valid,'density_delta_error':delta,
                                     'gradient_budget':ratio})
            except Exception as error:
                valid=False;chain_checks.append({'candidate':candidate+1,'passed':False,
                                                  'error_type':type(error).__name__,'error':str(error)})
            if valid:chosen=candidate;break
        checks.append({'chain':chain+1,'candidates':chain_checks})
        if chosen is None:
            with (output/'FAILED-preflight.json').open('x') as file:
                json.dump({'scope':'synthetic only','checks':checks},file,indent=2,allow_nan=False)
            raise SystemExit('no valid initial within a chain stratum')
        selected.append(candidates[chain,chosen]);selection.append(chosen)
    np.savez(output/'data.npz',ode_log_observations=fixture.observations)
    np.savez(output/'initials.npz',ode=np.asarray(selected),ode_candidates=candidates,
             stratum=bins,selected_indices=np.asarray(selection))
    meta={'scope':'SYNTHETIC TEST ONLY; no formal data', 'data_sha256':digest(output/'data.npz'),
          'initials_sha256':digest(output/'initials.npz'),
          'ode':{'center':np.exp(center).tolist()},
          'initials':{'synthetic_strata_seed':744211,'formal_random_stream_seed':887132,
                      'rule':'ten strata of central 80% per coordinate, up to four candidates'}}
    with (output/'manifest.json').open('x') as file:json.dump(meta,file,indent=2);file.write('\n')
    report={'scope':'synthetic ODE starts only; not study approval',
            'inputs_manifest_sha256':digest(output/'manifest.json'),
            'data_sha256':meta['data_sha256'],'initials_sha256':meta['initials_sha256'],
            'checks':{'ode':{'passed':True,'chains':checks}},'formal_sampling_started':False}
    with (output/'preflight.json').open('x') as file:json.dump(report,file,indent=2,allow_nan=False);file.write('\n')
    print(json.dumps({'passed':True,'selected_candidate_indices_1_based':[x+1 for x in selection],
                      'manifest_sha256':report['inputs_manifest_sha256']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    main(parser.parse_args().output.resolve())
