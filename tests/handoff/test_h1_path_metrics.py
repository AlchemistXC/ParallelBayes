import json
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/analysis'))
from h1_path_metrics import functions, compare_functions
from h1_function_paths import Evidence, verified_resume, sha, save


def test_small_coordinate_sign_error_and_discard_are_not_hidden():
    a=np.zeros((2,6,2));a[...,0]=1e6;a[...,1]=1e-12
    b=a.copy();b[0,1,1]=-1e-12;b[1,4,1]=-1e-12
    rows,d=compare_functions(functions(a),functions(b),3)
    row=next(x for x in rows if x['chain']=='pooled' and x['scope']=='full' and x['function']=='x1_positive')
    assert row['event_disagreements']==2 and row['max_abs']==1
    row=next(x for x in rows if x['chain']=='pooled' and x['scope']=='retained' and x['function']=='x1_positive')
    assert row['event_disagreements']==1 and row['event_positions']==[{'chain_1based':2,'transition_1based':5}]
    assert row['signed_mean']==pytest.approx(1/6)


def test_mean_cancellation_keeps_rms_and_local_error():
    a=np.zeros((1,4,4));b=np.zeros_like(a);a[0,:,0]=[2,-2,2,-2]
    rows,_=compare_functions(a,b,0);r=rows[0]
    assert r['signed_mean']==0 and r['mean_abs']==2 and r['rms']==2 and r['max_abs']==2


def test_overflow_is_retained_not_clipped_or_masked():
    a=np.zeros((1,2,2));a[0,1]=[-2000,1]
    f=functions(a);rows,_=compare_functions(f,np.zeros_like(f),0)
    r=next(x for x in rows if x['scope']=='full' and x['chain']=='pooled' and x['function']=='cos_z1')
    assert r['nonfinite_count']==1 and r['status']=='nonfinite' and r['signed_mean'] is None
    json.dumps(rows,allow_nan=False)


def test_affine_mapping_must_precede_function_evaluation():
    q=np.zeros((1,3,2));q[...,1]=.25
    original=q.copy();original[...,0]+=3;original[...,1]*=2
    assert np.all(functions(original)[...,0]==1)
    assert not np.array_equal(functions(q),functions(original))


def test_resume_refuses_mutated_arrays_and_changed_input(tmp_path):
    root=tmp_path/'raw';root.mkdir();(root/'a').write_bytes(b'original')
    m=tmp_path/'manifest.json';save(m,{'files':{'a':{'bytes':8,'sha256':sha(root/'a')}}})
    evidence=Evidence(root,m,sha(m));folder=tmp_path/'result';folder.mkdir();(folder/'d.npz').write_bytes(b'array')
    result={'task':{'id':'one'},'protocol_sha256':'p','source_assets_sha256':{'a':sha(root/'a')},
        'outputs_sha256':{'d.npz':sha(folder/'d.npz')},'original_classification_changed':False,'new_formal_repetitions':0}
    save(folder/'result.json',result)
    assert verified_resume(folder,{'id':'one'},'p',evidence)==result
    (folder/'d.npz').write_bytes(b'change')
    with pytest.raises(ValueError,match='output'):verified_resume(folder,{'id':'one'},'p',evidence)
    (folder/'d.npz').write_bytes(b'array');(root/'a').write_bytes(b'changed!')
    with pytest.raises(ValueError,match='evidence'):verified_resume(folder,{'id':'one'},'p',evidence)
