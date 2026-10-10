"""Audit receipts must preserve incomplete aggregate status and unknown ESS."""
import copy
import json
from pathlib import Path
import sys

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/analysis'))
from review_nuts_workers import checked,digest,extract_worker,metadata_member


def fixture():
    task=dict(id='example',model='G1',batch='1',replicate='0',budget='4096',outcome='output_failure_unclassified')
    candidate=dict(status='failed',target_id='target',chain_seeds=[11,12,13,14])
    worker=dict(chain=0,result_directory='worker-0',worker_wall=10.)
    meta=dict(status='completed',chain_seeds=[11],target_id='target',draws_per_chain=4096,
        warmup_per_chain=1024,provider='pyro_cpu_nuts',names=['q1','q2'],
        timing=dict(warmup=2.,sample=6.,finalization_diagnostics=.5,transform=.1,total=9.),
        chain_records=[dict(diagnostics=dict(q=dict(n_eff=[5000.,4500.])))],
        pyro_version='1.9.2',torch_version='test')
    return task,candidate,worker,meta


def test_completed_child_never_promotes_failed_aggregate_and_reads_partial_file():
    task,candidate,worker,meta=fixture()
    name='attempt/worker-0/partial-fit.json'
    assert metadata_member('attempt/',candidate,worker,{name:{}})==name
    row=extract_worker(task,candidate,worker,meta)
    assert row['task_outcome']=='output_failure_unclassified' and row['child_status']=='completed'
    assert row['post_final_hook_fraction']==pytest.approx(1/18)
    assert not row['legacy_ess_all_null']


def test_null_legacy_ess_stays_missing_without_reclassifying_sampler():
    task,candidate,worker,meta=fixture()
    meta['chain_records'][0]['diagnostics']['q']['n_eff']=[None,None]
    row=extract_worker(task,candidate,worker,meta)
    assert row['legacy_ess_all_null'] and row['legacy_ess_null']==2
    assert row['child_status']=='completed'


@pytest.mark.parametrize('change',['seed','budget','negative_duration','overcounted_duration'])
def test_misbound_and_invalid_child_records_are_rejected(change):
    task,candidate,worker,meta=fixture()
    if change=='seed':meta['chain_seeds']=[99]
    elif change=='budget':meta['draws_per_chain']=1024
    elif change=='negative_duration':meta['timing']['sample']=-1.
    else:meta['timing']['sample']=10.
    with pytest.raises(ValueError):extract_worker(task,candidate,worker,meta)


def test_manifest_corruption_and_absent_declared_child_cannot_be_treated_as_pending(tmp_path):
    raw=b'{"status":"completed"}'
    path=tmp_path/'record.json';path.write_bytes(raw)
    members={'record.json':dict(bytes=len(raw),sha256=digest(raw))}
    assert checked(tmp_path,members,'record.json',{})['status']=='completed'
    path.write_bytes(raw.replace(b'completed',b'corrupted'))
    with pytest.raises(ValueError,match='differs'):checked(tmp_path,members,'record.json',{})
    _,candidate,worker,_=fixture()
    with pytest.raises(ValueError,match='absent'):metadata_member('attempt/',candidate,worker,{})
