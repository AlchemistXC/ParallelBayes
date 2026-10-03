"""Rebuild reference and formal summaries from checksum-verified raw task records."""
import argparse
import csv
import json
import time
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.special import expit
from scipy.stats import norm,beta
from parallelbayes.experiment import write_json,file_hash
from parallelbayes.models import fingerprint


def verify_inputs(protocol, root):
    """Link frozen design, execution identity, and the complete task set."""
    p=json.loads(Path(protocol).read_text());unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
    if fingerprint(unsigned)!=digest:raise ValueError('Protocol content changed after freeze')
    root=Path(root);manifest=json.loads((root/'manifest.json').read_text())
    identity=manifest['identity']
    if identity.get('protocol_sha256')!=digest or identity.get('source_sha256')!=p['source_sha256'] or identity.get('platform') not in p['platforms']:
        raise ValueError('Run identity differs from frozen protocol')
    expected={fingerprint(t)[:20]:t for t in p['tasks']}
    states={f.parent.name:json.loads(f.read_text()) for f in root.glob('tasks/*/state.json')}
    if len(expected)!=len(p['tasks']) or set(states)!=set(expected):
        raise ValueError('Missing, extra, or duplicate tasks in analysis inputs')
    for tid,state in states.items():
        if state['task']!=expected[tid] or state['status'] not in ('completed','failed'):
            raise ValueError('Task configuration or completion state differs')
    return p,dict(identity=identity,manifest_sha256=file_hash(root/'manifest.json'),
                  state_sha256={k:file_hash(root/'tasks'/k/'state.json') for k in sorted(states)},
                  protocol_file_sha256=file_hash(protocol),analysis_sha256=file_hash(__file__))


def records(root):
    root=Path(root)
    for statefile in sorted(root.glob('tasks/*/state.json')):
        state=json.loads(statefile.read_text());folder=statefile.parent/state['attempt']
        for name,digest in state['checksums'].items():
            if file_hash(folder/name)!=digest:raise RuntimeError(f'Checksum mismatch: {folder/name}')
        if json.loads((folder/'task.json').read_text())!=state['task']:
            raise ValueError('Saved task differs from receipt')
        result=json.loads((folder/'result.json').read_text())
        if result['status']!=state['status']:raise ValueError('Result status differs from receipt')
        raw=np.load(folder/'raw.npz') if (folder/'raw.npz').exists() else None
        yield state['task'],result,raw,state


def functions(spec,draws):
    kind=spec['kind']
    if kind=='gaussian':
        q=(draws[...,0]-spec['mean'][0])/np.sqrt(spec['covariance'][0][0])
        return np.stack((q,q*q,q>1),axis=-1)
    if kind=='logistic':
        return np.stack((draws[...,0],draws[...,1],expit(draws[...,0]),draws[...,0]>0),axis=-1)
    if kind in ['funnel','funnel_noncentered']:
        v=draws[...,0];z=draws[...,1]*np.exp(-v/2)
        return np.stack((v/3,np.tanh(v/3),draws[...,1]>0,np.cos(z)),axis=-1)
    if kind=='mixture':
        return np.stack((draws[...,0]/np.sqrt(1+spec['separation']**2),draws[...,0]>0,draws[...,1],draws[...,1]**2),axis=-1)
    raise ValueError(kind)


def analytic(spec):
    if spec['kind']=='gaussian':return np.array([0,1,norm.sf(1)])
    if spec['kind'] in ['funnel','funnel_noncentered']:return np.array([0,0,.5,np.exp(-.5)])
    if spec['kind']=='mixture':return np.array([0,.5,0,1])
    return None


def split_rhat(x):
    # Classical split Rhat on the specified functions, not rank-normalized Rhat.
    n=x.shape[1]//2;x=np.concatenate((x[:,:n],x[:,-n:]),axis=0)
    within=np.mean(np.var(x,axis=1,ddof=1),axis=0)
    between=n*np.var(x.mean(1),axis=0,ddof=1)
    with np.errstate(divide='ignore',invalid='ignore'):
        value=np.sqrt(((n-1)/n*within+between/n)/within)
    # No changes in a nonconstant estimand provide no convergence information.
    return np.where((within==0)&(between==0),np.nan,value)


