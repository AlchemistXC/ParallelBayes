"""Portable checks of persisted localization evidence; never invokes a sampler."""
import itertools
import json
from pathlib import Path
import numpy as np
from nuts_events import sha


def read_events(path):
    path=Path(path)
    if not path.exists():return [],False
    lines=path.read_text().splitlines();rows=[];truncated=False
    for index,line in enumerate(lines):
        try:rows.append(json.loads(line))
        except json.JSONDecodeError:
            if index!=len(lines)-1:raise ValueError('Malformed nonterminal event record')
            truncated=True
    return rows,truncated


def phase_path(directory,phase):
    values=[];end=0
    events=directory/'events.ndjson'
    if not events.exists():return None
    rows,_=read_events(events)
    if [r['sequence'] for r in rows]!=list(range(len(rows))):raise ValueError('Chain stage sequence is broken')
    for row in rows:
        if row['event']!='chunk_persisted' or row['phase']!=phase:continue
        if row['start']!=end or row['stop']<=end:raise ValueError('Chunk prefix is not contiguous')
        for key in ('state','step_size'):
            metadata=row[key];path=directory/metadata['name']
            if path.parent!=directory or sha(path)!=metadata['sha256']:raise ValueError('Chunk integrity differs')
            with path.open('rb') as f:array=np.load(f,allow_pickle=False)
            if list(array.shape)!=metadata['shape'] or str(array.dtype)!=metadata['dtype'] or not np.isfinite(array).all():
                raise ValueError('Invalid recorded array')
            if key=='state':values.append(array)
        if len(values[-1])!=row['stop']-row['start']:raise ValueError('Chunk dimensions differ')
        end=row['stop']
    return np.concatenate(values) if values else None


def paired_prefixes(left,right):
    result=[]
    for chain in range(4):
        a=left/f'chain-{chain}';b=right/f'chain-{chain}'
        for phase in ('warmup','sample'):
            x=phase_path(a,phase);y=phase_path(b,phase)
            n=0 if x is None or y is None else min(len(x),len(y))
            if n and x.shape[1:]!=y.shape[1:]:raise ValueError('Compared coordinates differ')
            result.append(dict(chain=chain,phase=phase,common_steps=n,
                exact_match=bool(np.array_equal(x[:n],y[:n])) if n else None,
                max_absolute_difference=float(np.max(np.abs(x[:n]-y[:n]))) if n else None))
        for filename in ('initial-rng.json','rng-after-sampling.json'):
            p=a/filename;q=b/filename
            result.append(dict(chain=chain,phase=filename,both_available=p.exists() and q.exists(),
                exact_match=json.loads(p.read_text())==json.loads(q.read_text()) if p.exists() and q.exists() else None))
    return result


def qualification_check(root,records):
    issues=[]
    if len(records)!=4:return dict(passed=False,issues=['Exactly four qualification conditions required'])
    conditions={(r['request']['workers'],r['request']['diagnostics_enabled']) for r in records}
    if conditions!={(1,True),(1,False),(4,True),(4,False)}:issues.append('Incomplete 2x2 conditions')
    bindings={r['request']['binding_sha256'] for r in records}
    if len(bindings)!=1:issues.append('Qualification sources/environments differ')
    for record in records:
        request=record['request'];directory=root/'calls'/record['id']
        if not record['outcome'] or record['outcome']['status']!='completed':
            issues.append(record['id']+': call incomplete');continue
        if request['config']['warmup']!=64 or request['config']['draws']!=64:issues.append('Wrong fixture budget')
        if len(request['case']['initial'])!=4 or request['case']['target_spec']['dimension']!=2:issues.append('Wrong fixture dimensions')
        for chain in range(4):
            path=directory/f'chain-{chain}'
            events,truncated=read_events(path/'events.ndjson')
            if truncated:issues.append('Truncated qualification event file')
            names=[r['event'] for r in events]
            required=['actual_rng_restored','warmup_completed','sample_completed','mcmc_run_returned',
                'samples_persisted_before_diagnostics','baseline_call_returned','serialization_ready','chain_function_exit']
            required.insert(5,'legacy_diagnostics_enter' if request['diagnostics_enabled'] else 'legacy_diagnostics_bypassed')
            if request['diagnostics_enabled']:required.insert(6,'legacy_diagnostics_exit')
            positions=[names.index(n) if n in names else -1 for n in required]
            if min(positions)<0 or positions!=sorted(positions):issues.append(record['id']+f': chain {chain} stage sequence')
            for phase in ('warmup','sample'):
                x=phase_path(path,phase)
                if x is None or x.shape!=(64,2):issues.append(record['id']+f': chain {chain} incomplete {phase}')
            saved=np.load(path/'samples-before-diagnostics.npy',allow_pickle=False)
            if not np.array_equal(saved,phase_path(path,'sample')):issues.append('Hook/persisted sample mismatch')
            initial=json.loads((path/'initial-rng.json').read_text())
            expected=json.loads((root/'rng'/f"{request['model']}.json").read_text())['states'][chain]
            if initial!=expected:issues.append('Actual initial RNG differs')
        final=record['outcome'].get('final_job')
        if not final or final['active_processes']!=0:issues.append('No final zero-process observation')
        if final and final['hard_job_commit_limit_bytes']!=12*1024**3:issues.append('Job commitment limit differs')
    pairs=[]
    for left,right in itertools.combinations(records,2):
        comparison=paired_prefixes(root/'calls'/left['id'],root/'calls'/right['id'])
        pairs.append(dict(left=left['id'],right=right['id'],comparisons=comparison))
        if any(r.get('exact_match') is not True for r in comparison):issues.append('Cross-condition state/RNG mismatch or missing data')
    return dict(passed=not issues,issues=issues,pairs=pairs,scope='Native instrumentation qualification; no convergence or performance claim')


def failure_stage(directory):
    result=[]
    for chain in range(4):
        path=directory/f'chain-{chain}'/'events.ndjson'
        rows,truncated=read_events(path)
        names=[x['event'] for x in rows]
        if 'legacy_diagnostics_enter' in names and 'legacy_diagnostics_exit' not in names:stage='diagnostics_entered_not_returned'
        elif 'serialization_ready' in names:stage='worker_serialization_ready'
        elif 'samples_persisted_before_diagnostics' in names:stage='samples_persisted'
        elif 'sample_completed' in names:stage='sampling_hook_completed'
        elif 'warmup_completed' in names:stage='sampling_or_later'
        else:stage='before_warmup_completed'
        result.append(dict(chain=chain,last_event=names[-1] if names else None,observed_stage=stage,truncated_last_event=truncated,
            scope='Last durable marker bounds the failure interval; does not prove root cause'))
    return result
