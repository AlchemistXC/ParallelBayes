"""Integrity and semantic checks use fabricated preflight receipts, never sampling."""
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/prospective_reference'))
sys.path.insert(0,str(ROOT/'scripts/prospective_plan'))
from audit_candidate import audit
from prepare_inputs import generate
from input_transfer import pack


def digest(path):return sha256(path.read_bytes()).hexdigest()


def fake_checks(inputs):
    meta=json.loads((inputs/'manifest.json').read_text()); manifest_sha=digest(inputs/'manifest.json')
    rows=[{'chain':i,'finite':True,'density_delta_error':0.,'gradient_max_ratio':0.} for i in range(1,11)]
    report={'scope':'MOCK TEST ONLY','inputs_manifest_sha256':manifest_sha,'data_sha256':meta['data_sha256'],
            'initials_sha256':meta['initials_sha256'],'formal_sampling_started':False,
            'checks':{m:{'passed':True,'rows':rows} for m in ('logistic','ode')}}
    (inputs/'preflight.json').write_text(json.dumps(report))
    (inputs/'ode-points.json').write_text(json.dumps({'scope':'MOCK TEST ONLY','manifest_sha256':manifest_sha,
            'status':'passed','results':[{'index':i,'passed':True,'state':0.,'offset':0.,
            'gradient_budget':0.,'hv_budget':0.,'reference_budget':0.} for i in range(21)]}))
    fresh=inputs.parent/'fresh-preflight.json';fresh.write_text(json.dumps(report))
    return fresh


def test_candidate_audit_and_hash_failures(tmp_path):
    inputs=tmp_path/'inputs';generate(inputs);preflight=fake_checks(inputs)
    archive=tmp_path/'archive.zip';pack(inputs,archive)
    result=audit(inputs,archive,digest(archive),preflight)
    assert result['status']=='passed' and result['ode_fixed_points']==21
    with pytest.raises(ValueError,match='external bundle hash mismatch'):
        audit(inputs,archive,'0'*64,preflight)
    (inputs/'data.npz').write_bytes(b'tampered')
    with pytest.raises(ValueError,match='data.npz checksum differs'):
        audit(inputs,archive,digest(archive),preflight)


def test_bad_replacement_rejected_even_after_rehash(tmp_path):
    inputs=tmp_path/'inputs';generate(inputs)
    with np.load(inputs/'initials.npz',allow_pickle=False) as original:
        arrays={key:original[key].copy() for key in original.files}
    arrays['ode_candidates'][0,1,0]=100.
    np.savez(inputs/'initials.npz',**arrays)
    manifest=json.loads((inputs/'manifest.json').read_text());manifest['initials_sha256']=digest(inputs/'initials.npz')
    (inputs/'manifest.json').write_text(json.dumps(manifest))
    preflight=fake_checks(inputs);archive=tmp_path/'rehash.zip';pack(inputs,archive)
    with pytest.raises(ValueError,match='outside central prior interval'):
        audit(inputs,archive,digest(archive),preflight)


def test_stale_pass_flag_does_not_hide_bad_numeric_check(tmp_path):
    inputs=tmp_path/'inputs';generate(inputs);preflight=fake_checks(inputs)
    archive=tmp_path/'archive.zip';pack(inputs,archive)
    report=json.loads(preflight.read_text())
    report['checks']['ode']['rows'][2]['gradient_max_ratio']=1.01
    preflight.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='numerical threshold failed'):
        audit(inputs,archive,digest(archive),preflight)


def test_model_specific_audits_do_not_require_other_model_pass(tmp_path):
    inputs=tmp_path/'inputs';generate(inputs);preflight=fake_checks(inputs)
    archive=tmp_path/'archive.zip';pack(inputs,archive)
    for path in (inputs/'preflight.json',preflight):
        report=json.loads(path.read_text());report['checks']['ode']['passed']=False;path.write_text(json.dumps(report))
    (inputs/'ode-points.json').unlink()
    result=audit(inputs,archive,digest(archive),preflight,'logistic')
    assert result['status']=='passed' and result['models']==['logistic'] and result['ode_fixed_points'] is None
    with pytest.raises(ValueError,match='ode preflight failed'):
        audit(inputs,archive,digest(archive),preflight,'ode')


def test_ode_audit_does_not_require_logistic_pass(tmp_path):
    inputs=tmp_path/'inputs';generate(inputs);preflight=fake_checks(inputs)
    archive=tmp_path/'archive.zip';pack(inputs,archive)
    for path in (inputs/'preflight.json',preflight):
        report=json.loads(path.read_text());report['checks']['logistic']['passed']=False;path.write_text(json.dumps(report))
    result=audit(inputs,archive,digest(archive),preflight,'ode')
    assert result['status']=='passed' and result['models']==['ode'] and result['ode_fixed_points']==21
    with pytest.raises(ValueError,match='logistic preflight failed'):
        audit(inputs,archive,digest(archive),preflight,'logistic')
