#!/usr/bin/env python3
"""Assemble a local submission entry. Never copy the full formal raw evidence.

The only raw arrays included are the already existing small R technical archive.
No publication, upload or scientific execution. Source and all versions are
bound through manifests; the final Git and transport seal is written externally.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def verify(directory):
    root=Path(directory)
    manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Entry contains a symlink')
    if actual!=set(manifest['files'])|{'MANIFEST.json','SHA256SUMS'}:
        raise ValueError('Entry members differ from the manifest')
    for name,item in manifest['files'].items():
        path=root/name
        if not path.resolve().is_relative_to(root.resolve()) or path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:
            raise ValueError('Entry content differs: '+name)
    expected=''.join(item['sha256']+'  '+name+'\n' for name,item in manifest['files'].items())
    expected+=sha(root/'MANIFEST.json')+'  MANIFEST.json\n'
    if (root/'SHA256SUMS').read_text(encoding='utf-8')!=expected:
        raise ValueError('Entry SHA256SUMS differs')
    return dict(passed=True,identity=manifest['identity'],content_files=len(manifest['files']),
                total_files=len(actual),source_commit=manifest['source_commit'])


def build(source, source_bundle, source_commit, software, r_evidence, locations, output):
    source,source_bundle,software,r_evidence,locations,output=map(Path,
        (source,source_bundle,software,r_evidence,locations,output))
    if output.exists():
        raise FileExistsError('Use a new release directory')
    output.mkdir(parents=True)
    root=output/'parallelbayes-submission-v5-rc1';root.mkdir()
    def copy(path,name):
        dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    copy(source_bundle,'source/ParallelBayes-submission-v5-rc1.bundle')
    copy(source/'LICENSE','LICENSE')
    for name in ('SUBMISSION-V5-RC1.md','SUBMISSION-V5-REPRODUCE.md','REPRODUCTION-MAP-V5.md','AUTHOR-DECISIONS-V5.md'):
        copy(source/'docs'/name,'docs/'+name)
    for folder in ('execution/submission-v5-rc1','environment/locks'):
        for path in sorted((source/folder).rglob('*')):
            if path.is_file():copy(path,path.relative_to(source).as_posix())
    for path in sorted(software.iterdir()):
        if path.name in ('parallelbayes-0.2.0.dev2-py3-none-any.whl','parallelbayes-0.2.0.dev2.tar.gz','parallelbayes_0.2.0.9002.tar.gz'):
            copy(path,'software/'+path.name)
    for name in ('parallelbayes-paper-v5.zip','软件与基准研究-审读修订v5.pdf',
                 '补充材料A-审读修订v5.pdf','补充材料B-审读修订v5.pdf'):
        copy(source/'output/software-paper'/name,'paper/'+name)
    copy(r_evidence,'evidence-small/'+r_evidence.name)
    inventory=json.loads((source/'execution/submission-v5-rc1/COMPONENTS.json').read_text(encoding='utf-8'))
    bindings=json.loads(locations.read_text(encoding='utf-8'))
    for component in inventory['components']:
        if component['kind']=='tree':
            path=Path(bindings[component['id']]['manifest'])
            if sha(path)!=component['manifest_sha256']:
                raise ValueError('External component manifest changed')
            copy(path,'component-manifests/'+component['manifest_filename'])
    copy(source/'scripts/submission/build_v5_entry.py','verify_entry.py')
    (root/'README.md').write_text('''# ParallelBayes v5 内部投稿候选

身份 submission-v5-rc1。先核对包外SEAL.json/SHA256SUMS中的归档哈希，再解包；根目录运行 `python verify_entry.py verify --directory .` 核对所有内容。

`source/`是固定源码Git bundle。运行 `git clone --branch codex/submission-v5-rc1 source/ParallelBayes-submission-v5-rc1.bundle NEW_SOURCE`，核对commit/tag与包外seal一致。版本、43组件、验收和作者决策分别见execution/submission-v5-rc1与docs。

`paper/`包含16/47/67页三PDF及完整TeX输入。解压paper-v5，在其根目录运行BUILD.py即可重编译。`software/`包含原安装候选，数值核心未改。`evidence-small/`含约2MiB的原R技术证据（成功、失败、日志全部保留），仅用于读取和核验，不代表正式实验新增样本。

约39.36GB的历史/主实验组件没有复制进本包，另按COMPONENTS.json取得真实权限；其中存在历史表示重叠。此入口仅在作者本地，未自动公开。Windows草稿、作者信息、期刊和材料许可/公开范围仍待确认。内部验收不等于真实非作者权限下载通过，也不授权投稿或CRAN发布。
''',encoding='utf-8')
    files={p.relative_to(root).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))
           for p in sorted(root.rglob('*')) if p.is_file()}
    manifest=dict(identity='submission-v5-rc1',source_commit=source_commit,
                  full_formal_raw_evidence_included=False,small_saved_R_raw_included=True,
                  automatic_publication=False,files=files)
    (root/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    sums=''.join(v['sha256']+'  '+k+'\n' for k,v in files.items())+sha(root/'MANIFEST.json')+'  MANIFEST.json\n'
    (root/'SHA256SUMS').write_text(sums,encoding='utf-8')
    result=verify(root)
    archive=output/'parallelbayes-submission-v5-rc1-entry.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for path in sorted(root.rglob('*')):
            if path.is_file():tar.add(path,arcname=path.relative_to(root).as_posix(),recursive=False)
    with tarfile.open(archive) as tar:
        for name,item in files.items():
            if hashlib.sha256(tar.extractfile(name).read()).hexdigest()!=item['sha256']:
                raise ValueError('Entry archive member differs')
    result.update(filename=archive.name,bytes=archive.stat().st_size,sha256=sha(archive),
                  full_formal_raw_evidence_included=False,small_saved_R_raw_included=True,new_sampler_calls=0)
    (output/'BUILD-ENTRY.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('build','verify'))
    p.add_argument('--directory',type=Path)
    for name in ('source','source-bundle','source-commit','software','r-evidence','locations','output'):
        p.add_argument('--'+name)
    a=p.parse_args()
    if a.action=='verify':
        if a.directory is None:p.error('--directory required')
        print(json.dumps(verify(a.directory)))
    else:
        kwargs={k:v for k,v in vars(a).items() if k not in ('action','directory')}
        if any(v is None for v in kwargs.values()):p.error('All build arguments required')
        build(**kwargs)
