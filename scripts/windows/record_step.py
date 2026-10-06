"""Record one native Windows command in an explicitly selected evidence batch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--name',required=True)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    batch=(ROOT/args.batch).resolve()
    if not batch.is_relative_to(ROOT) or not batch.is_dir():
        raise ValueError('Use an existing project batch directory')
    if not args.name or Path(args.name).name!=args.name or args.name in ('.','..'):
        raise ValueError('Use a simple unique command name')
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command or sys.platform!='win32':
        raise ValueError('Command and native Windows required')
    folder=batch/'commands'/args.name
    folder.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8',
        PYTHONPATH=str(ROOT/'r-package/inst/python'))
    receipt=dict(command=command,cwd=str(ROOT),batch=str(batch),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        recorder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        started_utc=datetime.now(timezone.utc).isoformat(),
        environment_overrides={k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','PYTHONUTF8','PYTHONIOENCODING','PYTHONPATH')})
    dest=folder/'receipt.json'
    def save():dest.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    save();start=time.perf_counter()
    try:
        with (folder/'stdout-stderr.log').open('xb') as log:
            child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            receipt['pid']=child.pid;save()
            code=child.wait()
    except BaseException as exc:
        receipt.update(recording_error=type(exc).__name__+': '+str(exc),
            elapsed_seconds=time.perf_counter()-start,
            process_exit_not_confirmed=True)
        save()
        raise
    receipt.update(exit_code=code,elapsed_seconds=time.perf_counter()-start,
        ended_utc=datetime.now(timezone.utc).isoformat(),
        log_sha256=hashlib.sha256((folder/'stdout-stderr.log').read_bytes()).hexdigest())
    save()
    print(json.dumps(dict(step=args.name,exit_code=code,seconds=receipt['elapsed_seconds'],pid=child.pid)),flush=True)
    return code


if __name__=='__main__':sys.exit(main())
