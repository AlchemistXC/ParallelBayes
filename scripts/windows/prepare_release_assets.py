"""Split the immutable CPU evidence archive for GitHub Releases (<2 GiB/asset)."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 source=ROOT/'output/reproduction';dest=ROOT/'output/github-assets';dest.mkdir(exist_ok=True);rows=[]
 index=json.loads((source/'index.json').read_text());chunk_size=512*1024*1024
 for row in index['archives']:
  src=source/row['path'];assert src.stat().st_size==row['bytes'] and digest(src)==row['sha256']
  r={'name':src.name,'bytes':row['bytes'],'sha256':row['sha256']}
  if src.stat().st_size<=chunk_size:shutil.copy2(src,dest/src.name)
  else:
   parts=[]
   with src.open('rb') as stream:
    i=0
    while stream.tell()<row['bytes']:
     name=src.name+f'.part{i:03d}';path=dest/name;h=hashlib.sha256();n=0
     with path.open('wb') as f:
      while n<chunk_size:
       b=stream.read(min(8*1024*1024,chunk_size-n))
       if not b:break
       f.write(b);h.update(b);n+=len(b)
     parts.append({'name':name,'bytes':n,'sha256':h.hexdigest()});i+=1
   r['parts']=parts
  rows.append(r)
 manifest={'release_tag':'cpu-review-v1','repository':'AlchemistXC/ParallelBayes','scope':'Immutable historical CPU evidence; native Windows GPU not yet implemented','archives':rows}
 body=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
 (ROOT/'handoff/windows-native/release-assets.json').write_text(body);(dest/'release-assets.json').write_text(body)
 for name in ['index.json','validation.json','SHA256SUMS']:shutil.copy2(source/name,dest/name)
 (dest/'ASSEMBLE.md').write_text('Download all assets. Clone AlchemistXC/ParallelBayes, then run:\n\n    py -3.12 scripts/windows/assemble_evidence.py --directory PATH_TO_DOWNLOADS\n\nThe repository manifest pins the expected hashes. Extract all three reconstructed archives in a SEPARATE historical reproduction directory; do not overwrite the development checkout.\n')
 (dest/'ASSET-SHA256SUMS').write_text(''.join(digest(p)+'  '+p.name+'\n' for p in sorted(dest.iterdir()) if p.is_file() and p.name!='ASSET-SHA256SUMS'))
 print(json.dumps({'asset_count':len(list(dest.iterdir())),'total_bytes':sum(p.stat().st_size for p in dest.iterdir()),'manifest':'handoff/windows-native/release-assets.json'}))
if __name__=='__main__':main()
