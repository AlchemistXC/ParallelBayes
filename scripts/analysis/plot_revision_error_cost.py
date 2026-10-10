#!/usr/bin/env python3
"""Presentation-only projection of four declared functions from verified statistics."""
import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/analysis')]
from formal_report import StatisticsBundle, model_tables, DISPLAY
from formal_publication_plots import configure, save, STYLES
from formal_runtime import file_hash
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import LogLocator, NullFormatter, FixedLocator, FuncFormatter

PANELS = [('G1', 'standard_q1', 'G1: standardised first parameter'),
          ('G2', 'standard_q1', 'G2: standardised first parameter'),
          ('H1', 'v_over_3', 'H1: centred funnel, v / 3'),
          ('H2', 'v_over_3', 'H2: noncentred funnel, v / 3')]


def build(statistics_directory, manifest_sha256, output):
    out = Path(output)
    if out.exists(): raise FileExistsError(out)
    bundle = StatisticsBundle(statistics_directory, manifest_sha256)
    if not bundle.compact_frame or bundle.frame['main_planned'] != 3888:
        raise ValueError('Full compact study required')
    rows=[]
    for model, function, title in PANELS:
        table = model_tables(bundle, model)[1]
        selected = [dict(model=model, **r) for r in table['errors']
                    if r['phase']=='ordinary_workflow' and r['function']==function]
        if len(selected)!=18 or len({(r['workflow'],r['budget']) for r in selected})!=18:
            raise ValueError('Expected all nine workflows and both budgets')
        if any(not r['plot_point'] or r['point']<=0 or r['mean_seconds']<=0 for r in selected):
            raise ValueError('This log-scale projection requires all 72 finite positive saved points')
        rows += selected
    out.mkdir(parents=True)
    cols=['model','function','workflow','budget','planned','available','point','low','high',
          'mean_seconds','cost_low','cost_high','interval_status','cost_interval_status']
    with (out/'source.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)
    configure()
    fig,axes=plt.subplots(2,2,figsize=(160/25.4,183/25.4))
    fig.subplots_adjust(left=.13,right=.97,bottom=.245,top=.93,hspace=.52,wspace=.48)
    for k,(ax,(model,function,title)) in enumerate(zip(axes.flat,PANELS)):
        selected=[r for r in rows if r['model']==model]
        for r in selected:
            color, marker = STYLES[r['workflow']]
            x,y=r['mean_seconds'],r['point']
            if r['low'] is not None: ax.plot([x,x],[r['low'],r['high']],lw=.6,color=color,alpha=.75)
            if r['cost_low'] is not None: ax.plot([r['cost_low'],r['cost_high']],[y,y],lw=.6,color=color,alpha=.75)
            ax.plot(x,y,marker=marker,ls='none',ms=3.4 if r['budget']==1024 else 5.2,
                    color=color,mew=.7,mfc=color if r['low'] is not None and r['cost_low'] is not None else 'white')
        ax.set_xscale('log');ax.set_yscale('log');ax.set_xlim(2,120)
        ax.xaxis.set_major_locator(LogLocator(base=10,numticks=3));ax.xaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_locator(LogLocator(base=10,numticks=4));ax.yaxis.set_minor_formatter(NullFormatter())
        if model=='H1':
            ax.yaxis.set_major_locator(FixedLocator([.05,.1,.2,.5]))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f'{v:g}'))
        ax.set_title(chr(97+k)+'  '+title.replace(': ',':\n'),loc='left',pad=9,fontsize=9)
        ax.set_xlabel('Ordinary workflow time (s)')
        ax.set_ylabel('Conditional MSE')
        ax.tick_params(axis='both',which='both',length=2.5)
    handles=[Line2D([],[],color=c,marker=m,ls='none',ms=4,label=DISPLAY[w]) for w,(c,m) in STYLES.items()]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.53,.17),ncol=3,
               columnspacing=1.4,handletextpad=.4)
    sizes=[Line2D([],[],color='#555555',marker='o',mfc='none',ls='none',ms=s,
                  label=f'{n} draws/chain') for n,s in [(1024,3.4),(4096,5.2)]]
    fig.legend(handles=sizes,loc='upper center',bbox_to_anchor=(.53,.055),ncol=2)
    contract=dict(question='How do kernel choice and parameterisation change fixed-budget error and workflow time?',
        core_conclusion='Same-kernel time executors change cost without improving paired trajectory information; kernel and parameterisation differences remain material',
        archetype='quantitative grid',backend='Python/matplotlib',
        selection='Retrospective explanatory projection: G1 low-dimensional reference, G2 higher-dimensional whitened Gaussian, H1/H2 a common funnel estimand in different parameterisations. No selection by favourable speed ratio. All other functions remain in full annex.',
        panel_roles=['Simple-target cost','Dimension after full whitening','Centred stress target','Alternative parameterisation'],
        source_manifest_sha256=manifest_sha256,source_table='source.csv',displayed_points=72,
        budgets=[1024,4096],points=[{k:r[k] for k in cols} for r in rows],
        interval='Saved pointwise 95% BCa on complete four-chain units, minimum 20 valid repeats; no new intervals or multiplicity correction',
        failure_rule='All planned denominators remain 24; hollow points indicate unavailable intervals, not accepted failures',
        interpolation=False,new_sampler_calls=0,new_estimates=0,
        caveat='G2 was fully whitened. H1/H2 do not represent the same original-scale kernel. Success-conditional workflow points need not have identical valid sets.')
    save(fig,out/'error-cost-overview',contract=contract)
    (out/'SHA256.json').write_text(json.dumps({p.name:file_hash(p) for p in out.iterdir() if p.is_file()},indent=2)+'\n')
    print(json.dumps({'points':len(rows),'output':str(out),'new_sampler_calls':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in ('statistics-directory','manifest-sha256','output'):p.add_argument('--'+a,required=True)
    build(**vars(p.parse_args()))
