#!/usr/bin/env python3
"""Bounded W1 posterior enclosure; distinct from ordinary quadrature stability."""
import argparse
import fcntl
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
from flint import arb,ctx
import psutil
from checkpoint_cubature import Engine,pack,unpack
from verified_cubature import rectangle_rule
from wells_ball_target import WellsBallTarget
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from external_wells import load_wells,make_wells

IDENTITY='w1-reference-enclosure-v1'
SOURCES=['scripts/analysis/run_w1_enclosure.py','scripts/analysis/checkpoint_cubature.py',
         'scripts/analysis/verified_cubature.py','scripts/analysis/wells_ball_target.py','examples/external_wells.py',
         'r-package/inst/python/parallelbayes/reference.py','r-package/inst/python/parallelbayes/__init__.py',
         'models/external/wells/source-manifest.json']
NAMES=['alpha','beta','alpha_squared','beta_squared','p_switch_0m','p_switch_100m','beta_positive']


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(path,obj):
    p=Path(path);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');t.replace(p)


def bounded_json(path,obj):
    if path.exists():
        if json.loads(path.read_text())!=obj:raise ValueError('Immutable result differs: '+str(path))
    else:save(path,obj)


def nonnegative(x):
    hi=x.upper()
    if hi<0:raise ArithmeticError('Enclosure contradicts known nonnegativity')
    lo=x.lower();lo=lo if lo>0 else arb(0)
    return lo.union(hi)


def posterior(regions,tails):
    total=[a+b for a,b in zip(*regions)]
    mass=tails[0];den=nonnegative(total[0])+arb(0).union(mass)
    if not den>0:return dict(status='normalizer_lower_unresolved',normalizer=den,ratios=None,met=False)
    signed=[total[1]+arb(0,tails[1]),total[2]+arb(0,tails[2])]
    positive=[nonnegative(total[i])+arb(0).union(tails[j]) for i,j in [(3,3),(4,4),(5,0),(6,0)]]
    event=nonnegative(regions[1][0])+arb(0).union(mass)
    ratios=[n/den for n in signed+positive+[event]]
    met=all(z.rad()<=arb('1e-8') for z in ratios[:-1])
    met=met and ratios[-1].rad()<=arb('1e-13') and ratios[-1]>0 and ratios[-1].rad()<=abs(ratios[-1].mid())/100
    return dict(status='posterior_targets_met' if met else 'valid_enclosure_wider_than_target',normalizer=den,ratios=ratios,met=bool(met))


def report_ball(x):return dict(binary_ball=pack(x),display=x.str(22),midpoint=float(x.mid()),radius=float(x.rad()),lower=float(x.lower()),upper=float(x.upper()),float_endpoints_for_display_only=True)


def report_result(result):
    return dict(status=result['status'],normalizer=report_ball(result['normalizer']),
        functions=None if result['ratios'] is None else {n:report_ball(x) for n,x in zip(NAMES,result['ratios'])},all_targets_met=result['met'])


def guard(output):
    rss=psutil.Process().memory_info().rss
    if rss>4*1024**3:raise MemoryError('4 GiB RSS limit')
    size=sum(p.stat().st_size for p in output.parent.rglob('*') if p.is_file())
    if size>3*1024**3-128*1024**2:raise MemoryError('Conservative combined follow-up working area exceeds S3 reserve')
    if shutil.disk_usage(output).free<10*1024**3:raise MemoryError('Insufficient disk reserve')
    return dict(rss=rss,combined_working_bytes=size)


def model_and_boxes(data,geometry):
    m=WellsBallTarget(data['dist'],data['switched'],geometry['center'],geometry['factor'])
    if m.factor[1][0]!=0 or not m.factor[1][1]>0:raise ValueError('Upper-triangular geometry required')
    boundary=-m.center[1]/m.factor[1][1];r=arb(12)
    if not -r<boundary<r:raise ValueError('Event boundary outside fixed square')
    boxes=[(-r,r,-r,boundary),(-r,r,boundary,r)]
    return m,boxes


