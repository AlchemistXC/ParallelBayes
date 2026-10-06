from pathlib import Path
from datetime import datetime, timezone
import json, os, subprocess, sys, time

B=Path(__file__).resolve().parent
step=sys.argv[1]
out=B/'reconstruction';out.mkdir(exist_ok=True)
R='/usr/local/bin/Rscript'
rlib='/Users/haku/Workspace/ParallelBayes/output/research-completion/release-review-v1/R-library'
commands={}
runtime=B/'sources/runtime'
commands['runtime']=[sys.executable,str(runtime/'scripts/windows/audit_technical_batch.py'),'audit',
 '--bundle',str(B/'received/runtime/output/windows-runtime-technical-v1'),
 '--output',str(out/'runtime'), '--rscript',R,'--r-library',rlib,'--cross-platform']
for device in ('cpu','cuda'):
    source=B/'sources/mechanism';raw=B/'received/mechanism/output/completion/windows-mechanism-original-attempt01'
    commands['mechanism-'+device]=[sys.executable,str(source/'scripts/completion/analyze_mechanism_pilot.py'),
      '--plan',str(source/'benchmark/protocols/mechanism-windows-pilot-v1.json'),
      '--run',str(raw/('mechanism-'+device)),'--inputs',str(raw/'original-inputs'),
      '--output',str(out/('mechanism-'+device))]
    commands['package-'+device]=[R,'--vanilla',str(B/'sources/package/scripts/windows/installed_R_objects.R'),
      str(B/'received/package/output/windows-package-candidate-v1'/('R-example-'+device)),str(out/('package-'+device+'.json'))]
cmd=commands[step];receipt=out/(step+'-command.json');log=out/(step+'.log')
if receipt.exists() or log.exists():raise FileExistsError('Retain old attempt; choose new identity for a changed command')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',R_LIBS_USER=rlib)
record=dict(command=cmd,started_utc=datetime.now(timezone.utc).isoformat(),R_LIBS_USER=rlib,
            scope='Read-only reception; no Windows/CUDA timing or new MCMC')
receipt.write_text(json.dumps(record,indent=2)+'\n')
start=time.perf_counter()
with log.open('w') as f:p=subprocess.run(cmd,cwd=B,env=env,stdout=f,stderr=subprocess.STDOUT)
record.update(exit_code=p.returncode,receiver_elapsed_seconds=time.perf_counter()-start,
              ended_utc=datetime.now(timezone.utc).isoformat())
receipt.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(step=step,exit_code=p.returncode,seconds=record['receiver_elapsed_seconds'],log=str(log))))
sys.exit(p.returncode)
