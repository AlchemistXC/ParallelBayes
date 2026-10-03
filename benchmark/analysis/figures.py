"""Source-backed vector figures; no invented values or implicit exclusions."""
import json
import os
os.environ.setdefault('MPLCONFIGDIR',str(__import__('pathlib').Path('environment/matplotlib-cache').resolve()))
from pathlib import Path
import sys
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
sys.path.insert(0,str(Path('benchmark/analysis').resolve()))
from layout_check import require_matplotlib_panel_alignment

mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],
 'font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,
 'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,
 'legend.frameon':False,'axes.linewidth':.6})
out=Path('figures/software');out.mkdir(parents=True,exist_ok=True)

def save(fig,name):
 # Plain exponent notation avoids undersized math superscripts after the
 # 183 mm source figure is scaled to the manuscript's 160 mm text block.
 for ax in fig.axes:
  for axis,scale in [(ax.xaxis,ax.get_xscale()),(ax.yaxis,ax.get_yscale())]:
   if scale=='log':
    axis.set_major_formatter(mpl.ticker.FuncFormatter(lambda value,pos:f'{value:g}'))
    axis.set_minor_formatter(mpl.ticker.NullFormatter())
 fig.canvas.draw()
 require_matplotlib_panel_alignment(fig,json_out=str(out/f'{name}.alignment.json'),
  overlay_svg=str(out/f'{name}.alignment.svg'),tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
 fig.savefig(out/f'{name}.pdf')
 fig.savefig(out/f'{name}.svg')
 fig.savefig(out/f'{name}.png',dpi=600)
 plt.close(fig)

fig,ax=plt.subplots(figsize=(183/25.4,94/25.4));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
boxes=[(.02,.70,.36,.24,'Stan / BridgeStan CPU\nSequential RWM or MALA only\nNo time-parallel / NUTS route'),
       (.57,.70,.41,.24,'Explicit native JAX target\nSequential RWM / MALA; NUTS\nPicard RWM / quasi-DEER MALA'),
       (.28,.33,.44,.23,'Validation and experiment records\nIndependent reference where provided\nFixed inputs / branches / costs / failures'),
       (.02,.02,.36,.19,'Valid output\nposterior draws + run record'),
       (.62,.02,.36,.19,'Failed output\nTrajectory + cause + costs')]
for x,y,w,h,text in boxes:
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.01',facecolor='#eef2f5',edgecolor='#506373',lw=.7))
 ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=8,linespacing=1.5)
for xy,xytext in [((.40,.57),(.20,.68)),((.60,.57),(.78,.68)),((.20,.23),(.40,.31)),((.80,.23),(.60,.31))]:
 ax.annotate('',xy=xy,xytext=xytext,arrowprops=dict(arrowstyle='->',color='#506373',lw=.8))
fig.subplots_adjust(left=.025,right=.975,bottom=.03,top=.97)
save(fig,'architecture')

# Symbolic schedules, not invented experiment trajectories or iteration counts.
fig,axes=plt.subplots(1,2,figsize=(183/25.4,80/25.4))
for ax,label in zip(axes,'ab'):
 ax.set(xlim=(-1.2,8.6),ylim=(-.5,4.4));ax.axis('off')
 ax.text(-1.1,4.15,label,fontweight='bold',fontsize=9)
ax=axes[0]
ax.text(3.7,4.05,'Windowed quasi-DEER',ha='center',fontsize=9)
for start,color in [(0,'#326b98'),(4.3,'#c78343')]:
 ax.add_patch(FancyBboxPatch((start-.25,1.35),3.7,1.9,boxstyle='round,pad=.03',facecolor=color+'12',edgecolor=color,lw=.7))
 for j in range(4):
  ax.plot(start+j,2.8,'o',color=color,ms=4)
  ax.plot(start+j,1.8,'o',color=color,ms=4)
  ax.text(start+j,.95,f'q{j+1 if start==0 else j+5}',ha='center',fontsize=7)
 ax.annotate('',xy=(start+.5,1.98),xytext=(start+.5,2.58),arrowprops=dict(arrowstyle='->',lw=.7,color=color))
 ax.text(start+1.85,2.3,'Affine scan',ha='center',fontsize=6.5)
ax.annotate('',xy=(4.08,1.8),xytext=(3.15,1.8),arrowprops=dict(arrowstyle='->',lw=.8))
ax.text(3.7,.25,'Iterate each block to the hard residual threshold',ha='center',fontsize=7)
ax.text(3.7,-.15,'Pass its final state to the next block',ha='center',fontsize=7)
ax=axes[1]
ax.text(3.7,4.05,'Online Picard',ha='center',fontsize=9)
for j in range(8):
 ax.text(j,3.1,f'q{j+1}',ha='center',fontsize=7)
 color='#427f62' if j<3 else '#b8c0c7'
 ax.plot(j,2.55,'s',ms=7,color=color)
