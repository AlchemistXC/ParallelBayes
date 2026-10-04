"""Independent CPU budget pilot; no automatic formal-study or speed claim.

Each budget is timed as a complete separate fit. Actual MH input prefixes and
NUTS chain seeds are shared across budgets within a development repetition.
Four-chain repetitions, not budgets/chains/draws, are the independent units.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'r-package/inst/python'),str(ROOT/'examples'),str(ROOT/'scripts/completion')]
from mechanism_runner import identity,sha,write,actual_hash,experiment_lease
from inference_readiness import build_target,save_result
from inference_tuning import source_files as tuning_sources


def source_files():
    files=tuning_sources()
    for n in ['scripts/completion/inference_budget_pilot.py','scripts/completion/inference_parallel_nuts.py',
              'scripts/completion/inference_estimands.py','benchmark/protocols/inference-tuning-mac-v1.json',
              'benchmark/analysis/outputs/inference-tuning-v1/analysis/selections.json',
              'benchmark/analysis/outputs/completion-f3/reference-reuse.json',
              'benchmark/analysis/outputs/wells-quadrature-v1/result.json',
              'benchmark/analysis/outputs/wells-quadrature-v1/R12-n96.json',
              'benchmark/analysis/outputs/wells-quadrature-v1/comparison.json']:
        files[n]=sha(ROOT/n)
    return dict(sorted(files.items()))


def input_payload(p,item,rep):
    from parallelbayes.torch_backend.sampling import settings,random_tape
    offset=100*p['targets'].index(item)+rep
    config=settings(dict(chains=p['chains'],draws=p['mh_warmup']+max(p['budgets']),
        seed=p['tape_seed_base']+offset,solver_seed=p['solver_seed_base']+offset))
    payload=random_tape(config,item['dimension'])
    rng=np.random.Generator(np.random.Philox(p['initial_seed_base']+offset))
    initial=2*rng.standard_normal((p['chains'],item['dimension']))
    if item['name']=='M1':initial[:,0]=[-5.,5.,-5.,5.]
    payload.update(initial=initial,nuts_seeds=np.asarray([p['nuts_seed_base']+offset*10+i for i in range(p['chains'])],dtype=np.int64))
    return payload


def freeze(protocol,inputs,tuning_run):
    protocol,inputs,tuning_run=Path(protocol),Path(inputs),Path(tuning_run)
    if protocol.exists() or inputs.exists():raise FileExistsError('Fresh frozen protocol and inputs required')
    sources=source_files()
    for name,h in sources.items():
        if hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()!=h:
            raise ValueError('Commit scientific source first: '+name)
    tuning=json.loads((ROOT/'benchmark/protocols/inference-tuning-mac-v1.json').read_text())
    selections=json.loads((ROOT/'benchmark/analysis/outputs/inference-tuning-v1/analysis/selections.json').read_text())
    if selections['original_protocol_sha256']!=tuning['protocol_sha256']:raise ValueError('Development identity mismatch')
    targets=[]
    for item in tuning['targets']:
        setup_path=tuning_run/item['name']/'setup.json';setup=json.loads(setup_path.read_text())
        unsigned=dict(setup);h=unsigned.pop('setup_sha256')
        if identity(unsigned)!=h or setup['protocol_sha256']!=tuning['protocol_sha256']:
            raise ValueError('Development geometry checksum differs')
        selected={s['kernel']:s['selected_step'] for s in selections['selections'] if s['model']==item['name']}
        if set(selected)!=set(['rwm','mala']) or any(s is None or not np.isfinite(s) or s<=0 for s in selected.values()):
            raise ValueError('Every target needs a declared valid within-grid choice')
        targets.append(dict(name=item['name'],dimension=item['dimension'],geometry=setup['geometry'],
            base_target_id=setup['base_target_id'],development_setup_file_sha256=sha(setup_path),
            step_rwm=selected['rwm'],step_mala=selected['mala']))
    p=dict(identity='inference-budget-pilot-mac-v1',required_platform='darwin',device='cpu',torch_threads=4,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_files=sources,
        targets=targets,chains=4,mh_warmup=512,budgets=[256,1024,4096],replicates=[0,1,2,3],
        nuts_warmup=1024,nuts_tree_depth=8,nuts_target_accept=.8,nuts_full_mass=False,nuts_workers=4,nuts_threads=1,
        window=8,max_iter=2048,memory_limit_mb=2048,
        initial_seed_base=7361000,tape_seed_base=7362000,solver_seed_base=7363000,nuts_seed_base=7364000,order_seed=7365000,
        independent_unit='One complete four-chain experiment per model and repetition; four independent repetitions. Budgets and workflows are paired within repetition and do not increase n.',
        scope='Independent budget development, baseline coverage and reference-error planning. Not formal inference or performance comparison.',
        pilot_not_formal=True,formal_inference_complete=False,
        geometry='Reuse exact fixed development geometry; no adaptation of MH or reference-draw access. Initial geometry/tuning costs remain in predecessor evidence, not hidden as zero.',
        initialization='Independent N(0,4I) in frozen coordinates; M1 first coordinate fixed -5,+5,-5,+5. This does not prove cross-mode exploration.',
        seeds='New independent namespace. Actual MH arrays archived, shared prefixes across budgets/kernels. NUTS uses explicit per-chain seeds and archives initial/final actual RNG states; no MH/NUTS path-equivalence claim.',
        methods='sequential RWM, sequential MALA and mature Pyro CPU NUTS with true spawn processes. Time-executor performance belongs to separately frozen Windows work.',
        timing='Every budget is a fresh complete fit, including discarded/adaptation phase and all NUTS process startup/IPC/shutdown. MH audit, archival and task wall are recorded. No fresh-parent-process cold-start or exclusive-core claim.',
        resources='MH one process with four torch intraop threads; NUTS up to four processes with one intraop and one interop thread each. Same host, no assertion of exclusive or exactly utilized cores.',
        failures='Every planned task retained. Full MH fixed-path audit, not reanchored per-step checks; failures produce no ordinary samples. No implicit fallback, redrawn inputs or post hoc deletion. Partial NUTS children preserved on overall failure.',
        analysis='Historical original-parameter estimands plus seven wells functions. Report all failures and undefined diagnostics; successful-only error summaries explicitly conditional. Propagate/qualify finite-reference uncertainty; L2 event remains unresolved. No precision guarantee from pilot n=4.',
        error_scale='Historical functions retain their original definitions and scaling; no normalization by short-chain estimated variance. Report per-function squared discrepancy and within-target maximum; no cross-model metric ranking.',
        references='Analytic expectations for Gaussian/funnel/mixture; audited finite reference and conservative MCSE for L1/L2, preserving unresolved L2 sign event; wells R12/n96 quadrature with grid/tail and finite-MCMC comparisons, not certified exact truth. Reference source files are hashed above.',
        next_design='Use independent pilot variability, diagnostics and failure rates to choose a finite formal protocol before observing formal outputs; keep old negative results and weak choices such as H1 boundary candidate.',
        development_protocol_sha256=tuning['protocol_sha256'],master_inputs={},tasks=[])
    inputs.mkdir(parents=True)
    for item in targets:
        for rep in p['replicates']:
            name=f"{item['name']}-rep{rep}.npz";payload=input_payload(p,item,rep)
            np.savez_compressed(inputs/name,**payload)
            p['master_inputs'][name]=dict(sha256=sha(inputs/name),actual_sha256=actual_hash(payload))
    order=np.random.default_rng(p['order_seed'])
    for budget in p['budgets']:
        for rep in p['replicates']:
            for index in order.permutation(len(targets)):
                item=targets[index]
                for workflow in order.permutation(['rwm','mala','nuts']):
                    task=dict(model=item['name'],workflow=str(workflow),replicate=rep,budget=budget,input=f"{item['name']}-rep{rep}.npz")
                    task['id']=identity(task)[:20];p['tasks'].append(task)
    p['protocol_sha256']=identity(p);protocol.parent.mkdir(parents=True,exist_ok=True);write(protocol,p)
    return dict(protocol_sha256=p['protocol_sha256'],tasks=len(p['tasks']),master_inputs=len(p['master_inputs']),source_commit=p['source_commit'])


def validate(protocol,inputs):
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if identity(unsigned)!=digest:raise ValueError('Protocol checksum differs')
    if sys.platform!=p['required_platform']:raise ValueError('A new platform needs its own protocol')
    for name,h in p['source_files'].items():
        if sha(ROOT/name)!=h:raise ValueError('Frozen source changed: '+name)
    for name,row in p['master_inputs'].items():
        if sha(Path(inputs)/name)!=row['sha256']:raise ValueError('Actual input checksum differs')
        with np.load(Path(inputs)/name,allow_pickle=False) as z:
            if actual_hash(dict(z))!=row['actual_sha256']:raise ValueError('Actual input arrays differ')
    if len({x['id'] for x in p['tasks']})!=len(p['tasks']):raise ValueError('Duplicate task identity')
    return p


def save_parallel(folder,result):
    """Avoid duplicating valid full paths in JSON; preserve partial children."""
    aggregate=dict(result);records=[]
    for worker in result['worker_records']:
        item={k:v for k,v in worker.items() if k!='result'}
        child=folder/('worker-'+str(worker['chain']));child.mkdir()
        value=worker['result']
        if result['status']=='completed':
            # Full states/RNG are in the aggregate NPZ. Adaptation traces and
            # per-chain diagnostics remain independently inspectable here.
            meta={k:v for k,v in value.items() if not isinstance(v,np.ndarray) and k!='partial_chains'}
            steps={}
            for trace in value['partial_chains']:
                for key in ['warmup_step_size','sample_step_size']:
                    steps[key]=np.asarray(trace[key])
            np.savez_compressed(child/'adaptation.npz',**steps)
            write(child/'metadata.json',meta)
        else:
            save_result(child,'partial-fit',value)
        item['result_directory']=child.name;records.append(item)
    aggregate['worker_records']=records
    save_result(folder,'fit',aggregate)


def run(protocol,inputs,source,output,resume=False):
    import torch
    import psutil
    from parallelbayes.torch_backend.sampling import sample
    from affine_target import affine_model
    from inference_parallel_nuts import sample_parallel_nuts
    p=validate(protocol,inputs);inputs=Path(inputs);out=Path(output)
    torch.set_num_threads(p['torch_threads'])
    runtime=dict(protocol_sha256=p['protocol_sha256'],python=platform.python_version(),platform=platform.platform(),
        machine=platform.machine(),torch_threads=torch.get_num_threads(),torch_interop_threads=torch.get_num_interop_threads(),
        cpu_logical=psutil.cpu_count(),cpu_physical=psutil.cpu_count(logical=False),ram_bytes=psutil.virtual_memory().total,
        thread_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS']},
        packages=dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())))
    if out.exists():
        if not resume:raise FileExistsError('Use explicit resume')
        if json.loads((out/'runtime.json').read_text())!=runtime:raise ValueError('Resume runtime differs')
    else:out.mkdir(parents=True);write(out/'runtime.json',runtime)
    models={};states=[];began=time.perf_counter();invocation_id=str(time.time_ns());new=0
    with experiment_lease(out):
        for task in p['tasks']:
            item=next(i for i in p['targets'] if i['name']==task['model'])
            folder=out/task['model']/task['id'];statefile=folder/'state.json'
            if statefile.exists():
                state=json.loads(statefile.read_text())
                if state['task']!=task or state['protocol_sha256']!=p['protocol_sha256']:
                    raise ValueError('Task identity mismatch')
                for name,h in state['assets'].items():
                    if sha(folder/name)!=h:raise ValueError('Terminal asset checksum differs: '+name)
                if state['status'] not in ['completed','failed']:raise ValueError('Nonterminal state file')
                states.append(state);continue
            folder.mkdir(parents=True,exist_ok=True);attempt=folder/('attempt-'+str(time.time_ns()));attempt.mkdir()
            state=dict(task=task,protocol_sha256=p['protocol_sha256'],status='started',attempt=attempt.name,
                master_input=p['master_inputs'][task['input']],discarded_draws_per_chain=p['mh_warmup'] if task['workflow']!='nuts' else 0,
                nuts_warmup_per_chain=p['nuts_warmup'] if task['workflow']=='nuts' else 0)
            write(attempt/'started.json',state);start=time.perf_counter()
            print(json.dumps(dict(starting=len(states)+1,total=len(p['tasks']),task=task)),flush=True)
            try:
                setup_start=time.perf_counter()
                if task['model'] not in models:
                    base=build_target(task['model'],source)
                    if base.target_id!=item['base_target_id']:raise ValueError('Base target identity mismatch')
                    g=item['geometry'];models[task['model']]=affine_model(base,g['center'],g['factor'])
                model=models[task['model']];state['target_setup_seconds']=time.perf_counter()-setup_start
                state['target_id']=model.target_id
                with np.load(inputs/task['input'],allow_pickle=False) as z:payload={k:z[k].copy() for k in z.files}
                initial=payload.pop('initial');seeds=payload.pop('nuts_seeds').tolist()
                if task['workflow']=='nuts':
                    result=sample_parallel_nuts(model.spec,model.target_id,initial,seeds,
                        workers=p['nuts_workers'],threads_per_worker=p['nuts_threads'],draws=task['budget'],
                        warmup=p['nuts_warmup'],max_tree_depth=p['nuts_tree_depth'],
                        target_accept_prob=p['nuts_target_accept'],full_mass=p['nuts_full_mass'],memory_limit_mb=p['memory_limit_mb'])
                    save_parallel(attempt,result)
                    state['observed_worker_count']=len(result['observed_worker_pids'])
                    state['observed_worker_pids']=result['observed_worker_pids']
                    state['pool_wall_seconds']=result['timing']['pool_wall']
                else:
                    n=p['mh_warmup']+task['budget'];tape={k:v[:,:n].copy() for k,v in payload.items()}
                    config=dict(kernel=task['workflow'],executor='sequential',device='cpu',chains=p['chains'],draws=n,
                        initial=initial.tolist(),step_size=item['step_'+task['workflow']],window=p['window'],
                        max_iter=p['max_iter'],memory_limit_mb=p['memory_limit_mb'],on_failure='error',audit=True)
                    result=sample(model,config,tape);save_result(attempt,'fit',result)
                    state['actual_tape_sha256']=result['tape_sha256'];state['audit']=result['audit']
                state['status']=result['status'];state['result_timing']=result['timing']
            except Exception as exc:
                state.update(status='failed',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
                write(attempt/'failure.json',dict(error=state['error'],traceback=state['traceback']))
            state['whole_task_seconds_including_archive']=time.perf_counter()-start
            state['assets']={f.relative_to(folder).as_posix():sha(f) for f in sorted(attempt.rglob('*')) if f.is_file()}
            write(folder/'state.tmp',state);(folder/'state.tmp').replace(statefile)
            states.append(state);new+=1
            print(json.dumps(dict(done=len(states),total=len(p['tasks']),model=task['model'],workflow=task['workflow'],
                budget=task['budget'],replicate=task['replicate'],status=state['status'],seconds=state['whole_task_seconds_including_archive'])),flush=True)
        summary=dict(protocol_sha256=p['protocol_sha256'],planned=len(p['tasks']),terminal=len(states),
            completed=sum(s['status']=='completed' for s in states),failed=sum(s['status']=='failed' for s in states),
            newly_executed_tasks=new,all_task_seconds=sum(s['whole_task_seconds_including_archive'] for s in states),
            invocation_seconds=time.perf_counter()-began,scope=p['scope'],formal_inference_complete=False)
        invocations=out/'invocations';invocations.mkdir(exist_ok=True)
        write(invocations/(invocation_id+'.json'),dict(summary,resume=resume));write(out/'summary.json',summary)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze')
    for name in ['protocol','inputs','tuning-run']:f.add_argument('--'+name,type=Path,required=True)
    r=sub.add_parser('run')
    for name in ['protocol','inputs','source','output']:r.add_argument('--'+name,type=Path,required=True)
    r.add_argument('--resume',action='store_true');a=parser.parse_args()
    result=freeze(a.protocol,a.inputs,a.tuning_run) if a.action=='freeze' else run(a.protocol,a.inputs,a.source,a.output,a.resume)
    print(json.dumps(result,indent=2))