def precision_probe(data,protocol,method,bits):
    ctx.prec=bits;m,boxes=model_and_boxes(data,protocol['geometry']);parts=[];calls=0
    for box in boxes:
        a,b,c,d=box;values=[arb(0)]*7;errors=[arb(0)]*7
        for i in range(4):
            for j in range(4):
                tile=(a+(b-a)*i/4,a+(b-a)*(i+1)/4,c+(d-c)*j/4,c+(d-c)*(j+1)/4)
                cell=rectangle_rule(m.value,m.fourth,tile,method)
                values=[x+y for x,y in zip(values,cell.value)];errors=[x+y for x,y in zip(errors,cell.remainder)]
                calls+=protocol['charge_per_cell'][method]
        parts.append(dict(quadrature=[pack(x) for x in values],remainder_upper=[pack(x.upper()) for x in errors]))
    return dict(method=method,precision_bits=bits,regions=parts,charged_evaluations=calls,
                model_calls=m.calls,scope='Fixed 4x4 tiles per region; precision/stability probe, not posterior accuracy')


def freeze(path):
    if path.exists():raise FileExistsError('Preserve prior frozen protocol')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for name in SOURCES:
        if subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)!=(ROOT/name).read_bytes():raise ValueError('Commit source before freezing')
    qpath=ROOT/'execution/targeted-followups-v1/qualification/w1-target-component.json';qualification=json.loads(qpath.read_text())
    protocol=dict(identity=IDENTITY,frozen=True,source_commit=commit,source_files={n:sha(ROOT/n) for n in SOURCES},
        python=platform.python_version(),dependencies={n:importlib.metadata.version(n) for n in ['python-flint','numpy','scipy','psutil']},
        environment={'OPENBLAS_NUM_THREADS':'1','VECLIB_MAXIMUM_THREADS':'1'},qualification_sha256=sha(qpath),
        target_id=qualification['target_id'],geometry={k:qualification[k] for k in ('center','factor')},
        functions=NAMES,radius=12,tail_sectors=256,precision_bits=[128,256,384],adaptive_precision_bits=384,
        methods=['gauss2','simpson'],probe_tiles_per_axis=4,charge_per_cell={'gauss2':7,'simpson':12},
        maximum_charged_evaluations_per_method=1999000,shared_tail_and_qualification_reserve=2000,
        maximum_active_cells_per_method=262144,checkpoint_block_splits=128,
        continuous_halfwidth='1e-8',event_halfwidth='1e-13',event_relative_halfwidth='0.01',
        priorities=[['1e-10']*7,['1e-15']+['1e-10']*6],
        resource_policy=dict(rss_gib=4,working_gib=3,minimum_free_gib=10,total_runtime_cutoff=None),
        event_domain='Split second integration coordinate at exact expression -center_beta/factor_22 represented by a ball. Endpoint uncertainty is propagated through nodes, widths and derivative bounds.',
        checkpoint_policy='Reserve block work durably before evaluation; interrupted reservations stay charged. Restore balls outward; never narrow radii. SQLite atomic partition/aggregate update.',
        evaluation_definition='Each vector density value, derivative-bound callback, and its shared midpoint log-density evaluation is charged. Counts bound actual evaluations including interrupted blocks; archived completed callbacks also reported.',
        positivity_policy='Intersect integrals of known nonnegative functions with [0,infinity); require strictly positive denominator lower bound before ratio division.',
        scope='Deterministic companion on original binary data; no MCMC fits or changes to old references')
    save(path,protocol);print(json.dumps(dict(protocol=str(path),sha256=sha(path),source_commit=commit)))


