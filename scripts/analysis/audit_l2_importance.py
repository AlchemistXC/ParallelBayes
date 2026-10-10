#!/usr/bin/env python3
"""Independent reaggregation of saved L2 weights and sensitivity of old estimands."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def audit(source,frames,output):
    if output.exists():raise FileExistsError('Fresh audit output required')
    output.mkdir(parents=True)
    checks=json.loads((source/'checksums.json').read_text())
    for name,digest in checks.items():
        if sha(source/name)!=digest:raise ValueError('Source checksum differs: '+name)
    summary=json.loads((source/'SUMMARY.json').read_text());selection=json.loads((source/'SELECTION.json').read_text())
    target_file=ROOT/'benchmark/protocols/windows-native-v1.json'
    spec=json.loads(target_file.read_text())['models']['L2']
    sys.path.insert(0,str(ROOT/'r-package/inst/python'))
    from parallelbayes.reference import make_reference
    reference=make_reference(spec)
    constant=-8*math.log(2.5*math.sqrt(2*math.pi))
    # This check recalculates the target and proposal scalar densities without
    # calling the importance implementation or its reporting functions.
    xdesign=np.array(spec['X']);max_weight_error=0.;proposals=[];all_batches=[];scalar_checks=0
    for estimate,mspec in zip(summary['reference_estimates'],selection['proposal_specs']):
        index=estimate['candidate'];logs=[];events=[]
        for batch in range(8):
            folder=source/f'proposal-{index}-batch-{batch:02d}'
            with np.load(folder/'points.npz',allow_pickle=False) as z:x=z['points'];components=z['component']
            w=np.concatenate([np.load(p,allow_pickle=False) for p in sorted(folder.glob('weights-*.npy'))])
            event=x[:,0]>0;logs.append(w);events.append(event)
            # Endpoints and heaviest numerator/denominator plus one point per component.
            positive=np.flatnonzero(event)
            chosen=sorted({0,len(x)-1,int(np.argmax(w)),int(positive[np.argmax(w[positive])]),*[int(np.flatnonzero(components==c)[0]) for c in range(3)]})
            mu=np.array(mspec['mean']);cov=np.array(mspec['covariance']);em=np.array(mspec['event_mean']);ec=np.array(mspec['event_covariance'])
            precision=np.linalg.inv(cov);ep=np.linalg.inv(ec);df=mspec['df'];d=8
            from scipy.special import log_ndtr
            trunc=float(log_ndtr(em[0]/math.sqrt(ec[0,0])))
            for i in chosen:
                q=x[i];delta=q-mu;ed=q-em
                t=(math.lgamma((df+d)/2)-math.lgamma(df/2)-d/2*math.log(df*math.pi)-.5*np.linalg.slogdet(cov)[1]
                    -(df+d)/2*math.log1p(float(np.einsum('i,ij,j->',delta,precision,delta))/df))
                e=(-d/2*math.log(2*math.pi)-.5*np.linalg.slogdet(ec)[1]-.5*float(np.einsum('i,ij,j->',ed,ep,ed))-trunc) if q[0]>0 else -math.inf
                prior=constant-.5*math.fsum((q/2.5)**2)
                terms=[math.log(a)+b for a,b in zip([.45,.45,.1],[t,e,prior])];s=max(terms)
                logq=s+math.log(math.fsum(math.exp(a-s) for a in terms))
                expected=reference.reference(q)+constant-logq
                max_weight_error=max(max_weight_error,abs(expected-w[i]));scalar_checks+=1
                if abs(expected-w[i])>1e-8:raise ValueError('Independent saved log-weight differs')
        shift=max(float(v.max()) for v in logs);pairs=[];scaled=[]
        for w,event in zip(logs,events):
            z=np.exp(w-shift);scaled.append(z)
            pairs.append([math.fsum(z[event])/len(z),math.fsum(z)/len(z)])
        A=math.fsum(v[0] for v in pairs)/8;B=math.fsum(v[1] for v in pairs)/8;p=A/B
        se=math.sqrt(math.fsum(((a-p*b)/B)**2 for a,b in pairs)/(8*7))
        den=math.fsum(math.fsum(z) for z in scaled);num=math.fsum(math.fsum(z[e]) for z,e in zip(scaled,events))
        deness=den**2/math.fsum(math.fsum(z*z) for z in scaled)
        numess=num**2/math.fsum(math.fsum(z[e]*z[e]) for z,e in zip(scaled,events))
        derived=dict(probability=p,mcse=se,denominator_ess=deness,numerator_ess=numess)
        for k,v in derived.items():
            if not math.isclose(v,estimate[k],rel_tol=2e-10,abs_tol=1e-20):raise ValueError('Reaggregation differs: '+k)
        proposals.append(dict(candidate=index,**derived,verified=True))
        for b,values in enumerate(pairs):all_batches.append(dict(candidate=index,batch=b,scaled_A=values[0],scaled_B=values[1],shift=shift))
    frame_hash='bae58d58ab91fe4e9a293d7ec51b375ffa76a8e607fd47b6007d5bcd95db6521'
    if sha(frames)!=frame_hash:raise ValueError('Old L2 frame differs')
    rows=[json.loads(s) for s in frames.read_text().splitlines()]
    groups=defaultdict(list)
    for row in rows:
        if row['task']['artifact_kind']!='posterior':continue
        groups[(row['task']['workflow'],row['task']['budget'])].append(row)
    sensitivity=[]
    for (workflow,budget),items in sorted(groups.items()):
        valid=[v for v in items if v['outcome']=='valid'];values=[v['means'][v['names'].index('q1_positive')] for v in valid]
        for reference_est in proposals:
            p=reference_est['probability'];se=reference_est['mcse']
            # This is event-only, original-scale MSE, not the all-function metric.
            mse=math.fsum((v-p)**2 for v in values)/len(values) if values else None
            derivative=-2*(math.fsum(values)/len(values)-p) if values else None
            sensitivity.append(dict(workflow=workflow,budget=budget,reference_candidate=reference_est['candidate'],
                original_tasks=len(items),valid=len(values),failures=len(items)-len(values),event_estimate_min=min(values,default=None),event_estimate_max=max(values,default=None),
                event_only_mse=mse,first_order_reference_mcse=abs(derivative)*se if values else None,
                empirical_all_zero=bool(values and all(v==0 for v in values)),
                old_task_outcomes_unchanged=True,undefined_chain_diagnostics_unchanged=True))
    save(output/'audit.json',dict(passed=True,checked_source_assets=len(checks),scalar_log_weight_checks=scalar_checks,
        maximum_independent_log_weight_difference=max_weight_error,independent_reaggregation=proposals,
        source_summary_sha256=sha(source/'SUMMARY.json'),old_frame_sha256=sha(frames),old_frame_counts=dict(Counter(v['outcome'] for v in rows)),
        interpretation='Approximate independent importance reference only; unchanged original diagnostic and task eligibility rules'))
    save(output/'batches-reaggregated.json',all_batches);save(output/'old-L2-event-sensitivity.json',sensitivity)
    print(json.dumps(dict(passed=True,scalar_checks=scalar_checks,groups=len(groups),source_assets=len(checks))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--frames',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit(a.source.resolve(),a.frames.resolve(),a.output.resolve())
