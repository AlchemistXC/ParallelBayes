"""Rebuild the fixed Windows-v1 manuscript section from its retained evidence.

This is a historical results renderer, not a new experiment or a general report
for arbitrary protocols. Static environment/validation/SBC/intake prose belongs
to this fixed protocol; new evidence needs a new reviewed section identity.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import numpy as np


INPUTS = (
    'benchmark/analysis/outputs/windows-native-v1/delivery-review.json',
    'benchmark/analysis/outputs/windows-native-v1/summary.json',
    'benchmark/analysis/outputs/windows-native-v1/run-metrics.json',
    'execution/windows-native/windows-native-v1/modern-diagnostics.json',
    'execution/windows-native/windows-native-v1/protocol.json',
)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def render(root, evidence):
    root, evidence = Path(root), Path(evidence)
    paths = [evidence/p for p in INPUTS]
    report, summary, rows, diagnostics, protocol = [json.loads(p.read_text(encoding='utf-8-sig')) for p in paths]
    unsigned=dict(protocol);digest=unsigned.pop('protocol_sha256')
    identity=hashlib.sha256(json.dumps(unsigned,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if digest != identity or digest != '1d233dd09956c4575fc5775082310e5edca65407db5fcef40bc2ce329e6f5898':
        raise ValueError('This renderer only covers the frozen Windows-v1 protocol')
    if summary['protocol_sha256'] != digest or report['protocol_sha256'] != digest:
        raise ValueError('Summary protocol identity differs')
    for relative in INPUTS[1:]:
        if sha(evidence/relative)!=report['input_sha256'][relative]:
            raise ValueError('Received evidence hash differs: '+relative)
    if len(rows)!=512 or len(diagnostics)!=512 or len(protocol['tasks'])!=512 or any(r['status']!='completed' for r in rows):
        raise ValueError('Historical task frame/status differs')
    index={(r['model'],r['device'],r['kernel'],r['executor'],r['draws'],r['replicate']):r for r in rows}
    if len(index)!=512: raise ValueError('Duplicate rows')
    paired=defaultdict(list)
    for row in rows:
        if row['executor']=='sequential':continue
        seq=index[(row['model'],row['device'],row['kernel'],'sequential',row['draws'],row['replicate'])]
        key=(row['device'],row['kernel'],row['model'],row['draws'])
        paired[key].append(seq['warmed_seconds']/row['warmed_seconds'])
    if len(paired)!=64 or any(len(v)!=4 for v in paired.values()):raise ValueError('Paired denominators differ')
    tokens={};checks=[]
    for device in ('cpu','cuda'):
        for kernel in ('mala','rwm'):
            values=[float(np.median(v)) for k,v in paired.items() if k[:2]==(device,kernel)]
            expected=next(s['warmed_speed_ratio'] for s in report['speed'] if s['device']==device and s['kernel']==kernel)
            if min(values)!=expected['group_median_min'] or max(values)!=expected['group_median_max']:
                raise ValueError('Speed range differs from the underlying paired rows')
            tokens[(device+'_'+kernel).upper()]=f'{min(values):.3f}--{max(values):.3f}'
            checks.append(dict(device=device,kernel=kernel,groups=len(values),tapes_per_group=4,range=[min(values),max(values)]))
    flat=[s for d in diagnostics.values() for s in d['summary']]
    high=sum(any(s['rhat'] is not None and s['rhat']>1.01 for s in d['summary']) for d in diagnostics.values())
    constant=sum(any(s['state']=='undefined_no_variation' for s in d['summary']) for d in diagnostics.values())
    d=report['diagnostics'];res=report['resources'];num=report['numerical']
    if high!=d['fits_with_finite_rhat_over_1_01'] or constant!=d['constant_fits']:
        raise ValueError('Diagnostic fit denominators differ')
    if sum(r['acceptance_mismatches'] for r in rows)!=0:raise ValueError('Acceptance mismatch present')
    for field,derived in (
        ('max_finite_rhat',max(s['rhat'] for s in flat if s['rhat'] is not None)),
        ('min_finite_bulk_ess',min(s['ess_bulk'] for s in flat if s['ess_bulk'] is not None)),
        ('min_finite_tail_ess',min(s['ess_tail'] for s in flat if s['ess_tail'] is not None)),
        ('elapsed_seconds',sum(x['elapsed'] for x in diagnostics.values())),
    ):
        if not np.isclose(derived,d[field],rtol=1e-14,atol=1e-14):raise ValueError('Diagnostic reduction differs: '+field)
    if sum(r['all_attempt_seconds'] for r in rows)!=res['all_attempt_seconds']:
        raise ValueError('All-attempt cost differs')
    if max(r['max_path_error'] for r in rows)!=num['oracle_max_path_error']:
        raise ValueError('Saved audit maximum differs')
    def scientific(value):
        mantissa,exponent=f'{value:.3e}'.split('e')
        return mantissa+r'\times10^{'+str(int(exponent))+'}'
    cuda_rwm=next(s['warmed_speed_ratio'] for s in report['speed'] if s['device']=='cuda' and s['kernel']=='rwm')
    tokens.update(ORACLE_ERROR=scientific(num['oracle_max_path_error']),
        DEVICE_PATH_ERROR=scientific(num['cross_device_max_path_error']),
        DEVICE_OUTPUT_ERROR=scientific(num['cross_device_max_constrained_error']),
        TASKS=str(len(rows)),RHAT_FITS=str(high),CONSTANT_FITS=str(constant),
        RHAT_MAX=f'{d["max_finite_rhat"]:.3f}',BULK_MIN=f'{d["min_finite_bulk_ess"]:.3f}',
        TAIL_MIN=f'{d["min_finite_tail_ess"]:.3f}',ATTEMPT_SECONDS=f'{res["all_attempt_seconds"]:.3f}',
        DIAGNOSTIC_SECONDS=f'{d["elapsed_seconds"]:.3f}',CUDA_ALLOCATED=f'{res["cuda_peak_allocated_bytes"]:,}',
        CUDA_RESERVED=f'{res["cuda_peak_reserved_bytes"]:,}',SCALAR_READS=f'{res["host_scalar_reads"]:,}',
        SCALAR_SECONDS=f'{res["host_scalar_wait_seconds"]:.3f}',
        CUDA_PICARD_FASTER=str(cuda_rwm['group_medians_over_one']),CUDA_PICARD_CI=str(cuda_rwm['groups_ci95_low_over_one']),
        NO_MOVE=str(report['no_movement']['zero_acceptance_models_kernels']['A1/rwm']))
    template=root/'manuscript/software/windows-native.template.tex'
    tex=template.read_text(encoding='utf-8')
    used=set(re.findall(r'@([A-Z_]+)@',tex))
    if used!=set(tokens):raise ValueError('Template field set differs')
    for key,value in tokens.items():tex=tex.replace('@'+key+'@',value)
    return tex,dict(scope='Fixed-v1 section assembly; selected reductions independently recalculated from saved rows/diagnostics; no path replay or new sampling',
        inputs={p:sha(evidence/p) for p in INPUTS},template_sha256=sha(template),
        protocol_sha256=digest,paired_speed_checks=checks,diagnostic_fits=512,
        numerical_values_changed=False,static_prose='Fixed historical environment, algorithm, SBC and intake prose; not generated from new evidence')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists() or args.output.with_suffix('.provenance.json').exists():raise FileExistsError(args.output)
    text,receipt=render(args.root,args.evidence)
    args.output.write_text(text,encoding='utf-8')
    args.output.with_suffix('.provenance.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
