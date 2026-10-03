"""Rebuild checked Windows summaries, paired comparisons and static figures."""
import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path
import numpy as np
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[2]/'execution/windows-native/matplotlib-cache'))
from scipy.special import expit
from scipy.stats import norm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from evidence import ROOT,write_json,sha,fingerprint,verify_checksums


def functions(spec,draws):
    kind=spec['kind']
    if kind=='gaussian':
        q=(draws[...,0]-spec['mean'][0])/np.sqrt(spec['covariance'][0][0])
        return np.stack((q,q*q,q>1),-1),np.array([0.,1.,norm.sf(1)])
    if kind in ['funnel','funnel_noncentered']:
        v=draws[...,0];z=draws[...,1]*np.exp(-v/2)
        return np.stack((v/3,np.tanh(v/3),draws[...,1]>0,np.cos(z)),-1),np.array([0.,0.,.5,np.exp(-.5)])
    if kind=='mixture':
        return np.stack((draws[...,0]/np.sqrt(1+spec['separation']**2),draws[...,0]>0,draws[...,1],draws[...,1]**2),-1),np.array([0.,.5,0.,1.])
    if kind=='logistic':
        return np.stack((draws[...,0],draws[...,1],expit(draws[...,0]),draws[...,0]>0),-1),None
    raise ValueError('unsupported estimands')


def interval(values,statistic=np.median):
    values=np.asarray(values,float)
    if len(values)<2:return None
    rng=np.random.Generator(np.random.Philox(555124))
    samples=rng.integers(0,len(values),(2000,len(values)))
    return np.quantile(statistic(values[samples],axis=1),[.025,.975]).tolist()


