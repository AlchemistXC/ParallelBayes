"""Download/check the locked BridgeStan source and platform stanc executable."""
from pathlib import Path
import hashlib,json,os,platform,shutil,tarfile,urllib.request
root=Path('environment');root.mkdir(exist_ok=True)
assets=json.loads((root/'locks/bridgestan-assets.json').read_text())
def fetch(path,info):
 if not path.exists():urllib.request.urlretrieve(info['url'],path)
 if hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:raise RuntimeError(f'Asset checksum failed: {path}')
fetch(root/'bridgestan-2.7.0.tar.gz',assets['bridgestan-2.7.0.tar.gz'])
source=root/'bridgestan-2.7.0'
if not source.exists():
 with tarfile.open(root/'bridgestan-2.7.0.tar.gz') as tar:tar.extractall(root,filter='data')
if platform.system()=='Darwin':
 info=json.loads((root/'locks/bridgestan-macos-asset.json').read_text())
elif platform.system()=='Linux' and platform.machine()=='x86_64':info=assets['stanc-linux-2.37.0']
else:raise SystemExit('This reproduction installer validates macOS and Linux x86_64 CPU only. Native Windows GPU is not implemented.')
fetch(source/'bin/stanc',info);os.chmod(source/'bin/stanc',0o755)
print('BRIDGESTAN='+str(source.resolve()))
