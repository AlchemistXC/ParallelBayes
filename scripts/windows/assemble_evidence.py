"""Verify Release assets and join evidence parts using bounded memory, on any OS."""
from pathlib import Path
import argparse,hashlib,json,os

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def safe_name(name):
    if not isinstance(name,str) or not name or name in {'.','..'} or any(c in name for c in '/\\:'):
        raise ValueError('Manifest filenames must be plain basenames')
    return name

def verify(path,record):
    if not path.is_file():raise FileNotFoundError(path)
    if path.stat().st_size!=record['bytes'] or digest(path)!=record['sha256']:raise ValueError('Checksum/size mismatch: '+path.name)

def assemble(directory,manifest):
    directory=Path(directory);done=[]
    for item in manifest['archives']:
        dest=directory/safe_name(item['name'])
        if dest.exists():verify(dest,item);done.append(dest.name);continue
        parts=item.get('parts')
        if not parts:raise FileNotFoundError('Download asset '+dest.name)
        for part in parts:verify(directory/safe_name(part['name']),part)
        temporary=dest.with_name(dest.name+'.assembling')
        # Exclusive creation prevents concurrent assemblers overwriting one another.
        with temporary.open('xb') as target:
            for part in parts:
                with (directory/part['name']).open('rb') as src:
                    for block in iter(lambda:src.read(8*1024*1024),b''):target.write(block)
        verify(temporary,item)
        if dest.exists():raise FileExistsError(dest)
        temporary.replace(dest);done.append(dest.name)
    return done

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--manifest',type=Path,default=Path(__file__).resolve().parents[2]/'handoff/windows-native/release-assets.json');a=p.parse_args()
    print(json.dumps({'verified_archives':assemble(a.directory,json.loads(a.manifest.read_text(encoding='utf-8'))),'next':'Extract into a separate historical CPU reproduction directory, not over the Git working tree.'}))
if __name__=='__main__':main()
