"""Full frozen native frame -> recoverable, per-task receiver analysis.

This is a read-only receiver, never a sampler/Windows launcher. Every planned
task has a row; absent evidence cannot become not_run or a sampler failure.
"""
import argparse
from collections import Counter
import importlib.metadata
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'scripts/analysis')]
from formal_archive import EvidenceIndex,build_index
from formal_runtime import atomic_json,file_hash,fingerprint,host_lease
from formal_freeze import verify_sealed_study,relative_file
from formal_validation import verify_validation_bundle,validation_slots
from formal_execution import StudyDispatch
from formal_science import ScientificReader


class FrozenFrame:
    """Validate the original full design; preserve the finite gate's identity."""
    def __init__(self,index):
        self.index=index;marker=index.json('FROZEN.json')
        if marker['schema']=='formal-study-freeze-v1':
            _,self.protocol=verify_sealed_study(index.root)
            self.design=index.json('study-plan.json');catalog=index.json('catalog.json')
            self.dispatch=StudyDispatch(self.protocol,self.design['cache_allocation'],catalog)
            self.phases=tuple((b,p) for b in range(4) for p in ('main','cache'))
        elif marker['schema']=='formal-adapter-validation-freeze-v1':
            _,self.protocol,self.design,_=verify_validation_bundle(index.root)
            self.dispatch=None;self.phases=((0,'main'),(0,'cache'))
        elif marker['schema']=='compact-study-freeze-v1':
            from compact_freeze import verify as verify_compact
            from compact_execution import CompactDispatch
            _,self.protocol,self.design,_=verify_compact(index.root)
            self.dispatch=CompactDispatch(self.protocol,self.design,index.root/'source')
            self.phases=self.dispatch.phases
        else:raise ValueError('Unsupported frozen native analysis frame')
        if index.json('protocol.json')!=self.protocol:raise ValueError('Indexed protocol differs from validated freeze')
        self.identity=self.protocol['identity'];self.scope=self.protocol['scope_kind']
        self.counts=dict(main=len(self.protocol['tasks']),cache=len(self.design['cache_allocation']['probes']))
        expected={(b,p,t['id']) for b,p in self.phases for t in self.tasks(b,p)}
        observed=set(index.db.execute('SELECT DISTINCT batch,phase,task_id FROM histories'))
        if not observed<=expected:raise ValueError('Archive contains undeclared native task histories')

    def phase_root(self,batch,phase):
        if (batch,phase) not in self.phases:raise ValueError('Undeclared analysis phase')
        return f'formal-runs/batch-{batch:02d}/{phase}' if self.dispatch else phase

    def tasks(self,batch,phase):
        if self.dispatch:return self.dispatch.tasks(batch,phase)
        return (s['task'] for s in validation_slots(self.protocol,phase))

    def slots(self):
        for batch,phase in self.phases:
            slots=self.dispatch.slots(batch,phase) if self.dispatch else validation_slots(self.protocol,phase)
            for position,slot in enumerate(slots,1):
                yield batch,phase,position,slot

    def receipt(self):
        return dict(identity=self.identity,scope=self.scope,protocol_sha256=self.protocol['protocol_sha256'],
            main_planned=self.counts['main'],cache_planned=self.counts['cache'],
            formal_scientific_repetitions_per_model=(self.design['formal_scientific_repetitions']
                if self.protocol.get('compact_execution_contract') else 128 if self.dispatch else 0),
            execution_contract=self.protocol.get('compact_execution_contract','historical-formal-v1'),
            analysis_can_authorize_sampling=False)


def analysis_environment(rscript,r_library):
    code='cat(jsonlite::toJSON(list(R=R.version.string,posterior=as.character(packageVersion("posterior")),jsonlite=as.character(packageVersion("jsonlite"))),auto_unbox=TRUE))'
    result=json.loads(subprocess.check_output([str(rscript),'--vanilla','-e',code],
        env=dict(os.environ,R_LIBS_USER=str(r_library)),text=True))
    return dict(python=sys.version,platform=sys.platform,
        packages={n:importlib.metadata.version(n) for n in ('numpy','scipy')},
        rscript=str(Path(rscript).resolve()),r_library=str(Path(r_library).resolve()),R=result)


def output_inventory(root):
    files={}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():raise ValueError('Analysis outputs may not be symlinked')
        if path.is_file() and path!=Path(root)/'RECEIPT.json':files[path.relative_to(root).as_posix()]=file_hash(path)
    return files


