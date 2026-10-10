"""Readable publication derivative of formal_plots; saved statistics are unchanged.

The historical renderer and frozen Windows figures remain available separately.
All dimensions are final physical dimensions; captions carry methodological detail.
"""
import math
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'pb-formal-report-mpl'))
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter,NullFormatter,MaxNLocator,FixedLocator,ScalarFormatter
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'benchmark/analysis')]
from formal_report import DISPLAY
from formal_runtime import atomic_json,file_hash
from layout_check import require_matplotlib_panel_alignment

STYLES={
 'cpu-rwm-sequential':('#376b9c','o'),'cpu-rwm-online_picard':('#376b9c','s'),
 'cuda-rwm-sequential':('#54a5b3','^'),'cuda-rwm-online_picard':('#54a5b3','D'),
 'cpu-mala-sequential':('#a66025','o'),'cpu-mala-quasi_deer':('#a66025','s'),
 'cuda-mala-sequential':('#b9899d','^'),'cuda-mala-quasi_deer':('#b9899d','D'),
 'cpu-nuts-spawn_chains':('#353b44','*')}


def configure():
    mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],
        'font.size':9,'axes.titlesize':9,'axes.labelsize':9,'xtick.labelsize':8.5,'ytick.labelsize':8.5,
        'legend.fontsize':8.5,'legend.frameon':False,'axes.spines.top':False,'axes.spines.right':False,
        'axes.linewidth':.65,'pdf.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'parallelbayes-publication-layout-v1',
        'axes.formatter.use_mathtext':False})


def mark(fig,fixture,technical):
    if fixture:fig.text(.5,.98,'ARTIFICIAL TEST DATA — NOT RESEARCH RESULTS',ha='center',va='top',fontsize=9,color='#8b3e34',weight='bold')
    elif technical:fig.text(.5,.98,'TECHNICAL VALIDATION — NOT FORMAL INFERENCE',ha='center',va='top',fontsize=9,weight='bold')


def signed_axis(ax,which,values):
    """Keep real zeros/negative differences; never substitute plotting epsilon."""
    values=[v for v in values if v is not None]
    nonzero=[abs(v) for v in values if v!=0]
    setter=ax.set_xscale if which=='x' else ax.set_yscale
    if nonzero and max(nonzero)/min(nonzero)>=100:
        threshold=max(1e-300,10.**max(-300,math.floor(math.log10(min(nonzero)))-1))
        setter('symlog',linthresh=threshold,linscale=.75)
        result=dict(scale='symlog',linear_threshold=threshold,zero_values_replaced=False)
    else:
        result=dict(scale='linear',linear_threshold=None,zero_values_replaced=False)
        (ax.xaxis if which=='x' else ax.yaxis).set_major_locator(MaxNLocator(nbins=4,min_n_ticks=3))
    axis=ax.xaxis if which=='x' else ax.yaxis
    if result['scale']=='linear':
        formatter=ScalarFormatter(useOffset=False,useMathText=False)
        formatter.set_powerlimits((-3,4));axis.set_major_formatter(formatter)
    else:
        axis.set_major_formatter(FuncFormatter(lambda x,_:f'{x:.3g}'))
    if result['scale']=='symlog':
        lo,hi=sorted(ax.get_xlim() if which=='x' else ax.get_ylim())
        ticks=[v for v in axis.get_majorticklocs() if lo<=v<=hi]
        if len(ticks)>5:
            negatives=[v for v in ticks if v<0];positives=[v for v in ticks if v>0]
            ticks=sorted(set(([min(negatives),max(negatives)] if negatives else [])+
                             ([0.] if lo<=0<=hi else [])+
                             ([min(positives),max(positives)] if positives else [])))
            axis.set_major_locator(FixedLocator(ticks))
    axis.set_minor_formatter(NullFormatter())
    return result


def segment(ax,point,lo,hi,y,*,color='#376b9c'):
    # BCa bounds need not contain their point estimator: draw bounds directly.
    if lo is not None and hi is not None:ax.plot([lo,hi],[y,y],color=color,lw=.8,zorder=2)
    if point is not None:
        ax.plot(point,y,'o',markersize=3.1,color=color,markerfacecolor=color if lo is not None else 'white',markeredgewidth=.65,zorder=3)


