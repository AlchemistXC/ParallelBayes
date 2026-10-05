"""Plot descriptive NUTS readiness diagnostics; serial/spawn is one paired input."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with args.csv.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    args.output.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(8.8,4.7),layout='constrained')
    x=[float(r['max_finite_rhat']) for r in rows]
    y=list(range(len(rows)))
    ax.scatter(x,y,s=45,color='#215b86',zorder=3)
    ax.axvline(1.01,color='#ab4a32',linestyle='--',linewidth=1.2,label='1.01 diagnostic threshold')
    for i,r in enumerate(rows):
        ax.text(2.43,i,r['undefined_rhat'],ha='center',va='center',color='#555555')
    ax.text(2.43,-.9,'Undefined\nfunctions',ha='center',va='center',fontsize=9)
    ax.set_yticks(y,[r['target'] for r in rows]);ax.invert_yaxis()
    ax.set_xlim(.975,2.60);ax.set_ylim(8.6,-1.5)
    ax.set_xlabel('Maximum finite rank/folded Rhat among recorded functions')
    ax.set_title('Native Windows CPU NUTS: nine-target readiness check',loc='left',fontweight='bold')
    ax.grid(axis='x',alpha=.2);ax.spines[['top','right']].set_visible(False)
    ax.legend(loc='upper center',bbox_to_anchor=(.48,.96),frameon=False,fontsize=9)
    fig.supxlabel('4 chains × 64 retained draws. Serial/spawn replay is one validation input per target.\nUndefined functions remain undefined; these short chains do not certify convergence.',fontsize=9)
    for ext in ('png','svg','pdf'):fig.savefig(args.output/('nuts-readiness-rhat.'+ext),dpi=180)
    plt.close(fig)


if __name__=='__main__':main()
