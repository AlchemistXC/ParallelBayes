"""Current supported routes, not a performance or correctness guarantee.

Single schematic at the manuscript's 160 mm text width; no quantitative data.
Source is the public capability matrix and explicit research CLI contracts.
Historical architecture and quantitative figure generators remain unchanged.
"""
import argparse
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'pb-mpl-current'))
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'benchmark/analysis'))
from layout_check import require_matplotlib_panel_alignment


def render(out):
    out.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update({'font.family':'sans-serif', 'font.sans-serif':['DejaVu Sans'],
                        'font.size':7, 'pdf.fonttype':42, 'svg.fonttype':'none',
                        'legend.frameon':False})
    fig, ax = plt.subplots(figsize=(160/25.4, 124/25.4))
    fig.subplots_adjust(left=.025, right=.975, bottom=.02, top=.98)
    ax.set(xlim=(0,1), ylim=(0,1)); ax.axis('off')
    def box(x,y,w,h,title,body, color='#eef2f5'):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.003',
                                   facecolor=color,edgecolor='#536677',lw=.7))
        ax.text(x+w/2,y+h-.037,title,ha='center',va='center',fontweight='bold',fontsize=7)
        ax.text(x+w/2,y+h/2-.017,body,ha='center',va='center',fontsize=7,linespacing=1.4)
    def arrow(start,end):
        ax.annotate('', xy=end,xytext=start, arrowprops=dict(arrowstyle='->',lw=.7,color='#536677'))
    box(.01,.86,.98,.12,'Target and coordinate contract',
        'R control / Python protocol; explicit capability checks')
    providers=[(.01,'Stan / BridgeStan','CPU sequential MH only\nNo time-parallel route'),
               (.345,'Explicit JAX target','CPU sequential / time MH\nBlackJAX NUTS'),
               (.68,'Explicit torch target','CPU / CUDA MH routes\nPython host control')]
    for x,title,body in providers:
        box(x,.65,.31,.15,title,body)
        arrow((x+.155,.86),(x+.155,.805))
        arrow((x+.155,.65),(x+.155,.595))
    box(.01,.44,.98,.15,'Kernel, executor and resource records',
        'MH: actual random arrays; sequential or matched time executor\nNUTS: own RNG / adaptation; CPU Pyro is a separate research CLI')
    arrow((.5,.44),(.5,.385))
    box(.01,.22,.98,.16,'Separate numerical checks and measured costs',
        'Independent path / event reference where provided; transform checks\nResiduals / stopping causes; ordinary process / research audit costs', '#e8f0f4')
    arrow((.32,.22),(.25,.165)); arrow((.68,.22),(.75,.165))
    box(.01,.015,.47,.145,'Numerically valid output',
        'Draws + run record\nStatistical diagnostics still required')
    box(.52,.015,.47,.145,'Failure or interruption record',
        'Cause + raw evidence + known costs\nNo ordinary posterior sample')
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(out/'architecture-current.alignment.json'),
        overlay_svg=str(out/'architecture-current.alignment.svg'),tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,strict=True)
    fig.savefig(out/'architecture-current.pdf')
    fig.savefig(out/'architecture-current.svg')
    fig.savefig(out/'architecture-current.png',dpi=600)
    plt.close(fig)

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); render(a.output)
