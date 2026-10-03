"""Additional read-only audit of every frozen input, including terminal tasks.

The original driver checks input files when executing a task. This audit also
checks inputs for skipped terminal tasks, and all recorded source/lock identities.
It is a separate post-freeze reviewer; the frozen numerical source is unchanged.
"""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/windows'))
from evidence import configure,sha,write_json,verify_checksums
from run_study import verify_protocol
from parallelbayes.torch_backend.sampling import tape_hash
import numpy as np


def main():
    configure()
    run=ROOT/'execution/windows-native/windows-native-v1'
    p=json.loads((run/'protocol.json').read_text())
    assert p==json.loads((ROOT/'benchmark/protocols/windows-native-v1.json').read_text())
    verify_protocol(p)
    for field in ('dependency_lock','r_dependency_lock'):
        assert sha(ROOT/p[field])==p[field+'_sha256']
    assert sha(p['r_executable'])==p['r_executable_sha256']
    marker=json.loads((Path(sys.prefix)/'PARALLELBAYES-FROZEN.json').read_text())
    for key in ('protocol_sha256','source_commit','dependency_lock_sha256'):
        assert marker[key]==p[key]
    inputs={t['tape_sha256']:t['tape_file_sha256'] for t in p['tasks']}
    for digest,file_digest in inputs.items():
        path=run/'inputs'/(digest+'.npz')
        assert sha(path)==file_digest
        with np.load(path) as f:
            assert tape_hash({k:f[k] for k in f.files})==digest
    count=0
    for statefile in run.glob('tasks/*/state.json'):
        s=json.loads(statefile.read_text())
        folder=statefile.parent/s['attempt']
        verify_checksums(folder,s['checksums'])
        r=json.loads((folder/'result.json').read_text())
        if r.get('normal'):
            verify_checksums(folder/'normal',r['normal']['checksums'])
        count+=1
    assert count==len(p['tasks'])
    receipt=dict(status='passed',protocol_sha256=p['protocol_sha256'],source_commit=p['source_commit'],
        source_files=len(p['source_files']),input_files=len(inputs),terminal_tasks=count,
        python_runtime='matches frozen identity',python_lock='matches',r_lock='matches',
        r_executable='matches',venv_marker='matches',verifier_sha256=sha(__file__))
    write_json(run/'final-identity-audit.json',receipt)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
