#!/usr/bin/env python3
"""Create a relocatable v5 TeX bundle from the sealed v4 inputs and new sources.

Does not regenerate experiments or change the 45 historical result figures.
The base archive is pinned; outputs must be fresh. Compile from the new copy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(project, base_archive, output):
    root, archive, out = map(Path,(project,base_archive,output))
    if out.exists(): raise FileExistsError('Use a fresh output directory')
    if sha(archive)!='f15972b2d59d49138c877cbe06dcb44545c029e5ec41eb31fdc55d3fa361fb12':
        raise ValueError('Sealed v4 build inputs differ')
    out.mkdir(parents=True)
    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            name=Path(member.name)
            if name.is_absolute() or '..' in name.parts or not member.isfile():
                raise ValueError('Unsafe or nonregular base member')
            p=out/name;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(tf.extractfile(member).read())
    old_manifest=json.loads((out/'MANIFEST.json').read_text())
    # Base manifest formats have been stable since v4; verify every input.
    mapping=old_manifest.get('files',old_manifest)
    if not isinstance(mapping,dict): raise ValueError('Invalid base manifest')
    for name,value in mapping.items():
        digest=value.get('sha256') if isinstance(value,dict) else value
        if sha(out/name)!=digest: raise ValueError('Base input failed manifest: '+name)
    for p in (root/'manuscript/software-v5').glob('*.tex'):
        shutil.copy2(p,out/'manuscript/software'/p.name)
    shutil.copytree(root/'figures/manuscript-v5',out/'figures/manuscript-v5')
    for folder in ('benchmark/analysis/outputs/manuscript-review-v5',):
        shutil.copytree(root/folder,out/folder)
    for name in ('docs/MANUSCRIPT-REVIEW-V5.md','docs/MANUSCRIPT-V5-BUILD.md','examples/paper-api-v5.R',
                 'scripts/analysis/review5_evidence.py','scripts/analysis/review5_diagnostics.R',
                 'scripts/analysis/write_review5_tex.py','scripts/analysis/plot_review5_schematic.py',
                 'scripts/analysis/plot_review5_error_cost.py'):
        (out/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,out/name)
    p=out/'complete-results/report.tex';s=p.read_text()
    s=s.replace('正式实验分析附件','补充材料B：完整主实验结果')
    marker=r'\setcounter{tocdepth}'
    note=r'''\par 本附录保留原冻结参考及其全部图表、区间和诊断。W1的“尚未数值认证”与L2事件的“未解决”标记指该历史统计计算的参考状态；随后完成的W1数值区间与L2重要性参考及其影响见补充材料A。这些新参考未追溯替换本附录的数据或统计区间。L1配对尾ESS的分位数并列值敏感性亦见补充材料A，原两套数值保持。
'''
    s=s.replace(marker,note+'\n'+marker,1);p.write_text(s)
    readme='''# ParallelBayes 中文论文 v5 可编译输入

主文件：`manuscript/software/软件与基准研究.tex`。
补充A：`manuscript/software/补充材料.tex`。
补充B：`complete-results/report.tex`。

安装Tectonic（ctex/Fandol字体）或完整TeX Live的XeLaTeX后，在本包根目录运行 `python BUILD.py`，编译三份PDF并生成日志/校验记录；可指定 `--compiler /绝对路径/tectonic`。只核对源文件可运行 `python BUILD.py --verify-only`。不需Codex专用插件。所有input及图件保留相对路径，可搬移到任意新目录。此包重建论文图文；完整实验重放另需原数组、协议与源码环境，见仓库复现指南。

v4原稿/协议/结果保持，本包包含v5新论证、既有计时/诊断再分析与单独R技术示例摘要。未启动新正式采样，未改变旧失败/成功数、区间和参考类别。作者、期刊与长期公开原件标识尚待决定。附带的部分分析脚本供溯源；要运行这些分析，应克隆对应版本的完整仓库、安装锁定依赖并取得原件。本包是完整图文编译输入，不是完整数值复现原件包。
'''
    (out/'README.md').write_text(readme)
    shutil.copy2(root/'scripts/delivery/compile_paper_bundle.py',out/'BUILD.py')
    provenance=dict(schema='parallelbayes-v5-paper-inputs',base_archive_sha256=sha(archive),
        frozen_main_tasks=3888,new_formal_sampler_calls=0,new_R_technical_final_calls=2,
        new_R_technical_total_sampler_calls=4,new_R_technical_environment_failures_before_sampling=1,
        R_technical_first_pair=['completed','failed'],
        R_technical_failed_picard=dict(record_reason='solver_or_audit_failed',iterations=256,confirmed=3848),
        full_result_figures_unchanged=True,base_manifest=old_manifest,
        note='New argument and presentation; read-only old-evidence companion. Full data access remains separate.')
    (out/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
    (out/'MANIFEST.json').unlink()
    files={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'MANIFEST.json').write_text(json.dumps(dict(schema='parallelbayes-v5-build-inputs',files=files),indent=2)+'\n')
    print(json.dumps(dict(files=len(files),output=str(out),new_formal_sampler_calls=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in ('project','base-archive','output'):p.add_argument('--'+a,required=True)
    build(**vars(p.parse_args()))