ax.add_patch(FancyBboxPatch((-.3,2.2),4.6,.7,boxstyle='round,pad=.03',facecolor='none',edgecolor='#326b98',lw=.8))
ax.add_patch(FancyBboxPatch((2.7,1.1),4.6,.7,boxstyle='round,pad=.03',facecolor='none',edgecolor='#326b98',lw=.8))
for j in range(3,8):ax.plot(j,1.45,'s',ms=7,color='#b8c0c7')
ax.annotate('',xy=(4.7,1.85),xytext=(1.7,2.1),arrowprops=dict(arrowstyle='->',lw=.8,color='#326b98'))
ax.text(1.,1.3,'Verified\nprefix',ha='center',color='#427f62',fontsize=7)
ax.text(3.7,.25,'Recheck increments and advance the matching prefix',ha='center',fontsize=7)
ax.text(3.7,-.15,'Illustrative prefix length; not measured data',ha='center',fontsize=7)
fig.subplots_adjust(left=.02,right=.98,bottom=.02,top=.98,wspace=.12)
save(fig,'methods')

summary_path=Path('benchmark/analysis/outputs/cpu-formal/formal-summary.json')
if not summary_path.exists():raise SystemExit(0)
summary=json.loads(summary_path.read_text());pairs=json.loads(summary_path.with_name('paired-speedups.json').read_text())
models=['G1','G2','L1','L2','H1','H2','A1','M1'];colors=['#326b98','#c78343']
fig,axes=plt.subplots(2,2,figsize=(183/25.4,155/25.4),sharex=True,sharey=True)
for row,n in enumerate([256,2048]):
 for col,metric in enumerate(['cached_speedup','complete_speedup']):
  ax=axes[row,col];ax.axhline(1,color='.6',lw=.7,ls='--')
  for ki,method in enumerate(['mala/quasi_deer','rwm/online_picard']):
   for i,model in enumerate(models):
    values=[p[metric] for p in pairs if p['model']==model and p['method']==method and p['retained_draws']==n]
    if not values:continue
    assert np.all(np.asarray(values)>0)
    center=i+(ki-.5)*.25;offset=np.linspace(-.065,.065,len(values))
    ax.scatter(center+offset,values,s=7,color=colors[ki],alpha=.45,linewidths=0)
    ax.plot([center-.09,center+.09],[np.median(values)]*2,color=colors[ki],lw=1.6)
  ax.set_yscale('log');ax.set_xticks(range(len(models)),models)
  ax.set_title(('Cached execution' if col==0 else 'Research audit workflow')+f' | N = {n}',pad=8)
  ax.text(-.16,1.12,chr(97+row*2+col),transform=ax.transAxes,fontweight='bold',fontsize=9)
  if col==0:ax.set_ylabel('Sequential / parallel time')
fig.subplots_adjust(left=.11,right=.98,bottom=.10,top=.89,wspace=.22,hspace=.40)
fig.text(.22,.97,'MALA + quasi-DEER',color=colors[0],fontsize=8)
fig.text(.59,.97,'RWM + Online Picard',color=colors[1],fontsize=8)
save(fig,'paired-costs')

# All formal groups, including failures, remain in source JSON/CSV. Error curves
# describe successful runs conditionally; label failed counts in every panel.
fig,axes=plt.subplots(2,4,figsize=(183/25.4,122/25.4),sharey=True)
styles={'mala/sequential':('#326b98','o','-'),'mala/quasi_deer':('#326b98','x','--'),
 'rwm/sequential':('#c78343','s','-'),'rwm/online_picard':('#c78343','+','--'),'nuts/sequential':('#62676c','^','-')}
for ax,model,label in zip(axes.flat,models,'abcdefgh'):
 for method,(color,marker,ls) in styles.items():
  groups=sorted([g for g in summary['groups'] if g['model']==model and g['method']==method],key=lambda g:g['retained_draws'])
  valid=[g for g in groups if 'max_mean_squared_error' in g]
  if valid:
   x=np.array([g['median_total_seconds'] for g in valid]);y=np.array([g['max_mean_squared_error'] for g in valid])
   intervals=np.array([g['error_with_reference_sensitivity_95'] for g in valid])
   assert np.all(x>0) and np.all(y>0)
   ax.plot(x,y,marker=marker,ls=ls,color=color,lw=.7,ms=3)
   ax.vlines(x,intervals[:,0],intervals[:,1],color=color,lw=.7)
 ax.axhline(.01,color='.7',ls=':',lw=.6)
 failed=sum(g['failed'] for g in summary['groups'] if g['model']==model)
 unresolved=any(not g['reference_usable'] for g in summary['groups'] if g['model']==model)
 ax.set_title(f'{model} | failures: {failed}'+(' *' if unresolved else ''),fontsize=8,pad=8)
 if unresolved:ax.text(.04,.86,'* Reference unresolved',transform=ax.transAxes,fontsize=6)
 ax.text(-.17,1.13,label,transform=ax.transAxes,fontweight='bold',fontsize=9)
 ax.set_xscale('log');ax.set_yscale('log');ax.tick_params(labelsize=6)
for ax in axes[1]:ax.set_xlabel('Workflow time (s)',fontsize=7)
for ax in axes[:,0]:ax.set_ylabel('Max function squared error',fontsize=7)
fig.subplots_adjust(left=.09,right=.98,bottom=.13,top=.91,wspace=.35,hspace=.50)
save(fig,'error-cost')
