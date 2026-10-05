"""Record one authorized native Windows completion command without changing its inputs."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
BATCH=ROOT/'output/completion/windows-round2-20261005'


def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command or Path(a.name).name!=a.name:raise ValueError('Command and simple step name required')
    if sys.platform!='win32':raise RuntimeError('Native Windows only')
    folder=BATCH/'commands'/a.name;folder.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,R_LIBS_USER='D:/Tools/R-library-4.6',LC_ALL='C',LANG='C',
        PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONPATH=str(ROOT/'r-package/inst/python'))
    receipt=dict(command=command,cwd=str(ROOT),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        environment_overrides={k:env[k] for k in ('R_LIBS_USER','LC_ALL','LANG','PYTHONDONTWRITEBYTECODE','PYTHONUTF8','PYTHONIOENCODING','PYTHONPATH')})
    target=folder/'receipt.json';target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    start=time.perf_counter()
    with (folder/'stdout-stderr.log').open('xb') as log:
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        receipt['pid']=child.pid;target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        code=child.wait()
    receipt.update(exit_code=code,elapsed_seconds=time.perf_counter()-start,
        ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        log_sha256=hashlib.sha256((folder/'stdout-stderr.log').read_bytes()).hexdigest())
    target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(step=a.name,exit_code=code,elapsed_seconds=receipt['elapsed_seconds'],log=str(folder/'stdout-stderr.log'))),flush=True)
    return code


if __name__=='__main__':sys.exit(main())
