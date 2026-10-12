#!/usr/bin/env python3
"""Rebuild new v5 evidence from the verified historical inputs without sampling.

The full unchanged historical reconstruction is inherited from submission-v4-rc1.
This runner rebuilds the changed v5 companion, saved R demonstration, figures,
three TeX fragments and all three PDFs. Every stage writes to a new directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import fitz


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def same_pdf(left,right):
    a,b=fitz.open(left),fitz.open(right)
    if len(a)!=len(b):
        raise ValueError('PDF page count changed')
    for p,q in zip(a,b):
        if p.get_text()!=q.get_text() or p.get_pixmap().samples!=q.get_pixmap().samples:
            raise ValueError('PDF text or 72dpi render changed')
    return dict(pages=len(a),text_equal=True,render_equal=True)


def build(source, statistics, delivery, index, paper, r_evidence, integrity, output,
          rscript='Rscript', compiler=None):
    source,statistics,delivery,index,paper,r_evidence,integrity,output=map(
        lambda p:Path(p).resolve(),(source,statistics,delivery,index,paper,r_evidence,integrity,output))
    if output.exists():
        raise FileExistsError('Use a new reconstruction directory')
    check=json.loads(integrity.read_text(encoding='utf-8'))
    manifest=source/'execution/submission-v5-rc1/COMPONENTS.json'
    if not check['passed'] or check['component_count']!=43 or check['manifest_sha256']!=sha(manifest):
        raise ValueError('Complete v5 component verification required first')
    output.mkdir(parents=True)
    stages=[]
    def run(label,command):
        start=time.monotonic()
        with (output/(label+'.log')).open('xb') as log:
            proc=subprocess.run(list(map(str,command)),cwd=source,stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',
                         OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'))
        row=dict(stage=label,returncode=proc.returncode,elapsed_seconds=time.monotonic()-start)
        stages.append(row);(output/'stages.json').write_text(json.dumps(stages,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(row),flush=True)
        if proc.returncode:
            raise RuntimeError('Failed stage retained: '+label)
    run('v5-companion',[sys.executable,source/'scripts/analysis/review5_evidence.py',
        '--project',source,'--delivery',delivery,'--index',index,'--statistics-dir',statistics,
        '--output',output/'companion'])
    run('L1-R-diagnostics',[rscript,'--vanilla',source/'scripts/analysis/review5_diagnostics.R',output/'companion'])
    original=source/'benchmark/analysis/outputs/manuscript-review-v5'
    for name in ('SUMMARY.json','diagnostic-replay.json'):
        if json.loads((output/'companion'/name).read_text())!=json.loads((original/name).read_text()):
            raise ValueError('Companion differs: '+name)
    for name in ('w1-phase-means.csv','w1-phase-records.csv','w1-three-boundaries.csv'):
        if (output/'companion'/name).read_bytes()!=(original/name).read_bytes():
            raise ValueError('Phase CSV differs: '+name)
    run('v5-fragments',[sys.executable,source/'scripts/analysis/write_review5_tex.py',
        '--evidence',output/'companion','--output',output/'fragments'])
    fragment_names=sorted(p.name for p in (output/'fragments').glob('*.tex'))
    for name in fragment_names:
        if (output/'fragments'/name).read_bytes()!=(source/'manuscript/software-v5'/name).read_bytes():
            raise ValueError('v5 TeX fragment differs: '+name)
    run('prefix-figure',[sys.executable,source/'scripts/analysis/plot_review5_schematic.py','--output',output/'schematic'])
    run('error-cost-figure',[sys.executable,source/'scripts/analysis/plot_review5_error_cost.py',
        '--statistics-directory',statistics,'--manifest-sha256',sha(statistics/'SHA256.json'),
        '--output',output/'error-cost'])
    if (output/'error-cost/source.csv').read_bytes()!=(source/'figures/manuscript-v5/error-cost/source.csv').read_bytes():
        raise ValueError('72 plotted rows/intervals differ')
    figures=[same_pdf(source/'figures/manuscript-v5/trajectory-schematic.pdf',output/'schematic/trajectory-schematic.pdf'),
             same_pdf(source/'figures/manuscript-v5/error-cost/error-cost-overview.pdf',output/'error-cost/error-cost-overview.pdf')]
    run('R-saved-export',[rscript,'--vanilla',source/'scripts/submission/export_saved_v5.R',r_evidence,output/'R-export'])
    run('R-saved-NumPy-replay',[sys.executable,source/'scripts/submission/audit_v5_saved_api.py',
        '--source',source,'--exported',output/'R-export','--evidence',r_evidence,'--output',output/'R-audit'])
    command=[sys.executable,paper/'BUILD.py','--output',output/'PDF-build']
    if compiler:
        command.extend(['--compiler',compiler])
    run('TeX-build',command)
    documents=[]
    for label,name,relative in [('main','软件与基准研究-审读修订v5.pdf','main/软件与基准研究.pdf'),
        ('A','补充材料A-审读修订v5.pdf','supplement-a/补充材料.pdf'),
        ('B','补充材料B-审读修订v5.pdf','supplement-b/report.pdf')]:
        documents.append(dict(document=label,**same_pdf(source/'output/software-paper'/name,output/'PDF-build'/relative)))
        log=(output/'PDF-build'/relative).parent.joinpath('compile.log').read_text(encoding='utf-8')
        if 'Overfull' in log or 'Missing character' in log:
            raise ValueError('Final PDF has overflow or missing glyphs')
    result=dict(identity='submission-v5-rc1-new-evidence-rebuild',passed=True,stages=stages,
        W1_original_phase_records=216,L1_original_paths=2,original_diagnostics_preserved=True,
        phase_csvs_byte_equal=3,TeX_fragments_byte_equal=fragment_names,
        figures=figures,error_cost_rows_preserved=72,documents=documents,
        R_saved_replay=json.loads((output/'R-audit/SUMMARY.json').read_text()),
        component_manifest_sha256=sha(manifest),new_sampler_calls=0,new_independent_random_inputs=0,
        outside_author_access_tested=False,unchanged_historical_full_rebuild='submission-v4-rc1 accepted evidence inherited after version binding',
        scope='Same host and previously accepted locked environments. Read-only original-data companion, saved technical paths and current presentation rebuilt; no fresh full 4144-path replay or performance benchmark.')
    (output/'SUMMARY.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,stages=len(stages),new_sampler_calls=0,pages=[d['pages'] for d in documents])))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','statistics','delivery','index','paper','r-evidence','integrity','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--rscript',default='Rscript');p.add_argument('--compiler')
    build(**vars(p.parse_args()))
