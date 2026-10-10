#!/usr/bin/env python3
"""Create a local W1 evidence archive after final audit, report, and zero-work resume.

No upload, extraction, sampling or target evaluation occurs here. Inputs must be
separate from the output tar. Only explicitly selected source/data are included.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

PROTOCOL = 'benchmark/protocols/w1-reference-enclosure-v1.json'
PROTOCOL_SHA = '85506f871a4fedb6f1cb30da1d9509afa764d2621e40ee51c48a1a6b44a97d36'
STATISTICS_SHA = 'd928a497889e11f6aaf5829bf1ffd807a647a880a5d4ae7cef4acf3046c34bfb'
TOOLS = ['scripts/analysis/audit_w1_enclosure.py', 'scripts/analysis/report_w1_enclosure.py',
         'scripts/analysis/export_w1_evidence.py']
TESTS = ['tests/handoff/'+name+'.py' for name in
         ['test_verified_cubature', 'test_checkpoint_cubature', 'test_wells_ball_target',
          'test_w1_posterior_enclosure', 'test_w1_independent_audit', 'test_w1_report', 'test_w1_archive']]
QUALIFICATION = 'execution/targeted-followups-v1/qualification/'
EXTRA = [PROTOCOL, 'LICENSE', 'docs/W1-ENCLOSURE-METHOD-NOTE.md', 'docs/W1-INDEPENDENT-AUDIT.md'] + TESTS + [QUALIFICATION+n for n in [
    'requirements-mac-followups.txt', 'w1-target-component.json', 'w1-driver-qualification.json',
    'w1-independent-auditor-qualification.json', 'w1-independent-auditor-tests.xml',
    'w1-report-qualification-v1.json', 'w1-report-tests-v1.xml',
    'w1-archive-qualification-v1.json', 'w1-archive-tests-v1.xml']]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relative_file(root, name):
    p = Path(name)
    require(not p.is_absolute() and bool(p.parts) and '..' not in p.parts, 'unsafe archive path')
    candidate = root/p
    require(candidate.is_file() and not candidate.is_symlink() and
            candidate.resolve().is_relative_to(root.resolve()), 'missing or linked archive input: '+name)
    return candidate


def checked(directory):
    manifest = json.loads((directory/'checksums.json').read_text())
    for name, expected in manifest.items():
        require(sha(relative_file(directory,name)) == expected, 'asset checksum differs: '+name)
    return manifest


def resume_receipts(raw, asset_count):
    receipts = sorted((raw/'invocations').glob('*.json'))
    require(bool(receipts), 'completed zero-work resume evidence required')
    for path in receipts:
        receipt = json.loads(path.read_text())
        require(receipt['reused_complete'] and receipt['new_evaluations'] == 0 and
                receipt['verified_assets'] == asset_count, 'resume did not verify all prior assets')
    return receipts


def inspect_inputs(root, raw, audit, report, statistics, data):
    require(sha(root/PROTOCOL) == PROTOCOL_SHA, 'frozen protocol differs')
    protocol = json.loads((root/PROTOCOL).read_text())
    manifests = {'raw':checked(raw), 'audit':checked(audit), 'report':checked(report)}
    required = {'raw':{'SUMMARY.json','IDENTITY.json','gauss2.sqlite','simpson.sqlite',
                       'gauss2-result.json','simpson-result.json','tail.json','work-reservations.json'},
                'audit':{'audit.json','reference-sensitivity.json'},
                'report':{'REPORT.md','reference-intervals.csv','method-costs.csv',
                          'reference-sign-sensitivity.csv','reference-sensitivity.json',
                          'w1-reference-table.generated.tex','report.provenance.json'}}
    for prefix in required:
        require(required[prefix] <= set(manifests[prefix]), 'required archive evidence missing: '+prefix)
    summary = json.loads((raw/'SUMMARY.json').read_text())
    check = json.loads((audit/'audit.json').read_text())
    rendered = json.loads((report/'report.provenance.json').read_text())
    require(check['passed'] and check['source_summary_sha256'] == sha(raw/'SUMMARY.json'), 'audit binding differs')
    require(check['protocol_sha256'] == summary['protocol_sha256'] == PROTOCOL_SHA, 'result protocol differs')
    require(rendered['source_summary_sha256'] == sha(raw/'SUMMARY.json') and
            rendered['audit_sha256'] == sha(audit/'audit.json') and
            rendered['sensitivity_sha256'] == sha(audit/'reference-sensitivity.json'), 'report binding differs')
    require(check['new_mcmc_calls'] == rendered['new_mcmc_calls'] == summary['new_mcmc_fits'] == 0
            and summary['preserved_old_references'], 'reference scope differs')
    require(check['auditor_sha256'] == sha(root/TOOLS[0]) and
            rendered['generator_sha256'] == sha(root/TOOLS[1]), 'current audit/report source differs')
    require(summary['source_commit'] == protocol['source_commit'], 'scientific source commit differs')
    require(sha(statistics/'SHA256.json') == STATISTICS_SHA, 'old statistics identity differs')
    stat_index = json.loads((statistics/'SHA256.json').read_text())
    for name in ['W1.frame.ndjson', 'reference-contract.json']:
        require(sha(statistics/name) == stat_index[name], 'old statistics changed')
    files = {}
    def add(name, path):
        require(name not in files, 'duplicate archive member')
        require(path.is_file() and not path.is_symlink(), 'nonregular archive input')
        files[name] = path
    for prefix, directory in [('raw',raw),('audit',audit),('report',report)]:
        for name in manifests[prefix]: add(prefix+'/'+name,relative_file(directory,name))
        add(prefix+'/checksums.json',directory/'checksums.json')
    add('raw/run.lock',raw/'run.lock')
    receipts = resume_receipts(raw,len(manifests['raw']))
    for path in receipts:
        add('raw/invocations/'+path.name,path)
    for name, expected in protocol['source_files'].items():
        require(sha(relative_file(root,name)) == expected, 'frozen numerical source changed')
    source_names = sorted(set(protocol['source_files']) | set(TOOLS) | set(EXTRA))
    for name in source_names: add('source/'+name,relative_file(root,name))
    sources = json.loads((root/'models/external/wells/source-manifest.json').read_text())
    for row in sources['files']:
        p = relative_file(data,row['path'])
        require(p.stat().st_size == row['bytes'] and sha(p) == row['sha256'], 'external data changed')
        add('inputs/external/'+row['path'],p)
    for name in ['SHA256.json','W1.frame.ndjson','reference-contract.json']:
        add('inputs/statistics/'+name,statistics/name)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    for name in source_names:
        require(subprocess.check_output(['git','show',commit+':'+name],cwd=root) == (root/name).read_bytes(),
                'commit delivery sources before packaging: '+name)
    return files, dict(identity='w1-reference-evidence-v1',protocol_sha256=PROTOCOL_SHA,
        scientific_source_commit=protocol['source_commit'],delivery_source_commit=commit,
        source_summary_sha256=sha(raw/'SUMMARY.json'),new_mcmc_calls=0,
        zero_work_resume_receipts=len(receipts),old_references_preserved=True,
        uploaded=False,archiver_sha256=sha(Path(__file__)))


README = '''# W1独立参考复现包

本地伴随分析归档，不是新的MCMC实验。raw为积分单元、检查点与最终包络；audit为独立端点/分区/比率核验；report为结果表；source含冻结数值源码和交付时的核验程序；inputs仅含必要的原W1数据和旧统计汇总。旧主研究原始轨迹不在本包内。

先逐文件核对MANIFEST.json。Python 3.12.14和source/execution/targeted-followups-v1/qualification/requirements-mac-followups.txt固定本轮环境；在单独环境安装，勿修改旧实验环境。从解压目录执行：

```sh
PYTHONDONTWRITEBYTECODE=1 python source/scripts/analysis/audit_w1_enclosure.py \\
  --source raw --protocol source/benchmark/protocols/w1-reference-enclosure-v1.json \\
  --root source --statistics inputs/statistics --output rebuilt-audit
PYTHONDONTWRITEBYTECODE=1 python source/scripts/analysis/report_w1_enclosure.py \\
  --source raw --audit rebuilt-audit --output rebuilt-report
```

两步不重新评价目标或采样；核验器仅用标准库。输出目录必须是新目录。正式源程序的恢复检查需锁定Python和依赖，命令如下，已有终态原件将逐项核验并写入一条新的invocations记录，新增评价应为0：

```sh
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \\
  python -W error source/scripts/analysis/run_w1_enclosure.py run \\
  --protocol source/benchmark/protocols/w1-reference-enclosure-v1.json \\
  --data inputs/external --output raw
```

若要从头重算，另设新输出目录且预留计划资源。不要删除检查点后写入原目录。区间有效性依赖所记录的函数、导数、尾界与球算术条件；通过有限检查不是一般正确性证明。参考敏感性不代替重复实验不确定性。文件浮点显示值不是误差界，完整二进制球和有理端点为准。没有自动上传或公开本包。
'''


def write_archive(files, metadata, destination):
    destination = destination.resolve()
    require(destination.suffix == '.tar' and not destination.exists(), 'fresh .tar destination required')
    require(destination.parent.is_dir(), 'archive parent must exist')
    receipt_path = destination.with_suffix('.receipt.json')
    require(not receipt_path.exists(), 'archive receipt already exists')
    total = sum(p.stat().st_size for p in files.values())
    require(total <= 3*1024**3, 'W1 archive inputs exceed 3 GiB allocation')
    require(shutil.disk_usage(destination.parent).free >= 2*total + 4*1024**3, 'archive and verification disk reserve unavailable')
    manifest = dict(metadata,files={n:{'bytes':p.stat().st_size,'sha256':sha(p)} for n,p in sorted(files.items())})
    readme = README.encode()
    manifest['files']['README.md'] = {'bytes':len(readme),'sha256':hashlib.sha256(readme).hexdigest()}
    manifest_bytes = (json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    def add_bytes(tar,name,data):
        info = tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0
        tar.addfile(info,io.BytesIO(data))
    with destination.open('xb') as stream:
        with tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT) as archive:
            for name,p in sorted(files.items()):
                info = tarfile.TarInfo(name);info.size=p.stat().st_size;info.mode=0o644;info.mtime=0
                with p.open('rb') as input_stream:archive.addfile(info,input_stream)
            add_bytes(archive,'README.md',readme)
            add_bytes(archive,'MANIFEST.json',manifest_bytes)
    with tarfile.open(destination,'r:') as archive:
        members = archive.getmembers();seen=set()
        for member in members:
            require(member.isfile() and member.name not in seen, 'nonregular/duplicate tar member')
            seen.add(member.name)
            if member.name == 'MANIFEST.json':
                require(archive.extractfile(member).read() == manifest_bytes, 'manifest changed while packing')
                continue
            expected = manifest['files'][member.name]
            with archive.extractfile(member) as stream:
                require(member.size == expected['bytes'] and hashlib.file_digest(stream,'sha256').hexdigest() == expected['sha256'],
                        'archive member differs: '+member.name)
        require(seen == set(manifest['files']) | {'MANIFEST.json'}, 'archive inventory differs')
    receipt = dict(metadata,archive=destination.name,bytes=destination.stat().st_size,
        sha256=sha(destination),verified_members=len(manifest['files']),manifest_members=1,
        new_target_evaluations=0,portable_rebuild_verified=False)
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    return receipt


def build(root,raw,audit,report,statistics,data,output):
    require((raw/'SUMMARY.json').is_file(), 'completed W1 evidence required')
    with (raw/'run.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        files,metadata=inspect_inputs(root,raw,audit,report,statistics,data)
        for p in files.values():require(p.resolve()!=output.resolve(), 'archive cannot replace an input')
        return write_archive(files,metadata,output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['root','raw','audit','report','statistics','data','output']:
        parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args()
    print(json.dumps(build(a.root,a.raw,a.audit,a.report,a.statistics,a.data,a.output)))
