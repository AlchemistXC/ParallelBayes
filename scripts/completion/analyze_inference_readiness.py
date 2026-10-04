"""Binary posterior diagnostics for all preserved readiness workflows."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from scipy.special import expit

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/completion'))
from mechanism_runner import sha,write,plain


def analyze(run,output,rscript):
    run=Path(run).resolve();out=Path(output).resolve()
    if out.exists():raise FileExistsError(out)
    if run==out or run in out.parents:raise ValueError('Analysis must not modify original run')
    out.mkdir(parents=True)
    rows=[];fits=[]
    for statefile in sorted(run.glob('*/state.json')):
        state=json.loads(statefile.read_text());folder=statefile.parent
        for name,digest in state['assets'].items():
            if sha(folder/name)!=digest:raise ValueError('Input checksum differs: '+name)
        for workflow,status in state.get('workflows',{}).items():
            identifier=state['target']+'-'+workflow
            raw=folder/state['attempt']/(workflow+'.npz');metadata=raw.with_suffix('.json')
            meta=json.loads(metadata.read_text())
            row=dict(id=identifier,model=state['target'],workflow=workflow,status=status['status'],
                raw_sha256=sha(raw),state_sha256=sha(statefile),
                max_rhat=None,min_bulk_ess=None,min_tail_ess=None,undefined_rhat=None,
                divergences=None,accepted=None,total_transitions=None)
            if workflow=='nuts-cpu':
                row['divergences']=sum(len(v) for c in meta['chain_records'] for v in c['diagnostics']['divergences'].values())
            with np.load(raw,allow_pickle=False) as z:
                if 'accept' in z:
                    row['accepted']=int(z['accept'].sum());row['total_transitions']=int(z['accept'].size)
                if status['status']=='completed':
                    x=z['draws'].copy()
                    if x.ndim!=3 or not np.isfinite(x).all():raise ValueError('Invalid completed draws')
                    names=list(meta['names']);extra=[]
                    if state['target']=='W1':
                        extra=[x[:,:,0]**2,x[:,:,1]**2,expit(x[:,:,0]),expit(x[:,:,0]+x[:,:,1]),(x[:,:,1]>0).astype(float)]
                        names+=['alpha_squared','beta_squared','p_switch_0m','p_switch_100m','beta_positive']
                    else:
                        extra=[expit(x[:,:,0]),(x[:,:,0]>0).astype(float)]
                        names+=['sigmoid_q1','q1_positive']
                    values=np.concatenate([x]+[a[:,:,None] for a in extra],axis=2).transpose(1,0,2)
                    binary=identifier+'.bin';np.asarray(values,dtype='<f8').ravel(order='F').tofile(out/binary)
                    fits.append(dict(id=identifier,input=binary,shape=list(values.shape),names=names,
                        source_raw_sha256=sha(raw),input_sha256=sha(out/binary),
                        discard='NUTS adaptation already excluded; MH no extra discard in readiness'))
            rows.append(row)
    write(out/'transport.json',dict(fits=fits,failed_workflows=[r['id'] for r in rows if r['status']!='completed']))
    proc=subprocess.run([str(rscript),str(ROOT/'scripts/completion/readiness_diagnostics.R'),str(out)],
        text=True,capture_output=True)
    (out/'R.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:raise RuntimeError('R diagnostics failed; preserve log')
    result=json.loads((out/'posterior.json').read_text())
    for fit in fits:
        if sha(out/(fit['input']+'.roundtrip'))!=fit['input_sha256']:raise ValueError('R binary roundtrip differs')
    for row in rows:
        if row['status']!='completed':continue
        stat=result['results'][row['id']]
        for field,op,column in [('max_rhat',max,'rhat'),('min_bulk_ess',min,'ess_bulk'),('min_tail_ess',min,'ess_tail')]:
            values=[s[column] for s in stat if s.get(column) is not None and np.isfinite(s[column])]
            row[field]=op(values) if values else None
        row['undefined_rhat']=sum(s.get('rhat') is None for s in stat)
    with (out/'workflows.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=dict(rows=rows,completed_fits=len(fits),failed_workflows=sum(r['status']!='completed' for r in rows),
        binary_roundtrips_verified=len(fits),R=result['R'],posterior=result['posterior'],
        script_sha256=sha(Path(__file__)),r_script_sha256=sha(ROOT/'scripts/completion/readiness_diagnostics.R'),
        source_run_protocol_sha256=json.loads((run/'summary.json').read_text())['protocol_sha256'],
        scope='Post hoc development diagnostics; counts are workflows, not independent inferential repetitions; no posterior accuracy gate')
    write(out/'summary.json',summary)
    write(out/'checksums.json',{f.name:sha(f) for f in sorted(out.iterdir()) if f.is_file()})
    return {k:v for k,v in summary.items() if k!='rows'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--rscript',required=True)
    a=p.parse_args();print(json.dumps(analyze(a.run,a.output,a.rscript),indent=2))
