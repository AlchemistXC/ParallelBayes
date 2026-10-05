"""Read-only source and installed-artifact bridge for the unified candidate.

This verifies identity, not sampling performance or native Windows installation.
Original frozen experiments still require their own source/environment identities.
"""
import argparse,hashlib,json,subprocess,tarfile,zipfile
from pathlib import Path
PACKAGE='01609ed52e9737f00661ce5653a35a80ea9f8796'
RESEARCH='826d6a83f2cd351457a6ff4dfa1d39de675d87e3'
sha=lambda b:hashlib.sha256(b).hexdigest()

def verify(root,artifacts,installed,r_info):
    def git(*args):return subprocess.check_output(['git',*args],cwd=root)
    head=git('rev-parse','HEAD').decode().strip()
    checks={}
    for label,ref,prefixes in [
        ('package',PACKAGE,['r-package','pyproject.toml','examples/installed-torch.R','tests/release']),
        ('research',RESEARCH,['scripts/completion','tests/external','benchmark/protocols']),
    ]:
        names=git('ls-tree','-r','--name-only',ref,'--',*prefixes).decode().splitlines()
        current=git('ls-tree','-r','--name-only','HEAD','--',*prefixes).decode().splitlines()
        if current!=names:raise ValueError(label+' source inventory differs')
        hashes={}
        for name in names:
            actual=(root/name).read_bytes()
            if actual!=git('show',ref+':'+name):raise ValueError('Source differs: '+name)
            hashes[name]=sha(actual)
        checks[label]=dict(source_commit=ref,files=len(hashes),sha256=hashes)
    expected={}
    for line in (root/'benchmark/analysis/outputs/package-candidate-v1/ARTIFACT-SHA256SUMS').read_text().splitlines():
        h,name=line.split(maxsplit=1)
        if name.endswith(('.whl','.tar.gz')):expected[name]=h
    actual={}
    for name,h in expected.items():
        path=artifacts/name
        if sha(path.read_bytes())!=h:raise ValueError('Original installation artifact differs: '+name)
        actual[name]=dict(sha256=h,bytes=path.stat().st_size)
    wheel=next(artifacts.glob('*.whl'));r_archive=artifacts/'parallelbayes_0.2.0.9002.tar.gz'
    prefix='r-package/inst/python/'
    names=[n for n in checks['package']['sha256'] if n.startswith(prefix) and n.endswith('.py')]
    modules={};r_members=0
    with zipfile.ZipFile(wheel) as whl,tarfile.open(r_archive) as rt:
        for name in names:
            relative=name.removeprefix(prefix);value=(root/name).read_bytes()
            if whl.read(relative)!=value or rt.extractfile('parallelbayes/inst/python/'+relative).read()!=value:
                raise ValueError('Python payload differs from unified source: '+relative)
            modules[relative]=sha(value)
        for member in rt.getmembers():
            if not member.isfile():continue
            relative=member.name.removeprefix('parallelbayes/')
            if relative=='DESCRIPTION':continue  # Original candidate receipt verifies standard build-only metadata.
            path=root/'r-package'/relative
            if not path.is_file() or rt.extractfile(member).read()!=path.read_bytes():raise ValueError('R source payload differs: '+relative)
            r_members+=1
    origins=[]
    for name in installed:
        info=json.loads(name.read_text());base=Path(info['distribution_root'])
        if info['version']!='0.2.0.dev2' or info['isolated_mode']!=1 or info['direct_url'].get('dir_info',{}).get('editable',False):
            raise ValueError('Installed version/origin mode differs')
        for relative,h in modules.items():
            if sha((base/relative).read_bytes())!=h:raise ValueError('Installed wheel module differs: '+relative)
        origins.append(dict(receipt=name.name,receipt_sha256=sha(name.read_bytes()),module=info['module'],version=info['version'],modules=len(modules),providers=info['providers_installed']))
    ri=json.loads(r_info.read_text());rbase=Path(ri['embedded_python']).parent.parent
    if ri['python_version']!='0.2.0.dev2' or ri['package_version']!='0.2.0.9002' or not ri['validation']['passed']:
        raise ValueError('Installed R package or model validation differs')
    for relative,h in modules.items():
        if sha((rbase/relative).read_bytes())!=h:raise ValueError('Installed R Python payload differs: '+relative)
    return dict(integration_source_commit=head,verifier_sha256=sha(Path(__file__).read_bytes()),source_trees=checks,
        artifacts=actual,python_payloads=modules,R_source_members_matched=r_members,installed_python=origins,
        installed_R_receipt_sha256=sha(r_info.read_bytes()),installed_R_embedded_modules=len(modules),
        original_freeze_files_changed=False,new_clean_installation_claimed=False,
        numerical_kernels_changed=False,performance_equivalence_claimed=False,native_windows_installation_verified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--artifacts',type=Path,required=True)
    p.add_argument('--installed',type=Path,nargs='+',required=True);p.add_argument('--r-info',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Choose a new output file')
    result=verify(a.root,a.artifacts,a.installed,a.r_info)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_trees','artifacts','python_payloads','installed_python')},indent=2))
