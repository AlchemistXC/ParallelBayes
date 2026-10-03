"""Original conceptual diagrams; no simulated or measured performance data."""
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parents[2] / 'tmp/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Ellipse
from audit_panel_alignment import require_matplotlib_panel_alignment

OUT = Path(__file__).resolve().parent
font_manager.fontManager.addfont('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams.update({'font.family':'Arial Unicode MS','font.size':8,
                     'pdf.fonttype':42,'svg.fonttype':'none',
                     'axes.linewidth':.7,'savefig.facecolor':'white'})
BLUE='#245B78'; LIGHT='#EAF1F5'; GRAY='#6D777D'; PALE='#D9DFE3'; ORANGE='#AF691E'; INK='#23333B'

def axsetup(ax, label, title):
    ax.set(xlim=(0,1), ylim=(0,1)); ax.axis('off')
    ax.text(0,.985,label,ha='left',va='top',weight='bold',fontsize=9,color=INK,fontfamily='DejaVu Sans')
    ax.text(.045,.985,title,ha='left',va='top',fontsize=9,color=INK)

def txt(ax,x,y,s,**kw):
    ax.text(x,y,s,color=INK,ha='left',va='center',linespacing=1.6,**kw)

def arrow(ax,x1,y1,x2,y2,color=BLUE,dashed=False,scale=8):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=scale,
                   linewidth=1,color=color,linestyle='--' if dashed else '-',shrinkA=0,shrinkB=0))

def node(ax,x,y,filled=False,gray=False):
    # Fixed physical diameter across unequal-height panels.
    bbox=ax.get_position(); fw,fh=ax.figure.get_size_inches()
    dx=3.6/(fw*bbox.width*25.4);dy=3.6/(fh*bbox.height*25.4)
    ax.add_patch(Ellipse((x,y),dx,dy,facecolor=BLUE if filled else 'white',
                        edgecolor=PALE if gray else BLUE,linewidth=1.1,zorder=4))
    return dx/2,dy/2

def box(ax,x,y,w,h,s,fill=LIGHT,edge=None,fontsize=8):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.004,rounding_size=0.016',
                         facecolor=fill,edgecolor=edge or fill,linewidth=.7))
    ax.text(x+w/2,y+h/2,s,ha='center',va='center',fontsize=fontsize,color=INK,linespacing=1.55)

def export(fig,name):
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(OUT/(name+'.alignment.json')),
        overlay_svg=str(OUT/(name+'.alignment.svg')),tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,require_panel_labels=True,strict=True)
    # Fixed physical page bounds preserve the alignment dimensions and font scale.
    fig.savefig(OUT/(name+'.pdf'))
    fig.savefig(OUT/(name+'.svg'))
    fig.savefig(OUT/(name+'.png'),dpi=300)
    plt.close(fig)