def analyze(root,output,pilot=False):
    p=json.loads((root/('design.json' if pilot else 'protocol.json')).read_text(encoding='utf-8'))
    if not pilot:
        unsigned=dict(p);digest=unsigned.pop('protocol_sha256')
        if fingerprint(unsigned)!=digest:raise ValueError('protocol checksum differs')
        for name,h in p['source_files'].items():
            if sha(ROOT/name)!=h:raise ValueError('source identity changed: '+name)
    tasks=p['tasks'];expected={fingerprint(t):t for t in tasks}
    states=list(root.glob('*/state.json') if pilot else root.glob('tasks/*/state.json'))
    if len(states)!=len(tasks):raise ValueError('incomplete/extra task states')
    rows=[];seen=set();input_hashes={}
    for file in states:
        s=json.loads(file.read_text());t=s['task'];tid=fingerprint(t)
        if tid not in expected or tid in seen:raise ValueError('task set differs')
        seen.add(tid);input_hashes[file.relative_to(root).as_posix()]=sha(file)
        folder=file.parent if pilot else file.parent/s['attempt']
        verify_checksums(folder,s['checksums'])
        r=json.loads((folder/'result.json').read_text())
        if r['status']!=s['status'] or s['status'] not in ['completed','failed']:raise ValueError('nonterminal or different status')
        if not pilot and s['protocol_sha256']!=p['protocol_sha256']:raise ValueError('protocol identity differs')
        c=t['config'];n=c['draws']*c['chains']
        row=dict(task_id=tid,model=t['model'],replicate=t['replicate'],device=c['device'],kernel=c['kernel'],
            executor=c['executor'],draws=c['draws'],chains=c['chains'],window=c['window'],status=r['status'],
            all_attempt_seconds=s['elapsed_including_output'],failed_cost_seconds=s['elapsed_including_output'] if r['status']=='failed' else 0)
        if r.get('normal'):verify_checksums(folder/'normal',r['normal']['checksums'])
        if r['status']=='completed':
            diag=r['diagnostics'];timing=r['timing']
            warmed=[v['timing']['sample'] for v in r['warmed_eager_replays']]
            row.update(warmed_seconds=float(np.median(warmed)),normal_seconds=r['normal']['wall_seconds'],
                audit_api_seconds=timing['total'],normal_output_seconds=r['normal']['ordinary_output_seconds'],
                audit_output_seconds=s['output_seconds'],seconds_per_confirmed_transition=float(np.median(warmed))/diag['confirmed'],
                mapping_per_transition=diag['forward_evals']/n,jvp_per_transition=diag['jvp_evals']/n,
                iterations=diag['iterations'],confirmed=diag['confirmed'],clips=diag['clips'],residual=diag['residual'],
                host_scalar_reads=diag['host_scalar_reads'],host_scalar_wait_seconds=diag['host_scalar_wait_seconds'],
                tensor_device=diag['tensor_device'],memory=r['memory'],
                max_path_error=max(r['audit']['max_abs_path_error']),acceptance_mismatches=sum(r['audit']['acceptance_mismatches']),
                timing=timing)
            with np.load(folder/'raw.npz') as raw:
                draws=raw['draws'][:,t['discard']:]
                f,truth=functions(p['models'][t['model']],draws)
                if not np.isfinite(draws).all() or not np.isfinite(f).all():raise ValueError('nonfinite posterior output')
                row['estimate']=f.mean((0,1)).tolist();row['analytic_reference']=None if truth is None else truth.tolist()
                row['squared_error']=None if truth is None else ((f.mean((0,1))-truth)**2).tolist()
                row['reference_state']='unresolved_finite_reference' if truth is None else 'analytic'
                row['constant_functions']=np.flatnonzero(np.ptp(f,axis=(0,1))==0).tolist()
                if not pilot:
                    combined=np.concatenate((draws,f),axis=-1)
                    table=np.column_stack((np.repeat(np.arange(c['chains']),len(draws[0])),
                        np.tile(np.arange(len(draws[0])),c['chains']),combined.reshape(-1,combined.shape[-1])))
                    header=','.join(['chain','iteration']+[f'q{k+1}' for k in range(draws.shape[-1])]+[f'f{k+1}' for k in range(f.shape[-1])])
                    # Derived diagnostic inputs are outside immutable attempt contents.
                    target=root/'diagnostic-inputs'/tid/'diagnostic-input.csv';target.parent.mkdir(parents=True,exist_ok=True)
                    np.savetxt(target,table,delimiter=',',header=header,comments='',fmt='%.17g')
        rows.append(row)
    if seen!=set(expected):raise ValueError('missing task identities')
    paired=[];groups=defaultdict(list)
    for row in rows:
        if row['executor']=='sequential':continue
        matches=[x for x in rows if x['executor']=='sequential' and all(x[k]==row[k] for k in ['model','device','kernel','draws','chains','window','replicate'])]
        if len(matches)!=1:raise ValueError('paired sequential comparison missing or ambiguous')
        seq=matches[0]
        pair={k:row[k] for k in ['model','device','kernel','draws','chains','window','replicate']}
        pair['both_completed']=row['status']==seq['status']=='completed'
        if pair['both_completed']:
            pair.update(warmed_speed_ratio=seq['warmed_seconds']/row['warmed_seconds'],
                normal_speed_ratio=seq['normal_seconds']/row['normal_seconds'],
                audit_api_speed_ratio=seq['audit_api_seconds']/row['audit_api_seconds'],
                mapping_per_transition=row['mapping_per_transition'],jvp_per_transition=row['jvp_per_transition'])
        paired.append(pair)
        key=tuple(pair[k] for k in ['model','device','kernel','draws','chains','window'])
        groups[key].append(pair)
    grouped=[]
    for key,rr in sorted(groups.items()):
        g=dict(zip(['model','device','kernel','draws','chains','window'],key));ok=[r for r in rr if r['both_completed']]
        g.update(planned=len(rr),both_completed=len(ok),failed_pairs=len(rr)-len(ok))
        for metric in ['warmed_speed_ratio','normal_speed_ratio','audit_api_speed_ratio','mapping_per_transition','jvp_per_transition']:
            values=[r[metric] for r in ok]
            g[metric]=dict(median=float(np.median(values)),ci95=interval(values),values=values) if values else None
        grouped.append(g)
    accuracy=[]
    for key in sorted({(r['model'],r['device'],r['kernel'],r['executor'],r['draws']) for r in rows}):
        rr=[r for r in rows if (r['model'],r['device'],r['kernel'],r['executor'],r['draws'])==key]
        ok=[r for r in rr if r['status']=='completed'];a=dict(zip(['model','device','kernel','executor','draws'],key))
        a.update(planned=len(rr),completed=len(ok),failed=len(rr)-len(ok))
        if ok and ok[0]['squared_error'] is not None:
            errors=np.array([r['squared_error'] for r in ok]);a['function_mse']=errors.mean(0).tolist()
            a['function_mse_ci95']=[interval(errors[:,j],np.mean) for j in range(errors.shape[1])]
            a['reference_state']='analytic';a['conditional_on_completion']=len(ok)!=len(rr)
        else:a['reference_state']='unresolved_finite_reference'
        accuracy.append(a)
    summary=dict(scope='pilot' if pilot else 'windows-native-v1',planned=len(rows),completed=sum(r['status']=='completed' for r in rows),
        failed=sum(r['status']=='failed' for r in rows),all_attempt_seconds=sum(r['all_attempt_seconds'] for r in rows),
        failed_attempt_seconds=sum(r['failed_cost_seconds'] for r in rows),groups=grouped,accuracy=accuracy,
        source_commit=p['source_commit'],protocol_sha256=p.get('protocol_sha256'),analysis_sha256=sha(__file__),input_state_sha256=input_hashes,
        notes='Paired speed ratios are conditional on both completing; failed pair counts and all attempt costs retained. Bootstrap n=4 is limited. Logistic reference uncertainty unresolved. Eager execution includes Python control. No precise time-to-accuracy.')
    write_json(output/'summary.json',summary);write_json(output/'run-metrics.json',rows);write_json(output/'paired.json',paired)
    with (output/'paired.csv').open('w',newline='',encoding='utf-8') as f:
        fields=sorted(set().union(*(r.keys() for r in paired)));writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(paired)
    if not pilot:figure(grouped,output)
    print(summary['planned'],'tasks;',summary['failed'],'failed; all outputs verified')


