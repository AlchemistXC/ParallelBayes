"""Plot all descriptive time-executor cells without pooling technical replays."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--batch',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    colors={'G1':'#376ca3','G2':'#bc6338','L1':'#4f8554'}
    fig,axes=plt.subplots(2,2,figsize=(9.6,7.5),sharex=True,sharey=True)
    for i,device in enumerate(('cpu','cuda')):
        with (a.batch/('analysis-'+device)/'workflows.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
        for j,kernel in enumerate(('mala','rwm')):
            ax=axes[i,j]
            cells=[r for r in rows if r['kernel']==kernel and r['label']!='sequential']
            missing=0
            for r in cells:
                if r['status']!='completed' or not r.get('paired_cached_ratio'):
                    missing+=1;continue
                x=float(r['forward_maps_per_transition']);y=float(r['paired_cached_ratio'])
                if x<=0 or y<=0:raise ValueError('Nonpositive cost/ratio')
                width=int(r['label'].rsplit('-w',1)[1])
                ax.scatter(x,y,color=colors[r['model']],marker='o' if width==4 else '^',
                    s=46,alpha=.65,edgecolor='white',linewidth=.4)
            ax.axhline(1,color='#555555',linestyle='--',linewidth=1)
            ax.set_xscale('log');ax.set_yscale('log');ax.grid(alpha=.17)
            ax.set_title(device.upper()+' — '+('quasi-DEER MALA' if kernel=='mala' else 'Picard RWM'),loc='left',fontsize=11)
            ax.text(.04,.07,f'{len(cells)} cells; {missing} unavailable',transform=ax.transAxes,fontsize=9)
            ax.spines[['top','right']].set_visible(False)
            if i==1:ax.set_xlabel('Forward maps per confirmed transition')
            if j==0:ax.set_ylabel('Sequential / time-executor\ncached sample time')
    handles=[Line2D([],[],color=c,marker='o',linestyle='',label=n) for n,c in colors.items()]
    handles += [Line2D([],[],color='#555555',marker=m,linestyle='',label='window '+str(w)) for m,w in [('o',4),('^',16)]]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,.93),ncol=5,frameon=False)
    fig.suptitle('Native Windows F2: additional work and observed cached cost',y=.99,fontweight='bold')
    fig.subplots_adjust(top=.85,bottom=.16,hspace=.28,wspace=.12)
    fig.text(.5,.045,'All 120 time-executor cells retained. Ratios >1 indicate shorter observed cached sample time.\n'
        '2 actual tapes/model; replays share those inputs. This pilot does not establish general speedup or inference accuracy.\n'
        'Fixed-state operation probes overlap and are not an additive cost decomposition.',ha='center',fontsize=9)
    for ext in ('png','svg','pdf'):fig.savefig(a.output/('work-and-cached-cost.'+ext),dpi=180)
    plt.close(fig)


if __name__=='__main__':main()
