"""Prepare a native-Windows identity for the already fixed wells validation."""
import copy
import hashlib
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'benchmark/protocols/wells-windows-validation-v1'
INPUT=ROOT/'benchmark/fixtures/wells-validation-v1/inputs.npz'


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def platform_protocol(original,device,source_commit,source_files):
    if device not in ('cpu','cuda'):
        raise ValueError('Unsupported Windows device')
    p=copy.deepcopy(original)
    p.pop('protocol_sha256')
    p.update(identity='external-wells-windows-'+device+'-v1',required_os='Windows',
        parent_protocol_sha256=original['protocol_sha256'],source_commit=source_commit,
        source_files=source_files,runtime='Native Windows only; record actual torch/CPU or RTX5080 CUDA runtime. Availability is not validation.')
    p['base_config']['device']=device
    p['protocol_sha256']=identity(p)
    return p


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(directory):
    if directory.exists():raise FileExistsError('Preserve the frozen Windows identity')
    old=json.loads((ROOT/'benchmark/protocols/external-wells-validation-v2.json').read_text())
    expected=old['protocol_sha256'];unsigned=dict(old);unsigned.pop('protocol_sha256')
    if identity(unsigned)!=expected:raise ValueError('Parent protocol identity mismatch')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    files={}
    for name,digest in old['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Parent source changed: '+name)
    names=list(old['source_files'])+['scripts/completion/windows_wells.py']
    for name in names:
        if (ROOT/name).read_bytes()!=subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT):
            raise ValueError('Commit source before freeze: '+name)
        files[name]=sha(ROOT/name)
    directory.mkdir(parents=True)
    for device in ['cpu','cuda']:
        p=platform_protocol(old,device,commit,files)
        p.pop('protocol_sha256')
        p['created_utc']=datetime.now(timezone.utc).isoformat()
        p['input_file_sha256']=sha(INPUT)
        p['protocol_sha256']=identity(p)
        (directory/(device+'.json')).write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps(inspect(directory),indent=2))


def inspect(directory):
    records=[]
    for device in ['cpu','cuda']:
        p=json.loads((directory/(device+'.json')).read_text())
        unsigned=dict(p);expected=unsigned.pop('protocol_sha256')
        if identity(unsigned)!=expected or p['base_config']['device']!=device or p['required_os']!='Windows':
            raise ValueError('Windows protocol changed')
        for name,digest in p['source_files'].items():
            if sha(ROOT/name)!=digest:raise ValueError('Source changed: '+name)
        if sha(INPUT)!=p['input_file_sha256']:raise ValueError('Actual input file changed')
        records.append(dict(identity=p['identity'],protocol_sha256=expected,device=device))
    return dict(status='plan_checks_passed',runtime_verified=False,
                scope='Source, protocol and input identity only; not a Windows/CUDA execution',protocols=records)


def run(device,source,output,directory):
    if sys.platform!='win32':raise RuntimeError('Native Windows is required; Mac/WSL/Linux cannot certify this run')
    inspect(directory)
    # Existing validator records actual platform, environment, every failed
    # trajectory, and NumPy audits; no silent backend substitution.
    sys.path.insert(0,str(ROOT/'scripts/completion'))
    from validate_wells import run_validation
    result=run_validation(source,output,'torch',directory/(device+'.json'),INPUT)
    print(json.dumps(result['record'],indent=2))
    return 0 if result['record']['status']=='passed' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,default=DIRECTORY)
    sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('freeze');sub.add_parser('inspect')
    r=sub.add_parser('run');r.add_argument('--device',choices=['cpu','cuda'],required=True)
    r.add_argument('--source',type=Path,required=True);r.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.action=='freeze':freeze(a.directory.resolve())
    elif a.action=='inspect':print(json.dumps(inspect(a.directory.resolve()),indent=2))
    else:sys.exit(run(a.device,a.source.resolve(),a.output.resolve(),a.directory.resolve()))
