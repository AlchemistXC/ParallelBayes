"""Append terminal formal evidence to the existing draft, after real waiting.

Never publishes, overwrites, deletes remote assets, merges, force-pushes or
samples. Full tar stays local. Temporary upload blocks are reproducible byte
ranges of that tar; remote digests and local range hashes are retained.
"""
import argparse
import gzip
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
from urllib.parse import quote,urlsplit

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/windows'))
from finish_formal_study import wait_for_manager,write,sha
REPO='AlchemistXC/ParallelBayes'
BRANCH='codex/windows-formal-delivery'
TAG='windows-completion-v2-20261005'
RELEASE=403644544
TARGET='ced54ef6ce945198339a138142dcdfede84f06bc'
API='https://api.github.com/repos/'+REPO
BLOCK=1536*1024**2


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--post',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    post=a.post.resolve();start=json.loads((post/'STARTED.json').read_text())
    write(out/'STARTED.json',dict(watched_post_manager=start['manager_identity'],post=str(post),
        helper_sha256=sha(__file__),automatic_retry=False,public_release_authorized=False,sampler_calls=0))
    begin=time.perf_counter()
    try:
        wait_for_manager(start['manager_identity'],out)
        from job_objects import observe_named_job
        for job_file in post.glob('*/job.json'):
            proof=observe_named_job(json.loads(job_file.read_text())['name'])
            if proof['state']=='present' and proof['active_processes']:
                raise ValueError('Postprocessing descendants active; refuse publication')
        terminal=post/'FINISHED.json' if (post/'FINISHED.json').exists() else post/'FAILED.json'
        if not terminal.exists():raise ValueError('No classified postprocessing terminal record')
        if git('branch','--show-current')!=BRANCH or git('remote','get-url','origin')!='https://github.com/'+REPO+'.git':
            raise ValueError('Unexpected reporting branch or remote repository')
        if git('status','--porcelain'):raise ValueError('Preserve dirty delivery checkout; do not auto-clean it')
        small=ROOT/'execution/windows-native/formal-inference-v1/terminal'
        small.mkdir(exist_ok=False)
        for name in ('FINISHED.json','FAILED.json','CLOSED-FRAME.json','STORAGE-BEFORE-ARCHIVE.json',
                     'MANAGER-ENDED.json','relocation.json','archive-verification.json','analysis-resume-invariance.json'):
            if (post/name).is_file():shutil.copy2(post/name,small/name)
        for folder in post.iterdir():
            if folder.is_dir():
                dest=small/'commands'/folder.name;dest.mkdir(parents=True,exist_ok=False)
                for name in ('started.json','finished.json','job.json','primary.json'):
                    if (folder/name).is_file():shutil.copy2(folder/name,dest/name)
        outcome=json.loads(terminal.read_text())
        frame=json.loads((post/'CLOSED-FRAME.json').read_text()) if (post/'CLOSED-FRAME.json').exists() else None
        summary=dict(local_postprocessing_terminal=terminal.name,postprocessing=outcome,
            phase_frame=frame,independent_Mac_intake_complete=False,formal_research_complete=False,
            originals_remain_on_Windows=True)
        write(small/'STATUS.json',summary)
        archive=None
        if (post/'archive-verification.json').exists():
            verified=json.loads((post/'archive-verification.json').read_text())
            if verified['status']!='passed':raise ValueError('Unverified raw tar')
            archive=Path(verified['archive'])
            if sha(archive)!=verified['archive_sha256']:raise ValueError('Verified raw archive changed')
            # Keep the complete file list in Git without adding raw arrays or a
            # >100MiB individual metadata file. Source manifest hash is bound.
            with tarfile.open(archive,'r') as stream:
                payload=stream.extractfile('WINDOWS-RETURN-MANIFEST.json')
                with gzip.open(small/'WINDOWS-RETURN-MANIFEST.json.gz','xb') as dest:
                    shutil.copyfileobj(payload,dest,1024*1024)
        analysis_root=Path('C:/ParallelBayes-formal-analysis-v1')
        if (analysis_root/'report').is_dir():
            report_dest=small/'report'
            shutil.copytree(analysis_root/'report',report_dest)
        # This is a new reporting commit, never a mutation of the sampling tree.
        git('add',str(small.relative_to(ROOT)))
        git('-c','user.name=Codex','-c','user.email=codex@local.invalid','commit','-m',
            'Record terminal formal evidence and retain all failures and intake limits')
        git('push','origin',BRANCH)
        commit=git('rev-parse','HEAD')
        remote=git('ls-remote','origin','refs/heads/'+BRANCH)
        if remote.split()[0]!=commit:raise ValueError('Reporting push identity differs')
        bundle=out/('windows-formal-source-'+commit[:12]+'.bundle')
        subprocess.run(['git','bundle','create',str(bundle),BRANCH,'codex/windows-formal-inference'],cwd=ROOT,check=True)
        bundle.with_suffix('.bundle.sha256').write_text(sha(bundle)+'  '+bundle.name+'\n',encoding='utf-8')
        # Logs/receipts and actual installed/source identities, no private skill
        # directories, credentials or venv binaries are included.
        metadata=out/('windows-formal-terminal-'+commit[:12]+'.tar')
        paths=[*small.rglob('*'),*post.rglob('*')]
        files={str(f.relative_to(ROOT)).replace('\\','/'):f for f in paths if f.is_file()}
        manifest=dict(scope='Terminal administrative/analysis evidence; not the raw trajectory archive',
            source_commit=commit,scientific_source_commit='0ba5643a6b580e79b8040f13a5e3165322db0e77',
            files={n:dict(bytes=f.stat().st_size,sha256=sha(f)) for n,f in files.items()})
        import io
        with tarfile.open(metadata,'x') as tar:
            for name,path in sorted(files.items()):tar.add(path,arcname=name,recursive=False)
            data=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('WINDOWS-RETURN-MANIFEST.json')
            info.size=len(data);tar.addfile(info,io.BytesIO(data))
        metadata.with_suffix('.tar.sha256').write_text(sha(metadata)+'  '+metadata.name+'\n',encoding='utf-8')
        receipt=out/'metadata-verification.json'
        subprocess.run([sys.executable,str(ROOT/'scripts/verify-windows-return.py'),str(metadata),'--output',str(receipt)],check=True)
        # Token comes only from existing Git credential helper and lives only in
        # memory; never write/print it or any authorization header.
        cred=subprocess.run(['git','credential','fill'],cwd=ROOT,
            input='protocol=https\nhost=github.com\npath='+REPO+'.git\n\n',text=True,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never'))
        if cred.returncode:raise RuntimeError('Existing GitHub account connection unavailable')
        fields=dict(x.split('=',1) for x in cred.stdout.splitlines() if '=' in x);token=fields.get('password')
        del cred,fields
        if not token:raise RuntimeError('No GitHub account credential available')
        def request(method,url,path=None):
            parsed=urlsplit(url)
            if parsed.scheme!='https' or parsed.hostname not in ('api.github.com','uploads.github.com') or not parsed.path.startswith('/repos/'+REPO+'/'):
                raise ValueError('Unauthorized API host/repository')
            if method not in ('GET','POST') or (method=='POST' and not parsed.path.endswith('/releases/'+str(RELEASE)+'/assets')):
                raise ValueError('Only reading/appending existing draft assets allowed')
            h={'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,
               'User-Agent':'ParallelBayes-formal-evidence','X-GitHub-Api-Version':'2026-03-10'}
            conn=http.client.HTTPSConnection(parsed.hostname,timeout=120)
            route=parsed.path+('?' +parsed.query if parsed.query else '')
            try:
                if path:
                    h.update({'Content-Type':'application/octet-stream','Content-Length':str(path.stat().st_size)})
                    conn.putrequest(method,route)
                    for k,v in h.items():conn.putheader(k,v)
                    conn.endheaders()
                    with path.open('rb') as stream:
                        for block in iter(lambda:stream.read(1024**2),b''):conn.send(block)
                else:conn.request(method,route,headers=h)
                response=conn.getresponse();body=response.read()
                if not 200<=response.status<300:raise RuntimeError('GitHub HTTP '+str(response.status)+' '+method+' '+parsed.path)
                return json.loads(body)
            finally:conn.close()
        def check_release():
            r=request('GET',API+'/releases/'+str(RELEASE))
            if r['tag_name']!=TAG or not r['draft'] or r['target_commitish']!=TARGET:
                raise ValueError('Original release is not the expected unchanged draft')
            return r
        def assets():
            result=[]
            for page in range(1,12):
                batch=request('GET',API+'/releases/'+str(RELEASE)+'/assets?per_page=100&page='+str(page))
                result.extend(batch)
                if len(batch)<100:break
            if len({x['name'] for x in result})!=len(result):raise ValueError('Duplicate asset names')
            return result
        release=check_release();before=assets();all_uploaded=[]
        nblocks=math.ceil(archive.stat().st_size/BLOCK) if archive else 0
        fixed=[metadata,metadata.with_suffix('.tar.sha256'),receipt,bundle,bundle.with_suffix('.bundle.sha256')]
        if any(p.stat().st_size>=2*1024**3 for p in fixed):
            raise OSError('A metadata asset exceeds the official per-asset limit; preserve it for explicit splitting')
        if len(before)+len(fixed)+nblocks+2>1000:raise OSError('Release asset capacity insufficient; retain Windows originals')
        upload_url=release['upload_url'].split('{',1)[0]
        def upload(path):
            check_release();digest=sha(path)
            existing=[x for x in assets() if x['name']==path.name]
            item=existing[0] if existing else request('POST',upload_url+'?name='+quote(path.name),path)
            if item['state']!='uploaded' or item['size']!=path.stat().st_size or item.get('digest')!='sha256:'+digest:
                raise ValueError('Remote size/digest differs; never overwrite '+path.name)
            all_uploaded.append({k:item.get(k) for k in ('id','name','size','digest','browser_download_url')})
            write(out/'UPLOAD-PROGRESS.json',dict(draft=True,commit=commit,assets=all_uploaded,
                full_independent_Mac_intake_complete=False))
        for path in fixed:upload(path)
        parts=[]
        if archive:
            archive_digest=json.loads((post/'archive-verification.json').read_text())['archive_sha256']
            with archive.open('rb') as source:
                for i in range(nblocks):
                    part=out/(archive.name+'.part'+str(i+1).zfill(4))
                    size=min(BLOCK,archive.stat().st_size-i*BLOCK);left=size
                    with part.open('xb') as dest:
                        while left:
                            block=source.read(min(left,1024**2))
                            if not block:raise ValueError('Raw tar truncated during split')
                            dest.write(block);left-=len(block)
                        dest.flush();os.fsync(dest.fileno())
                    parts.append(dict(order=i+1,name=part.name,offset=i*BLOCK,bytes=size,sha256=sha(part)))
                    write(out/'PARTS-IN-PROGRESS.json',dict(archive=str(archive),archive_sha256=archive_digest,
                        parts=parts,local_whole_tar_retained=True))
                    upload(part)
                    # Only this newly-created, remotely verified duplicate range
                    # is removed. Complete tar/originals/reserves/history remain.
                    part.unlink()
            parts_file=out/'windows-formal-raw-parts.json'
            write(parts_file,dict(archive_name=archive.name,archive_bytes=archive.stat().st_size,
                archive_sha256=json.loads((post/'archive-verification.json').read_text())['archive_sha256'],
                parts=parts,local_whole_tar=str(archive),local_whole_tar_retained=True,
                transient_blocks_removed_only_after_remote_digest_verification=True,
                reassembly='Concatenate listed files in order into a new binary file, verify whole SHA256, then verify-windows-return.py; no RNG/sampling',
                full_independent_Mac_intake_complete=False))
            upload(parts_file)
        after=assets();by_id={x['id']:x for x in after}
        for old in before:
            current=by_id.get(old['id'])
            if not current or any(current.get(k)!=old.get(k) for k in ('name','size','state','digest')):
                raise ValueError('An old release asset changed')
        check_release()
        write(out/'FINISHED.json',dict(status='terminal_assets_appended_to_original_draft',commit=commit,
            release_url=release['html_url'],assets=all_uploaded,previous_assets_unchanged=True,draft=True,
            archive_uploaded_as_verified_parts=bool(archive),whole_tar_retained_on_Windows=bool(archive),
            known_publish_sequence_seconds_including_wait=time.perf_counter()-begin,
            independent_Mac_intake_complete=False,formal_research_complete=False))
        return 0
    except BaseException as exc:
        import traceback
        write(out/'FAILED.json',dict(error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),
            known_seconds_including_wait=time.perf_counter()-begin,no_automatic_retry=True,
            preserve_originals_and_partial_publication=True,formal_research_complete=False))
        raise


if __name__=='__main__':sys.exit(main())
