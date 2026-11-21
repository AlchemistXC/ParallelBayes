"""Audit existing prospective candidate inputs without sampling or freezing."""
import argparse
import csv
from hashlib import sha256
import json
import platform
from pathlib import Path
import sys

import numpy as np
import scipy
from scipy.special import expit, ndtr

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/prospective_plan'))
from input_transfer import verify


def digest(path):return sha256(path.read_bytes()).hexdigest()


def audit(inputs, archive, archive_sha256, new_preflight, model='both'):
    if model not in ('logistic','ode','both'):raise ValueError('unknown candidate model')
    selected=('logistic','ode') if model=='both' else (model,)
    manifest_path=inputs/'manifest.json';meta=json.loads(manifest_path.read_text())
    if meta.get('scope')!='candidate, not yet frozen or authorized for formal sampling':
        raise ValueError('candidate scope differs')
    for name,key in (('data.npz','data_sha256'),('initials.npz','initials_sha256')):
        if digest(inputs/name)!=meta[key]:raise ValueError(f'{name} checksum differs')
    archive_contents=verify(archive,archive_sha256)
    for name,content in archive_contents.items():
        if content!=(inputs/name).read_bytes():raise ValueError(f'transfer bytes differ: {name}')
    source=ROOT/'scripts/prospective_reference/formal_source/hudson-bay-lynx-hare.csv'
    if 'ode' in selected:
        if digest(source)!=meta['source_sha256']:raise ValueError('ODE source hash differs')
        with source.open() as file:
            rows=list(csv.DictReader((line for line in file if not line.startswith('#')),skipinitialspace=True))
        years=np.array([int(row['Year']) for row in rows]);observed=np.log(np.array(
            [[float(row['Hare']),float(row['Lynx'])] for row in rows]))
    if 'logistic' in selected:
        rng=np.random.default_rng(20261122)
        trials=rng.integers(5,25,size=128);latent=rng.normal(size=128)
        successes=rng.binomial(trials,expit(-.2+.9*latent))
    with np.load(inputs/'data.npz',allow_pickle=False) as data:
        if 'ode' in selected and (not np.array_equal(data['years'],np.arange(1900,1921))
                or not np.array_equal(data['years'],years)
                or not np.array_equal(data['ode_log_observations'],observed)):
            raise ValueError('observed candidate data differ')
        if 'logistic' in selected and (not np.array_equal(data['trials'],trials)
                or not np.array_equal(data['successes'],successes)):
            raise ValueError('observed or regenerated candidate data differ')
    expected_ode=np.array([.55,.028,.8,.024,30.,4.,.25,.25])
    if (('ode' in selected and (not np.allclose(meta['ode']['center'],expected_ode,rtol=0,atol=1e-14)
                                or meta['ode']['prior']!='independent Normal(log(center),0.5) in log coordinates'))
            or ('logistic' in selected and meta['logistic']['prior']!='mu ~ Normal(0,2); log(tau) ~ Normal(0,1); z_j ~ Normal(0,1)')
            or meta['initials']['seed']!=20261123 or meta['initials']['formal_random_stream_seed']!=20261124):
        raise ValueError('candidate prior identity differs')
    strata={}
    with np.load(inputs/'initials.npz',allow_pickle=False) as data:
        for name,center,scale in (('logistic',np.zeros(130),np.r_[2.,1.,np.ones(128)]),
                                  ('ode',np.log(expected_ode),np.full(8,.5))):
            if name not in selected:continue
            q=data[name];alternatives=data[name+'_candidates'];dims=len(center)
            if q.shape!=(10,dims) or alternatives.shape!=(10,4,dims) or not np.array_equal(q,alternatives[:,0,:]):
                raise ValueError(f'{name} initial or candidate shapes differ')
            probability=ndtr((q-center)/scale);candidate_probability=ndtr((alternatives-center)/scale)
            if not np.all((probability>.1)&(probability<.9)) or not np.all((candidate_probability>.1)&(candidate_probability<.9)):
                raise ValueError(f'{name} initial outside central prior interval')
            bins=np.floor((probability-.1)*12.5).astype(int)
            candidate_bins=np.floor((candidate_probability-.1)*12.5).astype(int)
            if (any(not np.array_equal(np.sort(bins[:,j]),np.arange(10)) for j in range(dims))
                    or not np.array_equal(candidate_bins,np.broadcast_to(bins[:,None,:],candidate_bins.shape))):
                raise ValueError(f'{name} strata or candidate bins differ')
            strata[name]={'chains':10,'coordinates':dims,'candidates_per_chain':4,
                          'distinct_initials':len({q[i].tobytes() for i in range(10)})==10}
            if not strata[name]['distinct_initials']:raise ValueError(f'{name} initials repeat')
    preflights=[]
    if (inputs/'preflight.json').resolve()==new_preflight.resolve():
        raise ValueError('fresh preflight must be a separate file')
    for path in (inputs/'preflight.json',new_preflight):
        result=json.loads(path.read_text())
        if (result.get('inputs_manifest_sha256')!=digest(manifest_path)
                or result.get('data_sha256')!=meta['data_sha256'] or result.get('initials_sha256')!=meta['initials_sha256']
                or result.get('formal_sampling_started') is not False):
            raise ValueError('preflight input identity differs')
        for selected_model in selected:
            item=result['checks'][selected_model]
            if item['passed'] is not True or len(item['rows'])!=10:
                raise ValueError(f'{selected_model} preflight failed or incomplete')
            if sorted(row['chain'] for row in item['rows'])!=list(range(1,11)):
                raise ValueError(f'{selected_model} preflight chain identities differ')
            for row in item['rows']:
                limits=(1e-8 if selected_model=='logistic' else 1e-5,1.)
                values=(row['density_delta_error'],row['gradient_max_ratio'])
                if row['finite'] is not True or any(not np.isfinite(x) or x<0 or x>limit for x,limit in zip(values,limits,strict=True)):
                    raise ValueError(f'{selected_model} preflight numerical threshold failed')
        preflights.append({'path':str(path),'sha256':digest(path),
                           'max_gradient_budget':{m:max(row['gradient_max_ratio'] for row in result['checks'][m]['rows']) for m in selected}})
    if 'ode' in selected:
        fixed=json.loads((inputs/'ode-points.json').read_text())
        if fixed.get('manifest_sha256')!=digest(manifest_path) or fixed.get('status')!='passed' or len(fixed.get('results',[]))!=21 or not all(x['passed'] for x in fixed['results']):
            raise ValueError('ODE fixed-point validation identity or coverage differs')
        if sorted(x['index'] for x in fixed['results'])!=list(range(21)):
            raise ValueError('ODE fixed-point identities differ')
        for row in fixed['results']:
            for key,limit in (('state',1e-6),('offset',1e-5),('gradient_budget',1.),('hv_budget',1.),('reference_budget',.1)):
                value=row[key]
                if not np.isfinite(value) or value<0 or value>limit:raise ValueError(f'ODE fixed-point {key} failed')
    return {'scope':'candidate audit only; no freeze or posterior sampling',
            'status':'passed','models':list(selected),'manifest_sha256':digest(manifest_path),'data_sha256':meta['data_sha256'],
            'audit_source_sha256':digest(Path(__file__)),
            'audit_environment':{'python':sys.version,'platform':platform.platform(),
                                 'numpy':np.__version__,'scipy':scipy.__version__},
            'initials_sha256':meta['initials_sha256'],'archive_sha256':archive_sha256,
            'ode_source_sha256':digest(source) if 'ode' in selected else None,'prior_identity_verified':True,
            'actual_data_and_archive_bytes_match':True,'strata':strata,'preflights':preflights,
            'ode_fixed_points':21 if 'ode' in selected else None,
            'ode_fixed_points_sha256':digest(inputs/'ode-points.json') if 'ode' in selected else None,
            'formal_sampling_started':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs',type=Path);parser.add_argument('archive',type=Path)
    parser.add_argument('archive_sha256');parser.add_argument('new_preflight',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--model',choices=('logistic','ode','both'),default='both')
    args=parser.parse_args();result=audit(args.inputs,args.archive,args.archive_sha256,args.new_preflight,args.model)
    with args.output.open('x') as file:json.dump(result,file,indent=2,allow_nan=False);file.write('\n')
