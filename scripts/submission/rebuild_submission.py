#!/usr/bin/env python3
"""Rebuild saved submission evidence; never launch a sampler or device benchmark.

Requires the independently verified mac-final, H1, L2, W1 archives relocated
under one directory. Full raw reader replay remains a separate documented step.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(p):
    with Path(p).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def csv_rows(p):
    with p.open(newline='', encoding='utf-8') as f:
        return list(csv.reader(f))


def build(source, relocated, output):
    source, relocated, output = map(lambda x: Path(x).resolve(), (source, relocated, output))
    if output.exists():
        raise FileExistsError('Use a new output directory')
    output.mkdir(parents=True)
    mac = relocated/'mac-final'
    stats = mac/'statistics'
    stages = []

    def run(name, script, args):
        command = [sys.executable, str(source/script), *map(str,args)]
        started = time.monotonic()
        with (output/(name+'.log')).open('xb') as log:
            p = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1',
                         OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'))
        record = dict(stage=name, script=script, script_sha256=sha(source/script),
                      returncode=p.returncode, elapsed_seconds=time.monotonic()-started)
        stages.append(record)
        (output/'stages.json').write_text(json.dumps(stages,indent=2)+'\n')
        print(json.dumps(record), flush=True)
        if p.returncode:
            raise RuntimeError('Failed stage retained: '+name)

    run('complete-results', 'scripts/analysis/formal_report.py',
        ['--statistics-directory',stats,'--manifest-sha256',sha(stats/'SHA256.json'),
         '--publication-layout','--output',output/'complete-results'])
    run('overview','scripts/analysis/plot_compact_overview.py',
        ['--statistics-directory',stats,'--manifest-sha256',sha(stats/'SHA256.json'),
         '--output',output/'overview'])
    review=mac/'independent-review/SUMMARY.json'
    run('main-tables','scripts/analysis/write_compact_manuscript.py',
        ['--statistics-directory',stats,'--manifest-sha256',sha(stats/'SHA256.json'),
         '--review',review,'--review-sha256',sha(review),'--output',output/'main-tables'])
    run('h1-report','scripts/analysis/report_h1_function_paths.py',
        ['--source',relocated/'h1-companion/analysis','--output',output/'h1-report'])
    run('l2-audit','scripts/analysis/audit_l2_importance.py',
        ['--source',relocated/'l2-reference/raw','--frames',relocated/'l2-reference/inputs/L2.frame.ndjson',
         '--output',output/'l2-audit'])
    w=relocated/'w1-reference'
    run('w1-audit','scripts/analysis/audit_w1_enclosure.py',
        ['--source',w/'raw','--protocol',w/'source/benchmark/protocols/w1-reference-enclosure-v1.json',
         '--root',w/'source','--statistics',stats,'--output',output/'w1-audit'])
    run('w1-report','scripts/analysis/report_w1_enclosure.py',
        ['--source',w/'raw','--audit',output/'w1-audit','--output',output/'w1-report'])
    run('r-raw-verify','scripts/analysis/r_frontend_verify.py',
        ['--root',mac/'R-timing','--reference-file',mac/'R-reference/reference.py',
         '--output',output/'R-analysis'])
    run('r-report','scripts/analysis/r_frontend_report.py',
        ['--analysis',output/'R-analysis','--recovery',mac/'R-records/zero-new-recovery.json',
         '--output',output/'R-cost-report'])
    run('v4-explanation','scripts/analysis/review3_numerics.py',
        ['--root',source,'--inputs',source/'benchmark/analysis/outputs/manuscript-review-v3/inputs',
         '--output',output/'v4-explanation'])

    comparisons=[]
    for old in sorted((mac/'complete-results').rglob('*.csv')):
        rel=old.relative_to(mac/'complete-results')
        new=output/'complete-results'/rel
        if not new.is_file() or csv_rows(old)!=csv_rows(new):
            raise ValueError('Complete-result CSV differs: '+str(rel))
        comparisons.append(str(rel))
    pairs=[(output/'h1-report/function-differences.csv',relocated/'h1-companion/report/function-differences.csv'),
           (output/'h1-report/task-index.csv',relocated/'h1-companion/report/task-index.csv'),
           (output/'R-analysis/calls.csv',mac/'R-analysis/calls.csv'),
           (output/'R-analysis/diagnostics.csv',mac/'R-analysis/diagnostics.csv')]
    for new,old in pairs:
        if csv_rows(new)!=csv_rows(old):raise ValueError('Supplement CSV differs: '+new.name)
    tex=[]
    for p in (output/'main-tables').glob('*.tex'):
        old=source/'manuscript/software'/p.name
        if p.read_bytes()!=old.read_bytes():raise ValueError('Main TeX differs: '+p.name)
        tex.append(p.name)
    for p in (output/'v4-explanation').glob('*.tex'):
        old=source/'manuscript/software'/p.name
        if p.read_bytes()!=old.read_bytes():raise ValueError('v4 TeX differs: '+p.name)
        tex.append(p.name)
    result=dict(identity='submission-v4-rc1-saved-evidence-rebuild',passed=True,
        stages=stages,complete_result_csvs_equal=len(comparisons),supplement_csvs_equal=len(pairs),
        manuscript_fragments_equal=tex,new_sampler_calls=0,new_independent_repetitions=0,
        scope='All saved statistics/table/plot generation; H1/R saved array verification, L2 saved-point reweight audit, W1 exact saved-bound reaggregation. This is not a new 4144-task raw trajectory replay, GPU measurement or external reviewer access test.')
    (output/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','relocated','output'):p.add_argument('--'+n,type=Path,required=True)
    print(json.dumps(build(**vars(p.parse_args())),indent=2))
