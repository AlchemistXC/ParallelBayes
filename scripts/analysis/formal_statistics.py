"""Verified complete task frames -> model-level paired errors and costs.

Only formal_inference can produce formal intervals. Technical validation is
descriptive. Missing evidence blocks the affected model/phase, not its rows.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'scripts/analysis')]
from formal_archive import EvidenceIndex
from formal_analyze import FrozenFrame,output_inventory,analyzer_sources
from formal_runtime import atomic_json,file_hash,fingerprint
from formal_freeze import relative_file
from formal_uncertainty import create_plan,save_plan,analyze_function
from formal_cost_policy import analyze_task_costs,analyze_error_costs
from cache_probe_analysis import create_cache_plan,analyze_cache_probes


def save_report(path,report):
    """Save nested bootstrap vectors separately, with exact byte identities."""
    path=Path(path);arrays={}
    def visit(value,trail):
        if isinstance(value,dict):
            out={}
            for key,item in value.items():
                if key=='bootstrap_statistics':
                    prefix='/'.join(trail) or 'root'
                    for label,array in item.items():arrays[prefix+'/'+label]=array
                    out['bootstrap_array_keys']=[prefix+'/'+label for label in item]
                else:out[key]=visit(item,trail+[key])
            return out
        if isinstance(value,list):return [visit(x,trail+[str(i)]) for i,x in enumerate(value)]
        return value
    saved=visit(report,[])
    if arrays:
        payload=path.with_suffix('.bootstrap.npz');np.savez_compressed(payload,**arrays)
        saved['bootstrap_file']=payload.name;saved['bootstrap_file_sha256']=file_hash(payload)
    atomic_json(path,saved)


def reference_contract(index,frame):
    """Use the hash-bound archived references and explicit W1 snapshot."""
    import analyze_budget_pilot
    names=['benchmark/protocols/windows-native-v1.json',
        'benchmark/analysis/outputs/completion-f3/reference-reuse.json',
        'benchmark/analysis/outputs/wells-quadrature-v1/R12-n96.json',
        'benchmark/analysis/outputs/wells-quadrature-v1/result.json',
        'benchmark/analysis/outputs/inference-budget-pilot-v1/analysis/reference-contract.json']
    for name in names:
        if index.record('source/'+name)['sha256']!=frame.protocol['source_files'][name]:raise ValueError('Reference source binding differs')
        index.path('source/'+name)
    for name,digest in frame.protocol['source_files'].items():
        if name.startswith(('scripts/completion/','r-package/inst/python/','examples/','models/')) and file_hash(ROOT/name)!=digest:
            raise ValueError('Reference reconstruction dependency changed: '+name)
    old=analyze_budget_pilot.ROOT
    try:
        analyze_budget_pilot.ROOT=index.root/'source'
        _,references=analyze_budget_pilot.references(frame.protocol,index.root/'external')
    finally:analyze_budget_pilot.ROOT=old
    frozen=index.json('source/benchmark/analysis/outputs/inference-budget-pilot-v1/analysis/reference-contract.json')
    if references!={name:frozen[name] for name in references}:raise ValueError('Rebuilt reference contract differs from frozen development')
    return references


def checked_rows(analysis,frame,index):
    """Read receiver receipts/scalars; do not recompute arrays or diagnostics."""
    analysis=Path(analysis).resolve();binding=json.loads((analysis/'identity.json').read_text())
    if binding['index']!=index.receipt or binding['frame']!=frame.receipt() or binding['scientific_source_files']!=frame.protocol['source_files']:
        raise ValueError('Analysis belongs to another delivery/frame/source')
    # Pin the exact analysis implementation. A changed reader needs a new
    # analysis identity; historical output is not silently reused as current.
    if binding['analyzer_sources']!=analyzer_sources():raise ValueError('Receiver source changed or binding omitted files')
    db=sqlite3.connect((analysis/'analysis.sqlite3').as_uri()+'?mode=ro',uri=True)
    expected=set()
    try:
        for _,phase,_,slot in frame.slots():
            task=slot['task'];expected.add(task['id'])
            saved=db.execute('SELECT task,disposition,receipt,sha256 FROM results WHERE id=?',(task['id'],)).fetchone()
            if saved is None:yield dict(task=task,phase=phase,disposition='pending_analysis',outcome=None);continue
            path=relative_file(analysis,saved[2])
            if json.loads(saved[0])!=task or file_hash(path)!=saved[3]:raise ValueError('Analysis row/receipt identity differs')
            receipt=json.loads(path.read_text());folder=path.parent
            if receipt['task']!=task or receipt['disposition']!=saved[1] or receipt['files']!=output_inventory(folder):
                raise ValueError('Analysis output inventory differs')
            for name,digest in receipt['inputs']['manifest'].items():
                if index.record(name)['sha256']!=digest:raise ValueError('Scalar receipt has another input identity')
            row=json.loads((folder/'FRAME.json').read_text())
            if row['task']!=task or row['phase']!=phase:raise ValueError('Projected scientific task differs')
            if saved[1]=='analyzed':
                science=json.loads(relative_file(folder,row['scientific_result']).read_text())
                for key in ('task','outcome','means','names','function_status','diagnostics'):
                    if row[key]!=science[key]:raise ValueError('Projected scalar differs from scientific reader: '+key)
                if (row['costs']!=science['history']['costs'] or row.get('cache')!=science.get('cache') or
                        row.get('nuts')!=science.get('nuts')):
                    raise ValueError('Projected cost/measurement differs')
                if row['outcome']!=science['history']['summary']['outcome']:raise ValueError('Outcome and attempt history differ')
            yield dict(row,disposition=saved[1])
        if set(x[0] for x in db.execute('SELECT id FROM results'))-expected:raise ValueError('Unexpected analysis task records')
    finally:db.close()


def comparisons(workflows,budgets):
    """Explicit same-kernel pairs plus end-to-end MH versus CPU NUTS."""
    method_pairs=[]
    for device in ('cpu','cuda'):
        for kernel,executor in [('rwm','online_picard'),('mala','quasi_deer')]:
            pair=(device+'-'+kernel+'-sequential',device+'-'+kernel+'-'+executor)
            if all(w in workflows for w in pair):method_pairs.append((*pair,'same_kernel_execution'))
    if 'cpu-nuts-spawn_chains' in workflows:
        method_pairs.extend((w,'cpu-nuts-spawn_chains','end_to_end_workflow') for w in workflows if w!='cpu-nuts-spawn_chains')
    return [dict(left=a+'@'+str(b),right=c+'@'+str(b),kind=kind) for b in budgets for a,c,kind in method_pairs]


def summarize_model(rows,reference,*,name,protocol,allocation,output):
    """All planned repetitions retained; partial models are explicitly blocked."""
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    primary=[t for t in protocol['tasks'] if t['model']==name]
    probes=[p for p in allocation['probes'] if p['model']==name]
    expected={t['id'] for t in primary}|{p['id'] for p in probes}
    byid={r['task']['id']:r for r in rows}
    if len(byid)!=len(rows) or set(byid)!=expected:raise ValueError('Every model task and selected probe must appear exactly once')
    for task in primary:
        if byid[task['id']]['task']!=dict(task,protocol_sha256=protocol['protocol_sha256'],artifact_kind='posterior'):
            raise ValueError('Main scalar task differs from frozen protocol')
    primary_byid={t['id']:t for t in primary}
    for probe in probes:
        task=dict(primary_byid[probe['primary_task_id']],id=probe['id'],
                  protocol_sha256=protocol['protocol_sha256'],artifact_kind='cache_measurement')
        if byid[probe['id']]['task']!=task:raise ValueError('Cache scalar task differs from frozen allocation')
    if not primary or not probes:raise ValueError('Declared model requires main tasks and selected cache probes')
    n=len(reference['names'])
    if not n or any(len(reference[k])!=n for k in ('means','kinds','mcse')):
        raise ValueError('Reference function frame differs')
    main=[byid[t['id']] for t in primary];cache=[byid[p['id']] for p in probes]
    summary=dict(model=name,main_planned=len(main),cache_planned=len(cache),
        main_dispositions=dict(Counter(r['disposition'] for r in main)),cache_dispositions=dict(Counter(r['disposition'] for r in cache)),
        main_outcomes=dict(Counter(r.get('outcome') or 'unknown_evidence' for r in main)),
        cache_outcomes=dict(Counter(r.get('outcome') or 'unknown_evidence' for r in cache)),
        main_statistics='unavailable_evidence',cache_statistics='unavailable_evidence',
        reference=reference,reference_uncertainty_propagated=False,formal_inference_complete=False)
    atomic_json(output/'task-frame.json',rows)
    if protocol['scope_kind']!='formal_inference':
        summary.update(main_statistics='technical_descriptive_only',cache_statistics='technical_descriptive_only')
        atomic_json(output/'SUMMARY.json',summary);return summary
    ids=tuple(str(x) for x in sorted({t['replicate'] for t in primary}));budgets=sorted({t['budget'] for t in primary})
    workflows=sorted({t['workflow'] for t in primary});pairs=comparisons(workflows,budgets)
    pairs_arg=[(p['left'],p['right']) for p in pairs]
    atomic_json(output/'comparisons.json',dict(pairs=pairs,interval_coverage='pointwise; no familywise correction or general method superiority claim'))
    if all(r['disposition']=='analyzed' for r in main):
        mapping={}
        for row in main:
            task=row['task'];label=task['workflow']+'@'+str(task['budget']);rep=str(task['replicate'])
            if row['means'] is not None and (row['outcome']!='valid' or row['function_status']!='completed' or
                    row['names']!=reference['names'] or len(row['means'])!=n):raise ValueError('Function eligibility/reference names differ')
            mapping.setdefault(label,{})[rep]=row
        if set(mapping)!={w+'@'+str(b) for w in workflows for b in budgets} or any(set(r)!=set(ids) for r in mapping.values()):
            raise ValueError('Complete paired main repetition frame required')
        plan=create_plan(protocol['identity'],name,ids);save_plan(plan,output/'main-resampling')
        costs={label:{r:row['costs'] for r,row in values.items()} for label,values in mapping.items()}
        cost_complete=all(c is not None for values in costs.values() for c in values.values())
        if cost_complete:save_report(output/'costs.json',analyze_task_costs(plan,costs,pairs_arg))
        summary['cost_statistics']='completed' if cost_complete else 'unavailable_call_ledger'
        for j,function in enumerate(reference['names']):
            estimates={label:{r:None if row['means'] is None else row['means'][j] for r,row in values.items()} for label,values in mapping.items()}
            ref=dict(kind=reference['kinds'][j],value=reference['means'][j],mcse=reference['mcse'][j])
            result=analyze_error_costs(plan,costs,estimates,ref,pairs_arg) if cost_complete else dict(error=analyze_function(plan,estimates,ref,pairs_arg),costs=None)
            result.update(function=function,reference=ref,comparison_kinds=pairs)
            save_report(output/f'function-{j}.json',result)
        summary.update(main_statistics='completed',planned_repetitions=len(ids),resampling=plan.receipt())
    if all(r['disposition']=='analyzed' for r in cache):
        bindings={};observations={}
        for row in cache:
            item=row['cache'];pid=row['task']['id'];bindings[pid]=item['binding']
            observations[pid]=dict(item['observation'],task_outcome=row['outcome'])
        plan=create_cache_plan(allocation,protocol['tasks'],name);save_plan(plan,output/'cache-resampling')
        save_report(output/'cache-costs.json',analyze_cache_probes(allocation,protocol['tasks'],plan,bindings,observations))
        summary.update(cache_statistics='completed',cache_resampling=plan.receipt())
    atomic_json(output/'SUMMARY.json',summary)
    return summary


def run(delivery,index,analysis,output):
    output=Path(output).resolve();analysis=Path(analysis).resolve();evidence=EvidenceIndex(delivery,index)
    try:
        if (output.exists() or output.is_relative_to(evidence.delivery) or evidence.delivery.is_relative_to(output) or
                output.is_relative_to(analysis) or analysis.is_relative_to(output) or
                output.is_relative_to(evidence.directory) or evidence.directory.is_relative_to(output)):
            raise ValueError('Fresh statistics output separate from evidence and analysis required')
        frame=FrozenFrame(evidence);refs=reference_contract(evidence,frame)
        output.mkdir(parents=True);atomic_json(output/'reference-contract.json',refs)
        # Store compact projections by model; no trajectory is loaded here.
        paths={name:output/(name+'.frame.ndjson') for name in refs}
        with __import__('contextlib').ExitStack() as stack:
            streams={n:stack.enter_context(p.open('x')) for n,p in paths.items()}
            for row in checked_rows(analysis,frame,evidence):
                streams[row['task']['model']].write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')
        reports=[]
        for name,path in paths.items():
            rows=[json.loads(line) for line in path.read_text().splitlines()]
            reports.append(summarize_model(rows,refs[name],name=name,protocol=frame.protocol,
                allocation=frame.design['cache_allocation'],output=output/name))
        result=dict(frame=frame.receipt(),models=reports,raw_arrays_replayed_during_summary=False,
            diagnostics_recomputed_during_summary=False,analyzer_sha256=file_hash(__file__),
            analysis_identity_sha256=file_hash(analysis/'identity.json'),new_independent_repetitions=0,
            formal_inference_complete=False,figures_and_paper_not_generated=True)
        atomic_json(output/'SUMMARY.json',result)
        atomic_json(output/'SHA256.json',output_inventory(output))
        return result
    finally:evidence.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('delivery','index','analysis','output'):p.add_argument('--'+name,type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args())),indent=2))
