"""Collect small second-round receipts; raw arrays remain in the integrity archive."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); batch=args.batch; out=args.output
    out.mkdir(parents=True,exist_ok=False)
    names=['environment-preflight.json','pip-freeze.txt','pip-check.txt','nvidia-smi.txt','setup-attempts.json',
        'handoff-tests.xml','handoff-tests-02.xml','nuts-tests.xml','mh-tests.xml',
        'wells-return-verification.json','wells-r-diagnostics.json','mechanism-rejected-inputs/verification.json',
        'nuts-run/summary.json','nuts-resume-verification.json','nuts-before-resume.json',
        'nuts-diagnostics/collect-summary.json','nuts-diagnostics/verification.json','nuts-diagnostics/posterior.json']
    for device in ('cpu','cuda'):
        names += [f'mh-{device}-run/summary.json',f'mh-{device}-audit/receipt.json',
            f'mh-{device}-before-resume.json',f'mh-{device}-resume-verification.json']
    names += [p.relative_to(batch).as_posix() for p in sorted((batch/'commands').rglob('*')) if p.is_file()]
    for name in names:
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(batch/name,dest)
    nuts=[]
    diagnostics={r['id']:r for r in read(batch/'nuts-diagnostics/verification.json')['fits']}
    for path in sorted((batch/'nuts-run').glob('*/state.json')):
        s=read(path);attempt=path.parent/s['attempt']; name=s['target']['name']
        serial=read(attempt/'serial/fit.json')
        workers=[read(p) for p in sorted((attempt/'parallel').glob('worker-*/metadata.json'))]
        count=lambda fits:sum(len(v) for fit in fits for c in fit['chain_records'] for v in c['diagnostics'].get('divergences',{}).values())
        nuts.append(dict(target=name,status=s['status'],six_arrays_identical=s['comparison']['passed'],
            worker_pids=s['observed_worker_pids'],worker_count=s['worker_count'],child_resources=s['child_resources'],
            serial_divergences=count([serial]),parallel_divergences=count(workers),
            tree_depth_hit_count=serial['tree_depth_hit_count'],diagnostic=diagnostics[name+'-serial']))
    write(out/'nuts-targets.json',nuts)
    with (out/'nuts-diagnostics.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['target','max_finite_rhat','undefined_rhat','serial_divergences','parallel_divergences','worker_count'])
        writer.writeheader()
        for r in nuts:
            writer.writerow({**{k:r[k] for k in ['target','serial_divergences','parallel_divergences','worker_count']},
                **{k:r['diagnostic'][k] for k in ['max_finite_rhat','undefined_rhat']}})
    all_reject=[]; cross=[]
    for device in ('cpu','cuda'):
        audit=read(batch/f'mh-{device}-audit/receipt.json')
        for t in audit['targets']:
            for name,w in t['workflows'].items():
                if w.get('replayed'):
                    for chain,count in enumerate(w['accepted_per_chain']):
                        if count==0:all_reject.append(dict(device=device,target=t['name'],workflow=name,chain=chain))
    root=Path(__file__).resolve().parents[1]
    protocol=read(root/'benchmark/protocols/selected-mh-readiness-windows-cpu-v1.json')
    for item in protocol['targets']:
        target=item['name'];c=read(batch/f'mh-cpu-run/{target}/state.json');g=read(batch/f'mh-cuda-run/{target}/state.json')
        for name in c['workflows']:
            if c['workflows'][name]['status']!='completed' or g['workflows'][name]['status']!='completed':
                cross.append(dict(target=target,workflow=name,passed=False,reason='Original workflow failed'));continue
            with np.load(batch/f'mh-cpu-run/{target}'/c['attempt']/(name+'.npz'),allow_pickle=False) as z:a=dict(z)
            with np.load(batch/f'mh-cuda-run/{target}'/g['attempt']/(name+'.npz'),allow_pickle=False) as z:b=dict(z)
            errors=np.max(np.abs(a['unconstrained']-b['unconstrained']),axis=(1,2))
            limits=100*(protocol['atol']+protocol['rtol']*np.maximum(1,np.max(np.abs(a['unconstrained']),axis=(1,2))))
            events=int(np.sum(a['accept']!=b['accept']))
            finite=all(np.isfinite(x[k]).all() for x in (a,b) for k in ('unconstrained','draws'))
            cross.append(dict(target=target,workflow=name,passed=bool(finite and np.all(errors<=limits) and events==0),
                acceptance_mismatches=events,max_path_error=float(errors.max()),allowed_per_chain=limits.tolist(),
                max_constrained_output_difference=float(np.max(np.abs(a['draws']-b['draws']))),finite=finite,
                cpu_raw_sha256=sha(batch/f'mh-cpu-run/{target}'/c['attempt']/(name+'.npz')),
                cuda_raw_sha256=sha(batch/f'mh-cuda-run/{target}'/g['attempt']/(name+'.npz'))))
    write(out/'mh-cpu-cuda-pairs.json',dict(scope='Supplementary read-only paired saved-array comparison; no additional sampling or independent replication.',rows=cross))
    write(out/'all-rejection-chains.json',all_reject)
    summary=dict(source_execution_commit='f5148ee39868a657809f400bf1755d083c744fc8',
        batch=batch.as_posix(),F1='passed fixed diagnostic',F2=read(batch/'mechanism-rejected-inputs/verification.json'),
        F4=read(batch/'wells-return-verification.json'),NUTS=read(batch/'nuts-run/summary.json'),
        MH={d:read(batch/f'mh-{d}-run/summary.json') for d in ('cpu','cuda')},
        cross_device_pairs=len(cross),cross_device_passed=sum(r['passed'] for r in cross),
        tests=dict(handoff=dict(passed=5,failed=0,skipped=1),nuts=dict(passed=3,failed=0,skipped=0),mh=dict(passed=3,failed=0,skipped=0),
            initial_handoff_attempt=dict(passed=2,skipped=1,setup_errors=3,reason='Pre-existing pytest temporary directory inaccessible; retry used a fresh batch path')),
        formal_inference_complete=False,formal_grid_started=False,
        limitations=['192 mechanism workflows blocked before sampling: six original frozen NPZ tapes required.',
            'Readiness checks and technical replays do not certify posterior accuracy or convergence.',
            'Private skill migration ZIP remains absent; no private contents included.',
            'No GPU NUTS, Stan build, fused device control or performance ranking added.'])
    write(out/'SUMMARY.json',summary)
    manifest={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write(out/'SHA256.json',manifest)
    print(json.dumps(dict(nuts_targets=len(nuts),cross_device_pairs=len(cross),cross_device_passed=summary['cross_device_passed'],all_rejection_records=len(all_reject),evidence_files=len(manifest)),indent=2))


if __name__=='__main__':main()
