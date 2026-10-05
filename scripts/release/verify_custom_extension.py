"""Read-only check of the four installed custom-target demonstration runs.

python verify_custom_extension.py ARCHIVE_ROOT --output NEW_REPORT
Needs NumPy only. Does not resample, rerun diagnostics, or use recorded absolute
installation paths, so the same saved arrays can be checked after relocation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def verify(root):
    root=Path(root)
    manifest=json.loads((root/'inputs/input-manifest.json').read_text(encoding='utf-8'))
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((root/'inputs'/name).read_bytes()).hexdigest()==digest, name
    cases=('python-torch','r-torch','python-jax','r-jax')
    arrays={}; reports={}; rows=[]; binaries=0
    for case in cases:
        report=json.loads((root/case/'summary.json').read_text(encoding='utf-8'))
        assert report['all_passed'] and report['validation']['passed'],case
        assert report['input_files']==manifest['files'],case
        assert report['inputs_manifest_sha256']==hashlib.sha256((root/'inputs/input-manifest.json').read_bytes()).hexdigest(),case
        assert report['package_version']=='0.2.0.dev2',case
        wanted=case.split('-')[-1]
        assert report['optional_provider_imported']=={'torch':wanted=='torch','jax':wanted=='jax'},case
        reports[case]=report; arrays[case]=[]
        for i in range(4):
            record=json.loads((root/case/f'workflow-{i}.json').read_text(encoding='utf-8'))
            with np.load(root/case/f'workflow-{i}.npz',allow_pickle=False) as saved:
                q=saved[record['unconstrained']['array']].copy()
                theta=saved[record['draws']['array']].copy()
                event_ref=record['accept'] if wanted=='torch' else record['diagnostics']['accept']
                accept=saved[event_ref['array']].copy()
            assert record['status']=='completed' and np.isfinite(q).all(),(case,i)
            assert q.shape==(4,128,2) and accept.shape==(4,128),(case,i)
            assert np.array_equal(q,theta),(case,i,'identity transform')
            assert sum(record['audit']['acceptance_mismatches'])==0,(case,i)
            arrays[case].append((q,accept))
            if case.startswith('r-'):
                expected=np.asarray(theta.transpose(1,0,2),dtype='<f8').tobytes(order='F')
                assert (root/case/f'workflow-{i}-R.bin').read_bytes()==expected,(case,i,'R bytes')
                binaries+=1
        for i,j in ((0,1),(2,3)):
            a,aa=arrays[case][i];b,ba=arrays[case][j]
            recorded=report['comparisons'][i//2]
            difference=float(np.max(np.abs(a-b)))
            assert np.array_equal(aa,ba) and difference<=recorded['path_limit'],(case,i,j)
            assert difference==recorded['path_error'],(case,i,j,'recorded difference')
            rows.append(dict(case=case,sequential=i,parallel=j,path_difference=difference,
                             acceptance_mismatches=0))
    language=[]; provider=[]
    for wanted in ('torch','jax'):
        for i in range(4):
            a,aa=arrays['python-'+wanted][i];b,ba=arrays['r-'+wanted][i]
            assert np.array_equal(a,b) and np.array_equal(aa,ba),(wanted,i,'language')
            language.append(dict(backend=wanted,workflow=i,bitwise_equal=True))
    for i in range(4):
        a,aa=arrays['python-torch'][i];b,ba=arrays['python-jax'][i]
        difference=float(np.max(np.abs(a-b)))
        limit=100*(1e-10+1e-10*max(1.,float(np.max(np.abs(a)))))
        assert difference<=limit and np.array_equal(aa,ba),(i,'provider')
        provider.append(dict(workflow=i,path_difference=difference,limit=limit,acceptance_mismatches=0))
    diagnostics=[]
    for case in ('r-torch','r-jax'):
        result=json.loads((root/case/'R-summary.json').read_text(encoding='utf-8'))
        assert result['all_passed'] and result['parallelbayes']=='0.2.0.9002'
        for name,workflow in result['workflows'].items():
            assert workflow['posterior_eligible'] and workflow['shape']==[128,4,2]
            for row in workflow['diagnostics']:
                diagnostics.append(dict(case=case,workflow=name,**row))
    return dict(scope='Read-only numerical example verification; no new sampling or diagnostic calls',
        workflow_runs=16,independent_formal_repetitions_added=0,
        actual_input_blocks=1,within_provider_pairs=rows,language_pairs=language,
        cross_provider_pairs=provider,R_binary_roundtrips=binaries,
        diagnostics=diagnostics,
        finite_rhat_above_1_01=sum(r['rhat'] is not None and r['rhat']>1.01 for r in diagnostics),
        undefined_rhat=sum(r['rhat'] is None for r in diagnostics),all_passed=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root');p.add_argument('--output',required=True)
    args=p.parse_args()
    out=Path(args.output)
    if out.exists(): raise FileExistsError(out)
    report=verify(args.root)
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('within_provider_pairs','language_pairs','cross_provider_pairs','diagnostics')},indent=2))
