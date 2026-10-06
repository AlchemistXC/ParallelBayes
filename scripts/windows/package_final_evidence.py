"""Record installed runtime/lock and summarize already completed checks.

Execute with the installed Python -I, outside the repository. No sampler.
"""
import hashlib,importlib.util,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
import parallelbayes
import torch

batch=Path(sys.argv[1]).resolve()
def write(name,value):
    (batch/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert 'site-packages' in str(Path(parallelbayes.__file__).resolve()).lower()
assert importlib.util.find_spec('jax') is None
freeze=subprocess.run([sys.executable,'-I','-m','pip','freeze','--all'],capture_output=True,text=True)
check=subprocess.run([sys.executable,'-I','-m','pip','check'],capture_output=True,text=True)
for name,result in [('pip-freeze',freeze),('pip-check',check)]:
    (batch/(name+'.stdout.log')).write_text(result.stdout,encoding='utf-8')
    (batch/(name+'.stderr.log')).write_text(result.stderr,encoding='utf-8')
assert freeze.returncode==check.returncode==0
smi=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total,compute_cap','--format=csv'],capture_output=True,text=True)
(batch/'nvidia-smi.stdout.log').write_text(smi.stdout,encoding='utf-8')
(batch/'nvidia-smi.stderr.log').write_text(smi.stderr,encoding='utf-8')
assert smi.returncode==0 and torch.cuda.is_available()
prop=torch.cuda.get_device_properties(0)
write('final-environment.json',dict(python=sys.version,executable=sys.executable,package_file=parallelbayes.__file__,
    package_version=parallelbayes.__version__,torch=torch.__version__,cuda_build=torch.version.cuda,
    gpu=prop.name,architecture=[prop.major,prop.minor],vram_bytes=prop.total_memory,
    pip_check_exit=check.returncode,freeze_exit=freeze.returncode,nvidia_smi_exit=smi.returncode,
    dependency_lock_sha256=sha(batch/'pip-freeze.stdout.log'),JAX_available=False,
    installed_noneditable=True))
tests={}
for name in ['cli','cpu','cuda']:
    suites=list(ET.parse(batch/(name+'-tests.xml')).getroot().iter('testsuite'))
    record={k:sum(int(x.attrib.get(k,0)) for x in suites) for k in ['tests','failures','errors','skipped']}
    assert record['failures']==record['errors']==record['skipped']==0
    tests[name]=record
r=json.loads((batch/'R-integration/summary.json').read_text())
rt=[x for group in r['tests'].values() for x in group]
assert all(not x['failed'] and not x['error'] and not x['skipped'] for x in rt)
assert r['ram_bytes_R']==r['ram_bytes_Python']
examples={}
for device in ['cpu','cuda']:
    data=json.loads((batch/f'R-example-{device}/summary.json').read_text())
    assert len(data['workflows'])==4
    for item in data['workflows']:
        assert item['status']=='completed' and item['audit']['passed'] and item['shape']==[64,4,2]
        assert all(v==0 for v in item['audit']['acceptance_mismatches'])
    if device=='cuda':
        assert data['failure_isolated'] and all(x['device'].startswith('cuda') and x['dtype']=='torch.float64' for x in data['workflows'])
    examples[device]=dict(completed=4,failed=0,posterior_shape=[64,4,2],same_kernel_pairs=2,acceptance_mismatches=0)
commands={}
for p in sorted((batch/'commands').glob('*/finished.json')):
    result=json.loads(p.read_text());commands[p.parent.name]=result
    if result['job_final'] is not None:assert result['job_final']['active_processes']==0
checklog=(batch/'R-check-locale-C/parallelbayes.Rcheck/00check.log').read_text()
assert 'Status: OK' in checklog
write('SUMMARY.json',dict(scope='F5 native Windows installed candidate; no formal inference/performance conclusion',
    build_source_commit='341234ed4341c4c77458a9b352016e1581e4c62e',python_version='0.2.0.dev2',R_version='0.2.0.9002',
    tests=tests,torch_warnings_each_device=18,R_explicit_tests=len(rt),R_explicit_assertions=sum(x['passed'] for x in rt),
    R_explicit_failed=0,R_explicit_skipped=0,R_check_final='OK',R_check_default_skipped=7,
    retained_failures=['attempt01 WinError206 long worktree path','wheel build global cache WinError5',
       'initial R CMD check inherited C.UTF-8 locale: 1 ERROR, 1 WARNING'],
    expected_negative_check='Default JAX environment exit 1 with actionable message, no output file',
    ram_bytes_R=r['ram_bytes_R'],ram_bytes_Python=r['ram_bytes_Python'],examples=examples,
    CUDA_failed_trajectory_isolated=True,validation_evidence_historical_version='0.2.0.dev1',
    numeric_modules_unchanged_from_52fdfd0=15,modules_source_wheel_installed_R_identical=17,
    source_kernel_changes=0,formal_repeats_added=0,private_skills_available=False,
    not_validated=['Windows JAX/Stan candidate installation','CUDA NUTS','external organization clean installation',
       'formal posterior convergence/performance','formal research grid and full two-platform result rebuild'],
    commands=commands))
print(json.dumps(dict(status='passed',python_tests=tests,R_tests=len(rt),R_assertions=sum(x['passed'] for x in rt))))