def run(protocol_path,data_root,output):
    protocol=json.loads(protocol_path.read_text());ph=sha(protocol_path)
    if protocol['identity']!=IDENTITY or not protocol['frozen']:raise ValueError('Frozen W1 protocol required')
    if platform.python_version()!=protocol['python']:raise ValueError('Python version differs')
    for n,v in protocol['dependencies'].items():
        if importlib.metadata.version(n)!=v:raise ValueError('Dependency differs: '+n)
    for k,v in protocol['environment'].items():
        if os.environ.get(k)!=v:raise ValueError('Execution environment differs: '+k)
    for name,digest in protocol['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Frozen source changed: '+name)
    data=load_wells(data_root)
    if make_wells(data).target_id!=protocol['target_id']:raise ValueError('Original data/target differs')
    if output.exists() and any(output.iterdir()) and not (output/'IDENTITY.json').exists():raise ValueError('Unbound nonempty output')
    output.mkdir(parents=True,exist_ok=True);bounded_json(output/'IDENTITY.json',dict(protocol_sha256=ph,target_id=protocol['target_id']))
    with (output/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (output/'SUMMARY.json').exists():
            expected=json.loads((output/'checksums.json').read_text())
            for name,digest in expected.items():
                if sha(output/name)!=digest:raise ValueError('Completed result asset differs: '+name)
            calls=output/'invocations';calls.mkdir(exist_ok=True)
            save(calls/f'{time.time_ns()}.json',dict(reused_complete=True,new_evaluations=0,verified_assets=len(expected)))
            print(json.dumps(dict(reused_complete=True,new_evaluations=0)),flush=True);return
        started=time.time();peak=guard(output)['rss'];probes={}
        ledger_path=output/'work-reservations.json'
        if ledger_path.exists():
            ledger=json.loads(ledger_path.read_text())
            if ledger['protocol_sha256']!=ph:raise ValueError('Work reservation identity differs')
        else:
            ledger=dict(protocol_sha256=ph,probes={m:0 for m in protocol['methods']},shared=64,
                        shared_initial_qualification_reserve=64)
            save(ledger_path,ledger)
        for method in protocol['methods']:
            probes[method]=0
            for bits in protocol['precision_bits']:
                path=output/f'probe-{method}-{bits}.json'
                if path.exists():
                    record=json.loads(path.read_text())
                    if sha(path)!=json.loads(path.with_suffix('.sha256.json').read_text())['sha256']:raise ValueError('Precision probe changed')
                else:
                    charge=32*protocol['charge_per_cell'][method]
                    if ledger['probes'][method]+charge>=protocol['maximum_charged_evaluations_per_method']:
                        raise RuntimeError('Precision-probe work budget exhausted')
                    ledger['probes'][method]+=charge;save(ledger_path,ledger)
                    record=precision_probe(data,protocol,method,bits);save(path,record);save(path.with_suffix('.sha256.json'),dict(sha256=sha(path)))
                probes[method]=ledger['probes'][method]
        ctx.prec=384;m,boxes=model_and_boxes(data,protocol['geometry'])
        tail_path=output/'tail.json'
        if tail_path.exists():
            record=json.loads(tail_path.read_text())
            if sha(tail_path)!=json.loads((output/'tail.sha256.json').read_text())['sha256']:raise ValueError('Tail record changed')
            tails=[unpack(x) for x in record['upper_bounds']]
        else:
            if ledger['shared']+256>protocol['shared_tail_and_qualification_reserve']:raise RuntimeError('Shared work budget exhausted')
            ledger['shared']+=256;save(ledger_path,ledger)
            t=m.tail(12,256);tails=t['bounds'];record=dict(upper_bounds=[pack(x) for x in tails],minimum_decay=pack(t['minimum_decay']),
                scope=t['scope'],precision_bits=384,log_gradient_evaluations=256)
            save(tail_path,record);save(output/'tail.sha256.json',dict(sha256=sha(tail_path)))
        results=[]
        for method in protocol['methods']:
            finished=output/f'{method}-result.json'
            if finished.exists():
                r=json.loads(finished.read_text())
                if sha(finished)!=json.loads(finished.with_suffix('.sha256.json').read_text())['sha256']:raise ValueError('Method result changed')
                results.append(r);continue
            method_model,boxes=model_and_boxes(data,protocol['geometry'])
            engine=Engine(output/f'{method}.sqlite',dict(protocol_sha256=ph,method=method),method_model.value,method_model.fourth,boxes,protocol['priorities'],method=method,
                maximum_cells=protocol['maximum_active_cells_per_method'],maximum_charged_evaluations=protocol['maximum_charged_evaluations_per_method']-probes[method],charge_per_cell=protocol['charge_per_cell'][method])
            reason='continue';begin=time.time()
            try:
                while reason=='continue':
                    now=posterior(engine.enclosures(),tails)
                    if now['met']:reason='tolerance_met';break
                    reason=engine.advance(protocol['checkpoint_block_splits'],stop=lambda regions:posterior(regions,tails)['met'])
                    resources=guard(output);peak=max(peak,resources['rss'])
                    state=dict(method=method,**engine.counters(),elapsed_this_invocation=time.time()-begin,rss=resources['rss'],
                        posterior=report_result(posterior(engine.enclosures(),tails)),stop_reason=reason)
                    with (output/'progress.ndjson').open('a') as f:f.write(json.dumps(state,allow_nan=False)+'\n')
                    if engine.counters()['committed_splits']%512==0:print(json.dumps(dict(method=method,**engine.counters(),status=state['posterior']['status'])),flush=True)
            except MemoryError as exc:
                reason='resource_stopped';save(output/f'{method}-resource-stop.json',dict(error=str(exc),**engine.counters()))
            finally:
                result=report_result(posterior(engine.enclosures(),tails));counts=engine.counters();engine.close()
            r=dict(method=method,stop_reason=reason,**counts,probe_charged_evaluations=probes[method],posterior=result,
                   source_commit=protocol['source_commit'],protocol_sha256=ph)
            save(finished,r);save(finished.with_suffix('.sha256.json'),dict(sha256=sha(finished)));results.append(r)
            print(json.dumps(dict(method=method,stop_reason=reason,status=result['status'],**counts)),flush=True)
            if reason=='resource_stopped':break
        combined=None
        if len(results)==2 and all(r['posterior']['functions'] is not None for r in results):
            values={}
            for name in NAMES:
                a,b=[unpack(r['posterior']['functions'][name]['binary_ball']) for r in results]
                if not a.overlaps(b):raise ArithmeticError('Certified formulations disagree; retain evidence and investigate')
                values[name]=report_ball(a.intersection(b))
            combined=values
        summary=dict(identity=IDENTITY,protocol_sha256=ph,source_commit=protocol['source_commit'],target_id=protocol['target_id'],methods=results,
            intersection=combined,all_method_targets_met=len(results)==2 and all(r['posterior']['all_targets_met'] for r in results),
            charged_evaluations_upper_bound=sum(r['charged_evaluations_upper_bound']+r['probe_charged_evaluations'] for r in results)+ledger['shared'],
            preserved_old_references=True,new_mcmc_fits=0,elapsed_this_invocation_seconds=time.time()-started,observed_rss_bytes=peak,
            meaning='Enclosures depend on implemented ball arithmetic and derivative/tail inequalities; qualification tests are not a general software proof. Float endpoints are display only; binary balls retain outward bounds.')
        save(output/'SUMMARY.json',summary)
        save(output/'checksums.json',{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name not in ('checksums.json','run.lock') and 'invocations' not in p.parts})
        print(json.dumps(dict(status='finished',all_method_targets_met=summary['all_method_targets_met'],charged_evaluations=summary['charged_evaluations_upper_bound'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');f.add_argument('--output',type=Path,required=True)
    r=sub.add_parser('run');r.add_argument('--protocol',type=Path,required=True);r.add_argument('--data',type=Path,required=True);r.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.action=='freeze':freeze(a.output.resolve())
    else:run(a.protocol.resolve(),a.data.resolve(),a.output.resolve())
