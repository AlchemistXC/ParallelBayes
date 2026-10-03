"""Continue the authorized local pipeline after the frozen v1 benchmark ends."""
from pathlib import Path
import subprocess,json,time,sys,os
python=sys.executable
root=Path.cwd()
def call(args,filename,env=None):
 with (root/'execution/logs'/filename).open('w') as out:
  result=subprocess.run(args,cwd=root,stdout=out,stderr=subprocess.STDOUT,env=env)
 if result.returncode:raise RuntimeError(f'{filename}: exit {result.returncode}')
 print(filename,'completed',flush=True)
if '--after-wait' not in sys.argv:
 (root/'execution/local-pipeline.pid').write_text(str(os.getpid()))
 while (root/'benchmark/runs/cpu-formal-v1/.runner.lock').exists():time.sleep(30)
 os.execv(python,[python,str(Path(__file__).resolve()),'--after-wait'])
call([python,'scripts/promote-reviewed-source.py'],'source-promotion.txt')
call([python,'-m','pip','install','--no-deps','--no-build-isolation','-e','.'],'python-release-install.txt')
call([python,'-m','pytest','tests/python','tests/safety','-q','--junitxml=execution/logs/python-reviewed-release.xml'],'python-reviewed-release.txt')
call([python,'scripts/verify-statistical-evidence.py','--protocol','benchmark/protocols/statistical-v4.json','--output','execution/statistical-v4'],'statistical-preflight.txt')
call([python,'scripts/statistical-validation.py','--protocol','benchmark/protocols/statistical-v4.json','--replicates','64','--output','execution/statistical-v4'],'statistical-formal.txt')
call([python,'scripts/verify-statistical-evidence.py','--protocol','benchmark/protocols/statistical-v4.json','--output','execution/statistical-v4','--require-complete'],'statistical-integrity.txt')
call([python,'benchmark/analysis/sbc-functions.py','--runs','execution/statistical-v4','--output','execution/statistical-v4/likelihood-ranks.json'],'statistical-likelihood-ranks.txt')
call([python,'benchmark/analysis/analyze.py','reference','--protocol','benchmark/protocols/reference-v1.json','--runs','benchmark/runs/cpu-reference-v1','--output','benchmark/analysis/outputs/reference-summary.json'],'reference-analysis-reviewed.txt')
call([python,'benchmark/analysis/analyze.py','formal','--protocol','benchmark/protocols/protocol-v1.json','--runs','benchmark/runs/cpu-formal-v1','--reference','benchmark/analysis/outputs/reference-summary.json','--output','benchmark/analysis/outputs/cpu-formal'],'formal-analysis.txt')
call([python,'scripts/write-results-tex.py'],'write-results-tex.txt')
call([python,'benchmark/analysis/figures.py'],'formal-figures.txt')
call(['/usr/local/bin/Rscript','--vanilla','scripts/install-r.R'],'r-release-install.txt')
call(['/usr/local/bin/Rscript','--vanilla','examples/quickstart.R'],'r-release-quickstart.txt')
call(['/usr/local/bin/Rscript','--vanilla','examples/logistic-paired.R'],'r-release-logistic-paired.txt')
(root/'execution/local-data-pipeline-complete.json').write_text(json.dumps(dict(status='completed',next='Figure QA, manuscript compilation and final evidence review'),indent=2))
print('Local data pipeline complete',flush=True)