def mechanisms():
    fig,axs=plt.subplots(3,1,figsize=(162/25.4,168/25.4),gridspec_kw={'height_ratios':[1,1,1.7]})
    fig.subplots_adjust(left=.035,right=.985,bottom=.035,top=.985,hspace=.21)
    a,b,c=axs
    axsetup(a,'a','预取：先计算可能路径，再确认实际分支')
    edges=[(.07,.48,.275,.72,BLUE),(.07,.48,.275,.23,PALE),
           (.29,.72,.49,.82,PALE),(.29,.72,.49,.60,BLUE),
           (.29,.23,.49,.33,PALE),(.29,.23,.49,.11,PALE)]
    for x,y,u,v,col in edges:arrow(a,x,y,u,v,col)
    for x,y,on,g in [(.07,.48,1,0),(.29,.72,1,0),(.29,.23,0,1),(.50,.82,0,1),(.50,.60,1,0),(.50,.33,0,1),(.50,.11,0,1)]:node(a,x,y,on,g)
    txt(a,.018,.15,'当前状态',fontsize=7.4)
    txt(a,.65,.68,'深色路径经完整检验确认\n浅灰分支是额外计算',fontsize=8)
    txt(a,.65,.26,'保持指定顺序路径\n不自动改善原链混合',fontsize=8)

    axsetup(b,'b','多提议：同一步生成候选，联合构造新转移核')
    for yy in [.72,.46,.20]:
        arrow(b,.09,.46,.30,yy);node(b,.32,yy)
        arrow(b,.35,yy,.48,.46,color=GRAY)
    node(b,.075,.46,True)
    box(b,.485,.28,.11,.36,'相容\n选择')
    txt(b,.025,.15,'当前状态',fontsize=7.4)
    txt(b,.265,.055,'同一步候选集',fontsize=7.4)
    txt(b,.65,.67,'联合提议与接受规则\n共同决定目标不变性',fontsize=8)
    txt(b,.65,.25,'改变转移核及每步工作\n候选多不等于等比例增益',fontsize=8)

    axsetup(c,'c','时间并行：固定随机输入，反复修正同一段轨迹')
    xs=[.075,.235,.395,.555]
    for i,x in enumerate(xs):
        c.text(x,.85,'n = '+str(i),ha='center',va='center',fontsize=7.5,color=GRAY)
        node(c,x,.73,filled=i==0)
        arrow(c,x,.685,x,.625)
        box(c,x-.054,.51,.108,.11,'D'+str(i),fontsize=8)
        arrow(c,x,.505,x,.465)
        arrow(c,x,.335,x,.283)
        node(c,x,.235,filled=i<2)
        c.text(x,.135,'n = '+str(i+1),ha='center',va='center',fontsize=7.5,color=GRAY)
    box(c,.022,.34,.59,.12,'固定初值 + 增量前缀和（可并行扫描）',fontsize=7.7)
    txt(c,.65,.73,'旧轨迹：第 j 轮',fontsize=8)
    txt(c,.65,.565,'并行评估增量\n随机输入保持固定',fontsize=8)
    txt(c,.65,.235,'新轨迹：第 j+1 轮\n实心部分已确认',fontsize=8)
    txt(c,.025,.015,'前缀确认示例：增量比较 [ =, =, ≠, = ]，只提交至 n=2。',fontsize=7.6)
    export(fig,'fig01-mechanisms')

def evidence():
    fig,axs=plt.subplots(2,1,figsize=(162/25.4,96/25.4))
    fig.subplots_adjust(left=.035,right=.985,bottom=.055,top=.975,hspace=.25)
    a,b=axs
    axsetup(a,'a','误差连接：每支箭头都需要条件')
    box(a,.005,.51,.20,.24,'轨迹残差 r')
    box(a,.27,.51,.20,.24,'单步核误差 δ')
    box(a,.535,.51,.20,.24,'近似链与基准链\n的分布差')
    box(a,.805,.51,.19,.24,'函数期望差')
    arrow(a,.21,.63,.26,.63,color=ORANGE,dashed=True)
    arrow(a,.475,.63,.525,.63)
    arrow(a,.74,.63,.795,.63)
    txt(a,.015,.33,'残差 → 核误差\n需稳定性或分支控制',fontsize=7.4)
    txt(a,.315,.33,'核误差 → 分布差\n示例需式（11）的收缩',fontsize=7.4)
    txt(a,.685,.33,'TV → 期望差\n直接界限用于有界函数',fontsize=7.4)
    txt(a,.015,.05,'还需基准链混合、初始化与估计方差，才能评价后验 MSE。',fontsize=7.6)

    axsetup(b,'b','比较协议：先固定问题，再计量完整成本')
    box(b,.005,.49,.21,.28,'预设目标\n函数、误差、资源')
    box(b,.265,.49,.21,.28,'确认比较对象\n同一路径或不同核')
    box(b,.525,.49,.21,.28,'完整流程计时\n编译、预热、采样')
    box(b,.785,.49,.21,.28,'误差与诊断\n不确定性、失败率')
    for x in [.221,.481,.741]:arrow(b,x,.63,x+.033,.63)
    txt(b,.015,.27,'路径等价已确认：可比较固定步数的执行时间。',fontsize=7.8)
    txt(b,.015,.085,'核或近似程度不同：比较共同误差目标，并披露参照不确定性。',fontsize=7.8)
    export(fig,'fig02-evidence-workflow')

if __name__=='__main__':
    mechanisms(); evidence()