def analyzer_sources():
    # Scalar reports/plots are downstream consumers. Editing them must not
    # silently reuse changed readers, or force unchanged numerical replay.
    names=('formal_analyze.py','formal_archive.py','formal_science.py')
    return {'scripts/analysis/'+name:file_hash(ROOT/'scripts/analysis'/name) for name in names}


class AnalysisStore:
    """One transaction per completed analysis; interrupted output is retained."""
    def __init__(self,root,binding,resume=False):
        self.root=Path(root).resolve()
        if self.root.exists():
            if not resume:raise FileExistsError('Explicit analysis resume required')
            if (not (self.root/'analysis.sqlite3').is_file() or
                    json.loads((self.root/'identity.json').read_text())!=binding):
                raise ValueError('Analysis identity/environment changed or setup is incomplete')
        else:
            if resume:raise ValueError('Cannot resume absent analysis')
            self.root.mkdir(parents=True);atomic_json(self.root/'identity.json',binding)
        self.db=sqlite3.connect(self.root/'analysis.sqlite3')
        self.db.execute('PRAGMA synchronous=FULL');self.db.execute('PRAGMA cache_size=-2048')
        self.db.execute('CREATE TABLE IF NOT EXISTS results (id TEXT PRIMARY KEY, task TEXT NOT NULL, disposition TEXT NOT NULL, receipt TEXT NOT NULL, sha256 TEXT NOT NULL)')
        self.db.commit()

    def close(self):self.db.close()

    def prior(self,task,inputs,index):
        row=self.db.execute('SELECT task,disposition,receipt,sha256 FROM results WHERE id=?',(task['id'],)).fetchone()
        folder=self.root/'tasks'/task['id']
        if row is None:
            if folder.exists():
                # Never assume a partially written analysis stopped or overwrite
                # it. A new analysis identity/directory can retain this attempt.
                raise ValueError('Uncommitted analysis directory retained; inspect original process and output before retry')
            return None
        if json.loads(row[0])!=task:raise ValueError('Analysis task identity changed')
        receipt=relative_file(self.root,row[2])
        if file_hash(receipt)!=row[3]:raise ValueError('Analysis receipt changed')
        saved=json.loads(receipt.read_text())
        if saved['task']!=task or saved['inputs']!=inputs or saved['disposition']!=row[1]:
            raise ValueError('Prior analysis input frame differs')
        index.verify_local_files(inputs['manifest'])
        if saved['files']!=output_inventory(folder):raise ValueError('Analysis files changed or missing')
        return saved

    def finish(self,task,inputs,disposition,result):
        folder=self.root/'tasks'/task['id'];folder.mkdir(parents=True,exist_ok=True)
        path=folder/'RECEIPT.json'
        if path.exists():raise FileExistsError('Do not overwrite a completed analysis receipt')
        atomic_json(folder/'FRAME.json',result)
        receipt=dict(task=task,inputs=inputs,disposition=disposition,files=output_inventory(folder),
            row='FRAME.json',new_sampler_calls=0,new_independent_repetitions=0)
        atomic_json(path,receipt)
        with self.db:
            self.db.execute('INSERT INTO results VALUES (?,?,?,?,?)',
                (task['id'],json.dumps(task,sort_keys=True),disposition,path.relative_to(self.root).as_posix(),file_hash(path)))
        return receipt


