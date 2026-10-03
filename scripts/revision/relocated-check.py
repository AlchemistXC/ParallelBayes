"""Separate dependency environment and relocated source; same Mac/toolchain."""
from pathlib import Path
import shutil,subprocess,os,json
root=Path.cwd();dest=root/'execution/cpu-revision-v1/relocated-checkout';dest.mkdir(exist_ok=True)
for folder in ['r-package','models/stan','tests/python','tests/safety','examples','environment/locks','software/parallel-mcmc-upstream']:
 shutil.copytree(root/folder,dest/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.so','*.dylib','*.o'))
for name in ['pyproject.toml','LICENSE']:shutil.copy2(root/name,dest/name)
# Tests import the original analysis module, so include its implementation/data.
for folder in ['benchmark/analysis','benchmark/protocols']:
 shutil.copytree(root/folder,dest/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.png','*.pdf','*.svg'))
py=root/'execution/cpu-revision-v1/clean-python/bin/python'
env=dict(os.environ,BRIDGESTAN=str(root/'environment/bridgestan-2.7.0'))
with (root/'execution/cpu-revision-v1/relocated-check.log').open('w') as log:
 subprocess.run([str(py),'-m','pip','install','--no-build-isolation','--no-deps',str(dest)],check=True,env=env,stdout=log,stderr=subprocess.STDOUT)
 subprocess.run([str(py),'-m','pytest','tests/python','tests/safety','-q','--junitxml=validation.xml'],cwd=dest,env=env,check=True,stdout=log,stderr=subprocess.STDOUT)
 subprocess.run([str(py),'examples/custom-poisson-target.py'],cwd=dest,env=env,check=True,stdout=log,stderr=subprocess.STDOUT)
print('Relocated Python validation completed')
