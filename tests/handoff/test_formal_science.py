"""Artificial v2 lifecycle around real NumPy/R arrays; no Windows execution."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'tests/handoff'),str(ROOT/'scripts/completion')]
from formal_science import ScientificReader, _defaults, compare
from test_formal_native_evidence import Fixture
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_inputs import build_payload
from mechanism_runner import actual_hash
from batch_contract import create_tasks,mh_config
from formal_streaming import extract_functions
from parallelbayes.reference import make_reference,numpy_reference
from affine_target import affine_model
from replay_windows_followup import tape_hash
from task_journal import TaskJournal
from formal_measurement_plan import POLICY,summarize_probe

RSCRIPT=os.environ.get('PB_READER_RSCRIPT') or shutil.which('Rscript')
RLIB=os.environ.get('PB_READER_RLIB',os.environ.get('R_LIBS_USER',''))


def reseal(f, p):
    state=json.loads((p/'state.json').read_text())
    state.update(worker_result=json.loads((p/'worker-result.json').read_text()),binding_sha256=fingerprint(f.binding))
    atomic_json(p/'binding.json',f.binding);atomic_json(p/'request.json',f.binding['request'])
    state['assets']={x.relative_to(p).as_posix():file_hash(x) for x in p.rglob('*') if x.is_file() and x.name not in ('state.json','completion.json')}
    atomic_json(p/'state.json',state);atomic_json(p/'completion.json',dict(state_sha256=file_hash(p/'state.json')))
    number=len(list(f.root.glob('science-history-*.json')))
    dest=f.root/f'science-history-{number}.json'
    with TaskJournal(f.base/f'science-journal-{number}',f.identity) as journal:
        key=TaskJournal.key(f.task);journal.save(key,f.entry,'artificial-scientific-files');journal.export(key,dest)
    f.history=dest.name


@pytest.fixture(scope='module')
def specimen(tmp_path_factory):
    assert RSCRIPT,'Set PB_READER_RSCRIPT to an installed Rscript with posterior and jsonlite'
    base=tmp_path_factory.mktemp('scientific-files');f=Fixture(base)
    required=('r-package/inst/python/parallelbayes/reference.py','examples/affine_target.py',
        'r-package/inst/python/parallelbayes/torch_backend/sampling.py','scripts/completion/inference_estimands.py',
        'scripts/completion/posterior_diagnostics.R','benchmark/protocols/windows-native-v1.json')
    f.sources={n:file_hash(ROOT/n) for n in set(f.sources)|set(required)}
    for field,name in [('worker_sha256','scripts/windows/formal_batch_worker.py'),
                       ('runtime_sha256','scripts/windows/formal_owned_runtime.py'),
                       ('journal_sha256','scripts/completion/task_journal.py'),
                       ('job_api_sha256','scripts/windows/job_objects.py')]:
        f.binding[field]=f.sources[name]
    for n in f.sources:
        dest=f.root/'source'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest)
    item=next(t for t in json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())['targets'] if t['name']=='G1')
    identity='formal-science-reader-artificial-files-v1'
    task=create_tasks(identity,[dict(models=['G1'],replicates=[0],budgets=[16],workflows=['cpu-rwm-sequential'])])[0]
    values=build_payload(identity,'G1',0,item['dimension'],20)
    (f.root/'inputs').mkdir();np.savez_compressed(f.root/'inputs'/task['input'],**values)
    ctrl=dict(chains=4,mh_discard=4,nuts_warmup=8,nuts_tree_depth=8,nuts_workers=4,nuts_threads=1,
        torch_threads=4,window=4,quasi_deer_max_iter=2048,memory_limit_mb=2048,maximum_member_bytes=128*1024**2,
        atol=1e-10,rtol=1e-10,nuts_target_accept=.8,nuts_full_mass=False)
    c=dict(schema=1,identity=identity,scope_kind='technical_batch_validation',required_platform='win32',
        source_commit='f'*40,source_files=f.sources,required_versions={},required_R_version='pending',required_R_posterior='pending',
        controls=ctrl,cost_policy='fixture',process_tree_rss_limit_bytes=1024,required_disk_bytes_per_task=1024,
        protocol_sha256='a'*64,task=task,target=item,input=dict(model='G1',replicate=0,chains=4,steps=20,
            dimension=item['dimension'],sha256=file_hash(f.root/'inputs'/task['input']),actual_sha256=actual_hash(values)))
    spec=json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())['models']['G1']
    model=affine_model(make_reference(spec),item['geometry']['center'],item['geometry']['factor'])
    config=dict(_defaults(ROOT/'r-package/inst/python/parallelbayes/torch_backend/sampling.py'),**mh_config(c,values['initial'].tolist()))
    refs=[numpy_reference(model,'rwm',values['initial'][i],values['noise'][i],values['log_uniform'][i],config['step_size']) for i in range(4)]
    q=np.stack([r[0] for r in refs]);accept=np.stack([r[1] for r in refs])
    f.task.update(task,protocol_sha256=c['protocol_sha256']);f.binding['request']={}
    p=f.add();np.savez_compressed(p/'fit.npz',unconstrained=q,draws=model.constrain(q),accept=accept)
    extract=extract_functions(p/'fit.npz',file_hash(p/'fit.npz'),model,q.shape,4,p/'diagnostics')
    atomic_json(p/'diagnostics/estimates.json',dict(names=extract['names'],means=extract['means']))
    atomic_json(p/'diagnostics/transport.json',dict(fits=[dict(id=task['id'],input='functions.bin',shape=extract['shape'],names=extract['names'])],
        scope='Artificial reader fixture, not Windows execution',independent_unit='No scientific repetitions'))
    result=subprocess.run([RSCRIPT,'--vanilla',str(ROOT/'scripts/completion/posterior_diagnostics.R'),str(p/'diagnostics')],
        env=dict(os.environ,R_LIBS_USER=RLIB),capture_output=True,text=True)
    (base/'fixture-R.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stderr
    post=json.loads((p/'diagnostics/posterior.json').read_text());c['required_R_version']=post['R'];c['required_R_posterior']=post['posterior']
    digest=fingerprint(c);f.binding['request']=dict(capsule=c,capsule_sha256=digest,phase='main')
    audit=dict(passed=True,acceptance_mismatches=[0]*4)
    meta=dict(status='completed',target_id=model.target_id,config=config,tape_sha256=tape_hash({k:values[k] for k in ('noise','log_uniform','directions')}),
        audit=audit,diagnostics=dict(tensor_device='cpu',tensor_dtype='torch.float64'),timing={'fixture_only':True})
    atomic_json(p/'candidate.json',meta)
    decision=dict(status='completed',samples_eligible=True,audit=audit,failure_category=None)
    atomic_json(p/'external-audit.json',decision)
    meta.update(ordinary_candidate_arrays_sha256=file_hash(p/'fit.npz'),ordinary_candidate_metadata_sha256=file_hash(p/'candidate.json'),external_audit=decision)
    atomic_json(p/'fit.json',meta)
    worker=dict(status='completed',samples_eligible=True,measurement_available=False,artifact_kind='posterior',
        task=task,target_id=model.target_id,protocol_sha256=c['protocol_sha256'],capsule_sha256=digest,
        full_MH_audit=audit,diagnostics_status='completed')
    atomic_json(p/'worker-result.json',worker);reseal(f,p);f.ledger([(3.,'attempt-0001',True),(.25,'attempt-0001',False)])
    return f,c,model,values


def copy_fixture(specimen,tmp_path):
    original,c,model,values=specimen;f=copy.deepcopy(original);f.base=tmp_path;f.root=tmp_path/'relocated'
    shutil.copytree(original.root,f.root)
    return f,copy.deepcopy(c),model,values


def read(f,c,tmp_path):
    reader=ScientificReader(f.root,f.sources,rscript=RSCRIPT,r_library=RLIB)
    return reader.read(dict(task=f.task,capsule=c,capsule_sha256=fingerprint(c),probe=None),
        history_export=f.history,directory='task',ledger='ledger',manifest=f.manifest(),output=tmp_path/'analysis')


def test_actual_arrays_and_R_rebuild_after_relocation(specimen,tmp_path):
    f,c,_,_=copy_fixture(specimen,tmp_path);before=f.manifest();r=read(f,c,tmp_path)
    assert r['outcome']=='valid' and r['function_status']=='completed'
    assert r['independent_replay']['passed'] and r['independent_replay']['acceptance_mismatches']==[0]*4
    assert r['receiver_diagnostics_comparison']['exact'] and r['means']==r['receiver_means']
    assert r['history']['costs']['phases']['research_execution']['complete_seconds']==3.
    assert r['history']['costs']['phases']['additional_verification']['complete_seconds']==.25
    assert f.manifest()==before and 'torch' not in sys.modules and 'jax' not in sys.modules


@pytest.mark.parametrize('change',['accept','transform','tape','device'])
def test_rehashed_scientific_faults_cannot_pass_saved_success(specimen,tmp_path,change):
    f,c,_,_=copy_fixture(specimen,tmp_path);p=f.root/'task/attempt-0001'
    meta=json.loads((p/'fit.json').read_text())
    if change in ('accept','transform'):
        with np.load(p/'fit.npz') as z: arrays={k:z[k] for k in z.files}
        if change=='accept': arrays['accept'][0,0]=not arrays['accept'][0,0]
        else: arrays['draws'][0,0,0]+=1.
        np.savez_compressed(p/'fit.npz',**arrays);meta['ordinary_candidate_arrays_sha256']=file_hash(p/'fit.npz')
    elif change=='tape': meta['tape_sha256']='e'*64
    else: meta['diagnostics']['tensor_device']='cuda:0'
    atomic_json(p/'fit.json',meta);reseal(f,p)
    with pytest.raises((ValueError,AssertionError)):read(f,c,tmp_path)
    receipt=json.loads((tmp_path/'analysis/READER-FAILURE.json').read_text())
    assert receipt['recorded_outcome']=='valid' and receipt['original_outcome_reclassified'] is False
    assert not (tmp_path/'analysis/result.json').exists()


def test_failed_output_retains_cost_and_never_extracts_samples(specimen,tmp_path):
    f,c,_,_=copy_fixture(specimen,tmp_path);p=f.root/'task/attempt-0001'
    f.entry['attempts'][0]['outcome']='numerical_failure'
    worker=json.loads((p/'worker-result.json').read_text());worker.update(status='failed',samples_eligible=False,failure_category='numerical_failure')
    atomic_json(p/'worker-result.json',worker)
    state=json.loads((p/'state.json').read_text());state.update(status='failed',outcome='numerical_failure',samples_eligible=False,exit_code=1)
    atomic_json(p/'state.json',state);reseal(f,p)
    for path in (f.root/'ledger').glob('call-*/finished.json'):
        doc=json.loads(path.read_text());doc.pop('receipt_sha256');doc['result']['outcome']='numerical_failure';atomic_json(path,dict(doc,receipt_sha256=fingerprint(doc)))
    r=read(f,c,tmp_path)
    assert r['outcome']=='numerical_failure' and r['means'] is None and not (tmp_path/'analysis/functions').exists()
    assert r['history']['costs']['phases']['research_execution']['known_seconds']==3.


def test_task_binding_and_source_change_refused_before_analysis(specimen,tmp_path):
    f,c,_,_=copy_fixture(specimen,tmp_path);c['target']['step_rwm']*=2
    with pytest.raises(ValueError,match='capsule'):read(f,c,tmp_path)
    assert not (tmp_path/'analysis').exists()
    (f.root/'source/examples/affine_target.py').write_text('altered')
    with pytest.raises(ValueError,match='Archived source'):ScientificReader(f.root,f.sources,rscript=RSCRIPT,r_library=RLIB)


def test_missing_diagnostics_and_constant_values_are_not_ideal_convergence():
    assert compare([{'rhat':None,'ess_tail':None}],[{'rhat':None,'ess_tail':None}],1e-10,1e-10)['passed']
    assert not compare([{'rhat':None}],[{'rhat':1.}],1e-10,1e-10)['passed']
    assert not compare([float('nan')],[float('nan')],1e-10,1e-10)['passed']


@pytest.mark.parametrize('partial',[False,True])
def test_cached_replays_remain_measurements_and_partial_cost_survives(specimen,tmp_path,partial):
    f,c,model,values=copy_fixture(specimen,tmp_path)
    old=f.root/'task/attempt-0001'
    with np.load(old/'fit.npz') as z:q=z['unconstrained'];a=z['accept']
    probe=dict(c['task']);probe['primary_task_id']=probe.pop('id')
    probe.update(initial_calls=1,prepared_replays=3,samples_eligible=False,primary_outcome_is_selection_criterion=False)
    probe['id']=fingerprint(dict(policy=POLICY,identity=c['identity'],probe=probe))[:24]
    f.task.update(id=probe['id'],artifact_kind='cache_measurement');f.binding['worker_sha256']=f.sources['scripts/windows/formal_cache_worker.py']
    f.binding['request']=dict(capsule=c,capsule_sha256=fingerprint(c),phase='cache',probe=probe)
    shutil.rmtree(f.root/'task');f.entry['attempts']=[]
    outcome='infrastructure_interruption' if partial else 'measurement_available'
    p=f.add(outcome);cache=p/'cache';cache.mkdir()
    config=dict(_defaults(ROOT/'r-package/inst/python/parallelbayes/torch_backend/sampling.py'),**mh_config(c,values['initial'].tolist()))
    binding=dict(input_file_sha256=c['input']['sha256'],tape_sha256=tape_hash({k:values[k] for k in ('noise','log_uniform','directions')}),target_id=model.target_id,config=config)
    atomic_json(cache/'request.json',dict(capsule=c,capsule_sha256=fingerprint(c),probe=probe));atomic_json(cache/'binding.json',binding)
    records=[None]*4;states=['not_run']*4
    for i in range(1 if partial else 4):
        np.savez_compressed(cache/f'execution-{i}.npz',unconstrained=q,accept=a)
        record=dict(execution_index=i,has_prior_execution=i>0,target_id=model.target_id,tape_sha256=binding['tape_sha256'],config=config,
            status='candidate',samples_eligible=False,technical_output_valid=True,executor_wall_seconds=.1*(i+1),
            actual_array_file=f'execution-{i}.npz',actual_array_sha256=file_hash(cache/f'execution-{i}.npz'),
            audit=dict(passed=True,acceptance_mismatches=[0]*4),diagnostics=dict(tensor_device='cpu',tensor_dtype='torch.float64'))
        records[i]=record;states[i]='valid'
        atomic_json(cache/f'execution-{i}.started.json',dict(execution_index=i,probe_id=probe['id']))
        atomic_json(cache/f'execution-{i}.json',record)
    if partial:
        atomic_json(cache/'execution-1.started.json',dict(execution_index=1,probe_id=probe['id']))
        # Closed owned interruption without a completed numerical worker.
        atomic_json(p/'worker-result.json',dict(status='failed',samples_eligible=False,measurement_available=False,artifact_kind='cache_measurement'))
    else:
        summary=summarize_probe(probe,records,expected_tape_sha256=binding['tape_sha256'],expected_target_id=model.target_id,expected_config=config)
        atomic_json(cache/'cache-result.json',dict(artifact_kind='cache_measurement',samples_eligible=False,probe=probe,binding=binding,
            observation=dict(records=records,execution_outcomes=states),summary=summary,measurement_available=True,status='completed'))
        atomic_json(cache/'MANIFEST.json',{x.name:file_hash(x) for x in cache.iterdir() if x.is_file()})
    reseal(f,p);shutil.rmtree(f.root/'ledger');f.ledger([(3.,'attempt-0001',True)])
    reader=ScientificReader(f.root,f.sources,rscript=RSCRIPT,r_library=RLIB)
    r=reader.read(dict(task=f.task,capsule=c,capsule_sha256=fingerprint(c),probe=probe),history_export=f.history,
        directory='task',ledger='ledger',manifest=f.manifest(),output=tmp_path/'cache-analysis')
    assert r['outcome']==outcome and r['means'] is None and r['cache']['samples_eligible'] is False
    assert len(r['cache']['independent_replays'])==(1 if partial else 4)
    assert r['cache']['numerical_summary']['known_executor_seconds']==(.1 if partial else 1.)
    assert r['cache']['cached_seconds']==(None if partial else pytest.approx(.3))
    if partial:assert r['cache']['observation']['execution_outcomes']==['valid','infrastructure_interruption','not_run','not_run']


def test_nuts_arrays_adaptation_and_unknown_tree_depth_are_separate_contract(specimen,tmp_path):
    f,c,model,values=copy_fixture(specimen,tmp_path);reader=ScientificReader(f.root,f.sources,rscript=RSCRIPT,r_library=RLIB)
    p=tmp_path/'nuts-files';p.mkdir()
    c['task'].update(kernel='nuts',executor='spawn_chains',device='cpu')
    np.savez_compressed(p/'fit.npz',initial=values['initial'],warmup_states=np.zeros((4,8,model.dimension)),
        initial_torch_rng_states=np.zeros((4,32),dtype=np.uint8),final_torch_rng_states=np.ones((4,32),dtype=np.uint8))
    meta=dict(provider='pyro_cpu_spawn_chains',process_start_method='spawn',workers_requested=4,workers_allocated=4,
        threads_per_worker=1,chain_seeds=values['nuts_seeds'].tolist(),observed_worker_pids=[100,101,102,103],worker_records=[])
    for i in range(4):
        sub=p/f'worker-{i}';sub.mkdir()
        np.savez_compressed(sub/'adaptation.npz',warmup_step_size=np.ones(8),sample_step_size=np.ones(16))
        atomic_json(sub/'metadata.json',dict(status='completed',target_id=model.target_id,chain_seeds=[int(values['nuts_seeds'][i])],
            chain_records=[dict(diagnostics={'divergences':{'chain 0':[2]}})],tree_depth_hit_count=None,
            warmup_per_chain=8,draws_per_chain=16,max_tree_depth=8,target_accept_prob=.8,full_mass=False,
            mass_matrix_adaptation=True,provider='pyro_cpu_nuts'))
        meta['worker_records'].append(dict(chain=i,worker_pid=100+i,result_directory=sub.name))
    (p/'ownership.ndjson').write_text(json.dumps(dict(members=[dict(pid=i,member_of_owned_job=True) for i in range(100,104)]))+'\n')
    row=reader._nuts(c,model,values,p/'fit.npz',meta,p)
    assert row['MH_path_equivalence'] is False and row['receiver_reran_NUTS'] is False
    assert row['chain_diagnostics'][0]['records'][0]['diagnostics']['divergences']['chain 0']==[2]
    assert row['chain_diagnostics'][0]['tree_depth_hit_count'] is None
    np.savez_compressed(p/'worker-0/adaptation.npz',warmup_step_size=np.ones(7),sample_step_size=np.ones(16))
    with pytest.raises(ValueError,match='adaptation'):reader._nuts(c,model,values,p/'fit.npz',meta,p)
