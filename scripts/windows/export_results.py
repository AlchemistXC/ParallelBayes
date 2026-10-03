"""Export a Windows run with protocol/environment inclusions and per-file hashes."""
from pathlib import Path
import argparse,hashlib,io,json,subprocess,tarfile,time

def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--include',type=Path,action='append',default=[]);p.add_argument('--output',type=Path,default=Path('output/windows-return'));a=p.parse_args()
    root=Path(__file__).resolve().parents[2];run=(root/a.run).resolve();out=(root/a.output).resolve()
    if not run.is_relative_to(root) or not run.is_dir() or not out.is_relative_to(root) or out.is_relative_to(run):raise ValueError('Run and output must be separate project directories')
    if git(root,'status','--porcelain'):raise RuntimeError('Commit the source and protocol first; do not export results against an ambiguous dirty source state')
    paths=[]
    for requested in [run,*[(root/x).resolve() for x in a.include]]:
        if not requested.is_relative_to(root) or not requested.exists():raise ValueError('Missing/non-project inclusion: '+str(requested))
        paths.extend([requested] if requested.is_file() else requested.rglob('*'))
    files={}
    for f in paths:
        if f.is_symlink():raise ValueError('Do not export symlinked evidence: '+str(f))
        if not f.is_file():continue
        if f.name.startswith('.env') or f.name.lower() in {'credentials','credentials.json'}:raise ValueError('Potential credential file must not be exported')
        files[str(f.relative_to(root)).replace('\\','/')]=f
    if not files:raise ValueError('No run files')
    stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime());out.mkdir(parents=True,exist_ok=True);target=out/f'windows-native-{stamp}.tar'
    manifest={'scope':'Integrity archive, not an assertion of scientific success','source_commit':git(root,'rev-parse','HEAD'),'branch':git(root,'branch','--show-current'),'files':{name:{'bytes':f.stat().st_size,'sha256':digest(f)} for name,f in sorted(files.items())}}
    data=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    with tarfile.open(target,'x') as tar:
        for name,f in sorted(files.items()):tar.add(f,arcname=name,recursive=False)
        info=tarfile.TarInfo('WINDOWS-RETURN-MANIFEST.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
    target.with_suffix('.tar.sha256').write_text(digest(target)+'  '+target.name+'\n',encoding='utf-8')
    print(target)
if __name__=='__main__':main()
