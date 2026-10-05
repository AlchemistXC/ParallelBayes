"""Locate differences between verified original and rejected regenerated tapes."""
import argparse
import json
from pathlib import Path
import numpy as np
from mechanism_runner import read_plan, sha, actual_hash


def compare(plan_path, original, rejected, output):
    if output.exists():raise FileExistsError('Preserve previous input comparison')
    p=read_plan(plan_path); rows=[]
    for key,expected in p['inputs'].items():
        name=key+'.npz';a=original/name;b=rejected/name
        assert sha(a)==expected['file_sha256']
        with np.load(a,allow_pickle=False) as x,np.load(b,allow_pickle=False) as y:
            assert actual_hash(dict(x))==expected['actual_sha256']
            assert set(x.files)==set(y.files)=={'noise','log_uniform','directions'}
            components={}
            for k in x.files:
                assert x[k].shape==y[k].shape and x[k].dtype==y[k].dtype==np.float64
                assert np.isfinite(x[k]).all() and np.isfinite(y[k]).all()
                components[k]=dict(shape=list(x[k].shape),equal=np.array_equal(x[k],y[k]),
                    unequal=int(np.sum(x[k]!=y[k])),max_absolute_difference=float(np.max(np.abs(x[k]-y[k]))))
        rows.append(dict(name=name,original_file_sha256=sha(a),rejected_file_sha256=sha(b),components=components))
    result=dict(scope='Actual frozen Mac arrays versus rejected Windows reconstructions; component localization only, not a libm/compiler causal proof.',
        protocol_sha256=p['protocol_sha256'],source_script_sha256=sha(Path(__file__)),rows=rows)
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(original_files_verified=len(rows),differing_elements=sum(v['unequal'] for r in rows for v in r['components'].values())),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','original','rejected','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();compare(a.plan,a.original,a.rejected,a.output)
