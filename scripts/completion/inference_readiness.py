"""Frozen Mac CPU readiness study for F3, not a formal inference benchmark."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'r-package/inst/python'))
sys.path.insert(0,str(ROOT/'examples'))
sys.path.insert(0,str(ROOT/'scripts/completion'))
from mechanism_runner import identity,sha,plain,write,actual_hash,experiment_lease


def sources():
    old=json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())
    names=list(old['source_files'])+['benchmark/protocols/windows-native-v1.json',
        'examples/affine_target.py','examples/external_wells.py','models/external/wells/source-manifest.json',
        'scripts/completion/inference_setup.py','scripts/completion/inference_nuts.py',
        'scripts/completion/inference_readiness.py','scripts/completion/mechanism_runner.py']
    return {n:sha(ROOT/n) for n in sorted(set(names))}


def freeze(output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    files=sources()
    for name in files:
        data=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        if hashlib.sha256(data).hexdigest()!=files[name]:raise ValueError('Commit scientific source first: '+name)
    old=json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())
    targets=[]
    for name in ['G1','G2','A1','L1','L2','H1','H2','M1','W1']:
        geometry='laplace' if name in ['G2','A1','L1','L2','W1'] else 'identity'
        d=2 if name=='W1' else old['models'][name]['dimension']
        targets.append(dict(name=name,geometry=geometry,dimension=d,
            initial_rule='two chains from independent N(0, 2^2 I) in chosen coordinates; M1 first coordinate fixed -5,+5',
            step_rwm=float(1./np.sqrt(d)),step_mala=float(.1/d**(1/3)),
            role='Numerical and workflow readiness with deliberately untuned generic scales; no final kernel choice'))
    p=dict(identity='inference-readiness-mac-v2',required_platform='darwin',device='cpu',
        predecessor=dict(identity='inference-readiness-mac-v1',protocol_sha256='27eca16723aab5e837f39016aee5f1d6d5658d395e74d6382584b0a38e05f999',
            reason='Replace NumPy affine matmul with explicit einsum after bounded identity-map exception; no suppressed errors or weakened output criteria. Same design and RNG seed namespaces, new source identity.'),
        scope='Development-only custom target, fixed geometry and mature baseline readiness. No accuracy, convergence, tuning-optimality or speed claims.',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_files=files,
        targets=targets,chains=2,mh_draws=64,window=8,max_iter=2048,memory_limit_mb=2048,
        nuts_warmup=256,nuts_draws=256,nuts_tree_depth=8,nuts_target_accept=.8,nuts_full_mass=False,
        torch_threads=1,initial_seed_base=5821000,tape_seed_base=5822000,solver_seed_base=5823000,nuts_seed_base=5824000,
        statistical_repetitions=1,reference_draws_used=False,
        source_data='Historical target specs preserved; W1 uses all eight source-manifest hashes',
        acceptance='Model derivative and MH fixed-array numerical checks. NUTS finite/transform checks are not posterior correctness or convergence proof.',
        timing='CPU setup, NUTS warmup/sample/diagnostics and MH audit/output costs retained; not an efficiency experiment',
        failure='Retain all partial arrays and traceback, skip only failed target dependents, continue other targets. No silent geometry repair or fallback.',
        future='Independent tuning, budgets, repetitions and formal inference protocol remain to be designed; these trajectories never become formal replicates.')
    p['protocol_sha256']=identity(p);output.parent.mkdir(parents=True,exist_ok=True);write(output,p)
    return p


def build_target(name,source):
    if name=='W1':
        from external_wells import load_wells,make_wells,propriety_certificate
        data=load_wells(source)
        if not propriety_certificate(data)['certified']:raise ValueError('W1 integrability certificate unavailable')
        return make_wells(data,'torch','cpu')
    from parallelbayes import make_model
    old=json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())
    return make_model(old['models'][name],backend='torch')


def jsonable(value):
    import torch
    if isinstance(value,torch.Tensor):return plain(value.detach().numpy())
    if isinstance(value,dict):return {k:jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [jsonable(v) for v in value]
    return plain(value)


def save_result(folder,name,result):
    arrays={};meta={}
    for k,v in result.items():
        if isinstance(v,np.ndarray):arrays[k]=v
        elif k=='partial_chains':
            for chain in v:
                for key in ('warmup','sample','warmup_step_size','sample_step_size'):
                    arrays[f'chain{chain["chain"]}_{key}']=np.asarray(chain[key])
            meta['partial_chains_saved_separately']=len(v)
        else:meta[k]=jsonable(v)
    np.savez_compressed(folder/(name+'.npz'),**arrays)
    write(folder/(name+'.json'),meta)


def run(protocol,source,output,resume=False):
    import torch
    from parallelbayes import validate_model,sample
    from parallelbayes.torch_backend.sampling import settings,random_tape
    from affine_target import affine_model
    from inference_setup import prepare_geometry
    from inference_nuts import sample_nuts
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);expected=unsigned.pop('protocol_sha256')
    if identity(unsigned)!=expected:raise ValueError('Protocol checksum differs')
    if sys.platform!=p['required_platform']:raise ValueError('A new platform needs its own readiness identity')
    for name,digest in p['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Source changed: '+name)
    torch.set_num_threads(p['torch_threads'])
    runtime=dict(python=platform.python_version(),platform=platform.platform(),machine=platform.machine(),
        packages=dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())),
        torch_threads=torch.get_num_threads(),protocol_sha256=expected)
    out=Path(output)
    if out.exists():
        if not resume:raise FileExistsError('Use explicit resume')
        if json.loads((out/'runtime.json').read_text())!=runtime:raise ValueError('Resume runtime differs')
    else:out.mkdir(parents=True);write(out/'runtime.json',runtime)
    all_states=[]
    with experiment_lease(out):
        for index,item in enumerate(p['targets']):
            folder=out/item['name'];statefile=folder/'state.json'
            if statefile.exists():
                state=json.loads(statefile.read_text())
                for name,digest in state['assets'].items():
                    if sha(folder/name)!=digest:raise ValueError('Terminal checksum mismatch: '+name)
                all_states.append(state);continue
            folder.mkdir(exist_ok=True);attempt=folder/('attempt-'+str(time.time_ns()));attempt.mkdir()
            state=dict(target=item['name'],status='started',attempt=attempt.name)
            write(attempt/'started.json',dict(protocol_sha256=expected,target=item))
            try:
                begin=time.perf_counter();base=build_target(item['name'],source)
                state['target_setup_seconds']=time.perf_counter()-begin
                geometry=prepare_geometry(base,item['geometry']);write(attempt/'geometry.json',geometry)
                model=affine_model(base,geometry['center'],geometry['factor'])
                state.update(base_target_id=base.target_id,coordinate_target_id=model.target_id)
                rng=np.random.Generator(np.random.Philox(p['initial_seed_base']+index))
                initial=2*rng.standard_normal((p['chains'],base.dimension))
                if item['name']=='M1':initial[:,0]=[-5.,5.]
                points=np.vstack((np.zeros(base.dimension),initial,np.full(base.dimension,.25),np.full(base.dimension,-.25)))
                check=validate_model(model,points,backend='torch');write(attempt/'target-check.json',check)
                if not check['passed']:raise ValueError('Target derivative check failed')
                np.savez_compressed(attempt/'coordinates.npz',initial=initial,validation_points=points)
                c=settings(dict(chains=p['chains'],draws=p['mh_draws'],device='cpu',initial=initial.tolist(),
                    window=p['window'],max_iter=p['max_iter'],memory_limit_mb=p['memory_limit_mb'],
                    seed=p['tape_seed_base']+index,solver_seed=p['solver_seed_base']+index))
                tape=random_tape(c,base.dimension);np.savez_compressed(attempt/'mh-inputs.npz',**tape)
                state['tape_sha256']=actual_hash(tape);state['workflows']={}
                for kernel,executors in [('rwm',['sequential','online_picard']),('mala',['sequential','quasi_deer'])]:
                    for executor in executors:
                        name=kernel+'-'+executor
                        result=sample(model,dict(c,kernel=kernel,executor=executor,step_size=item['step_'+kernel]),tape,backend='torch')
                        save_result(attempt,name,result)
                        state['workflows'][name]=dict(status=result['status'],audit=result['audit'],
                            acceptance_rate=float(np.mean(result['accept'])))
                result=sample_nuts(model,initial,[p['nuts_seed_base']+index*10+i for i in range(p['chains'])],
                    draws=p['nuts_draws'],warmup=p['nuts_warmup'],max_tree_depth=p['nuts_tree_depth'],
                    target_accept_prob=p['nuts_target_accept'],full_mass=p['nuts_full_mass'],memory_limit_mb=p['memory_limit_mb'])
                save_result(attempt,'nuts-cpu',result)
                state['workflows']['nuts-cpu']=dict(status=result['status'],diagnostics=[r['diagnostics'] for r in result['chain_records']])
                state['status']='completed' if all(r['status']=='completed' for r in state['workflows'].values()) else 'failed'
            except Exception as exc:
                state.update(status='failed',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
            state=jsonable(state)
            state['assets']={str(f.relative_to(folder)):sha(f) for f in sorted(attempt.iterdir()) if f.is_file()}
            temporary=folder/'state.tmp';write(temporary,state);temporary.replace(statefile)
            all_states.append(state)
            print(json.dumps(dict(target=state['target'],status=state['status'])),flush=True)
        summary=dict(protocol_sha256=expected,targets=len(all_states),completed=sum(s['status']=='completed' for s in all_states),
            failed=sum(s['status']=='failed' for s in all_states),
            workflows_completed=sum(r['status']=='completed' for s in all_states for r in s.get('workflows',{}).values()),
            workflows_planned=len(p['targets'])*5,
            scope=p['scope'],formal_inference_complete=False)
        write(out/'summary.json',summary)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');f.add_argument('--output',type=Path,required=True)
    r=sub.add_parser('run');r.add_argument('--protocol',type=Path,required=True);r.add_argument('--source',type=Path,required=True)
    r.add_argument('--output',type=Path,required=True);r.add_argument('--resume',action='store_true')
    a=parser.parse_args()
    result=freeze(a.output) if a.action=='freeze' else run(a.protocol,a.source,a.output,a.resume)
    print(json.dumps(result,indent=2))
