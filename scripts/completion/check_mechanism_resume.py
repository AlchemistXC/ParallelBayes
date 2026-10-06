"""Snapshot terminal group files and verify an actual zero-recomputation resume."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def inventory(run):
    files={};attempts=[];states={}
    for statefile in sorted((run/'groups').glob('*/state.json')):
        state=read(statefile)
        if state['status'] not in ('completed','failed'):
            raise ValueError('Nonterminal group')
        folder=statefile.parent
        for name,digest in state['assets'].items():
            if sha(folder/name)!=digest:raise ValueError('Asset hash differs')
        states[folder.name]=dict(status=state['status'],identity=state['identity'])
        attempts += [p.relative_to(run).as_posix() for p in sorted(folder.glob('attempt-*')) if p.is_dir()]
        for p in sorted(folder.rglob('*')):
            if p.is_symlink():raise ValueError('Symlinked evidence')
            if p.is_file():files[p.relative_to(run).as_posix()]=sha(p)
    summary=read(run/'summary.json')
    if len(states)!=summary['planned_groups'] or summary['completed_groups']+summary['failed_groups']!=len(states):
        raise ValueError('All planned groups must be terminal')
    return dict(run=str(run.resolve()),summary=summary,summary_sha256=sha(run/'summary.json'),
        run_manifest_sha256=sha(run/'run.json'),files=files,attempt_directories=attempts,states=states)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['snapshot','verify'])
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--before',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();after=inventory(a.run)
    if a.action=='snapshot':result=after
    else:
        before=read(a.before)
        if before['run']!=after['run']:raise ValueError('Run path differs')
        changed=[n for n in sorted(set(before['files'])|set(after['files'])) if before['files'].get(n)!=after['files'].get(n)]
        new_attempts=sorted(set(after['attempt_directories'])-set(before['attempt_directories']))
        new_groups=sorted(set(after['states'])-set(before['states']))
        preserved=(before['states']==after['states'] and before['attempt_directories']==after['attempt_directories']
            and before['summary_sha256']==after['summary_sha256'] and before['run_manifest_sha256']==after['run_manifest_sha256'])
        result=dict(passed=not changed and preserved,terminal_groups=len(after['states']),
            terminal_files=len(after['files']),changed_files=changed,new_attempts=new_attempts,
            newly_executed_groups=len(set(new_groups)|{n.split('/')[1] for n in new_attempts}),
            evidence='Actual resume invocation plus unchanged complete terminal group trees and absence of new attempt directories. Frozen runner does not expose a new-group counter.',
            scope='Terminal resume only; no claim of interrupted recovery or Windows process-collection/resource protection.',
            before_summary_sha256=before['summary_sha256'],after_summary_sha256=after['summary_sha256'])
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('files','states','summary','attempt_directories')},indent=2))
    if a.action=='verify' and not result['passed']:raise ValueError('Resume changed terminal evidence')


if __name__=='__main__':main()
