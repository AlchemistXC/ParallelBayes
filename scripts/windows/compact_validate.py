"""Explicit new compact gate CLI; never accepts the historical full-grid gate."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'scripts/windows')]
from compact_acceptance import seal_acceptance,verify_acceptance,foundation
from compact_freeze import verify


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('seal');q.add_argument('--bundle',type=Path,required=True)
    q.add_argument('--foundation-path',type=Path,required=True)
    for name in ('portable-xml','portable-command','native-xml','native-command','receiver-receipt','analysis-receipt','analysis-resume-receipt'):
        q.add_argument('--'+name,required=True)
    q=s.add_parser('verify');q.add_argument('--bundle',type=Path,required=True)
    q=s.add_parser('foundation');q.add_argument('--acceptance',type=Path,required=True)
    a=vars(p.parse_args());cmd=a.pop('command')
    if cmd=='seal':result=seal_acceptance(**a)
    elif cmd=='foundation':result=foundation(a['acceptance'],ROOT)
    else:
        b=a['bundle'];_,protocol,_,binding=verify(b)
        gate=verify_acceptance(b/'native-acceptance.json',protocol,ROOT,environment=binding['environment'])
        result=dict(passed=True,gate_sha256=gate['gate_sha256'],native_tests=gate['native_tests'],portable_tests=gate['portable_tests'])
    print(json.dumps(result,indent=2),flush=True)
