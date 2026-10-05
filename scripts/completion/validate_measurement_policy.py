"""Planning-only full-grid allocation and bounded retained-evidence I/O checks.

No MCMC or R computation. The transfer fixture is a local filesystem copy,
not a network measurement. Existing cached executor outputs remain unchanged.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from batch_contract import create_tasks,WORKFLOWS
from batch_cost_ledger import BatchCostLedger,read_batch_costs
from formal_measurement_plan import create_measurement_plan,validate_measurement_plan,summarize_probe
from formal_runtime import atomic_json,file_hash,fingerprint
ROOT=Path(__file__).resolve().parents[2]


def inside(root,name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe evidence member')
    result=(root/p).resolve()
    if root.resolve() not in result.parents:raise ValueError('Evidence escaped source root')
    return result


def run(bundle,output,host_lock):
    bundle,output,host_lock=map(lambda p:Path(p).resolve(),(bundle,output,host_lock))
    if output.exists() or bundle in output.parents:raise ValueError('New output outside retained evidence required')
    sources=['scripts/completion/'+n+'.py' for n in ('formal_measurement_plan','batch_cost_ledger','validate_measurement_policy')]
    import hashlib
    for name in sources:
        if file_hash(ROOT/name)!=hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest():
            raise ValueError('Commit measurement source before validation')
    output.mkdir(parents=True)
    old=json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    dims={t['name']:t['dimension'] for t in old['targets']}
    identity='windows-formal-measurement-draft-v0.2-planning-only'
    groups=[dict(models=list(dims),replicates=list(range(128)),budgets=[256,1024,4096,16384],workflows=list(WORKFLOWS))]
    tasks=create_tasks(identity,groups)
    plan=create_measurement_plan(identity,tasks)
    validate_measurement_plan(plan,tasks)
    if len(tasks)!=41472 or len(plan['probes'])!=9216:raise ValueError('Declared draft grid differs')
    atomic_json(output/'primary-grid.json',dict(identity=identity,groups=groups,tasks=tasks,execution_authorized=False))
    atomic_json(output/'cache-allocation.json',plan)
    logical=sum(4*(512+p['budget'])*(dims[p['model']]*8+1)*(1+p['prepared_replays']) for p in plan['probes'])
    design=dict(identity='measurement-policy-technical-mac-v1',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_files={name:file_hash(ROOT/name) for name in sources},
        dependency_manifest_sha256=file_hash(bundle/'MANIFEST.json'),
        scope='No new inference; full-grid draft allocation plus local copy/archive/verification of retained cached evidence',
        primary_tasks=len(tasks),probes=len(plan['probes']),executor_calls=plan['total_executor_calls'],
        additional_cached_path_and_accept_logical_bytes=logical,
        planning_only=True,formal_protocol_frozen=False,native_Windows_measured=False,new_MCMC_fits=0)
    atomic_json(output/'design.json',design)
    spec=dict(study_identity=design['identity'],design_sha256=fingerprint(design),operations=[
        dict(id='prepare-retained-input',stage='input_preparation'),dict(id='archive',stage='archive'),
        dict(id='local-copy',stage='transfer'),dict(id='verify-local-copy',stage='verification')])
    ledger=BatchCostLedger(output/'batch-costs',spec,host_lock)
    source_hashes=json.loads((bundle/'MANIFEST.json').read_text());workspace=output/'retained-records'
    selected=sorted((bundle/'run/cached').glob('*/attempt-0001/execution-*.json'))
    if len(selected)!=16:raise ValueError('Expected four retained MH probes with four calls each')
    def prepare():
        for name,h in source_hashes.items():
            if file_hash(inside(bundle,name))!=h:raise ValueError('Original evidence changed: '+name)
        workspace.mkdir();manifest={}
        for path in selected:
            record=json.loads(path.read_text());raw=inside(path.parent,record['actual_array_file'])
            if file_hash(raw)!=record['actual_array_sha256']:raise ValueError('Retained array hash differs')
            for original in (path,raw):
                relative=original.relative_to(bundle/'run/cached');dst=workspace/relative
                dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,dst)
                manifest[relative.as_posix()]=file_hash(dst)
        atomic_json(workspace/'MANIFEST.json',manifest)
        return dict(source_files_verified=len(source_hashes),copied_files=len(manifest),manifest_sha256=file_hash(workspace/'MANIFEST.json'),
                    scope='Verify existing source hashes and copy retained outputs; no scientific random inputs generated')
    prepared=ledger.run('prepare-retained-input',prepare)
    archive=output/'retained-records.tar'
    def pack():
        with tarfile.open(archive,'w') as tar:
            for p in sorted(workspace.rglob('*')):
                if p.is_file():tar.add(p,arcname=p.relative_to(workspace).as_posix(),recursive=False)
        return dict(bytes=archive.stat().st_size,sha256=file_hash(archive))
    packed=ledger.run('archive',pack)
    local=output/'local-transport';local.mkdir()
    def transfer():
        shutil.copy2(archive,local/archive.name)
        return dict(bytes=(local/archive.name).stat().st_size,transport='local filesystem copy only; not network transmission')
    ledger.run('local-copy',transfer)
    def verify():
        path=local/archive.name
        if file_hash(path)!=packed['result']['sha256']:raise ValueError('Archive changed during local copy')
        with tarfile.open(path) as tar:
            manifest=json.load(tar.extractfile('MANIFEST.json'));names=[m.name for m in tar.getmembers()]
            if len(set(names))!=len(names) or set(names)!=set(manifest)|{'MANIFEST.json'}:raise ValueError('Archive inventory differs')
            for m in tar.getmembers():
                if not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts:raise ValueError('Unsafe archived evidence')
                if m.name in manifest and hashlib.sha256(tar.extractfile(m).read()).hexdigest()!=manifest[m.name]:raise ValueError('Archived member differs')
        return dict(files_verified=len(names),sha256=file_hash(path))
    ledger.run('verify-local-copy',verify)
    costs=read_batch_costs(output/'batch-costs');atomic_json(output/'batch-cost-summary.json',costs)
    # Re-reduce already numerically audited frozen evidence; no sampler calls.
    reductions=[]
    for task in sorted(workspace.iterdir()):
        if not task.is_dir():continue
        records=[json.loads((task/'attempt-0001'/f'execution-{i}.json').read_text()) for i in range(4)]
        reductions.append(summarize_probe(dict(id=task.name,primary_task_id=task.name,initial_calls=1,prepared_replays=3),records,
            expected_tape_sha256=records[0]['tape_sha256'],expected_target_id=records[0]['target_id'],expected_config=records[0]['config']))
    atomic_json(output/'retained-probe-summary.json',reductions)
    shutil.copytree(output/'batch-costs',output/'relocated-costs')
    relocated=read_batch_costs(output/'relocated-costs')
    if relocated!=costs:raise ValueError('Relocated overhead ledger differs')
    summary=dict(design=design,allocation_sha256=plan['allocation_sha256'],selected_repetitions_per_model={m:sum(len(s['selected_replicates']) for s in plan['strata'] if s['model']==m) for m in dims},
        primary_grid_sha256=plan['primary_grid_sha256'],source_assets_verified=prepared['result']['source_files_verified'],
        retained_probe_count=len(reductions),retained_executor_records=16,
        all_retained_probes_numerically_valid=all(r['all_executions_valid'] for r in reductions),
        complete_batch_cost_seconds=costs['complete_seconds'],batch_cost_stages=costs['by_stage'],
        relocated_ledger_equal=True,statistical_repetitions_added=0,executor_calls_actually_run=0,
        note='Draft allocation and technical I/O receipt only. Timings on this Mac do not estimate Windows study time; inputs for final formal identity are not generated.')
    atomic_json(output/'summary.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bundle','output','host-lock'):p.add_argument('--'+name,type=Path,required=True)
    run(**vars(p.parse_args()))
