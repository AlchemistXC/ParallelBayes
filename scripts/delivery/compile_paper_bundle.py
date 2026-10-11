#!/usr/bin/env python3
"""Verify and compile a relocated ParallelBayes paper bundle (standard library).

Copied to BUILD.py at the bundle root. No experimental sampling or source edits.
Tectonic handles reference passes; XeLaTeX is run three times. Failed commands
retain their logs and return nonzero. A new output directory is required.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', help='Tectonic or XeLaTeX executable/path')
    parser.add_argument('--output', default='build', help='A new output directory')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
    for name, digest in manifest['files'].items():
        path = root/name
        if path.resolve().is_relative_to(root) is False:
            raise ValueError('Unsafe manifest path: '+name)
        if not path.is_file() or sha(path) != digest:
            raise ValueError('Source verification failed: '+name)
    print('Verified', len(manifest['files']), 'source files.')
    if args.verify_only:
        return
    compiler = args.compiler or shutil.which('tectonic') or shutil.which('xelatex')
    if not compiler:
        raise RuntimeError('Install Tectonic or a complete TeX Live/MacTeX distribution.')
    executable = shutil.which(compiler) or str(Path(compiler).resolve())
    kind = Path(executable).name.lower()
    if kind not in ('tectonic','tectonic.exe','xelatex','xelatex.exe'):
        raise ValueError('Compiler must be tectonic or xelatex.')
    output = Path(args.output)
    if not output.is_absolute():
        output = root/output
    output.mkdir(parents=True, exist_ok=False)
    records = []
    entries = [('main','manuscript/software/软件与基准研究.tex'),
               ('supplement-a','manuscript/software/补充材料.tex'),
               ('supplement-b','complete-results/report.tex')]
    for label, name in entries:
        source = root/name
        dest = output/label
        dest.mkdir()
        if kind.startswith('tectonic'):
            command = [executable, '--outdir', str(dest), source.name]
            passes = 1
        else:
            command = [executable, '-interaction=nonstopmode', '-halt-on-error',
                       '-output-directory='+str(dest), source.name]
            passes = 3
        logs = []
        for iteration in range(passes):
            result = subprocess.run(command, cwd=source.parent, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, encoding='utf-8',
                                    errors='replace')
            logs.append('PASS '+str(iteration+1)+'\n'+result.stdout)
            (dest/'compile.log').write_text('\n'.join(logs), encoding='utf-8')
            if result.returncode:
                raise RuntimeError(label+' compile failed; see '+str(dest/'compile.log'))
        pdf = dest/source.with_suffix('.pdf').name
        if not pdf.is_file():
            raise RuntimeError(label+' compiler returned without a PDF.')
        records.append(dict(document=label, source=name, compiler=kind, passes=passes,
                            pdf=pdf.relative_to(output).as_posix(), sha256=sha(pdf),
                            bytes=pdf.stat().st_size, exit_code=0))
    # Compiling must not change any pinned source.
    for name,digest in manifest['files'].items():
        if sha(root/name) != digest:
            raise RuntimeError('Compiler changed pinned source: '+name)
    receipt = dict(schema='parallelbayes-paper-bundle-build-v1',
                   verified_input_files=len(manifest['files']), documents=records,
                   new_sampler_calls=0)
    (output/'BUILD-RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)
