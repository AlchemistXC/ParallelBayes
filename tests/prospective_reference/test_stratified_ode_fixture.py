"""Standalone validation of synthetic ODE stratification and reproducibility."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
from scipy.special import ndtr

HERE=Path(__file__).resolve().parent


def main():
    with tempfile.TemporaryDirectory(prefix='synthetic-strata-test-') as name:
        root=Path(name);results=[]
        for suffix in ('a','b'):
            out=root/suffix
            proc=subprocess.run([sys.executable,'-B',str(HERE/'prepare_stratified_ode_fixture.py'),str(out)],
                                capture_output=True,text=True)
            assert proc.returncode==0,(proc.stdout,proc.stderr)
            manifest=json.loads((out/'manifest.json').read_text())
            report=json.loads((out/'preflight.json').read_text())
            assert manifest['scope']=='SYNTHETIC TEST ONLY; no formal data'
            assert report['checks']['ode']['passed'] and report['formal_sampling_started'] is False
            with np.load(out/'initials.npz',allow_pickle=False) as data:
                arrays={key:data[key].copy() for key in data.files}
            q,candidates,chosen=arrays['ode'],arrays['ode_candidates'],arrays['selected_indices']
            assert q.shape==(10,8) and candidates.shape==(10,4,8)
            assert np.array_equal(q,candidates[np.arange(10),chosen])
            center=np.log(manifest['ode']['center'])
            bins=np.floor((ndtr((candidates-center)/.5)-.1)*12.5).astype(int)
            assert np.array_equal(bins,np.broadcast_to(arrays['stratum'][:,None,:],bins.shape))
            assert all(sorted(arrays['stratum'][:,j].tolist())==list(range(10)) for j in range(8))
            results.append(arrays)
        for key in results[0]:assert np.array_equal(results[0][key],results[1][key])
        again=subprocess.run([sys.executable,'-B',str(HERE/'prepare_stratified_ode_fixture.py'),str(root/'a')],
                             capture_output=True,text=True)
        assert again.returncode!=0
    print('synthetic ODE strata, same-bin alternatives, actual arrays and no-overwrite passed')


if __name__=='__main__':main()
