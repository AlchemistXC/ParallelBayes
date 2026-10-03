"""Predeclared data-dependent SBC diagnostic from the preserved posterior draws.

The fitting protocol remains statistical-v4. This companion never samples or
changes a fitted trajectory, and reports no uniformity-test pass/fail claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from parallelbayes.models import fingerprint
from parallelbayes.experiment import file_hash,write_json


def analyze(folder, protocol, output):
    frozen=json.loads(Path(protocol).read_text())
    digest=frozen.pop('protocol_sha256')
    if fingerprint(frozen)!=digest or file_hash(__file__)!=frozen['analysis_sha256']:
        raise ValueError('SBC function analysis differs from frozen companion protocol')
    folder=Path(folder)
    manifest=json.loads((folder/'manifest.json').read_text())
    if any(manifest[k]!=frozen[k] for k in ('replicates','seed','sampling_seed','source_sha256')):
        raise ValueError('Posterior fit identity differs from SBC companion protocol')
    methods=manifest['methods'];rows=[];inputs={}
    for replicate in range(frozen['replicates']):
        for method in methods:
            path=folder/f'{replicate:03d}-{method.replace("/","-")}.json'
            r=json.loads(path.read_text());inputs[path.name]=file_hash(path)
            row=dict(replicate=replicate,method=method,status=r['status'])
            if r['status']=='completed':
                raw_path=path.with_suffix('.npz')
                if file_hash(raw_path)!=r['raw_sha256']:raise ValueError('SBC raw checksum mismatch')
                inputs[raw_path.name]=r['raw_sha256']
                with np.load(raw_path) as data:
                    q=data['draws'];y=data['y']
                if not np.array_equal(y,np.asarray(r['y'])):raise ValueError('SBC data mismatch')
                kept=q[1024:] if not method.startswith('nuts/') else q
                posterior=kept[31::32]
                truth=float(r['theta'])
                loglike=lambda theta:-.5*np.sum((y[None,:]-np.atleast_1d(theta)[:,None])**2,axis=1)
                scores=loglike(posterior);score=float(loglike(truth)[0])
                less=int(np.sum(scores<score));ties=int(np.sum(scores==score))
                rng=np.random.Generator(np.random.Philox(np.random.SeedSequence([frozen['tie_seed'],replicate,methods.index(method)])))
                rank=less+int(rng.integers(0,ties+1))
                exact_mean=-.5*(np.sum((y-r['exact_mean'])**2)+len(y)*r['exact_sd']**2)
                row.update(rank=rank,rank_draws=len(scores),ties=ties,
                    loglikelihood_at_truth=score,posterior_loglikelihood_mean=float(loglike(kept).mean()),
                    exact_loglikelihood_mean=float(exact_mean),
                    posterior_loglikelihood_mean_error=float(loglike(kept).mean()-exact_mean),
                    rank_draw_lag1_correlation=float(np.corrcoef(scores[:-1],scores[1:])[0,1]))
            rows.append(row)
    summary=[]
    for method in methods:
        selected=[r for r in rows if r['method']==method]
        valid=[r for r in selected if r['status']=='completed']
        summary.append(dict(method=method,attempted=len(selected),failed=len(selected)-len(valid),
            rank_histogram=np.histogram([r['rank'] for r in valid],bins=np.arange(0,66,13))[0].tolist(),
            mean_rank=float(np.mean([r['rank'] for r in valid])) if valid else None,
            ties=sum(r['ties'] for r in valid),
            mean_squared_error=float(np.mean([r['posterior_loglikelihood_mean_error']**2 for r in valid])) if valid else None))
    write_json(output,dict(protocol_sha256=digest,input_sha256=inputs,rows=rows,methods=summary,
        scope='Prespecified likelihood-dependent SBC ranks, 64 correlated rank draws per fit; exploratory diagnostic, no general calibration certificate.'))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runs',required=True)
    p.add_argument('--protocol',default='benchmark/protocols/sbc-functions-v1.json')
    p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(analyze(a.runs,a.protocol,a.output),indent=2))
