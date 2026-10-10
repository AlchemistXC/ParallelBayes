#!/usr/bin/env python3
"""Reconstruct H1 tables and explanatory figures from immutable companion outputs."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'benchmark/analysis'))
from layout_check import require_matplotlib_panel_alignment
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save_json(p,o):
    Path(p).write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def export(fig,stem,contract):
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(stem)+'.alignment.json',
        tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
    fig.savefig(str(stem)+'.pdf')
    fig.savefig(str(stem)+'.svg')
    fig.savefig(str(stem)+'.png',dpi=300)
    save_json(str(stem)+'.contract.json',contract)
    plt.close(fig)


def build(source,output):
    source=Path(source);output=Path(output)
    if output.exists(): raise FileExistsError(output)
    summary=json.loads((source/'SUMMARY.json').read_text())
    records=[]
    for name,digest in summary['results_sha256'].items():
        p=source/name/'result.json'
        if sha(p)!=digest:raise ValueError('Companion result changed')
        record=json.loads(p.read_text())
        for file,d in record['outputs_sha256'].items():
            if sha(source/name/file)!=d:raise ValueError('Companion array changed')
        records.append(record)
    if len(records)!=80:raise ValueError('Complete selected set required')
    records.sort(key=lambda r:(r['task']['replicate'],r['task']['budget'],r['task']['device'],r['task']['executor']))
    output.mkdir(parents=True)
    table=[]; index=[]
    for k,r in enumerate(records):
        t=r['task'];index.append(dict(row=k+1,**t))
        for m in r['metrics']:
            table.append(dict(task_row=k+1,task_id=t['id'],replicate=t['replicate'],budget=t['budget'],device=t['device'],executor=t['executor'],original_outcome=t['original_outcome'],**{key:value for key,value in m.items() if key not in ('event_positions','nonfinite_positions','maximum_location')}))
    fields=list(dict.fromkeys(key for row in table for key in row))
    with (output/'function-differences.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(table)
    with (output/'task-index.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(index[0]));w.writeheader();w.writerows(index)
    peaks=[]
    for function in ('v_over_3','tanh_v_over_3','x1_positive','cos_z1'):
        selected=[x for x in table if x['scope']=='retained' and x['chain']=='pooled' and x['function']==function]
        peak=max(selected,key=lambda x:x['max_abs']);mean=max(selected,key=lambda x:abs(x['signed_mean']))
        peaks.append(dict(function=function,max_abs_point=peak['max_abs'],point_task=peak['task_id'],max_abs_pooled_mean=abs(mean['signed_mean']),mean_task=mean['task_id']))
    save_json(output/'maxima.json',peaks)
    mpl.rcParams.update({"font.family":"sans-serif", "font.sans-serif":["DejaVu Sans"],
        "font.size":9, "axes.titlesize":9, "axes.labelsize":9, "legend.fontsize":8.5,
        "xtick.labelsize":8.5, "ytick.labelsize":8.5, "legend.frameon":False,
        "axes.spines.top":False, "axes.spines.right":False, "axes.linewidth":.65,
        "pdf.fonttype":42, "svg.fonttype":"none", "axes.formatter.use_mathtext":False})
    styles={'v_over_3':('#0072B2','v / 3'),'tanh_v_over_3':('#D55E00','tanh(v / 3)'),'cos_z1':('#009E73','cos(z1)')}
    selected=[x for x in table if x['scope']=='retained' and x['chain']=='pooled']
    matched=defaultdict(dict)
    for x in selected:matched[(x['replicate'],x['budget'],x['device'],x['function'])][x['executor']]=x
    assert len(matched)==160 and all(set(pair)=={'sequential','quasi_deer'} for pair in matched.values())
    fig,axes=plt.subplots(1,2,figsize=(7.2047244,4.0944882))
    fig.subplots_adjust(left=.10,right=.985,bottom=.27,top=.77,wspace=.4)
    for key,pair in matched.items():
        if key[-1]=='x1_positive':continue
        color,label=styles[key[-1]]
        axes[0].plot(pair['sequential']['max_abs'],pair['quasi_deer']['max_abs'],'o',ms=3.0,color=color,alpha=.6,mew=0)
    for x in selected:
        if x['function']=='x1_positive':continue
        color,label=styles[x['function']]
        axes[1].plot(x['max_abs'],abs(x['signed_mean']),marker='o' if x['executor']=='sequential' else '^',ls='none',ms=3,color=color,alpha=.6,mew=0)
    for ax in axes:
        ax.set_xscale('symlog',linthresh=1e-16);ax.set_yscale('symlog',linthresh=1e-16)
        ax.set_xlim(-3e-17,.01);ax.set_ylim(-3e-17,.01)
        ticks=[0,1e-12,1e-8,1e-4]
        for axis in (ax.xaxis,ax.yaxis):
            axis.set_major_locator(FixedLocator(ticks));axis.set_major_formatter(FuncFormatter(lambda v,_:'0' if v==0 else f'{v:.0e}'))
        ax.plot([0,.01],[0,.01],ls='--',color='#999999',lw=.6,zorder=0)
        ax.tick_params(length=2)
    axes[0].set_title('a  Paired path discrepancies',loc='left',pad=10)
    axes[0].set_xlabel('Sequential: maximum point difference')
    axes[0].set_ylabel('quasi-DEER: maximum point difference')
    axes[1].set_title('b  Local versus averaged difference',loc='left',pad=10)
    axes[1].set_xlabel('Maximum point difference')
    axes[1].set_ylabel('Absolute four-chain mean difference')
    handles=[Line2D([],[],color=c,marker='o',ls='none',ms=4,label=n) for c,n in styles.values()]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.54,.98),ncol=3)
    fig.legend(handles=[Line2D([],[],color='#555555',marker=m,ls='none',ms=4,label=l) for m,l in [('o','Sequential'),('^','quasi-DEER')]],loc='lower center',bbox_to_anchor=(.55,.04),ncol=2)
    contract=dict(question='How do paired executor path errors propagate to declared functions?',core_conclusion='Pointwise discrepancies are larger than pooled mean discrepancies in these saved paths; original failures remain excluded.',backend='python',archetype='quantitative grid',panel_roles=['paired executor contrast','pointwise-to-mean decomposition'],source='function-differences.csv',tasks=80,paired_inputs_device_budget=40,original_input_labels=13,original_failed=42,independent_n_not_80=True,functions_shown=list(styles),omitted_function_rule='x1_positive identically zero difference on all saved full paths; reported explicitly in caption and complete source table',all_continuous_tasks_shown=True,scales='symlog, linear region 1e-16; zeros not replaced',intervals='none; deterministic differences, no independent-task CI',reference='independent NumPy float64',retained_only=True)
    export(fig,output/'h1-function-pairs',contract)
    # Every saved task and every transition contributes to a maximum within one of 128 time bins.
    matrices=[];bin_rows=[]
    for fidx in (0,3):
        matrix=[]
        for k,r in enumerate(records):
            with np.load(source/r['task']['id']/'differences.npz') as z:a=np.abs(z['function_delta'][:,:,fidx]).max(axis=0)
            bins=np.array_split(np.arange(len(a)),128)
            values=[float(a[b].max()) for b in bins];matrix.append(values)
            bin_rows.extend(dict(task_row=k+1,function=('v_over_3' if fidx==0 else 'cos_z1'),bin=j,first_transition=int(b[0]+1),last_transition=int(b[-1]+1),maximum=values[j]) for j,b in enumerate(bins))
        matrices.append(np.asarray(matrix))
    with (output/'position-bins.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(bin_rows[0]));w.writeheader();w.writerows(bin_rows)
    fig,axes=plt.subplots(1,2,figsize=(7.2047244,5.2755906))
    fig.subplots_adjust(left=.09,right=.985,bottom=.15,top=.86,wspace=.34)
    from matplotlib.colors import SymLogNorm
    norm=SymLogNorm(linthresh=1e-12,vmin=0,vmax=max(m.max() for m in matrices),base=10)
    for j,(ax,matrix,label) in enumerate(zip(axes,matrices,['v / 3','cos(z1)'])):
        ax.imshow(matrix,origin='lower',aspect='auto',extent=(0,1,.5,80.5),cmap='cividis',norm=norm,interpolation='nearest',rasterized=True)
        ax.set_title(chr(97+j)+'  '+label,loc='left',pad=9)
        ax.set_xlabel('Fraction of saved trajectory');ax.set_ylabel('Task row (see source index)')
        ax.set_yticks([1,20,40,60,80]);ax.set_xticks([0,.5,1]);ax.tick_params(length=2)
    # Shared colour scale outside comparable plot rectangles.
    from matplotlib.cm import ScalarMappable
    cax=fig.add_axes([.32,.94,.40,.024]);cax.set_gid('auxiliary-colorbar')
    cb=fig.colorbar(ScalarMappable(norm=norm,cmap='cividis'),cax=cax,orientation='horizontal')
    cb.set_ticks([0,1e-8,1e-4]);cb.set_ticklabels(['0','1e-8','1e-4']);cb.ax.tick_params(labelsize=8.5,length=2)
    cb.ax.set_title('Maximum absolute function difference',fontsize=9,pad=4)
    # Record first-party equal-grid measurement; auxiliary colorbar excluded by its role.
    export(fig,output/'h1-function-locations',dict(question='Where along all saved paths do discrepancies occur?',core_conclusion='Display all positions without selecting favourable windows.',backend='python',archetype='quantitative grid',panel_roles=['unbounded linear function','bounded nonlinear function'],source='position-bins.csv',tasks=80,original_input_labels=13,bins=128,bin_rule='maximum over all four chains and all transitions in each bin; full path includes discarded prefix',interpolation=False,selection='all selected tasks; other two functions remain in complete numeric table',intervals='none; descriptive fixed-input differences'))
    save_json(output/'provenance.json',dict(source_summary_sha256=sha(source/'SUMMARY.json'),report_source_sha256=sha(__file__),input_results=summary['results_sha256'],new_sampler_calls=0,source_data_sha256={p.name:sha(p) for p in output.glob('*.csv')}))
    print(json.dumps(dict(tasks=80,function_rows=len(table),position_bins=len(bin_rows),output=str(output))))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    build(**vars(p.parse_args()))