def reference_summary(protocol,root,output):
    p,provenance=verify_inputs(protocol,root);groups=defaultdict(list)
    for task,r,raw,state in records(root):
        if r['status']=='completed':
            f=functions(p['models'][task['model']],raw['draws'])
            groups[task['model']].append((f,r,task))
    summary={}
    for name in p['models']:
        rows=groups[name]
        if len(rows)!=4:
            summary[name]=dict(usable=False,reason='Not all four independent reference fits completed');continue
        f=np.concatenate([x[0] for x in rows],axis=0)
        means=np.array([x[0].mean((0,1)) for x in rows])
        between=np.std(means,axis=0,ddof=1)/np.sqrt(len(rows))
        batch=f.reshape(f.shape[0],32,-1,f.shape[-1]).mean(2).reshape(-1,f.shape[-1])
        batch_se=np.std(batch,axis=0,ddof=1)/np.sqrt(len(batch))
        uncertainty=np.maximum(batch_se,between)
        rhat=split_rhat(f)
        informative=np.isfinite(rhat)&(np.ptp(f,axis=(0,1))>0)
        uncertainty=np.where(informative,uncertainty,np.nan)
        divergent=sum(np.sum(x[1]['diagnostics']['divergent']) for x in rows)
        summary[name]=dict(mean=f.mean((0,1)),mcse_conservative=uncertainty,between_fit_mcse=between,batch_mcse=batch_se,
            split_rhat=rhat,divergences=int(divergent),draws=int(f.shape[0]*f.shape[1]),independent_fits=4,
            usable=bool(np.all(informative) and np.all(rhat<1.01) and divergent==0 and np.all(uncertainty<.01)),
            informative_functions=informative,constant_functions=np.flatnonzero(~informative),
            event_positive_counts=[int(np.sum(f[...,j])) if np.all(np.isin(f[...,j],[0,1])) else None for j in range(f.shape[-1])],
            reference_is_exact=False,reference_means=means,
            note='Finite NUTS reference; diagnostics cannot rule out common bias. No reference-variance subtraction from squared discrepancy.')
    write_json(output,summary)
    provenance.update(model_sha256={k:fingerprint(v) for k,v in p['models'].items()},summary_sha256=file_hash(output))
    write_json(Path(output).with_suffix('.provenance.json'),provenance)
    return summary


