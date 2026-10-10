#!/usr/bin/env python3
"""Frozen independent L2 reference, with immutable proposals and resumable weights."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import numpy as np
import psutil
from scipy.special import logsumexp
from flint import arb,ctx
from rare_importance import LogisticTarget,Mixture,fit_proposal_geometry,quality,batch_summary

ROOT=Path(__file__).resolve().parents[2]
IDENTITY='l2-rare-reference-is-v1'
SOURCES=['scripts/analysis/rare_importance.py','scripts/analysis/run_l2_importance.py']
MODEL_FILE='benchmark/protocols/windows-native-v1.json'
MODEL_FILE_SHA='6a9f830d2b870ab693ee7db57942b11d35d22aef9fd31039c09a1a90e37ec12d'
TARGET_SHA='7d3e601010f3c362f0cb37a7eca3e13efdd60a9622b718831200ecc0d65cee4f'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def fingerprint(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def save(path,obj):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');tmp.replace(path)


def immutable(path,obj):
    if path.exists():
        if json.loads(path.read_text())!=obj:raise ValueError('Immutable record differs: '+str(path))
    else:save(path,obj)


def guard(output):
    rss=psutil.Process().memory_info().rss
    if rss>4*1024**3:raise MemoryError('4 GiB RSS guard')
    size=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    if size>3*1024**3-32*1024**2:raise MemoryError('S3 working-output guard')
    # Space for full remaining work plus a same-size archive and 4 GiB margin.
    if shutil.disk_usage(output).free<10*1024**3:raise MemoryError('Insufficient space reserve')
    return dict(rss_bytes=rss,working_bytes=size)


def load_target():
    if sha(ROOT/MODEL_FILE)!=MODEL_FILE_SHA:raise ValueError('Frozen original target file differs')
    spec=json.loads((ROOT/MODEL_FILE).read_text())['models']['L2']
    if fingerprint(spec)!=TARGET_SHA:raise ValueError('L2 base target differs')
    return spec,LogisticTarget(spec)


def cross_check(target,modes):
    """Actual target values against independent 128-bit scalar Arb expressions."""
    points=[]
    for center,cov in modes:
        points.extend([center,center+np.arange(1,target.d+1)*.025,center-np.arange(1,target.d+1)*.025])
    ctx.prec=128;pi=arb.pi();sd=arb(target.scale);records=[]
    for q in points:
        prior=-sum((arb(float(z))*arb(float(z)) for z in q),arb(0))/(2*sd*sd)-target.d*(sd*(2*pi).sqrt()).log()
        total=prior
        for row,y in zip(target.x,target.y):
            eta=sum((arb(float(a))*arb(float(b)) for a,b in zip(row,q)),arb(0))
            signed=eta if y==1 else -eta
            total-=(1+(-signed).exp()).log()
        observed=float(target.logp(q)[0]);error=abs(observed-float(total.mid()))
        if not total.is_finite() or error>1e-9:raise ValueError('128-bit target comparison failed')
        # Central differences use the independent Arb target only above; gradient
        # comparison below is a separately labelled finite-difference check.
        fd=[];step=1e-4
        for j in range(target.d):
            d=np.zeros(target.d);d[j]=step
            fd.append((target.logp(q+d)[0]-target.logp(q-d)[0])/(2*step))
        gd=float(np.max(np.abs(np.asarray(fd)-target.gradient(q))))
        if gd>2e-5:raise ValueError('Analytic gradient finite-difference qualification failed')
        records.append(dict(point=q.tolist(),float64_log_target=observed,arb_log_target=str(total),absolute_difference=error,gradient_fd_max=gd))
    # Independent truncation constant for event proposal, evaluated with erf.
    event_mean,event_cov=modes[1];z=arb(float(event_mean[0]))/arb(float(event_cov[0,0])).sqrt()
    log_mass=((1+(z/arb(2).sqrt()).erf())/2).log()
    m=Mixture(*modes[0],*modes[1],target.scale)
    if abs(float(log_mass.mid())-m.log_mass)>1e-12:raise ValueError('Truncation normalizer differs')
    return dict(target_checks=records,truncation_arb=str(log_mass),status='passed',scope='six deterministic target points; not posterior accuracy certification')


def freeze(path):
    if path.exists():raise FileExistsError('Preserve protocol identity')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    hashes={n:sha(ROOT/n) for n in SOURCES}
    for n in SOURCES:
        if subprocess.check_output(['git','show',commit+':'+n],cwd=ROOT)!=(ROOT/n).read_bytes():raise ValueError('Commit source before freezing')
    load_target()
    protocol=dict(identity=IDENTITY,frozen=True,source_commit=commit,source_files=hashes,
        model_file=MODEL_FILE,model_file_sha256=MODEL_FILE_SHA,target_sha256=TARGET_SHA,
        python=platform.python_version(),environment={'OPENBLAS_NUM_THREADS':'1','VECLIB_MAXIMUM_THREADS':'1'},dependencies={n:importlib.metadata.version(n) for n in ['numpy','scipy','python-flint','psutil']},
        seed_namespace=[20261010,917],pilot_scale_pairs=[[1.,1.],[1.5,.5],[2.,.25],[3.,.125]],
        scale_interpretation='standard deviation multipliers for t and event covariance; squared in covariance',
        pilot_draws=4096,pilot_selection='Two legal proposals with lowest estimated relative influence variance; stable tie by candidate index. Pilot excluded from final estimate.',
        batches_per_proposal=8,draws_per_batch=131072,checkpoint_points=[8192,32768,131072],
        evaluation_block=256,persisted_weight_chunk=8192,maximum_proposal_points=2113536,
        component_weights=[.45,.45,.1],student_df=5,actual_rng='Independent PCG64 states saved before and after immutable full-batch proposal generation',
        event='Original first coordinate theta[0]>0; no affine transformation',
        map_maxiter=1000,information_eigenvalue_floor='max(1e-12, max_eigenvalue*1e-10)',
        event_covariance='At boundary mode rescale first-coordinate SD to min(Hinv SD,1/abs(boundary log-target slope)); preserve conditional covariance and regression',
        total_time_limit=None,rss_limit_gib=4,working_limit_gib=3,minimum_free_gib=10,
        qualification_required=True,new_formal_benchmark_repetitions=0,reference_type='self-normalized independent importance ratio with approximate batch delta MCSE; not certified',
        quality_targets=dict(relative_mcse=.1,numerator_ess=200,denominator_ess=1000,maximum_numerator_weight=.05,maximum_denominator_weight=.01))
    save(path,protocol);print(json.dumps(dict(protocol=str(path),sha256=sha(path),source_commit=commit)))


def samples(folder,mixture,n,seed,identity):
    folder.mkdir(parents=True,exist_ok=True);request=dict(identity=identity,proposal=mixture.spec(),draws=n,seed=seed)
    immutable(folder/'request.json',request)
    receipt=folder/'proposal.json';arrays=folder/'points.npz'
    if receipt.exists():
        meta=json.loads(receipt.read_text())
        if meta['request_sha256']!=sha(folder/'request.json') or meta['arrays_sha256']!=sha(arrays):raise ValueError('Proposal recovery differs')
        with np.load(arrays,allow_pickle=False) as z:return z['points'],z['component'],False
    if arrays.exists():raise ValueError('Uncommitted proposal arrays retained; inspect before recovery')
    rng=np.random.default_rng(np.random.SeedSequence(seed));before=rng.bit_generator.state
    x,c=mixture.sample(rng,n);after=rng.bit_generator.state
    # Save all actual proposals before computing any target value; restart never
    # generates a replacement random sequence for an existing completed batch.
    with arrays.open('xb') as f:np.savez(f,points=x,component=c)
    save(receipt,dict(request_sha256=sha(folder/'request.json'),arrays_sha256=sha(arrays),rng_before=before,rng_after=after))
    return x,c,True


def evaluate(folder,x,m,target,output,stats):
    values=[]
    for start in range(0,len(x),8192):
        stop=min(start+8192,len(x));p=folder/f'weights-{start:06d}-{stop:06d}.npy';receipt=p.with_suffix('.json')
        if receipt.exists():
            r=json.loads(receipt.read_text())
            if sha(p)!=r['sha256'] or r['proposal_sha256']!=sha(folder/'proposal.json'):raise ValueError('Weight recovery differs')
            w=np.load(p,allow_pickle=False);stats['reused_weight_chunks']+=1
        else:
            if p.exists():raise ValueError('Uncommitted weight array retained')
            w=np.concatenate([target.logp(x[i:min(i+256,stop)])-m.logpdf(x[i:min(i+256,stop)]) for i in range(start,stop,256)])
            if not np.isfinite(w).all() or np.max(w)>math.log(10)+1e-10:raise ValueError('Invalid defensive importance weights')
            with p.open('xb') as f:np.save(f,w,allow_pickle=False)
            save(receipt,dict(sha256=sha(p),proposal_sha256=sha(folder/'proposal.json'),start=start,stop=stop))
            stats['new_weight_chunks']+=1
        if w.shape!=(stop-start,):raise ValueError('Weight shape differs')
        values.append(w);resources=guard(output);stats['rss_observed_max']=max(stats['rss_observed_max'],resources['rss_bytes'])
        if stop in (8192,32768,131072):
            result=quality(np.concatenate(values),x[:stop,0]>0)
            immutable(folder/f'checkpoint-{stop}.json',dict(result=result,stop_on_accuracy=False))
    return np.concatenate(values)


def run(protocol_path,output):
    protocol=json.loads(protocol_path.read_text());ph=sha(protocol_path)
    if protocol['identity']!=IDENTITY or not protocol['frozen']:raise ValueError('Frozen protocol required')
    if platform.python_version()!=protocol['python']:raise ValueError('Python version differs')
    for k,v in protocol['environment'].items():
        if os.environ.get(k)!=v:raise ValueError('Execution environment differs: '+k)
    for n,v in protocol['dependencies'].items():
        if importlib.metadata.version(n)!=v:raise ValueError('Dependency differs: '+n)
    for n,h in protocol['source_files'].items():
        if sha(ROOT/n)!=h:raise ValueError('Frozen source changed: '+n)
    if output.exists() and any(output.iterdir()) and not (output/'IDENTITY.json').exists():raise ValueError('Nonempty unbound output')
    output.mkdir(parents=True,exist_ok=True);immutable(output/'IDENTITY.json',dict(protocol_sha256=ph,target_sha256=TARGET_SHA))
    started=time.time();stats=dict(new_proposal_points=0,reused_proposal_points=0,new_weight_chunks=0,reused_weight_chunks=0,rss_observed_max=0)
    spec,target=load_target();guard(output)
    geometry=output/'geometry.json'
    if geometry.exists():
        old=json.loads(geometry.read_text());modes=[(np.array(r['mode']),np.array(r['covariance'])) for r in old['fits']]
        if old['protocol_sha256']!=ph:raise ValueError('Geometry protocol differs')
        if sha(geometry)!=json.loads((output/'geometry-sha256.json').read_text())['sha256']:raise ValueError('Geometry changed')
    else:
        modes,records=fit_proposal_geometry(target);checks=cross_check(target,modes)
        save(geometry,dict(protocol_sha256=ph,fits=records,qualification=checks))
        save(output/'geometry-sha256.json',dict(sha256=sha(geometry)))
    candidates=[];pilot=[]
    for index,(s,t) in enumerate(protocol['pilot_scale_pairs']):
        m=Mixture(modes[0][0],modes[0][1]*s*s,modes[1][0],modes[1][1]*t*t,target.scale)
        candidates.append(m);folder=output/f'pilot-{index}'
        x,c,new=samples(folder,m,protocol['pilot_draws'],protocol['seed_namespace']+[0,index],ph)
        stats['new_proposal_points' if new else 'reused_proposal_points']+=len(x)
        w=evaluate(folder,x,m,target,output,stats);q=quality(w,x[:,0]>0)
        scaled=np.exp(w-w.max());event=x[:,0]>0
        score=float(np.mean((scaled*(event-q['probability']))**2)/np.mean(scaled*event)**2)
        pilot.append(dict(candidate=index,scale_pair=[s,t],score=score,quality=q))
    chosen=sorted(range(4),key=lambda i:(pilot[i]['score'],i))[:2]
    selected=dict(protocol_sha256=ph,geometry_sha256=sha(geometry),pilots=pilot,selected=chosen,
                  proposal_specs=[candidates[i].spec() for i in chosen],pilot_excluded=True)
    immutable(output/'SELECTION.json',selected) # saved before any formal reference draw
    print(json.dumps(dict(stage='pilot_complete',selected=chosen,scores=[p['score'] for p in pilot])),flush=True)
    summaries=[]
    for ordinal,index in enumerate(chosen):
        m=candidates[index];allw=[];alle=[]
        for batch in range(8):
            folder=output/f'proposal-{index}-batch-{batch:02d}'
            x,c,new=samples(folder,m,protocol['draws_per_batch'],protocol['seed_namespace']+[1,index,batch],ph)
            stats['new_proposal_points' if new else 'reused_proposal_points']+=len(x)
            w=evaluate(folder,x,m,target,output,stats);allw.append(w);alle.append(x[:,0]>0)
            print(json.dumps(dict(stage='batch_complete',proposal=index,batch=batch+1,new_points=stats['new_proposal_points'])),flush=True)
        s=batch_summary(allw,alle);s.update(candidate=index,scale_pair=protocol['pilot_scale_pairs'][index]);summaries.append(s)
    combined=math.hypot(summaries[0]['mcse'],summaries[1]['mcse'])
    discrepancy=abs(summaries[0]['probability']-summaries[1]['probability'])
    result=dict(identity=IDENTITY,protocol_sha256=ph,target_sha256=TARGET_SHA,source_commit=protocol['source_commit'],
        reference_estimates=summaries,proposals_compatible_3_combined_mcse=bool(discrepancy<=3*combined),
        between_proposals_absolute_difference=discrepancy,combined_mcse=combined,
        independent_batches_per_proposal=8,formal_reference_points=2097152,pilot_points=16384,new_mcmc_fits=0,
        status='quality_targets_met' if all(s['quality_targets_met'] for s in summaries) and discrepancy<=3*combined else 'reference_quality_unresolved',
        interpretation='Finite-sample self-normalized ratio, approximate MCSE, no strict probability certification; original zero-event reference preserved')
    immutable(output/'SUMMARY.json',result)
    payload={str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file() and 'invocations' not in p.parts and p.name!='checksums.json'}
    immutable(output/'checksums.json',payload)
    stats.update(elapsed_seconds=time.time()-started);calls=output/'invocations';calls.mkdir(exist_ok=True)
    save(calls/f'{time.time_ns()}.json',stats);print(json.dumps(dict(status=result['status'],**stats)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');f.add_argument('--output',type=Path,required=True)
    r=sub.add_parser('run');r.add_argument('--protocol',type=Path,required=True);r.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.action=='freeze':freeze(a.output.resolve())
    else:run(a.protocol.resolve(),a.output.resolve())
