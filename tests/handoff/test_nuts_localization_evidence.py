from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/followups'))
from nuts_events import ChainRecorder
from nuts_evidence import phase_path,paired_prefixes,qualification_check,failure_stage


def test_prefix_comparison_exposes_one_step_mismatch_and_partial_chain(tmp_path):
    for condition,length,offset in [('left',5,0),('right',3,1)]:
        for chain in range(4):
            r=ChainRecorder(tmp_path/condition/f'chain-{chain}',chain,2,5,block=2)
            for step in range(2):r.hook('Warmup',step,[step,chain],.2)
            for step in range(length):r.hook('Sample',step,[step+(offset if step==2 else 0),chain],.2)
            r.partial()
    comparison=paired_prefixes(tmp_path/'left',tmp_path/'right')
    sample=[x for x in comparison if x['phase']=='sample']
    assert len(sample)==4 and all(x['common_steps']==3 and x['max_absolute_difference']==1 for x in sample)
    assert all(x['exact_match'] is False for x in sample)
    assert failure_stage(tmp_path/'right')[0]['observed_stage']=='sampling_or_later'


def test_saved_path_tamper_rejected_and_absent_qualification_not_promoted(tmp_path):
    r=ChainRecorder(tmp_path/'chain',0,2,3,block=2)
    for i in range(2):r.hook('Warmup',i,[i],.1)
    np.save(tmp_path/'chain'/'warmup-000000-000002.npy',[[99],[99]])
    with pytest.raises(ValueError,match='integrity'):phase_path(tmp_path/'chain','warmup')
    assert not qualification_check(tmp_path,[])['passed']


def test_partial_last_event_is_marked_without_hiding_interior_corruption(tmp_path):
    from nuts_evidence import read_events
    path=tmp_path/'events.ndjson';path.write_text('{"event":"persisted"}\n{"event":')
    rows,truncated=read_events(path)
    assert rows==[{'event':'persisted'}] and truncated
    path.write_text('{"event":\n{"event":"later"}\n')
    with pytest.raises(ValueError,match='nonterminal'):read_events(path)


def test_memory_metrics_remain_separate_and_missing_is_not_zero(tmp_path):
    import json
    from analyze_nuts_localization import resource_summary
    rows=[dict(sampled_rss_bytes=10,kernel_peak_job_commit_bytes=40,active_processes=2,
        retained_process_handles=[dict(pid=1,creation_filetime=1,state='running',private_bytes=7,exit_code=None)],
        completion_messages=[])]
    (tmp_path/'ownership.ndjson').write_text('\n'.join(json.dumps(r) for r in rows))
    result=resource_summary(tmp_path)
    assert result['max_sampled_tree_rss_bytes']==10 and result['kernel_peak_job_commit_bytes']==40
    assert result['max_sampled_available_private_sum_bytes']==7 and result['private_incomplete_observations']==1
    assert result['missing_messages_exclude_resource_failure'] is False