def analyze_frame(index,frame,reader,output,binding,*,resume=False):
    """Use the same task-reader seam for actual or explicitly labelled fixtures.

    CLI callers always supply FrozenFrame and ScientificReader. Tests inject
    artificial frames/readers only for orchestration, not scientific evidence.
    """
    output=Path(output).resolve()
    if (output.is_relative_to(index.delivery) or index.delivery.is_relative_to(output) or
            output.is_relative_to(index.directory) or index.directory.is_relative_to(output)):
        raise ValueError('Analysis must be separate from immutable delivery and index')
    counts=Counter();new=0;reused=0;expected={};errors=0
    with host_lease(output.with_name(output.name+'.analysis.lock'),'read-only full-frame analysis'):
        store=AnalysisStore(output,binding,resume=resume)
        try:
            for batch,phase,position,slot in frame.slots():
                task=slot['task'];identifier=task['id']
                if identifier in expected:raise ValueError('Aliased task in analysis frame')
                expected[identifier]=task
                try:inputs=index.task_evidence(task,phase,frame.phase_root(batch,phase))
                except (ValueError,KeyError) as exc:
                    # Evidence contradictions are receiver errors, not new
                    # numerical failures or evidence that a task never ran.
                    inputs=dict(evidence_status='conflicting_evidence',manifest={},error=type(exc).__name__+': '+str(exc))
                old=store.prior(task,inputs,index)
                if old is not None:
                    disposition=old['disposition'];reused+=1
                else:
                    common=dict(task=task,batch=batch,phase=phase,scheduled_position=position,
                        outcome=None,means=None,names=None,diagnostics=None,costs=None,
                        function_status='unavailable',scientific_summary_available=False)
                    if inputs['evidence_status']!='available':
                        disposition=inputs['evidence_status'];result=dict(common,evidence=inputs)
                    else:
                        try:
                            science=reader.read(slot,history_export=inputs['history_export'],directory=inputs['directory'],
                                ledger=inputs['ledger'],manifest=inputs['manifest'],output=output/'tasks'/identifier/'science')
                        except (ValueError,KeyError,AssertionError,RuntimeError,OSError,MemoryError) as exc:
                            disposition='reader_error';result=dict(common,error=type(exc).__name__+': '+str(exc),
                                original_outcome_reclassified=False)
                            failure=output/'tasks'/identifier/'science/READER-FAILURE.json'
                            if failure.exists():
                                receipt=json.loads(failure.read_text());result.update(
                                    recorded_outcome=receipt['recorded_outcome'],costs=receipt['history']['costs'])
                        else:
                            disposition='analyzed';result=dict(common,outcome=science['outcome'],means=science['means'],names=science['names'],
                                function_status=science['function_status'],diagnostics=science['diagnostics'],costs=science['history']['costs'],
                                cache=science.get('cache'),nuts=science.get('nuts'),
                                scientific_summary_available=True,scientific_result='science/result.json')
                    store.finish(task,inputs,disposition,result);new+=1
                counts[(phase,disposition)]+=1;errors+=disposition in ('reader_error','conflicting_evidence')
                if (new+reused)%100==0:
                    print(json.dumps(dict(visited=new+reused,new_analyses=new,reused_analyses=reused,last_task=identifier)),flush=True)
            saved=set(x[0] for x in store.db.execute('SELECT id FROM results'))
            if saved!=set(expected):raise ValueError('Stored analyses differ from complete planned frame')
            totals={p:sum(v for (phase,_),v in counts.items() if phase==p) for p in ('main','cache')}
            if totals!=frame.counts:raise ValueError('Analysis did not visit every declared task')
            summary=dict(frame=frame.receipt(),visited=len(expected),new_analyses=new,reused_analyses=reused,
                counts={p:{d:v for (phase,d),v in counts.items() if phase==p} for p in ('main','cache')},
                every_planned_task_represented=True,evidence_complete=not errors and not any(d=='evidence_gap' for _,d in counts),
                new_sampler_calls=0,new_independent_repetitions=0,formal_inference_complete=False,
                summary_is_not_convergence_or_performance_inference=True)
            # Output summary is replaceable receiver bookkeeping. Task receipts
            # remain immutable and are checked before each explicit resume.
            atomic_json(output/'SUMMARY.json',summary)
            return summary
        finally:store.close()


def run(delivery,index,output,rscript,r_library,*,cross_platform=False,resume=False):
    evidence=EvidenceIndex(delivery,index)
    try:
        frame=FrozenFrame(evidence)
        env=analysis_environment(rscript,r_library)
        sources=analyzer_sources()
        binding=dict(schema='formal-frame-analysis-v1',index=evidence.receipt,frame=frame.receipt(),
            analyzer_sources=sources,receiver_environment=env,cross_platform=cross_platform,
            scientific_source_files=frame.protocol['source_files'])
        reader=ScientificReader(evidence.root,frame.protocol['source_files'],rscript=rscript,r_library=r_library,cross_platform=cross_platform)
        return analyze_frame(evidence,frame,reader,output,binding,resume=resume)
    finally:evidence.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('index');p.add_argument('--delivery',type=Path,required=True);p.add_argument('--bundle-relative',required=True)
    p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    p=commands.add_parser('run')
    for name in ('delivery','index','output','rscript','r-library'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cross-platform',action='store_true');p.add_argument('--resume',action='store_true')
    args=vars(parser.parse_args());command=args.pop('command')
    print(json.dumps((build_index if command=='index' else run)(**args),indent=2))
