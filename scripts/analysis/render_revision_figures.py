"""Readable historical paired plots; no new experiments or uncertainty intervals.

All 512 Windows-v1 rows form 256 same-device/kernel/input pairs. Each pair's
cached ratio is shown once; medians summarize four original inputs per cell.
CPU and CUDA panels stay separate. No inferential filtering or interpolation.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'pb-paper-revision-mpl'))
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
from matplotlib.patches import FancyBboxPatch


def render(root, output):
    root, output = root.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0,str(root/'benchmark/analysis'))
    from layout_check import require_matplotlib_panel_alignment
    mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':9,
        'axes.labelsize':9,'axes.titlesize':10,'xtick.labelsize':8.5,
        'ytick.labelsize':8.5,'pdf.fonttype':42,'svg.fonttype':'none',
        'axes.spines.right':False,'axes.spines.top':False})
    source=root/'benchmark/analysis/outputs/windows-native-v1/run-metrics.json'
    rows=json.loads(source.read_text())
    if len(rows)!=512:raise ValueError('Expected the complete frozen Windows-v1 frame')
    index={}
    for row in rows:
        k=tuple(row[n] for n in ('device','kernel','executor','model','draws','replicate'))
        if k in index:raise ValueError('Duplicate task key')
        if row['status']!='completed':raise ValueError('Unexpected failure: preserve and extend plot contract')
        if not np.isfinite(row['warmed_seconds']) or row['warmed_seconds']<=0:raise ValueError('Invalid cached time')
        index[k]=row
    pairs=[]
    for row in rows:
        if row['executor']=='sequential':continue
        seq=index[(row['device'],row['kernel'],'sequential',row['model'],row['draws'],row['replicate'])]
        pairs.append({k:row[k] for k in ('device','kernel','model','draws','replicate')}|
          dict(sequential_task=seq['task_id'],parallel_task=row['task_id'],
               sequential_seconds=seq['warmed_seconds'],parallel_seconds=row['warmed_seconds'],
               ratio=seq['warmed_seconds']/row['warmed_seconds']))
    if len(pairs)!=256:raise ValueError('Incomplete pair frame')
    with (output/'paired-source.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(pairs[0]));writer.writeheader();writer.writerows(pairs)
    # One question, two necessary controls: MALA and RWM executor behavior.
    models=['G1','G2','A1','L1','L2','H1','H2','M1']
    groups=[(m,n) for m in models for n in (128,512)]
    width_mm=160
    for device in ('cpu','cuda'):
        fig,axs=plt.subplots(1,2,figsize=(width_mm/25.4,139/25.4),sharey=True)
        fig.subplots_adjust(left=.15,right=.97,bottom=.12,top=.90,wspace=.19)
        for ax,kernel,label,color in zip(axs,['mala','rwm'],['a  quasi-DEER / MALA','b  Picard / RWM'],['#326C91','#B46E35']):
            for y,(model,n) in enumerate(groups):
                pts=sorted([r for r in pairs if (r['device'],r['kernel'],r['model'],r['draws'])==(device,kernel,model,n)],key=lambda r:r['replicate'])
                if len(pts)!=4:raise ValueError('Each row needs four original inputs')
                values=[r['ratio'] for r in pts]
                ax.scatter(values,y+np.array([-.21,-.07,.07,.21]),s=15,color=color,zorder=3,linewidths=0)
                median=float(np.median(values));ax.plot([median,median],[y-.30,y+.30],color='#20282E',lw=1.3,zorder=4)
            ax.set_xscale('log');ax.set_xlim(.045,9);ax.set_ylim(15.7,-.7)
            ax.set_title(label,loc='left',pad=11)
            ax.axvline(1,color='#677077',ls='--',lw=.8,zorder=1)
            ax.xaxis.set_major_locator(FixedLocator([.05,.1,.5,1,5]))
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x:g}'))
            ax.xaxis.set_minor_locator(NullLocator())
            ax.set_xlabel('Cached speed ratio')
            ax.set_yticks(range(16),[f'{m} / {n}' for m,n in groups])
            ax.tick_params(axis='y',length=0)
            for y in (1.5,3.5,5.5,7.5,9.5,11.5,13.5):ax.axhline(y,color='#E4E8EA',lw=.6,zorder=0)
        fig.canvas.draw()
        name=f'windows-{device}-pairs'
        require_matplotlib_panel_alignment(fig,json_out=str(output/f'{name}.alignment.json'),
            overlay_svg=str(output/f'{name}.alignment.svg'),strict=True)
        fig.savefig(output/f'{name}.pdf')
        fig.savefig(output/f'{name}.svg')
        fig.savefig(output/f'{name}.png',dpi=600)
        plt.close(fig)
    # Style adaptation of the existing provider diagram: all routes retained.
    fig,ax=plt.subplots(figsize=(width_mm/25.4,125/25.4))
    fig.subplots_adjust(left=.01,right=.99,bottom=.01,top=.99)
    ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    def box(x,y,w,h,title,body):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.002',facecolor='#EEF3F6',edgecolor='#536677',lw=.7))
        ax.text(x+w/2,y+h-.033,title,ha='center',va='center',fontsize=9,fontweight='bold')
        ax.text(x+w/2,y+h*.42,body,ha='center',va='center',fontsize=8.5,linespacing=1.5)
    def arrow(a,b):ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',lw=.8,color='#536677'))
    box(.005,.875,.99,.12,'Target and coordinates','R control / Python model interface')
    for x,title,body in [(.005,'Stan / BridgeStan','CPU sequential MH\nNo time executor'),(.34,'Native JAX target','CPU MH / time execution\nBlackJAX NUTS'),(.675,'Native torch target','CPU / CUDA MH\nPython host control')]:
        box(x,.645,.32,.17,title,body);arrow((x+.16,.875),(x+.16,.82));arrow((x+.16,.645),(x+.16,.595))
    box(.005,.435,.99,.16,'Kernel / executor / resource records','MH: shared actual random arrays\nCPU Pyro NUTS: separate research CLI')
    arrow((.5,.435),(.5,.385))
    box(.005,.225,.99,.16,'Numerical checks and measured costs','Independent path and event reference where provided\nResiduals / failures / ordinary and audit costs')
    arrow((.28,.225),(.25,.175));arrow((.72,.225),(.75,.175))
    box(.005,.01,.48,.165,'Numerically valid output','Draws and run record\nStatistical checks follow')
    box(.515,.01,.48,.165,'Failure record','Cause and retained evidence\nNo ordinary draws')
    fig.canvas.draw()
    fig.savefig(output/'architecture-readable.pdf')
    fig.savefig(output/'architecture-readable.svg')
    fig.savefig(output/'architecture-readable.png',dpi=600)
    plt.close(fig)
    contract=dict(source=source.relative_to(root).as_posix(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        rows=512,pairs=256,excluded=0,independent_inputs_per_cell=4,technical_replays_add_n=False,
        claim='Historical within-device cached ratios differ by executor; these are not inference speedups.',
        ratio='sequential warmed seconds / parallel warmed seconds on the same actual input',
        intervals='none; individual paired points and n=4 median',format='160 mm; editable PDF/SVG; 8.5 pt minimum nominal font',
        figure_role='CUDA main comparison; CPU companion; all 256 pairs retained',
        architecture_role='Style adaptation; all three existing provider arrows retained',
        sampler_calls=0)
    (output/'figure-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    print(json.dumps({'rows':len(rows),'pairs':len(pairs),'displays':3,'sampler_calls':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();render(a.root,a.output)
