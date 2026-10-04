"""Frozen whole-run pilot seam: actual sampling, evidence, and strict resume."""
from pathlib import Path
import json,sys
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'r-package/inst/python'),str(ROOT/'scripts/completion')]


def test_budget_pilot_preserves_prefix_inputs_real_workers_and_completed_files(tmp_path):
    import inference_budget_pilot as study
    from parallelbayes.reference import benchmark_model
    from mechanism_runner import identity,sha,actual_hash
    item=dict(name='G1',dimension=8,geometry=dict(center=[0.]*8,factor=np.eye(8).tolist()),
              base_target_id=benchmark_model('G1').target_id,step_rwm=.3,step_mala=.2)
    p=dict(identity='unit-budget',required_platform=sys.platform,device='cpu',torch_threads=1,
        targets=[item],chains=2,mh_warmup=4,budgets=[8,16],replicates=[0],
        initial_seed_base=7361000,tape_seed_base=7362000,solver_seed_base=7363000,nuts_seed_base=7364000,
        nuts_warmup=8,nuts_tree_depth=3,nuts_target_accept=.8,nuts_full_mass=False,nuts_workers=2,nuts_threads=1,
        max_iter=64,memory_limit_mb=128,window=4,source_files=study.source_files(),
        master_inputs={},tasks=[],scope='unit test; no formal inference')
    inputs=tmp_path/'inputs';inputs.mkdir();name='G1-rep0.npz'
    payload=study.input_payload(p,item,0);np.savez_compressed(inputs/name,**payload)
    p['master_inputs'][name]=dict(sha256=sha(inputs/name),actual_sha256=actual_hash(payload))
    for budget in p['budgets']:
        for workflow in ['rwm','mala','nuts']:
            task=dict(model='G1',workflow=workflow,replicate=0,budget=budget,input=name)
            task['id']=identity(task)[:20];p['tasks'].append(task)
    p['protocol_sha256']=identity(p);protocol=tmp_path/'protocol.json';protocol.write_text(json.dumps(p))
    out=tmp_path/'run';result=study.run(protocol,inputs,tmp_path/'unused-source',out)
    assert result['completed']==6 and result['failed']==0
    states=[json.loads(f.read_text()) for f in out.glob('G1/*/state.json')]
    nuts=[s for s in states if s['task']['workflow']=='nuts']
    assert len(nuts)==2 and all(s['observed_worker_count']==2 for s in nuts)
    small=next(s for s in states if s['task']['workflow']=='mala' and s['task']['budget']==8)
    large=next(s for s in states if s['task']['workflow']=='mala' and s['task']['budget']==16)
    def raw(s):return out/'G1'/s['task']['id']/s['attempt']/'fit.npz'
    with np.load(raw(small)) as a,np.load(raw(large)) as b:
        np.testing.assert_array_equal(a['draws'],b['draws'][:,:12])
    before={f.relative_to(out).as_posix():sha(f) for f in (out/'G1').rglob('*') if f.is_file()}
    resumed=study.run(protocol,inputs,tmp_path/'unused-source',out,resume=True)
    after={f.relative_to(out).as_posix():sha(f) for f in (out/'G1').rglob('*') if f.is_file()}
    assert resumed['newly_executed_tasks']==0 and before==after
    file=raw(small);file.write_bytes(file.read_bytes()+b'corrupt')
    with pytest.raises(ValueError,match='checksum'):
        study.run(protocol,inputs,tmp_path/'unused-source',out,resume=True)
