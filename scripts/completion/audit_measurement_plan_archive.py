"""Rebuild saved cache allocation and batch-cost reductions after relocation.

Read only. No input generation, MCMC, R, I/O remeasurement or process inference.
"""
import argparse
import json
from pathlib import Path
from batch_cost_ledger import read_batch_costs
from formal_measurement_plan import validate_measurement_plan,summarize_probe
from formal_runtime import file_hash,fingerprint


def audit(bundle):
    root=Path(bundle).resolve()
    manifest=json.loads((root/'MANIFEST.json').read_text())
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual!=set(manifest)|{'MANIFEST.json'}:raise ValueError('Archive inventory differs')
    for name,h in manifest.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or (root/p).is_symlink() or file_hash(root/p)!=h:
            raise ValueError('Archived asset differs: '+name)
    data=root/'validation'
    grid=json.loads((data/'primary-grid.json').read_text())
    plan=json.loads((data/'cache-allocation.json').read_text())
    validate_measurement_plan(plan,grid['tasks'])
    expected=json.loads((data/'summary.json').read_text())
    if (len(grid['tasks'])!=41472 or len(plan['probes'])!=9216 or plan['allocation_sha256']!=expected['allocation_sha256']
        or grid['execution_authorized'] or expected['executor_calls_actually_run']!=0):
        raise ValueError('Planning identity or non-execution scope differs')
    costs=read_batch_costs(data/'batch-costs')
    if costs!=json.loads((data/'batch-cost-summary.json').read_text()) or costs!=read_batch_costs(data/'relocated-costs'):
        raise ValueError('Saved batch costs differ')
    rebuilt=[];records=data/'retained-records'
    for task in sorted(records.iterdir()):
        if not task.is_dir():continue
        rows=[json.loads((task/'attempt-0001'/f'execution-{i}.json').read_text()) for i in range(4)]
        for row in rows:
            p=task/'attempt-0001'/row['actual_array_file']
            if file_hash(p)!=row['actual_array_sha256']:raise ValueError('Retained cached array differs')
        rebuilt.append(summarize_probe(dict(id=task.name,primary_task_id=task.name,initial_calls=1,prepared_replays=3),rows,
            expected_tape_sha256=rows[0]['tape_sha256'],expected_target_id=rows[0]['target_id'],expected_config=rows[0]['config']))
    if rebuilt!=json.loads((data/'retained-probe-summary.json').read_text()):raise ValueError('Cached reduction differs')
    return dict(verified_files=len(manifest),planned_primary_tasks=len(grid['tasks']),planned_probes=len(plan['probes']),
        allocation_sha256=plan['allocation_sha256'],batch_costs_exact=True,retained_probes_exact=len(rebuilt),
        retained_records_exact=4*len(rebuilt),new_MCMC_fits=0,new_timing_measurements=0,
        source_scope='Retained numerical validity receipts and arrays checked by hash, not a repeated independent NumPy audit')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True)
    print(json.dumps(audit(p.parse_args().bundle),indent=2))
