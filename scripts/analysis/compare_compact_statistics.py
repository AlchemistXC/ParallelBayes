#!/usr/bin/env python3
"""Compare independently rebuilt compact statistics to the archived Windows view.

Preserve all differences. Numeric drift is described, never resolved by silently
replacing values or widening a tolerance. No intervals are recalculated here.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/analysis'))
from formal_report import StatisticsBundle, model_tables, MODELS
from formal_runtime import file_hash

# These three source records duplicate already projected statistics and include
# file identities; original bundles remain independently manifest-verified.
DUPLICATE_RECORDS={'source_record','error_record','cost_record'}


def scalar_differences(left,right,path='$'):
    changes=[]
    def visit(a,b,key):
        if type(a) is dict and type(b) is dict:
            if a.keys()!=b.keys():
                changes.append(dict(path=key,kind='structure',left_keys=sorted(a),right_keys=sorted(b)));return
            for k in a:
                if k not in DUPLICATE_RECORDS:visit(a[k],b[k],key+'/'+k)
        elif type(a) is list and type(b) is list:
            if len(a)!=len(b):
                changes.append(dict(path=key,kind='structure',left_length=len(a),right_length=len(b)));return
            for i,(x,y) in enumerate(zip(a,b)):visit(x,y,key+'/'+str(i))
        elif type(a) in (float,int) and type(b) in (float,int):
            if not math.isfinite(a) or not math.isfinite(b):raise ValueError('Nonfinite statistic')
            if a!=b:
                changes.append(dict(path=key,kind='integer' if type(a) is type(b) is int else 'numeric',
                    left=a,right=b,absolute_difference=abs(a-b),scaled_difference=abs(a-b)/max(1.,abs(a),abs(b))))
        elif type(a) is not type(b) or a!=b:
            changes.append(dict(path=key,kind='state_or_label',left=a,right=b))
    visit(left,right,path)
    return changes


def decision_view(tables):
    def side(value,threshold):
        return None if value is None else -1 if value<threshold else 1 if value>threshold else 0
    return dict(
        ratios=[dict(key=[r['phase'],r['kind'],r['workflow_a'],r['workflow_b'],r['budget']],
            point_vs_one=side(r['point'],1.),low_vs_one=side(r['low'],1.),high_vs_one=side(r['high'],1.),
            interval_status=r['interval_status'],paired=r['paired']) for r in tables['ratios']],
        errors=[dict(key=[r['phase'],r['workflow'],r['budget'],r['function']],
            point_vs_001=side(r['point'],.01),low_vs_001=side(r['low'],.01),high_vs_001=side(r['high'],.01),
            interval_status=r['interval_status'],available=r['available']) for r in tables['errors']])


def bootstrap_difference(x,y):
    if x.shape!=y.shape or x.dtype!=y.dtype or x.dtype.kind not in 'fiu':
        raise ValueError('Bootstrap shape/type differs')
    # Frozen empty-denominator resamples deliberately retain NaN. Compare their
    # positions separately instead of dropping, filling or rejecting them.
    finite_x,finite_y=np.isfinite(x),np.isfinite(y)
    both=finite_x & finite_y
    equal=(x==y) | (np.isnan(x) & np.isnan(y))
    delta=np.abs(x[both]-y[both])
    return dict(shape=list(x.shape),dtype=str(x.dtype),equal=bool(equal.all()),
        differing_elements=int(np.count_nonzero(~equal)),
        left_nonfinite=int(np.count_nonzero(~finite_x)),right_nonfinite=int(np.count_nonzero(~finite_y)),
        nonfinite_pattern_changes=int(np.count_nonzero(~both & ~equal)),
        maximum_absolute_difference=float(delta.max(initial=0.)),
        maximum_scaled_difference=float((delta/np.maximum(1.,np.maximum(np.abs(x[both]),np.abs(y[both])))).max(initial=0.)))


def compare(left_directory,left_sha256,right_directory,right_sha256,output):
    out=Path(output)
    if out.exists():raise FileExistsError('Preserve earlier comparisons')
    left=StatisticsBundle(left_directory,left_sha256);right=StatisticsBundle(right_directory,right_sha256)
    if left.frame!=right.frame or not left.compact_frame or set(left.models)!=set(MODELS):
        raise ValueError('Different or incomplete compact statistical frames')
    changes=[];decisions=[];models=[]
    for name in MODELS:
        ls,lt=model_tables(left,name);rs,rt=model_tables(right,name)
        changes+=scalar_differences(ls,rs,name+'/summary')
        changes+=scalar_differences(lt,rt,name+'/tables')
        decisions+=scalar_differences(decision_view(lt),decision_view(rt),name+'/descriptive_thresholds')
        models.append(dict(model=name,table_rows={k:len(v) for k,v in lt.items()},
                           right_table_rows={k:len(v) for k,v in rt.items()}))
    # Compare bootstrap values, not ZIP container timestamps or summary hashes.
    names={k for k in left.manifest if k.endswith('.bootstrap.npz')}
    if names!={k for k in right.manifest if k.endswith('.bootstrap.npz')}:
        raise ValueError('Bootstrap inventory differs')
    arrays=[]
    for name in sorted(names):
        with np.load(left.root/name,allow_pickle=False) as a,np.load(right.root/name,allow_pickle=False) as b:
            if set(a.files)!=set(b.files):raise ValueError('Bootstrap array roles differ: '+name)
            for key in a.files:
                x,y=a[key],b[key]
                arrays.append(dict(file=name,key=key,**bootstrap_difference(x,y)))
    kinds=dict(Counter(r['kind'] for r in changes))
    summary=dict(schema='compact-statistics-cross-host-comparison-v1',
        left_manifest_sha256=left_sha256,right_manifest_sha256=right_sha256,
        left_analysis_identity_sha256=left.summary['analysis_identity_sha256'],
        right_analysis_identity_sha256=right.summary['analysis_identity_sha256'],
        frame=left.frame,models=models,projected_scalar_differences=kinds,
        structural_or_state_changes=sum(r['kind']!='numeric' for r in changes),
        numeric_maximum_absolute_difference=max((r['absolute_difference'] for r in changes if r['kind']=='numeric'),default=0.),
        numeric_maximum_scaled_difference=max((r['scaled_difference'] for r in changes if r['kind']=='numeric'),default=0.),
        descriptive_threshold_changes=len(decisions),bootstrap_files=len(names),bootstrap_arrays=len(arrays),
        bootstrap_arrays_equal=sum(r['equal'] for r in arrays),
        bootstrap_differing_elements=sum(r['differing_elements'] for r in arrays),
        bootstrap_nonfinite_pattern_changes=sum(r['nonfinite_pattern_changes'] for r in arrays),
        bootstrap_maximum_absolute_difference=max((r['maximum_absolute_difference'] for r in arrays),default=0.),
        original_values_replaced=False,new_sampler_calls=0,new_statistical_estimates=0,
        interpretation='Exact comparisons and descriptive differences only. Threshold 0.01 is the historical function-unit reporting landmark, not a new inference criterion. Any difference remains available for review.',
        comparator_sha256=file_hash(__file__))
    out.mkdir(parents=True)
    for name,value in [('SUMMARY.json',summary),('scalar-differences.json',changes),('threshold-differences.json',decisions),('bootstrap-arrays.json',arrays)]:
        (out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('left-directory','left-sha256','right-directory','right-sha256','output'):p.add_argument('--'+name,required=True)
    print(json.dumps(compare(**vars(p.parse_args())),indent=2))
