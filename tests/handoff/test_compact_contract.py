"""Portable scope/identity checks; these never certify native process ownership."""
import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/completion'), str(ROOT/'scripts/analysis')]
from compact_contract import create_plan, validate_plan, allocation, CompactPlan, validate_probe
from formal_inputs import build_payload
from formal_runtime import fingerprint


def test_complete_prescribed_frame_and_cache_failure_independence():
    p=create_plan(ROOT)
    assert len(p['tasks'])==3888
    assert sum(t['kernel']=='nuts' for t in p['tasks'])==432
    assert len(p['input_requirements'])==216
    assert {r['steps'] for r in p['input_requirements'].values()}=={4608}
    assert [sum(t['batch']==b for t in p['tasks']) for b in range(3)]==[1296]*3
    probes=allocation(p)['probes']
    assert len(probes)==256
    assert [sum(t['batch']==b for t in probes) for b in range(3)]==[64,64,128]
    assert {t['replicate'] for t in probes}=={0,8,16,23}
    assert {t['model'] for t in probes}=={'G1','G2','L2','W1'}
    assert {t['replicate'] for t in p['tasks'] if t['batch']==2}==set(range(16,24))
    assert all(t['kernel']!='nuts' for t in probes)
    assert all(p['cache_allocation']['primary_outcome_is_selection_criterion'] is False for _ in probes)


def test_technical_frame_is_separate_and_fixed():
    p=create_plan(ROOT, technical=True)
    assert len(p['tasks'])==18 and len(allocation(p)['probes'])==16
    assert {(t['model'],t['budget']) for t in p['tasks']}=={('G2',4096),('W1',1024)}
    assert p['formal_scientific_repetitions']==0
    main=create_plan(ROOT)
    assert not set(t['id'] for t in p['tasks']) & set(t['id'] for t in main['tasks'])
    for role in ('initial','noise','log_uniform','directions','nuts_seeds'):
        x=build_payload(main['identity'],'G2',0,64,20)[role]
        y=build_payload(p['identity'],'G2',0,64,20)[role]
        z=build_payload('windows-formal-inference-v1','G2',0,64,20)[role]
        assert not np.array_equal(x,y) and not np.array_equal(x,z)


@pytest.mark.parametrize('field', ['groups','controls','input_requirements','cache_allocation'])
def test_rehashed_changes_rejected(field):
    p=create_plan(ROOT)
    value=copy.deepcopy(p)
    if field=='groups': value[field][0]['budgets']=[1024]
    elif field=='controls': value[field]['atol']=1e-7
    elif field=='input_requirements': value[field].pop('G1-rep0023.npz')
    else: value[field]['probes'].pop()
    value['plan_sha256']=fingerprint({k:v for k,v in value.items() if k!='plan_sha256'})
    with pytest.raises(ValueError): validate_plan(value,ROOT)


def test_old_design_and_unfrozen_metadata_are_not_launch_protocols():
    design=json.loads((ROOT/'benchmark/designs/windows-compact-inference-v1/design.json').read_text())
    with pytest.raises(ValueError): CompactPlan(design)
    with pytest.raises(ValueError): CompactPlan(create_plan(ROOT))


def test_paired_configurations_cover_all_original_repetitions():
    p=create_plan(ROOT)
    for model in [t['name'] for t in p['targets']]:
        for budget in (1024,4096):
            for device in ('cpu','cuda'):
                for kernel in ('rwm','mala'):
                    records=[t for t in p['tasks'] if (t['model'],t['budget'],t['device'],t['kernel'])==(model,budget,device,kernel)]
                    assert len(records)==48
                    assert all(sum(t['replicate']==r for t in records)==2 for r in range(24))
