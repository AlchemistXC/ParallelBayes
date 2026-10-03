from pathlib import Path
import json,os,sys
os.environ.setdefault('MPLCONFIGDIR',str(Path('environment/matplotlib-cache').resolve()))
import numpy as np,matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path('benchmark/analysis').resolve()))
from layout_check import require_matplotlib_panel_alignment
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
data=json.loads(Path('output/cpu-revision/mechanism-summary.json').read_text())['groups'];out=Path('figures/software')
fig,axes=plt.subplots(2,2,figsize=(183/25.4,132/25.4))
fields=['cached_speed_ratio','batch_throughput_factor','forward_per_transition','core_equivalents'];titles=['Cached trajectory: sequential / parallel','Fixed states: serial map / batch','Forward mappings / output transition','Process CPU seconds / wall second']
for ax,key,title,label in zip(axes.flat,fields,titles,'abcd'):
 for k,color in [('mala','#326b98'),('rwm','#c78343')]:
  for w,marker in [(16,'o'),(64,'s')]:
   for i,(model,c) in enumerate([(x,c) for x in ['G1','G2','L1'] for c in [1,4]]):
    g=next(g for g in data if (g['model'],g['chains'],g['kernel'],g['window'])==(model,c,k,w));v=g[key];assert v['minimum']>0;x=i+(-.20 if k=='mala' else .12)+(-.055 if w==16 else .055)
    ax.vlines(x,v['minimum'],v['maximum'],color=color,lw=.7);ax.plot(x,v['median'],marker,color=color,ms=3,mfc=color if w==16 else 'white',mew=.7)
 ax.set_xticks(range(6),['G1\nC1','G1\nC4','G2\nC1','G2\nC4','L1\nC1','L1\nC4'])
 ax.set_title(title,pad=9,fontsize=8);ax.text(-.13,1.12,label,transform=ax.transAxes,fontweight='bold')
 if key in fields[:2]:ax.axhline(1,ls='--',lw=.6,color='.5');ax.set_yscale('log');ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v,p:f'{v:g}'));ax.yaxis.set_minor_formatter(mpl.ticker.NullFormatter())
 ax.grid(axis='y',alpha=.15,lw=.5)
fig.text(.16,.96,'quasi-DEER',color='#326b98',fontsize=8);fig.text(.38,.96,'Online Picard',color='#c78343',fontsize=8);fig.text(.65,.96,'Circle: W16   Square: W64',fontsize=8)
fig.subplots_adjust(left=.10,right=.98,bottom=.08,top=.85,hspace=.55,wspace=.27)
fig.canvas.draw();require_matplotlib_panel_alignment(fig,str(out/'cpu-mechanism.alignment.json'))
fig.savefig(out/'cpu-mechanism.pdf')
fig.savefig(out/'cpu-mechanism.svg')
fig.savefig(out/'cpu-mechanism.png',dpi=600)
plt.close(fig)
