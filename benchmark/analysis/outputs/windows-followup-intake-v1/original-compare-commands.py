"""Read-only artifact comparisons accompanying Windows follow-up intake."""
from pathlib import Path
import csv, hashlib, json, math, tarfile, zipfile, xml.etree.ElementTree as ET

B=Path(__file__).resolve().parent
M=B/'received/mechanism/output/completion/windows-mechanism-original-attempt01'
R=B/'received/runtime/output/windows-runtime-technical-v1'
P=B/'received/package/output/windows-package-candidate-v1'
result={}
def read(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def csvrows(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
mechanism={}
for device in ('cpu','cuda'):
    for table in ('workflows','probes'):
        old=M/('analysis-'+device)/(table+'.csv')
        new=B/'reconstruction'/('mechanism-'+device+'-v2')/(table+'.csv')
        a,b=csvrows(old),csvrows(new)
        assert a==b
        mechanism[device+'-'+table]=dict(rows=len(a),all_fields_equal=True,
            bytes_equal=old.read_bytes()==new.read_bytes(),old_sha256=sha(old.read_bytes()),new_sha256=sha(new.read_bytes()))
    rows=csvrows(B/'reconstruction'/('mechanism-'+device+'-v2/workflows.csv'))
    for kernel in ('mala','rwm'):
        ratios=[float(r['paired_cached_ratio']) for r in rows if r['kernel']==kernel and r['label']!='sequential']
        mechanism[device+'-'+kernel]=dict(pairs=len(ratios),minimum=min(ratios),maximum=max(ratios),over_one=sum(x>1 for x in ratios))
    mechanism[device+'-zero_acceptance_workflows']=sum(float(r['acceptance_fraction'])==0 for r in rows)
result['mechanism']=mechanism

main=read(B/'reconstruction/runtime/main.json');diags=read(B/'reconstruction/runtime/diagnostics.json')
result['runtime']=dict(function_binary_exact=sum(x['binary_rebuilt_exact'] for x in main),functions=len(main),
    function_max_difference=max(x['receiver_function_comparison']['maximum_absolute_difference'] for x in main),
    means_max_difference=max(x['receiver_estimate_comparison']['maximum_absolute_difference'] for x in main),
    diagnostics_max_difference=max(x['receiver_diagnostics_comparison']['maximum_absolute_difference'] for x in main),
    diagnostic_rows=len(diags),rhat_over_1_01=sum(x['rhat'] is not None and x['rhat']>1.01 for x in diags),
    rhat_null=sum(x['rhat'] is None for x in diags),tail_ess_null=sum(x['ess_tail'] is None for x in diags))

def compare(a,b,stats):
    if isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a:compare(a[k],b[k],stats)
    elif isinstance(a,list):
        assert len(a)==len(b)
        for x,y in zip(a,b):compare(x,y,stats)
    elif isinstance(a,(float,int)) and not isinstance(a,bool):
        assert isinstance(b,(float,int)) and math.isfinite(a) and math.isfinite(b)
        stats['max_abs_difference']=max(stats['max_abs_difference'],abs(a-b))
        stats['numerical_values']+=1
        assert abs(a-b)<=1e-10+1e-10*abs(a)
    else:assert a==b
for device in ('cpu','cuda'):
    stats=dict(max_abs_difference=0,numerical_values=0,atol=1e-10,rtol=1e-10)
    compare(read(P/('R-example-'+device)/'readonly-reconstruction.json'),
            read(B/'reconstruction'/('package-'+device+'.json')),stats)
    result['package_R_'+device]=stats

tests={}
for key,p in [('package-'+x,P/(x+'-tests.xml')) for x in ('cli','cpu','cuda')]+[
    ('runtime-behavior',B/'received/runtime/output/windows-runtime-engineering-v1/complete-tests.xml'),
    ('runtime-kernel-controls',B/'sources/runtime/benchmark/analysis/outputs/windows-runtime-technical-v1/kernel-controls.xml')]:
    suites=list(ET.parse(p).getroot().iter('testsuite'))
    tests[key]={field:sum(int(x.get(field,0)) for x in suites) for field in ('tests','failures','errors','skipped')}
    assert tests[key]['failures']==tests[key]['errors']==tests[key]['skipped']==0
result['tests']=tests

modules=read(P/'version-bridge.json')['modules'];copies={}
with zipfile.ZipFile(P/'dist/parallelbayes-0.2.0.dev2-py3-none-any.whl') as z:
    copies['wheel']={k:sha(z.read(k)) for k in modules}
for label,file,prefix in [('sdist','parallelbayes-0.2.0.dev2.tar.gz','parallelbayes-0.2.0.dev2/r-package/inst/python/'),
                          ('R','parallelbayes_0.2.0.9002.tar.gz','parallelbayes/inst/python/')]:
    with tarfile.open(P/'dist'/file) as t:
        copies[label]={k:sha(t.extractfile(prefix+k).read()) for k in modules}
copies['source']={k:sha((B/'sources/package/r-package/inst/python'/k).read_bytes()) for k in modules}
for label,values in copies.items():assert values==modules,label
result['package_modules']=dict(modules=len(modules),source_wheel_sdist_R_identical=True,
    installed_modules_directly_available=False,installed_identity_evidence='Archived version-bridge and noneditable installation provenance',
    versions=read(P/'version-bridge.json'))
result['limitations']=['Original test results are inspected artifacts, not tests rerun on Windows by the receiver.',
    'All performance numbers retain original Windows clocks; receiver wall time is not sampler timing.',
    'R diagnostic tolerance is explicit companion comparison, not bitwise identity or evidence of convergence.',
    'These technical records add no formal independent inference repetitions.']
out=B/'reconstruction/comparison-summary.json'
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='package_modules'},indent=2))
