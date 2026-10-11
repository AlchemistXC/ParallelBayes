#!/usr/bin/env python3
"""Conceptual four-position Picard prefix; no empirical states are depicted."""
import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'benchmark/analysis'))
from layout_check import require_matplotlib_panel_alignment


def draw(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans','Arial'],'font.size':9,'pdf.fonttype':42,'svg.fonttype':'none'})
    fig,ax=plt.subplots(figsize=(6.2992,3.1496))
    fig.subplots_adjust(left=0,right=1,bottom=0,top=1)
    ax.set(xlim=(0,1),ylim=(0,1));ax.set_axis_off()
    ax.text(.025,.95,'Fixed initial state + the same proposal noise and uniforms',fontsize=10,va='top')
    xs=[.32,.50,.68,.86]; ys=[.74,.48,.20]
    labels=['1  Guess path','2  Reconstruct and check','3  Commit prefix']
    for y,label in zip(ys,labels):ax.text(.025,y,label,va='center',fontsize=9)
    for i,x in enumerate(xs):
        ax.text(x,.84,f'Position {i+1}',ha='center',fontsize=9)
        ax.add_patch(FancyBboxPatch((x-.068,ys[0]-.045),.136,.09,boxstyle='round,pad=.007',
                                  fc='#eef1f4',ec='#85929e',lw=.7))
        ax.text(x,ys[0],'State guess',ha='center',va='center',fontsize=11)
        ax.annotate('',xy=(x,.555),xytext=(x,.674),arrowprops=dict(arrowstyle='->',lw=.8,color='#65747c'))
        label='Mismatch' if i==2 else 'Match'
        ax.text(x,ys[1],label,ha='center',va='center',color='#a05c36' if i==2 else '#376b9c')
        ax.annotate('',xy=(x,.275),xytext=(x,.43),arrowprops=dict(arrowstyle='->',lw=.8,color='#65747c'))
        ax.add_patch(FancyBboxPatch((x-.068,ys[2]-.045),.136,.09,boxstyle='round,pad=.007',
                                  fc='#dbe8f1' if i<2 else '#f5f5f5',ec='#376b9c' if i<2 else '#b4b4b4',lw=.7))
        ax.text(x,ys[2],'Commit' if i<2 else 'Keep solving',ha='center',va='center',fontsize=9)
    ax.text(.025,.055,'A match after the first mismatch cannot extend the confirmed prefix.',fontsize=9)
    require_matplotlib_panel_alignment(fig,json_out=str(out/'trajectory-schematic.alignment.json'),strict=True)
    fig.savefig(out/'trajectory-schematic.pdf');fig.savefig(out/'trajectory-schematic.svg')
    fig.savefig(out/'trajectory-schematic.png',dpi=300);plt.close(fig)
    (out/'trajectory-schematic.contract.json').write_text(json.dumps(dict(
        question='Which positions can Online Picard commit after a new-path check?',
        core_conclusion='Only the contiguous matching prefix can be committed.',
        archetype='schematic-led composite',backend='Python/matplotlib',
        data='Conceptual example, not measured states or acceptance frequencies',
        coordinates='Axes are diagram layout coordinates, not posterior coordinates',
        panels='One diagram; comparable multi-panel geometry is not applicable',
        new_sampler_calls=0),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);draw(**vars(p.parse_args()))