def figure(groups,output):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    names=sorted({r['model'] for r in groups});fig,axes=plt.subplots(2,2,figsize=(12,7),sharey=True,layout='constrained')
    for i,device in enumerate(['cpu','cuda']):
        for j,kernel in enumerate(['mala','rwm']):
            ax=axes[i,j]
            for n,shift,marker,color in [(128,-.12,'o','#2463A0'),(512,.12,'s','#C27D19')]:
                rr=[r for r in groups if r['device']==device and r['kernel']==kernel and r['draws']==n]
                for r in rr:
                    metric=r['warmed_speed_ratio'];x=names.index(r['model'])+shift
                    if metric:
                        y=metric['median'];bounds=metric['ci95']
                        ax.errorbar(x,y,yerr=None if bounds is None else [[max(0,y-bounds[0])],[max(0,bounds[1]-y)]],fmt=marker,color=color,capsize=3)
                    if r['failed_pairs']:ax.text(x,.012,f"{r['failed_pairs']}/4 fail",rotation=90,va='bottom',ha='center',fontsize=7)
                ax.plot([],[],marker=marker,color=color,linestyle='none',label=f'{n} transitions / chain')
            ax.axhline(1,color='#444444',linestyle='--',linewidth=1)
            ax.set_yscale('log');ax.set_xticks(range(len(names)),names);ax.grid(axis='y',alpha=.2)
            ax.set_title(f"{device.upper()} · {'quasi-DEER / MALA' if kernel=='mala' else 'Picard / RWM'}")
            ax.set_ylabel('Sequential / time-executor seconds')
    axes[0,0].legend(frameon=False,fontsize=9)
    fig.suptitle('Native Windows: paired warmed eager execution',fontsize=15)
    fig.supxlabel('4 paired independent tapes per cell; 95% replicate-bootstrap intervals; speed > 1 favors time executor',fontsize=10)
    fig.savefig(output/'speed-ratios.png',dpi=180);fig.savefig(output/'speed-ratios.pdf');plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--pilot',action='store_true');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);analyze(a.run,a.output,a.pilot)