def save(fig,stem,*,contract):
    fig.canvas.draw()
    labels=[]
    for number,ax in enumerate(fig.axes):
        for direction in ('x','y'):
            axis=ax.xaxis if direction=='x' else ax.yaxis
            lower,upper=sorted(ax.get_xlim() if direction=='x' else ax.get_ylim())
            values=[(float(loc),label.get_text()) for loc,label in zip(axis.get_majorticklocs(),axis.get_majorticklabels())
                    if lower<=loc<=upper and label.get_visible() and label.get_text()]
            if len({label for _,label in values})!=len(values):
                raise ValueError('Repeated visible tick labels: '+str((number,direction,values)))
            labels.append(dict(panel=number,axis=direction,ticks=values,offset=axis.get_offset_text().get_text()))
    contract['visible_ticks']=labels
    require_matplotlib_panel_alignment(fig,json_out=str(stem)+'.alignment.json',overlay_svg=str(stem)+'.alignment.svg',
        tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
    fig.savefig(str(stem)+'.pdf',metadata={'Creator':'ParallelBayes','CreationDate':None,'ModDate':None})
    fig.savefig(str(stem)+'.svg',metadata={'Date':None})
    fig.savefig(str(stem)+'.png',dpi=300)
    plt.close(fig)
    atomic_json(str(stem)+'.contract.json',dict(contract,physical_width_mm=float(fig.get_figwidth()*25.4),physical_height_mm=float(fig.get_figheight()*25.4),minimum_requested_font_pt=8.5,
        layout_identity='publication-layout-v1',
        exported_pdf_sha256=file_hash(str(stem)+'.pdf'),uncertainty='Saved pointwise 95% whole-four-chain BCa intervals; no simultaneous coverage',
        missing_intervals='Open points; no zero-width substitute. Unavailable points have no plotted mark.',
        scientific_claim='Fixed declared configurations only; no convergence or precise time-to-accuracy claim'))


def execution_figure(name,tables,dest,*,fixture,technical):
    frame=sorted({(r['workflow_a'],r['workflow_b'],r['budget']) for r in tables['ratios'] if r['kind']=='same_kernel_execution'})
    if not frame:return None
    ratios={(r['phase'],r['workflow_a'],r['workflow_b'],r['budget']):r for r in tables['ratios'] if r['kind']=='same_kernel_execution'}
    phases=['cached_executor','ordinary_workflow','research_execution'];titles=['Prepared executor','Ordinary workflow','Research audit']
    fig,axes=plt.subplots(3,1,figsize=(160/25.4,max(190.,70.+14.*len(frame))/25.4))
    fig.subplots_adjust(left=.28,right=.91,bottom=.17,top=.88,hspace=.70)
    shown=[]
    for k,(ax,phase,title) in enumerate(zip(axes,phases,titles)):
        ax.set_title(title,pad=13);ax.annotate(chr(97+k),xy=(0,1),xycoords='axes fraction',xytext=(-7,9),textcoords='offset points',weight='bold',fontsize=9)
        ax.axvline(1.,color='#9ca5ad',lw=.65,zorder=0)
        values=[1.]
        for y,(a,b,budget) in enumerate(frame):
            r=ratios.get((phase,a,b,budget));point=None if r is None else r['point']
            lo,hi=(None,None) if r is None else (r['low'],r['high'])
            if any(v is not None and v<=0 for v in (point,lo,hi)):raise ValueError('Positive ratio scale required')
            values.extend(v for v in (point,lo,hi) if v is not None)
            segment(ax,point,lo,hi,y,color=STYLES[b][0])
            count='—' if r is None else str(r['paired'])+('*' if point is None else '')
            ax.text(1.035,y,count,transform=ax.get_yaxis_transform(),va='center',fontsize=8.5)
            shown.append(dict(phase=phase,workflow_a=a,workflow_b=b,budget=budget,point_available=point is not None,
                interval_available=lo is not None,paired=None if r is None else r['paired'],status='unavailable_phase' if r is None else r['interval_status']))
        ax.set_xscale('log');ax.xaxis.set_major_formatter(FuncFormatter(lambda x,_:f'{x:.2g}'))
        ax.xaxis.set_minor_formatter(NullFormatter())
        lo,hi=min(values)/1.25,max(values)*1.25
        ticks=[m*10.**p for p in range(math.floor(math.log10(lo)),math.ceil(math.log10(hi))+1) for m in (1.,2.,5.) if lo<=m*10.**p<=hi]
        if len(ticks)>6:
            step=math.ceil(len(ticks)/5)
            ticks=sorted(set(ticks[::step]+[1.]))
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.set_xlim(min(values)/1.25,max(values)*1.25);ax.set_ylim(len(frame)-.45,-.65)
        ax.set_xlabel('Sequential / time-executor cost')
        ax.set_yticks(range(len(frame)),[DISPLAY[a].removesuffix(' seq')+' · '+str(budget) for a,_,budget in frame])
        ax.tick_params(axis='y',length=0)
    mark(fig,fixture,technical)
    fig.text(.5,.94,name+' | Same-kernel execution costs',ha='center',weight='bold',fontsize=10)
    fig.text(.5,.035,'Geometric paired ratios; >1 favours the time executor.\n'
        'Pointwise 95% BCa intervals; right labels: paired n.\n'
        'Open points: interval unavailable; *: point unavailable.',ha='center',fontsize=8.5,linespacing=1.3)
    stem=dest/'execution-costs';save(fig,stem,contract=dict(role='Compare prepared, ordinary and audit costs without adding nested scopes',
        panels=titles,cells=shown,source_table='ratios.csv',fixture=fixture))
    return dict(model=name,kind='execution_costs',file=name+'/'+stem.name+'.pdf',source_table=name+'/ratios.csv',panels=3)


def inference_figure(name,function,index,tables,dest,*,fixture,technical):
    errors=[r for r in tables['errors'] if r['function']==function and r['phase']=='ordinary_workflow']
    contrasts=sorted([r for r in tables['paired_errors'] if r['function']==function and r['kind']=='end_to_end_workflow'],key=lambda r:(r['workflow_a'],r['budget']))
    if not errors:return None
    fig,axes=plt.subplots(2,1,figsize=(160/25.4,max(210.,130.+5.*len(contrasts))/25.4))
    fig.subplots_adjust(left=.30,right=.92,bottom=.10,top=.90)
    axes[0].set_position([.30,.64,.62,.25])
    axes[1].set_position([.30,.115,.62,.30])
    ax,bx=axes;seen=[];xvalues=[];yvalues=[]
    budgets=sorted({r['budget'] for r in errors});sizes={b:4.+1.5*j for j,b in enumerate(budgets)}
    for r in errors:
        plotted=r['plot_point'];seen.append(dict(workflow=r['workflow'],budget=r['budget'],plotted=plotted,
            available=r['available'],planned=r['planned'],error_interval=r['interval_status'],cost_interval=r['cost_interval_status']))
        if not plotted:continue
        x,y=r['mean_seconds'],r['point'];color,marker=STYLES[r['workflow']]
        if x is None or y is None or min(x,y)<0:raise ValueError('Nonnegative available error-cost coordinates required')
        if r['low'] is not None:ax.plot([x,x],[r['low'],r['high']],lw=.65,color=color,alpha=.8)
        if r['cost_low'] is not None:ax.plot([r['cost_low'],r['cost_high']],[y,y],lw=.65,color=color,alpha=.8)
        ax.plot(x,y,marker=marker,color=color,ms=sizes[r['budget']],linestyle='none',mew=.7,
                markerfacecolor=color if r['low'] is not None and r['cost_low'] is not None else 'none')
        xvalues.extend(v for v in (x,r['cost_low'],r['cost_high']) if v is not None)
        yvalues.extend(v for v in (y,r['low'],r['high']) if v is not None)
    scales=dict(cost=signed_axis(ax,'x',xvalues),error=signed_axis(ax,'y',yvalues))
    kind=errors[0]['reference_kind'];ylabel='Conditional MSE' if kind=='analytic' else 'Conditional squared discrepancy'
    if not xvalues:
        ax.text(.5,.5,'No eligible error–cost point',ha='center',transform=ax.transAxes,fontsize=8.5)
        ax.set_xticks([]);ax.set_yticks([])
    ax.set_xlabel('Mean ordinary workflow time (s)'+(' [symlog]' if scales['cost']['scale']=='symlog' else ''));ax.set_ylabel(ylabel+(' [symlog]' if scales['error']['scale']=='symlog' else ''));ax.set_title('Fixed-budget error and cost',pad=13)
    bx.axvline(0.,lw=.65,color='#9ca5ad',zorder=0);bounds=[]
    for y,r in enumerate(contrasts):
        segment(bx,r['point'],r['low'],r['high'],y,color=STYLES[r['workflow_a']][0])
        bounds.extend(v for v in (r['point'],r['low'],r['high']) if v is not None)
        bx.text(1.035,y,str(r['paired'])+('*' if r['point'] is None else ''),transform=bx.get_yaxis_transform(),va='center',fontsize=8.5)
    scales['difference']=signed_axis(bx,'x',bounds)
    if not bounds:bx.set_xticks([])
    bx.set_ylim(max(1,len(contrasts))-.45,-.65)
    bx.set_yticks(range(len(contrasts)),[DISPLAY[r['workflow_a']]+' · '+str(r['budget']) for r in contrasts]);bx.tick_params(axis='y',length=0)
    bx.set_xlabel('MH loss − CPU NUTS loss'+(' [symlog]' if scales['difference']['scale']=='symlog' else ''));bx.set_title('Paired loss difference',pad=13)
    if not contrasts:bx.text(.5,.5,'No declared NUTS contrast',ha='center',transform=bx.transAxes,fontsize=8.5)
    for k,axis in enumerate(axes):axis.annotate(chr(97+k),xy=(0,1),xycoords='axes fraction',xytext=(-7,9),textcoords='offset points',weight='bold',fontsize=9)
    workflows=sorted({r['workflow'] for r in errors})
    handles=[Line2D([],[],color=STYLES[w][0],marker=STYLES[w][1],ls='none',ms=4,label=DISPLAY[w]) for w in workflows]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,.565),ncol=3,columnspacing=1.5,handletextpad=.5)
    budget_handles=[Line2D([],[],color='#555555',marker='o',markerfacecolor='none',ls='none',ms=sizes[b],label=str(b)+' draws/chain') for b in budgets]
    fig.legend(handles=budget_handles,loc='upper center',bbox_to_anchor=(.5,.485),ncol=4,columnspacing=1.5,handletextpad=.5)
    mark(fig,fixture,technical)
    fig.text(.5,.945,name+' | '+function,ha='center',weight='bold',fontsize=10)
    fig.text(.5,.028,'Pointwise 95% BCa; open points: an interval unavailable.\n'
        'Paired n at right; *: point unavailable. Reference type: see caption.',ha='center',fontsize=8.5,linespacing=1.3)
    stem=dest/f'inference-{index}';save(fig,stem,contract=dict(role='Fixed-budget marginal error/cost with shared-input loss contrasts',
        function=function,budget_marker_sizes=sizes,reference_kind=kind,panels=['ordinary_error_cost','paired_MH_minus_NUTS_loss'],
        source_tables=['errors.csv','paired_errors.csv'],axis_scales=scales,points=seen,
        excluded_from_plot_but_retained_in_tables=sum(not r['plotted'] for r in seen),
        omission_rule='Only absent reference/estimate or incomplete matched costs prevents an error-cost mark; all rows retained',fixture=fixture))
    return dict(model=name,function=function,kind='inference',file=name+'/'+stem.name+'.pdf',source_table=name+'/errors.csv',panels=2)


def render_model(name,summary,tables,dest,*,fixture=False,technical=False):
    configure();figures=[]
    r=execution_figure(name,tables,dest,fixture=fixture,technical=technical)
    if r is not None:figures.append(r)
    for j,function in enumerate(summary['reference']['names']):
        r=inference_figure(name,function,j,tables,dest,fixture=fixture,technical=technical)
        if r is not None:figures.append(r)
    return figures
