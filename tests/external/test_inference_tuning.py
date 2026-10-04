"""Tuning scores include every retained transition and preserve failed candidates."""
from pathlib import Path
import sys
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))


def test_rejections_count_in_jump_score_and_failed_replicates_cannot_win():
    from inference_tuning_stats import score_path,select_candidate
    path=np.array([[[1.],[1.],[3.],[3.]]])
    score=score_path(path,[[0.]],np.array([[True,False,True,False]]),warmup=1)
    assert score['transitions']==3
    assert score['accepted']==1 and score['rejections']==2
    assert score['mean_squared_jump_per_dimension']==pytest.approx(4/3)
    rows=[dict(step=.1,replicate=0,status='completed',score=1.),
          dict(step=.1,replicate=1,status='completed',score=2.),
          dict(step=.2,replicate=0,status='completed',score=10.),
          dict(step=.2,replicate=1,status='failed',score=None),
          dict(step=.3,replicate=0,status='completed',score=.5),
          dict(step=.3,replicate=1,status='completed',score=1.)]
    chosen=select_candidate(rows,steps=[.1,.2,.3],replicates=[0,1])
    assert chosen['selected_step']==.1
    assert len(chosen['candidates'])==3
    assert chosen['candidates'][1]['eligible'] is False
    assert chosen['statistical_convergence_claim'] is False


def test_small_frozen_tuning_run_resumes_without_resampling_and_rejects_corruption(tmp_path):
    import hashlib,json
    import inference_tuning as study
    from mechanism_runner import identity,sha,actual_hash
    item=dict(name='G1',dimension=8,geometry='identity')
    p=dict(identity='unit-tuning',required_platform=sys.platform,torch_threads=1,device='cpu',targets=[item],
        chains=1,warmup=2,retained=6,replicates=[0],initial_seed_base=651001,tape_seed_base=651002,solver_seed_base=651003,
        window=2,max_iter=32,memory_limit_mb=32,source_files=study.source_files(),master_inputs={},cases=[],scope='unit test only')
    inputs=tmp_path/'inputs';inputs.mkdir();payload=study.input_payload(p,item,0)
    name='G1-rep0.npz';np.savez_compressed(inputs/name,**payload)
    p['master_inputs'][name]=dict(sha256=sha(inputs/name),actual_sha256=actual_hash(payload))
    for kernel in ['rwm','mala']:
        for step in [.1,.2]:
            case=dict(model='G1',kernel=kernel,step=step,multiplier=step,replicate=0,input=name)
            case['id']=identity(case)[:20];p['cases'].append(case)
    p['protocol_sha256']=identity(p);protocol=tmp_path/'protocol.json';protocol.write_text(json.dumps(p))
    out=tmp_path/'run'
    result=study.run(protocol,inputs,tmp_path/'unused-external-source',out)
    assert result['completed']==4 and result['failed']==0
    before={str(f.relative_to(out)):sha(f) for f in (out/'G1').rglob('*') if f.is_file()}
    study.run(protocol,inputs,tmp_path/'unused-external-source',out,resume=True)
    after={str(f.relative_to(out)):sha(f) for f in (out/'G1').rglob('*') if f.is_file()}
    assert before==after
    raw=next((out/'G1').glob('*/attempt-*/fit.npz'))
    original=raw.read_bytes();raw.write_bytes(original+b'corrupt')
    with pytest.raises(ValueError,match='checksum'):
        study.run(protocol,inputs,tmp_path/'unused-external-source',out,resume=True)
    raw.write_bytes(original)
    setup=out/'G1/setup.json';data=json.loads(setup.read_text());data['geometry']['center'][0]+=1
    setup.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='geometry checksum'):
        study.run(protocol,inputs,tmp_path/'unused-external-source',out,resume=True)
