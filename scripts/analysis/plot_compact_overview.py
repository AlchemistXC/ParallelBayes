#!/usr/bin/env python3
"""All compact same-kernel ordinary-cost contrasts, without new statistics."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'benchmark/analysis')]
from formal_report import StatisticsBundle, model_tables, MODELS
from formal_publication_plots import configure, save
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter
from formal_runtime import file_hash


def select_complete_contrasts(tables):
    selected=[]
    for model in MODELS:
        rows=tables[model]['ratios']
        for device in ('cpu','cuda'):
            for kernel,executor in (('rwm','online_picard'),('mala','quasi_deer')):
                for budget in (1024,4096):
                    found=[r for r in rows if r['phase']=='ordinary_workflow' and
                           r['kind']=='same_kernel_execution' and r['budget']==budget and
                           r['workflow_a']==f'{device}-{kernel}-sequential' and
                           r['workflow_b']==f'{device}-{kernel}-{executor}']
                    if len(found)!=1: raise ValueError('Missing or duplicate declared contrast')
                    r=found[0]
                    if r['planned']!=24 or not 0<=r['paired']<=24:
                        raise ValueError('Paired denominator differs')
                    if (r['low'] is None)!=(r['high'] is None):
                        raise ValueError('One-sided missing interval')
                    for v in (r['point'],r['low'],r['high']):
                        if v is not None and (not math.isfinite(v) or v<=0):
                            raise ValueError('Positive finite cost ratio required')
                    selected.append(dict(model=model,device=device,kernel=kernel,executor=executor,**r))
    return selected


def build(statistics_directory,manifest_sha256,output,preview=False):
    out=Path(output)
    if out.exists(): raise FileExistsError(out)
    bundle=StatisticsBundle(statistics_directory,manifest_sha256)
    if not bundle.compact_frame or set(bundle.models)!=set(MODELS) or bundle.frame['scope']!='formal_inference':
        raise ValueError('Complete compact research statistics required')
    tables={m:model_tables(bundle,m)[1] for m in MODELS}
    rows=select_complete_contrasts(tables);assert len(rows)==72
    out.mkdir(parents=True)
    columns=['model','device','kernel','executor','budget','phase','workflow_a','workflow_b',
             'planned','paired','point','low','high','interval_status']
    with (out/'source.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore',lineterminator='\n')
        writer.writeheader();writer.writerows(rows)
    contract=dict(question='Do ordinary same-kernel cost gains persist across devices, kernels and all declared models?',
        core_conclusion='Ordinary time-executor benefits depend on device and kernel; all tested model/budget contrasts are shown',
        archetype='quantitative grid',backend='Python/matplotlib',
        panel_roles=['CPU Picard comparison','CUDA Picard device boundary','CPU quasi-DEER kernel boundary','CUDA quasi-DEER device/kernel boundary'],
        source_statistics_manifest_sha256=manifest_sha256,source_table='source.csv',
        frame=bundle.frame,original_planned_contrasts=72,displayed_contrasts=len(rows),
        selection_rule='All nine models, two budgets, two kernels and two devices; ordinary workflow costs only. Prepared and audit costs remain in complete supplementary report.',
        independent_unit='One original four-chain input per model; 24 planned. Shared budgets, kernels and devices do not increase n.',
        center='Geometric mean of within-input sequential/time-executor cost',
        interval='Saved pointwise conditional 95% BCa, 9999 resamples; at least 20 common valid inputs. Not simultaneous intervals.',
        missing='Missing interval shown by open marker; missing point has no mark but retains denominator and source row.',
        preview_original_reconstruction_pending=preview,new_sampler_calls=0,new_statistical_estimates=0)
    configure();fig,axes=plt.subplots(2,2,figsize=(160/25.4,170/25.4))
    fig.subplots_adjust(left=.115,right=.90,bottom=.13,top=.86,wspace=.60,hspace=.48)
    colors={1024:'#376b9c',4096:'#a66025'};markers={1024:'o',4096:'^'};offsets={1024:-.16,4096:.16}
    values=[v for r in rows for v in (r['point'],r['low'],r['high']) if v is not None]
    lower=min(.08,min(values)/1.2);upper=max(2.1,max(values)*1.2)
    ticks=[m*10.**p for p in range(math.floor(math.log10(lower)),math.ceil(math.log10(upper))+1) for m in (1.,2.,5.) if lower<=m*10.**p<=upper]
    cells=[]
    for index,(ax,device,kernel,label) in enumerate(zip(axes.flat,('cpu','cuda','cpu','cuda'),('rwm','rwm','mala','mala'),('CPU · Picard RWM','CUDA · Picard RWM','CPU · quasi-DEER MALA','CUDA · quasi-DEER MALA'))):
        ax.axvline(1.,color='#929292',lw=.65,zorder=0)
        for y,model in enumerate(MODELS):
            for budget in (1024,4096):
                r=next(r for r in rows if (r['model'],r['device'],r['kernel'],r['budget'])==(model,device,kernel,budget))
                yy=y+offsets[budget];color=colors[budget]
                if r['low'] is not None:ax.plot([r['low'],r['high']],[yy,yy],color=color,lw=.8)
                if r['point'] is not None:ax.plot(r['point'],yy,marker=markers[budget],ms=3.5,color=color,linestyle='none',mew=.7,markerfacecolor=color if r['low'] is not None else 'white')
                cells.append(dict(model=model,device=device,kernel=kernel,budget=budget,paired=r['paired'],point_available=r['point'] is not None,interval_available=r['low'] is not None))
            ns=[next(r for r in rows if (r['model'],r['device'],r['kernel'],r['budget'])==(model,device,kernel,b)) for b in (1024,4096)]
            count='/'.join(str(r['paired'])+('*' if r['point'] is None else '') for r in ns)
            ax.text(1.05,y,count,transform=ax.get_yaxis_transform(),ha='left',va='center',fontsize=8.5)
        ax.set_title(chr(97+index)+'  '+label,loc='left',pad=12,fontsize=9)
        ax.set_xscale('log');ax.set_xlim(lower,upper);ax.set_ylim(len(MODELS)-.4,-.6)
        ax.xaxis.set_major_locator(FixedLocator(ticks));ax.xaxis.set_major_formatter(FuncFormatter(lambda v,_:f'{v:g}'));ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_yticks(range(len(MODELS)),MODELS);ax.tick_params(axis='y',length=0)
        ax.text(1.05,1.025,'n',transform=ax.transAxes,fontsize=8.5)
    fig.legend(handles=[Line2D([],[],color=colors[b],marker=markers[b],ls='-',ms=4,label=f'{b} draws/chain') for b in (1024,4096)],ncol=2,loc='upper center',bbox_to_anchor=(.52,.942),columnspacing=2.5)
    fig.text(.51,.06,'Ordinary workflow cost ratio: sequential / time executor',ha='center',fontsize=9)
    if preview:fig.text(.5,.985,'RAW RECONSTRUCTION PENDING — LAYOUT PREVIEW',ha='center',va='top',fontsize=9,color='#8b3e34')
    contract['cells']=cells
    save(fig,out/'ordinary-cost-overview',contract=contract)
    inventory={p.name:file_hash(p) for p in out.iterdir() if p.is_file()}
    (out/'SHA256.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print(json.dumps(dict(contrasts=len(rows),intervals=sum(r['low'] is not None for r in rows),preview=preview,output=str(out))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('statistics-directory','manifest-sha256','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--preview',action='store_true')
    build(**vars(p.parse_args()))
