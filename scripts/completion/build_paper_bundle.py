"""Assemble only the checked-in TeX/PDF inputs needed to compile the current paper.

This is a paper-build bundle, not the raw-experiment reproduction package.
It copies only recursively referenced first-party TeX and figure PDFs plus a
checksum manifest. It does not fetch data, run inference, or alter old results.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile


def build(root, output, complete_results=None, complete_results_sha256=None):
    root, output = root.resolve(), output.resolve()
    if output.exists():
        raise ValueError('Use a new output directory')
    main = root / 'manuscript/software/软件与基准研究.tex'
    supplement = root / 'manuscript/software/补充材料.tex'
    entries = [main] + ([supplement] if supplement.exists() else [])
    pending, files = list(entries), set()
    while pending:
        p = pending.pop().resolve()
        if p in files:
            continue
        if root not in p.parents or not p.is_file():
            raise ValueError(f'Unsafe or missing manuscript dependency: {p.name}')
        files.add(p)
        if p.suffix == '.tex':
            text = p.read_text()
            for command, name in re.findall(r'\\(input|includegraphics)(?:\[[^\]]*\])?\{([^}]+)\}', text):
                child = p.parent / name
                if command == 'input' and not child.suffix:
                    child = child.with_suffix('.tex')
                pending.append(child)
    output.mkdir(parents=True)
    for p in files:
        dst = output / p.relative_to(root)
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,dst)
    report_identity = None
    if complete_results is not None:
        report = complete_results.resolve()
        manifest_path = report / 'SHA256.json'
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != complete_results_sha256:
            raise ValueError('Complete-results manifest differs')
        inventory = json.loads(manifest_path.read_text())
        selected = [name for name in inventory if Path(name).suffix in ('.pdf', '.csv') or
                    name in ('report.tex', 'REPORT.json', 'navigation.json')]
        if 'report.tex' not in selected:
            raise ValueError('Complete-results TeX absent')
        for name in selected:
            member = report/name
            source = member.resolve()
            if report not in source.parents or member.is_symlink():
                raise ValueError('Unsafe report member')
            if hashlib.sha256(source.read_bytes()).hexdigest() != inventory[name]:
                raise ValueError('Report member differs: '+name)
            target = output/'complete-results'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
        report_identity = dict(source_manifest_sha256=complete_results_sha256, files=len(selected),
                               scope='All report TeX, figure PDFs and CSV source tables; no raw trajectories')
    readme = '''# 中文论文独立构建输入

此包仅用于从已生成的LaTeX与矢量图编译当前研究稿。它不包含正式原始数组、完整分析代码或R包，不能代替实验复现包，也不表明研究已经完成。

先校验MANIFEST.json的每项SHA256。使用已有Tectonic（本次为0.17.0，中文依赖已缓存）或具备ctex/fandol的完整XeLaTeX。无需访问原作者的绝对路径。首次无缓存Tectonic可能需要获取其TeX资源。

```text
cd manuscript/software
tectonic 软件与基准研究.tex
tectonic 补充材料.tex
```

或在同目录使用`latexmk -xelatex 软件与基准研究.tex`。编译器资源与字体不随包再分发。各协议数字由生成文本保留；历史结果与前瞻方法已明确分开。对正文数字的独立复算须另取仓库源码、协议及相应原始证据。紧凑研究已完成独立全量重建；主文、补充材料及另附的完整结果报告注明各自证据范围。正文和补充材料应分别编译。
'''
    if report_identity:
        readme += '\n本包另含完整结果附录：在complete-results目录运行tectonic report.tex。45幅图和CSV来源表随包提供；完整统计与原始轨迹另取指定证据包。\n'
    (output/'README.md').write_text(readme)
    manifest = {'scope':'portable paper inputs only; no experimental reproduction claim',
                'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
                'complete_results':report_identity,
                'source_worktree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()),
                'main':main.relative_to(root).as_posix(),
                'entries':[p.relative_to(root).as_posix() for p in entries],
                'files':{p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(output.rglob('*')) if p.is_file()}}
    (output/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    archive = output.with_suffix('.tar')
    if archive.exists():
        raise ValueError('Archive already exists; do not replace it')
    with tarfile.open(archive,'w') as tar:
        for p in sorted(output.rglob('*')):
            if p.is_file():
                tar.add(p,arcname=p.relative_to(output).as_posix(),recursive=False)
    receipt={'archive':archive.name,'bytes':archive.stat().st_size,
             'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(manifest['files'])+1}
    archive.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--complete-results',type=Path)
    p.add_argument('--complete-results-sha256')
    args=p.parse_args();build(args.root,args.output,args.complete_results,args.complete_results_sha256)
