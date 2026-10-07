import copy
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/completion'))
from formal_study_plan import create_study_plan,validate_study_plan


def test_full_v02_frame_and_failed_cells_cannot_change_allocation():
    catalog=json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    plan=create_study_plan('windows-formal-contract-fixture-v1',catalog)
    assert len(plan['tasks'])==41472 and len(plan['input_requirements'])==1152
    assert len(plan['cache_allocation']['probes'])==9216
    assert plan['cache_allocation']['total_executor_calls']==36864
    assert [sum(t['batch']==b for t in plan['tasks']) for b in range(4)]==[10368]*4
    assert plan['sampling_allowed'] is False and plan['formal_inputs_generated'] is False
    chosen=plan['cache_allocation']['strata']
    assert len(chosen)==36 and all(len(s['selected_replicates'])==8 for s in chosen)
    assert {s['model'] for s in chosen}=={'G1','G2','A1','L1','L2','H1','H2','M1','W1'}
    assert plan['analysis_policy']['L2_unresolved_sign_error'] is None
    assert validate_study_plan(plan,catalog)==plan
    # Resigning the outer hash cannot permit dropping a slow/failed slot or
    # promoting a planning file to an executable frozen protocol.
    from formal_runtime import fingerprint
    for mutation in ('drop_task','grant_execution','relax_accuracy'):
        bad=copy.deepcopy(plan);bad.pop('design_sha256')
        if mutation=='drop_task':bad['tasks'].pop()
        elif mutation=='grant_execution':bad['sampling_allowed']=True
        else:bad['controls']['atol']=1e-4
        bad['design_sha256']=fingerprint(bad)
        with pytest.raises(ValueError):validate_study_plan(bad,catalog)
    changed=copy.deepcopy(catalog);changed.pop('protocol_sha256')
    changed['targets'][0]['step_mala']*=2
    changed['protocol_sha256']=fingerprint(changed)
    with pytest.raises(ValueError):create_study_plan('windows-formal-contract-fixture-v1',changed)