def formal_summary(protocol,root,reference,output):
    p,provenance=verify_inputs(protocol,root);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    ref=json.loads(Path(reference).read_text());rows=[];groups=defaultdict(list)
    ref_provenance=json.loads(Path(reference).with_suffix('.provenance.json').read_text())
    if ref_provenance['summary_sha256']!=file_hash(reference):raise ValueError('Reference summary checksum mismatch')
    for name,spec in p['models'].items():
        if analytic(spec) is None and ref_provenance['model_sha256'].get(name)!=fingerprint(spec):
            raise ValueError('Reference model differs from formal model')
    provenance.update(reference_sha256=file_hash(reference),reference_provenance_sha256=file_hash(Path(reference).with_suffix('.provenance.json')))
    write_json(out/'analysis-provenance.json',provenance)
    # Preserve measured analysis costs, so later reconstruction reuses evidence
    # instead of changing workflow time on every report rebuild.
    cost_path=out/'diagnostic-costs.json'
    costs=json.loads(cost_path.read_text()) if cost_path.exists() else {}
    for task,r,raw,state in records(root):
        model=task['model'];spec=p['models'][model];method=task['config']['kernel']+'/'+task['config']['executor']
        row=dict(model=model,method=method,retained_draws=task['retained_draws'],replicate=task['replicate'],status=r['status'],
                 **{f't_{k}':v for k,v in r.get('timing',{}).items()},task_wall_seconds=state.get('elapsed_including_output'),
                 replay_overhead=r.get('timing_replay_overhead',0),host_peak_rss=r.get('host_process_peak_rss_bytes_sampled'))
        if r['status']=='completed':
            draws=raw['draws'][:,task['discard']:]
            if not np.isfinite(draws).all():raise ValueError('Normal posterior output contains nonfinite values')
            diagnostic_start=time.perf_counter()
            f=functions(spec,draws)
            rhat=split_rhat(f)
            row['estimate']=f.mean((0,1)).tolist();row['split_rhat']=rhat.tolist()
            row['split_rhat_state']=['undefined_no_variation' if np.isnan(x) else
                'infinite_between_chain_separation' if np.isinf(x) else 'finite' for x in rhat]
            row['constant_functions']=np.flatnonzero(np.ptp(f,axis=(0,1))==0).tolist()
            row['divergences']=int(np.sum(r.get('diagnostics',{}).get('divergent',[])))
            diagnostics=r.get('diagnostics') or {}
            if 'leapfrogs' in diagnostics:
                steps=np.asarray(diagnostics['leapfrogs'])
                row['integration_steps_total']=int(steps.sum())
                row['integration_steps_max']=int(steps.max())
                depth=task['config'].get('max_tree_depth',p['defaults']['max_tree_depth'])
                row['retained_transitions_at_step_cap']=int(np.sum(steps>=2**depth-1))
            if 'forward_evals' in diagnostics:
                transitions=task['config']['draws']*draws.shape[0]
                row['kernel_forward_evals']=int(np.sum(diagnostics['forward_evals']))
                row['kernel_forward_evals_per_transition']=row['kernel_forward_evals']/transitions
                row['transition_jvp_evals']=int(np.sum(diagnostics.get('jvp_evals',[])))
                row['solver_iteration_sum']=int(np.sum(diagnostics.get('iterations',[])))
                row['derivative_clips']=int(np.sum(diagnostics.get('clips',[])))
                row['scaled_residual_max']=float(np.max(diagnostics.get('residual',[0])))
                row['confirmed_per_chain']=diagnostics.get('confirmed')
            audit=r.get('audit') or {};row['max_path_error']=max(audit.get('max_abs_path_error',[0]))
            row['acceptance_mismatches']=sum(audit.get('acceptance_mismatches',[]))
            cached=r.get('cached_execution_seconds',[])
            row['t_cached']=float(np.median(cached)) if cached else r['timing']['sample']
            identity=file_hash(Path(root)/'tasks'/fingerprint(task)[:20]/state['attempt']/'result.json')
            if identity not in costs:costs[identity]=time.perf_counter()-diagnostic_start
            row['t_diagnostics']=costs[identity]
        else:
            row['t_diagnostics']=0.
        row['t_sampler_api']=row.get('t_total')
        row['t_total']=row['task_wall_seconds']-row['replay_overhead']+row['t_diagnostics']
        rows.append(row);groups[(model,method,task['retained_draws'])].append(row)
    write_json(cost_path,costs)
    write_json(out/'run-metrics.json',rows)
    summary=[];rng=np.random.default_rng(160339)
    for (model,method,n),group in sorted(groups.items()):
        ok=[r for r in group if r['status']=='completed'];total=len(group);failed=total-len(ok)
        truth=analytic(p['models'][model]);is_exact=truth is not None
        reference_valid=True if is_exact else ref.get(model,{}).get('usable',False)
        if truth is None:truth=np.array(ref.get(model,{}).get('mean',[]))
        item=dict(model=model,method=method,retained_draws=n,attempted=total,failed=failed,
             failed_fraction=failed/total,failure_95_interval=[0 if failed==0 else beta.ppf(.025,failed,total-failed+1),
                       1 if failed==total else beta.ppf(.975,failed+1,total-failed)],
             reference_kind='analytic' if is_exact else 'finite_NUTS',reference_usable=reference_valid,
             reference_mcse=None if is_exact else ref.get(model,{}).get('mcse_conservative'),
             complete_grid_group=total==p['policy']['replicates'],
             all_attempt_cost_seconds=sum(r['t_total'] for r in group),
             failed_attempt_cost_seconds=sum(r['t_total'] for r in group if r['status']!='completed'),
             all_attempt_median_seconds=float(np.median([r['t_total'] for r in group])),
             peak_host_rss_bytes=max((r['host_peak_rss'] or 0) for r in group))
        if ok and len(truth):
            estimates=np.array([r['estimate'] for r in ok]);error=(estimates-truth)**2
            boot=rng.integers(0,len(ok),(4000,len(ok)))
            values=error[boot].mean(1).max(1)
            if not is_exact and reference_valid:
                # Common-reference sensitivity, not an assertion of unbiased normal truth.
                sensitivity=truth+rng.normal(size=(4000,len(truth)))*np.array(ref[model]['mcse_conservative'])
                expanded=((estimates[boot]-sensitivity[:,None,:])**2).mean(1).max(1)
            else:expanded=values
            item.update(max_mean_squared_error=float(error.mean(0).max()),function_mean_squared_error=error.mean(0),
                 function_error_mcse=np.std(error,axis=0,ddof=1)/np.sqrt(len(ok)) if len(ok)>1 else np.full(len(truth),np.nan),
                 error_bootstrap_95=np.quantile(values,[.025,.975]),
                 error_with_reference_sensitivity_95=np.quantile(expanded,[.025,.975]),
                 median_total_seconds=float(np.median([r['t_total'] for r in ok])),
                 median_execution_seconds=float(np.median([r['t_sample'] for r in ok])),
                 median_cached_seconds=float(np.median([r['t_cached'] for r in ok])),
                 divergent_runs=sum(r['divergences']>0 for r in ok),divergences=sum(r['divergences'] for r in ok),
                 max_function_split_rhat=float(np.nanmax([r['split_rhat'] for r in ok])),
                 runs_with_constant_function=sum(bool(r['constant_functions']) for r in ok),
                 runs_with_infinite_rhat=sum('infinite_between_chain_separation' in r['split_rhat_state'] for r in ok))
        item['precision_assessment']=[]
        for epsilon in p['policy']['epsilon']:
            lo,hi=item.get('error_with_reference_sensitivity_95',[None,None])
            if failed or not item['complete_grid_group'] or not reference_valid or lo is None:
                status='not_assessable'
            elif hi<=epsilon**2:status='below_threshold_pointwise'
            elif lo>epsilon**2:status='above_threshold_pointwise'
            else:status='undetermined'
            item['precision_assessment'].append(dict(epsilon=epsilon,threshold=epsilon**2,status=status))
        summary.append(item)
    write_json(out/'formal-summary.json',dict(planned=len(p['tasks']),observed=len(rows),pending=len(p['tasks'])-len(rows),
        failed=sum(r['status']!='completed' for r in rows),groups=summary,
        interval_scope='Pointwise 95% percentile bootstrap over independent repetitions. Reference sensitivity separately propagated. No simultaneous guarantee. Conditional errors if any failure.'))
    pairs=[]
    for row in rows:
        if row['status']!='completed' or row['method'].endswith('/sequential'):continue
        kernel=row['method'].split('/')[0]
        candidates=[b for b in rows if b['model']==row['model'] and b['retained_draws']==row['retained_draws'] and b['replicate']==row['replicate'] and b['method']==kernel+'/sequential' and b['status']=='completed']
        if candidates:
            base=candidates[0]
            pairs.append(dict(model=row['model'],method=row['method'],retained_draws=row['retained_draws'],replicate=row['replicate'],
                execution_speedup=base['t_sample']/row['t_sample'],cached_speedup=base['t_cached']/row['t_cached'],
                complete_speedup=base['t_total']/row['t_total'],max_path_error=row['max_path_error']))
    write_json(out/'paired-speedups.json',pairs)
    if pairs:
        with (out/'paired-speedups.csv').open('w') as file:
            writer=csv.DictWriter(file,fieldnames=list(pairs[0]));writer.writeheader();writer.writerows(pairs)
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['reference','formal']);parser.add_argument('--protocol',required=True)
    parser.add_argument('--runs',required=True);parser.add_argument('--output',required=True);parser.add_argument('--reference')
    a=parser.parse_args()
    if a.mode=='reference':reference_summary(a.protocol,a.runs,a.output)
    else:formal_summary(a.protocol,a.runs,a.reference,a.output)
