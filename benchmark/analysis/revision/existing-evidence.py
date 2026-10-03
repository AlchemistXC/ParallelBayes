"""Post-review companion: analytic SBC, input queue and cost/diagnostic tables.
Never samples or rewrites historical results. Run from the portable project root.
"""
from pathlib import Path
import json,sys,csv,hashlib,importlib.util
import numpy as np
from scipy.stats import norm,beta
from parallelbayes.experiment import write_json,file_hash
from parallelbayes.models import fingerprint
spec=importlib.util.spec_from_file_location('original_analysis','benchmark/analysis/analyze.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
out=Path('output/cpu-revision');out.mkdir(parents=True,exist_ok=True)

def analyze_sbc():
    root=Path('execution/statistical-v4');man=json.loads((root/'manifest.json').read_text());rows=[];exact=[];inputs={}
    z=float(norm.ppf(.95));n=man['replicates']
    for i in range(n):
        reference=None
        for method in man['methods']:
            p=root/f'{i:03d}-{method.replace("/","-")}.json';r=json.loads(p.read_text());inputs[str(p)]=file_hash(p)
            assert r['status']=='completed';praw=p.with_suffix('.npz');assert file_hash(praw)==r['raw_sha256'];inputs[str(praw)]=r['raw_sha256']
            with np.load(praw) as data:q=data['draws'];y=data['y']
            assert np.array_equal(y,np.asarray(r['y']))
            m=float(y.sum()/9);s=1/3;lo=m-z*s;hi=m+z*s;truth=r['theta'];cover=lo<=truth<=hi
            identity=(truth,tuple(y))
            if reference is None:
                reference=identity;exact.append(dict(replicate=i,theta=truth,y=y.tolist(),mean=m,sd=s,lower=lo,upper=hi,covered=cover))
            else:assert identity==reference
            kept=q[1024:] if not method.startswith('nuts/') else q
            qlo,qhi=np.quantile(kept,[.05,.95]);got=bool(qlo<=truth<=qhi)
            assert got==r['covered']
            rows.append(dict(replicate=i,method=method,analytic_covered=cover,mcmc_covered=got,disagrees=cover!=got,
                lower=float(qlo),upper=float(qhi),lower_error=float(qlo-lo),upper_error=float(qhi-hi),
                mean_error=float(kept.mean()-m),sd_error=float(kept.std(ddof=1)-s),draws=len(kept)))
    summaries=[]
    for method in man['methods']:
        rr=[v for v in rows if v['method']==method]
        summaries.append(dict(method=method,n=n,covered=sum(v['mcmc_covered'] for v in rr),
           disagreement_ids=[v['replicate'] for v in rr if v['disagrees']],
           analytic_only_ids=[v['replicate'] for v in rr if v['analytic_covered'] and not v['mcmc_covered']],
           mcmc_only_ids=[v['replicate'] for v in rr if not v['analytic_covered'] and v['mcmc_covered']],
           **{k:dict(mean=float(np.mean([v[k] for v in rr])),rmse=float(np.sqrt(np.mean([v[k]**2 for v in rr]))),max_abs=float(max(abs(v[k]) for v in rr))) for k in ['lower_error','upper_error','mean_error','sd_error']}))
    k=sum(v['covered'] for v in exact)
    result=dict(analysis_status='post_review_not_original_prespecification',independent_unit='64 shared parameter-data pairs; methods are paired, not five independent calibration experiments',
       analytic_coverage=dict(covered=k,n=n,estimate=k/n,binomial_95=[float(beta.ppf(.025,k,n-k+1)),float(beta.ppf(.975,k+1,n-k))],uncovered_ids=[v['replicate'] for v in exact if not v['covered']]),
       analytic=exact,rows=rows,methods=summaries,input_sha256=inputs,analysis_sha256=file_hash(__file__))
    write_json(out/'sbc-analytic.json',result)
    print('SBC analytic coverage',k,n,'disagreements',[(v['method'],v['disagreement_ids']) for v in summaries],flush=True)

def queues_and_costs():
    queue=[];costs=[]
    for label,protocol,root in [('formal','benchmark/protocols/protocol-v1.json','benchmark/runs/cpu-formal-v1'),('reference','benchmark/protocols/reference-v1.json','benchmark/runs/cpu-reference-v1')]:
        p,prov=a.verify_inputs(protocol,root)
        for task,result,raw,state in a.records(root):
            tid=fingerprint(task)[:20];folder=Path(root)/'tasks'/tid/state['attempt'];npz=folder/'raw.npz'
            if result['status']!='completed':continue
            queue.append(dict(id=label+'-'+tid,source=label,model=task['model'],method=task['config']['kernel']+'/'+task['config']['executor'],replicate=task.get('replicate',task.get('reference_repeat',task['config']['seed'])),retained_draws=task.get('retained_draws',result['config']['draws']),discard=task.get('discard',0),path=str(npz),protocol=protocol,raw_sha256=file_hash(npz)))
            if raw:raw.close()
        write_json(out/f'{label}-input-provenance.json',prov)
    with (out/'modern-inputs.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(queue[0]));w.writeheader();w.writerows(queue)
    original=json.loads(Path('benchmark/analysis/outputs/cpu-formal/run-metrics.json').read_text())
    # Existing clocks do not separately identify every ordinary output operation.
    # Label the reconstructed middle tier an estimate rather than an observed fresh unaudited run.
    for row in original:
        cost=dict(model=row['model'],method=row['method'],retained_draws=row['retained_draws'],replicate=row['replicate'])
        api=row['t_sampler_api'];audit=row.get('t_audit',0);diag=row.get('t_diagnostics',0)
        cost.update(cached=row['t_cached'],normal_in_memory_estimate=api-audit+diag,
          research_audit=row['t_total'],independent_reference=audit,
          archive_and_model_residual=row['t_total']-api-diag,
          compile=row.get('t_compile',0),sample=row.get('t_sample',0),warmup=row.get('t_warmup',0),
          transfer=row.get('t_transfer',0),input=row.get('t_input',0),diagnostics=diag,
          normal_estimate_scope='API - measured independent reference + saved function diagnostics; excludes model setup, R conversion and output persistence not separately clocked')
        assert cost['normal_in_memory_estimate']>=0
        costs.append(cost)
    write_json(out/'cost-tiers.json',dict(rows=costs,scope='Historical accounting sensitivity, middle tier estimated; direct normal-use measurements are a separate new mechanism protocol',analysis_sha256=file_hash(__file__)))
    print('Modern diagnostic queue',len(queue),'cost rows',len(costs),flush=True)

if __name__=='__main__':analyze_sbc();queues_and_costs()
