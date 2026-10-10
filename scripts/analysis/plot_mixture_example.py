#!/usr/bin/env python3
"""Plot the sole observed M1 crossing and its same-repeat CPU RWM example.

Retrospective illustration, no independent-repetition or interval claim.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'pb-mixture-mpl'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/analysis'), str(ROOT/'benchmark/analysis')]
from review_mixture_paths import verified, read_member, sha
from layout_check import require_matplotlib_panel_alignment


def plot(delivery, manifest, manifest_sha256, audit, summary_sha256, tasks_sha256, output):
    root, audit, out = Path(delivery), Path(audit), Path(output)
    if out.exists(): raise FileExistsError(out)
    for file, expected in [(Path(manifest), manifest_sha256), (audit/'SUMMARY.json', summary_sha256),
                           (audit/'tasks.json', tasks_sha256)]:
        if sha(file.read_bytes()) != expected: raise ValueError('Input identity differs: '+file.name)
    original = json.loads(Path(manifest).read_bytes())['files']
    summary = json.loads((audit/'SUMMARY.json').read_text()); rows = json.loads((audit/'tasks.json').read_text())
    if not summary['complete'] or summary['manifest_sha256'] != manifest_sha256 or len(rows) != 432:
        raise ValueError('Complete original M1 companion required')
    crossing = [r for r in rows if r['path_available'] and sum(r['all_saved_sign_crossings'])]
    if len(crossing) != 1 or sum(crossing[0]['retained_sign_crossings']) != 1:
        raise ValueError('Unique-crossing illustration rule no longer applies')
    companion = [r for r in rows if r['workflow'] == 'cpu-rwm-sequential' and
                 r['replicate'] == crossing[0]['replicate'] and r['budget'] == crossing[0]['budget']]
    if len(companion) != 1 or not companion[0]['path_available']:
        raise ValueError('Matched-repeat RWM example missing')
    selected = [companion[0], crossing[0]]; sources = {}; paths = []
    for row in selected:
        names = [n for n in summary['source_assets_sha256']
                 if n.endswith(f"tasks/{row['id']}/attempt-0001/fit.npz")]
        if len(names) != 1: raise ValueError('Ambiguous original path')
        path = verified(root, original, names[0], sources)
        if sources[names[0]] != summary['source_assets_sha256'][names[0]]:
            raise ValueError('Audit source binding differs')
        x = read_member(path, 'draws')
        discard = x.shape[1] - row['budget']
        if x.shape != (4, row['budget'] + discard, 8) or discard not in (0, 512):
            raise ValueError('Illustration shape differs')
        q = x[:, discard:, 0].copy(); del x
        if float((q > 0).mean()) != row['pooled_positive_fraction']:
            raise ValueError('Illustrated pooled fraction differs')
        paths.append(q)
    out.mkdir(parents=True)
    contract = dict(core_conclusion='A balanced pooled sign estimate can coexist with no observed within-chain sign crossing',
        question='Does a correct pooled sign probability establish within-chain exploration?',
        archetype='quantitative grid', backend='Python/matplotlib',
        panels=[dict(label='a', role='Balanced-start no-crossing example', task=selected[0]['id']),
                dict(label='b', role='The sole crossing exception in complete valid-fit audit', task=selected[1]['id'])],
        selection_rule='Retrospectively select the unique observed crossing fit and the CPU sequential RWM fit at the same original repeat and budget',
        full_frame=dict(planned=len(rows), valid=sum(r['path_available'] for r in rows), failed=sum(not r['path_available'] for r in rows)),
        independent_unit='The same original four-chain repetition; two workflows are not two independent datasets',
        uncertainty='Raw traces only, no confidence interval or fit-level performance inference',
        caveat='Known mode weights can support stratified estimation under additional conditions; absence of crossing alone does not refute accuracy of every pooled estimand',
        summary_sha256=summary_sha256, tasks_sha256=tasks_sha256,
        original_manifest_sha256=manifest_sha256, raw_assets_sha256=sources,
        new_sampler_calls=0, new_R_diagnostic_calls=0, new_formal_repetitions=0,
        final_width_mm=160, final_height_mm=125, minimum_font_pt=8.5)
    (out/'contract.json').write_text(json.dumps(contract, indent=2)+'\n')
    with (out/'source.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n'); writer.writerow(['task_id','workflow','chain','retained_iteration','theta1','positive'])
        for row, q in zip(selected, paths):
            for ch in range(4):
                for i, value in enumerate(q[ch], 1):
                    writer.writerow([row['id'], row['workflow'], ch+1, i, float(value), int(value>0)])
    matplotlib.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':9,'axes.labelsize':9,
        'xtick.labelsize':8.5,'ytick.labelsize':8.5,'legend.fontsize':8.5,'legend.frameon':False,
        'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,
        'pdf.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'parallelbayes-mixture-companion-v1'})
    fig, axes = plt.subplots(2, 1, sharex=True, sharey=True, figsize=(160/25.4,125/25.4))
    fig.subplots_adjust(left=.14,right=.96,bottom=.115,top=.86,hspace=.49)
    colors = ['#3B6E8F','#B77437','#4B8D87','#8A6D91']
    labels = ['CPU RWM','CPU NUTS']
    extent = math.ceil(max(float(np.max(np.abs(q))) for q in paths))
    for a, (ax, row, q, label) in enumerate(zip(axes, selected, paths, labels)):
        for ch, color in enumerate(colors):
            ax.plot(np.arange(1,q.shape[1]+1),q[ch],color=color,lw=.6,alpha=.92,label=f'Chain {ch+1}')
        ax.axhline(0.,color='#888888',lw=.55,ls=(0,(3,3)),zorder=0)
        ax.set_ylim(-extent,extent);ax.set_yticks([-8,-4,0,4,8])
        ax.set_xlim(1,q.shape[1]);ax.set_xticks([1,256,512,768,1024])
        ax.set_ylabel(r'Original parameter $\theta_1$')
        ax.set_title(f"{chr(97+a)}  {label}: pooled positive fraction = {row['pooled_positive_fraction']:.6f}",
                     loc='left',fontsize=9.5,pad=9)
    axes[1].set_xlabel('Retained iteration')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.55,.985),ncol=4,
               columnspacing=1.5,handlelength=2.)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(fig,json_out=str(out/'alignment.json'),
        overlay_svg=str(out/'alignment.svg'),tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
    fig.savefig(out/'mixture-example.pdf',metadata={'CreationDate':None,'ModDate':None})
    fig.savefig(out/'mixture-example.svg',metadata={'Date':None})
    fig.savefig(out/'mixture-example.png',dpi=300)
    plt.close(fig)
    inventory={p.name:sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}
    (out/'SHA256.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print(json.dumps({'tasks':[r['id'] for r in selected],'source_rows':sum(q.size for q in paths),
                      'output':str(out),'new_sampler_calls':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('delivery','manifest','manifest-sha256','audit','summary-sha256','tasks-sha256','output'):
        p.add_argument('--'+name,required=True)
    plot(**vars(p.parse_args()))
