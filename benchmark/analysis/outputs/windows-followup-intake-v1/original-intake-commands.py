from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import tarfile

ROOT = Path('/Users/haku/.codex/worktrees/research-integration/ParallelBayes')
BASE = Path(__file__).resolve().parent
DOWNLOAD = Path('/Users/haku/Workspace/ParallelBayes/downloads/windows-followup-20261007')
ARCHIVES = {
 'mechanism': ('20261006T111324Z',186511360,'ec69fd8032cae9198cd1eb7823f903eebb72bcc624a942b7da6373598b3d6ba7'),
 'runtime': ('20261006T170711Z',1083330560,'6ef0f6e299867d67b27cbd4067a062a30f3593894dc4b34c1da9086f80ae7274'),
 'runtime-supplement': ('20261006T171222Z',33792000,'a1f5752ad98b4d69c55a342a4f360d3162f6f35b7e8fc3c2f9156fe14a2a0ddb'),
 'package': ('20261006T173502Z',49428480,'9b8b805a4f4605541717f3644ff931e385156bf5f4ca009738a5a9f08d6017ce'),
 'package-supplement': ('20261006T173742Z',286720,'53bf0afa96abaf094f6846cd3a0e29a56a96eea8cac0af8b513bd8003703ce8d'),
}
SOURCES = {
 'mechanism':'1cfc83d9f979b0b58e830affc67ac22e277acc7d',
 'runtime':'b0582c33a5ea855c384acc9b15da908dea2999b6',
 'package':'0e44c2d5f2d5923f3c4ffa1c0700a18aca88b75b',
}

def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=importlib.util.spec_from_file_location('return_verifier',ROOT/'scripts/verify-windows-return.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
receipts=[]
for kind,(stamp,size,expected) in ARCHIVES.items():
    archive=DOWNLOAD/f'windows-native-{stamp}.tar'
    destination=BASE/'received'/kind
    assert not destination.exists(),destination
    assert archive.stat().st_size==size,(kind,archive.stat().st_size,size)
    result=module.verify(archive)
    assert result['archive_sha256']==expected,(kind,'GitHub asset SHA256 differs')
    destination.mkdir(parents=True)
    with tarfile.open(archive,'r') as tar:tar.extractall(destination,filter='data')
    manifest=json.loads((destination/'WINDOWS-RETURN-MANIFEST.json').read_text())
    for name,row in manifest['files'].items():
        p=destination/name
        assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],name
    result.update(kind=kind,bytes=size,extracted_files_verified=len(manifest['files']))
    receipts.append(result)
    write(BASE/f'{kind}-archive-verification.json',result)
    print(json.dumps(result),flush=True)
for kind,commit in SOURCES.items():
    destination=BASE/'sources'/kind;destination.mkdir(parents=True)
    archive=BASE/'sources'/f'{kind}.tar'
    subprocess.run(['git','archive','--format=tar','--output='+str(archive),commit],cwd=ROOT,check=True)
    with tarfile.open(archive,'r') as tar:tar.extractall(destination,filter='data')
    write(BASE/'sources'/f'{kind}.json',dict(source_commit=commit,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
write(BASE/'archive-verification.json',dict(archives=receipts,files_verified=sum(x['checked_files'] for x in receipts),
     scope='Archive and extracted-file integrity only; scientific checks follow separately',sampler_calls=0))
