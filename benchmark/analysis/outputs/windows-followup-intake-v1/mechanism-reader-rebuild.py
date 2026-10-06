from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time

B=Path(__file__).resolve().parent
ROOT=Path('/Users/haku/.codex/worktrees/research-integration/ParallelBayes')
reader=B/'sources/mechanism-reader-v2'
assert not reader.exists()
shutil.copytree(B/'sources/mechanism',reader)
script='scripts/completion/analyze_mechanism_pilot.py'
shutil.copy2(ROOT/script,reader/script)
batch=B/'received/mechanism/output/completion/windows-mechanism-original-attempt01'
for device in ('cpu','cuda'):
    output=B/'reconstruction'/('mechanism-'+device+'-v2')
    command=[sys.executable,str(reader/script),'--plan',str(reader/'benchmark/protocols/mechanism-windows-pilot-v1.json'),
        '--run',str(batch/('mechanism-'+device)),'--inputs',str(batch/'original-inputs'),'--output',str(output)]
    start=time.perf_counter()
    with (B/'reconstruction'/('mechanism-'+device+'-v2.log')).open('x') as f:
        p=subprocess.run(command,cwd=B,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=f,stderr=subprocess.STDOUT)
    receipt=dict(command=command,exit_code=p.returncode,receiver_seconds=time.perf_counter()-start,
        source_base='1cfc83d9f979b0b58e830affc67ac22e277acc7d',reader_sha256=hashlib.sha256((reader/script).read_bytes()).hexdigest(),
        frozen_numerical_source_changed=False)
    (B/'reconstruction'/('mechanism-'+device+'-v2-command.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)
    if p.returncode:sys.exit(p.returncode)
