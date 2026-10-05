"""Read-only final identity, raw-asset, log and curated-evidence validation."""
import argparse
import hashlib
import importlib.metadata as md
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):return json.loads(p.read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--small',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();root=Path(__file__).resolve().parents[1]
    before=read(a.batch/'environment-preflight.json');protocols=[]
    for row in before['protocols']:
        p=read(root/row['path']);unsigned=dict(p);identity=unsigned.pop('protocol_sha256')
        assert hashlib.sha256(json.dumps(unsigned,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==identity
        assert identity==row['identity']
        assert all(sha(root/n)==h for n,h in p['source_files'].items())
        protocols.append(dict(path=row['path'],identity=identity,source_files=len(p['source_files'])))
    distributions=dict(sorted((d.metadata['Name'],d.version) for d in md.distributions()))
    assert distributions==before['all_distributions']
    marker=Path(sys.executable).parents[1]/'PARALLELBAYES-FROZEN.json'
    assert sha(marker)==before['original_frozen_marker_sha256']
    freeze=subprocess.check_output([sys.executable,'-m','pip','freeze','--all'],text=True)
    assert freeze==(a.batch/'pip-freeze.txt').read_text(encoding='utf-8')
    checked=0
    for name in ['nuts-run','mh-cpu-run','mh-cuda-run']:
        for statefile in sorted((a.batch/name).glob('*/state.json')):
            s=read(statefile)
            for n,h in s['assets'].items():
                assert sha(statefile.parent/n)==h
                checked+=1
    manifest=read(a.small/'SHA256.json')
    for n,h in manifest.items():assert sha(a.small/n)==h
    commands=[]
    for receipt in sorted((a.batch/'commands').glob('*/receipt.json')):
        r=read(receipt);assert 'exit_code' in r
        assert sha(receipt.parent/'stdout-stderr.log')==r['log_sha256']
        commands.append(dict(step=receipt.parent.name,exit_code=r['exit_code']))
    failures=[r['step'] for r in commands if r['exit_code']!=0]
    assert failures==['f2-f4-handoff-tests','f2-prepare']
    tests={}
    for name in ['handoff-tests.xml','handoff-tests-02.xml','nuts-tests.xml','mh-tests.xml']:
        suite=ET.parse(a.batch/name).getroot().find('testsuite')
        tests[name]={key:int(suite.attrib[key]) for key in ('tests','failures','errors','skipped')}
    expected={'handoff-tests.xml':(6,0,3,1),'handoff-tests-02.xml':(6,0,0,1),'nuts-tests.xml':(3,0,0,0),'mh-tests.xml':(3,0,0,0)}
    for name,values in expected.items():assert tuple(tests[name].values())==values
    result=dict(status='passed',checked_protocols=protocols,raw_assets_verified=checked,
        curated_files_verified=len(manifest),commands=commands,retained_failed_commands=failures,
        tests=tests,original_environment_and_marker_unchanged=True,
        scope='Delivery integrity; explicitly preserves the blocked mechanism stage and adverse diagnostics.')
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('commands','checked_protocols')},indent=2))


if __name__=='__main__':main()
