"""Portable reconstruction of the current generated manuscript sections.

This capsule uses saved, authenticated analysis summaries. It does not rerun
MCMC, raw-array analyses, modern R diagnostics, or figure generation. Historical
raw reproduction remains a separate stage with the corresponding archives.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

CPU_INPUTS = [
 'benchmark/analysis/outputs/cpu-formal/formal-summary.json',
 'benchmark/analysis/outputs/cpu-formal/paired-speedups.json',
 'benchmark/analysis/outputs/cpu-formal/run-metrics.json',
 'execution/statistical-v4/summary.json',
 'execution/statistical-v4/likelihood-ranks.json',
 'output/cpu-revision/sbc-analytic.json',
 'output/cpu-revision/mechanism-summary.json',
 'output/cpu-revision/grouped-diagnostics.json',
 'output/cpu-revision/cost-tiers.json',
]
WINDOWS_INPUTS = [
 'benchmark/analysis/outputs/windows-native-v1/delivery-review.json',
 'benchmark/analysis/outputs/windows-native-v1/summary.json',
 'benchmark/analysis/outputs/windows-native-v1/run-metrics.json',
 'execution/windows-native/windows-native-v1/modern-diagnostics.json',
 'execution/windows-native/windows-native-v1/protocol.json',
]
COMPANION_INPUTS = [
 'benchmark/fixtures/rhat-midpoint-v1/case.json',
 'benchmark/analysis/outputs/completion-f1/mac-02/result.json',
 'benchmark/analysis/outputs/completion-f1/mac-02/receipt.json',
 'benchmark/analysis/outputs/completion-f2/summary.json',
 'benchmark/analysis/outputs/completion-f1/windows-01/result.json',
 'benchmark/analysis/outputs/windows-round2-intake-v1/summary.json',
]
CODE = ['scripts/write-results-tex.py','scripts/revision/write-revision-tex.py',
 'scripts/completion/write_windows_tex.py','scripts/completion/write_completion_tex.py',
 'scripts/completion/write_intake_tex.py','scripts/release/rebuild_current_results.py']
FOLLOWUP_INPUTS = ['benchmark/protocols/mechanism-windows-pilot-v1.json', 'benchmark/analysis/outputs/windows-followup-intake-v1/comparison-summary.json', 'benchmark/analysis/outputs/windows-followup-intake-v1/numpy-summary.json', 'benchmark/analysis/outputs/windows-followup-intake-v1/runtime/SUMMARY.json', 'manuscript/software/followup.template.tex', 'figures/windows-mechanism-pilot-v1/work-and-cached-cost.pdf', 'benchmark/analysis/outputs/mechanism-windows-pilot-v1/windows-20261006/analysis-cpu/workflows.csv', 'benchmark/analysis/outputs/mechanism-windows-pilot-v1/windows-20261006/analysis-cuda/workflows.csv']

SECTIONS = ['results.generated.tex','revision.generated.tex','windows-native.generated.tex',
 'completion-companion.generated.tex','intake.generated.tex']


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest()


def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def safe_relative(name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts or not p.parts:raise ValueError('Unsafe relative asset path')
    return p


def prepare(root,cpu_archive,windows,output):
    root,cpu_archive,windows,output=map(lambda p:Path(p).resolve(),(root,cpu_archive,windows,output))
    if output.exists():raise FileExistsError(output)
    if root==output or root in output.parents:raise ValueError('Use an evidence directory outside the checkout')
    expected=next(r for r in read(root/'output/reproduction/index.json')['archives'] if r['component']=='evidence-paper')
    if cpu_archive.stat().st_size!=expected['bytes'] or digest(cpu_archive)!=expected['sha256']:
        raise ValueError('Historical CPU archive identity differs')
    output.mkdir(parents=True)
    origins={}
    def save(name,content,origin):
        p=output/safe_relative(name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
        origins[name]=origin
    prefix='parallelbayes-reproduction/'
    with tarfile.open(cpu_archive,'r') as tar:
        old= json.loads(tar.extractfile(prefix+'reproduction-manifests/evidence-paper.json').read())
        for name in CPU_INPUTS:
            b=tar.extractfile(prefix+name).read()
            if hashlib.sha256(b).hexdigest()!=old['files'][name]:raise ValueError('CPU member hash differs: '+name)
            save(name,b,'cpu-review-v1/evidence-paper verified archive member')
    for name in WINDOWS_INPUTS:
        save(name,(windows/name).read_bytes(),'received Windows-v1 evidence')
    files=set(CODE+COMPANION_INPUTS+['manuscript/software/windows-native.template.tex','LICENSE'])
    followup='\\input{followup.generated.tex}' in (root/'manuscript/software/软件与基准研究.tex').read_text(encoding='utf-8')
    sections=SECTIONS+(['followup.generated.tex'] if followup else [])
    if followup:
        files.update(FOLLOWUP_INPUTS+['scripts/analysis/write_followup_tex.py','manuscript/software/intake.generated.tex','manuscript/software/completion-companion.generated.tex'])
    main=root/'manuscript/software/软件与基准研究.tex'
    todo=[main];seen=set()
    while todo:
        p=todo.pop().resolve()
        if p in seen:continue
        if root not in p.parents or not p.is_file():raise ValueError('Unsafe/missing paper input')
        seen.add(p);files.add(p.relative_to(root).as_posix())
        if p.suffix=='.tex':
            for command,name in re.findall(r'\\(input|includegraphics)(?:\[[^\]]*\])?\{([^}]+)\}',p.read_text(encoding='utf-8')):
                child=p.parent/name
                if command=='input' and not child.suffix:child=child.with_suffix('.tex')
                todo.append(child)
    for name in sorted(files):
        if Path(name).name in sections:
            dest='expected/'+Path(name).name
        else:dest=name
        save(dest,(root/name).read_bytes(),'current reviewed checkout')
    source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    metadata=dict(schema='current-paper-summary-capsule-v2' if followup else 'current-paper-summary-capsule-v1',sections=sections,source_commit=source,
        source_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()),
        cpu_archive=expected,scope=__doc__.strip(),python=sys.version,
        inputs={name:dict(sha256=digest(output/name),bytes=(output/name).stat().st_size,origin=origin) for name,origin in sorted(origins.items())})
    write(output/'MANIFEST.json',metadata)
    print(json.dumps(dict(prepared=True,assets=len(origins),scope='summary-to-section and PDF inputs; not full raw reproduction')))


def rebuild(capsule,output):
    capsule,output=Path(capsule).resolve(),Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    metadata=read(capsule/'MANIFEST.json')
    if metadata['schema'] not in ['current-paper-summary-capsule-v1','current-paper-summary-capsule-v2']:raise ValueError('Unsupported capsule')
    followup=metadata['schema']=='current-paper-summary-capsule-v2'
    sections=SECTIONS+(['followup.generated.tex'] if followup else [])
    if metadata.get('sections',sections)!=sections:raise ValueError('Unexpected section set')
    for name,row in metadata['inputs'].items():
        p=capsule/safe_relative(name)
        if p.is_symlink() or not p.is_file() or digest(p)!=row['sha256'] or p.stat().st_size!=row['bytes']:
            raise ValueError('Missing or changed capsule input: '+name)
    output.mkdir(parents=True)
    for name in metadata['inputs']:
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(capsule/name,p)
    commands=[
        ['scripts/write-results-tex.py'],['scripts/revision/write-revision-tex.py'],
        ['scripts/completion/write_windows_tex.py','--root','.', '--evidence','.', '--output','manuscript/software/windows-native.generated.tex'],
        ['scripts/completion/write_completion_tex.py','--root','.', '--output','manuscript/software/completion-companion.generated.tex'],
        ['scripts/completion/write_intake_tex.py','--root','.', '--output','manuscript/software/intake.generated.tex'],
    ]
    if followup:
        commands.append(['scripts/analysis/write_followup_tex.py','--root','.', '--output','manuscript/software/followup.generated.tex','--report','followup-analysis.json'])
    logdir=output/'rebuild-logs';logdir.mkdir()
    steps=[];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    for i,command in enumerate(commands):
        with (logdir/f'{i+1}.log').open('w',encoding='utf-8') as log:
            process=subprocess.run([sys.executable,*command],cwd=output,env=env,stdout=log,stderr=subprocess.STDOUT)
        steps.append(dict(command=command,exit_code=process.returncode))
        write(output/'REBUILD.json',dict(status='running' if process.returncode==0 else 'failed',steps=steps))
        if process.returncode:raise RuntimeError('Result generator failed; see retained log')
    comparisons=[]
    for name in sections:
        before=digest(output/'expected'/name);after=digest(output/'manuscript/software'/name)
        comparisons.append(dict(section=name,expected_sha256=before,actual_sha256=after,identical=before==after))
    report=dict(status='passed' if all(r['identical'] for r in comparisons) else 'failed',
        capsule_manifest_sha256=digest(capsule/'MANIFEST.json'),steps=steps,sections=comparisons,
        sources_relocated=True,sampler_calls=0,R_diagnostic_calls=0,figures_recomputed=False,
        scope=f'{len(sections)} generated sections rebuilt from saved summaries and checked rows; full raw-trajectory reconstruction and compiler verification are separate')
    write(output/'REBUILD.json',report)
    if report['status']!='passed':raise RuntimeError('Generated result text differs; do not replace expected evidence')
    print(json.dumps(dict(status=report['status'],sections=len(comparisons),sampler_calls=0,R_diagnostic_calls=0)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--cpu-archive',required=True);p.add_argument('--windows',required=True);p.add_argument('--output',required=True)
    p=sub.add_parser('rebuild');p.add_argument('--capsule',required=True);p.add_argument('--output',required=True)
    args=vars(parser.parse_args());command=args.pop('command')
    if command=='prepare':prepare(**args)
    else:rebuild(**args)
