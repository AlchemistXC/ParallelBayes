"""Read actual frozen file contracts; artificial OS metadata, no samplers."""
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'scripts/completion'),str(ROOT/'tests/handoff')]
from formal_analyze import FrozenFrame,analyze_frame
from formal_archive import build_index,EvidenceIndex
from formal_statistics import reference_contract
from formal_runtime import atomic_json,file_hash
from test_formal_validation import prepared
from test_formal_archive import delivery_manifest


def test_actual_finite_freeze_visits_all_51_slots_without_invented_outcomes(prepared,tmp_path):
    delivery=tmp_path/'delivery';shutil.copytree(prepared[0],delivery/'bundle')
    build_index(delivery,'bundle',delivery_manifest(delivery),tmp_path/'index')
    index=EvidenceIndex(delivery,tmp_path/'index')
    try:
        frame=FrozenFrame(index)
        assert frame.counts==dict(main=27,cache=24)
        assert frame.receipt()['formal_scientific_repetitions_per_model']==0
        class NoScientificCalls:
            def read(self,*args,**kwargs):raise AssertionError('No raw outputs exist in the fixture')
        report=analyze_frame(index,frame,NoScientificCalls(),tmp_path/'analysis',dict(scope='artificial-contract-test'))
        assert report['visited']==51 and report['new_analyses']==51
        assert report['counts']==dict(main=dict(evidence_gap=27),cache=dict(evidence_gap=24))
        assert report['every_planned_task_represented'] and not report['evidence_complete']
    finally:index.close()


def reference_fixture(tmp_path,*,changed=False):
    delivery=tmp_path/'delivery';bundle=delivery/'bundle'
    catalog=json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    names=['benchmark/protocols/windows-native-v1.json',
        'benchmark/analysis/outputs/completion-f3/reference-reuse.json',
        'benchmark/analysis/outputs/wells-quadrature-v1/R12-n96.json',
        'benchmark/analysis/outputs/wells-quadrature-v1/result.json',
        'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis/reference-contract.json']
    sources={}
    for name in names:
        target=bundle/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        if changed and name==names[-1]:
            value=json.loads(target.read_text());value['G1']['means'][0]=1.;atomic_json(target,value)
        sources[name]=file_hash(target)
    frame=SimpleNamespace(protocol=dict(targets=[t for t in catalog['targets'] if t['name'] in ('G1','G2')],source_files=sources))
    build_index(delivery,'bundle',delivery_manifest(delivery),tmp_path/'index')
    return EvidenceIndex(delivery,tmp_path/'index'),frame


def test_reference_rebuilt_in_original_coordinates_matches_frozen_means(tmp_path):
    index,frame=reference_fixture(tmp_path)
    try:
        refs=reference_contract(index,frame)
        assert refs['G1']['means']==refs['G2']['means']==[0.,1.,0.15865525393145707]
        assert refs['G1']['names']==refs['G2']['names']==['standard_q1','standard_q1_squared','standard_q1_gt1']
        assert refs['G1']['kinds']==['analytic']*3
    finally:index.close()


def test_resigned_reference_value_still_must_match_reconstruction(tmp_path):
    index,frame=reference_fixture(tmp_path,changed=True)
    try:
        with pytest.raises(ValueError,match='reference contract differs'):reference_contract(index,frame)
    finally:index.close()
